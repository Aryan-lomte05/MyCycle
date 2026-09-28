"""NFHS-5 loader tests (package A3 extension): WHO threshold label, pregnancy exclusion, leakage removal.

Skipped on a clone without the raw file (data/raw/nfhs5/Final.csv). Run data/download_nfhs5.py first.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sim.nfhs_data import RAW_CSV, WHO_ANEMIA_CUTOFF_NONPREGNANT, feature_matrix, feature_sets, load, stratified_subsample  # noqa: E402

pytestmark = pytest.mark.skipif(not RAW_CSV.exists(), reason="raw NFHS-5 data not present, run data/download_nfhs5.py")


@pytest.fixture(scope="module")
def df():
    return load()


def test_pregnant_respondents_excluded(df):
    assert "Curr_Preg" not in df.columns
    assert len(df) < 136136
    assert len(df) > 120000  # pregnancy prevalence in the raw file is a small minority


def test_anemia_label_matches_who_cutoff_exactly(df):
    # recomputed independently from the raw column still on df is not available (Hg_levelAdjusted
    # was dropped by ALWAYS_DROP only from feature sets, not from df itself)
    assert (df["anemia"] == (df["Hg_levelAdjusted"] < WHO_ANEMIA_CUTOFF_NONPREGNANT).astype(int)).all()
    rate = df["anemia"].mean()
    assert 0.3 < rate < 0.7  # anemia in Indian women of reproductive age is common, not rare


def test_thyroid_label_is_rare_and_binary(df):
    assert set(df["Thyroid"].unique()) == {0, 1}
    assert 0.005 < df["Thyroid"].mean() < 0.05


def test_bmi_engineered_and_plausible(df):
    assert df["bmi"].between(10, 60).mean() > 0.99


@pytest.mark.parametrize("task", ["anemia", "thyroid"])
def test_lab_and_imaging_columns_never_in_any_feature_set(df, task):
    fs = feature_sets(df, task)
    for cols in fs.values():
        assert "Hg_levelAdjusted" not in cols
        assert "Anemia_level" not in cols
        assert "ultrasound" not in cols
        assert "anemia" not in cols
        assert LABEL_at(task) not in cols


def LABEL_at(task):
    return {"anemia": "anemia", "thyroid": "Thyroid"}[task]


def test_other_tasks_self_reported_label_kept_as_feature(df):
    # Thyroid (self-report) is allowed as a feature for the anemia task; anemia (lab-derived) is not
    # kept as a feature for the thyroid task, since it is itself lab-derived (see ALWAYS_DROP).
    assert "Thyroid" in feature_sets(df, "anemia")["symptom_only"]
    assert "anemia" not in feature_sets(df, "thyroid")["symptom_only"]


def test_vitals_only_in_symptom_plus_vitals(df):
    for task in ["anemia", "thyroid"]:
        fs = feature_sets(df, task)
        assert not set(fs["symptom_only"]) & {"Resp_weight", "Resp_height", "bmi"}
        assert {"Resp_weight", "Resp_height", "bmi"} <= set(fs["symptom_plus_vitals"])
        assert set(fs["symptom_only"]) <= set(fs["symptom_plus_vitals"])


def test_feature_matrix_shapes(df):
    X, y, num, cat = feature_matrix(df, "anemia", "symptom_only")
    assert len(X) == len(y) == len(df)
    assert cat == ["State"]
    assert set(num) | set(cat) == set(X.columns)


def test_stratified_subsample_size_and_seed_determinism(df):
    a = stratified_subsample(df, "anemia", 2000, seed=0)
    b = stratified_subsample(df, "anemia", 2000, seed=0)
    c = stratified_subsample(df, "anemia", 2000, seed=1)
    assert abs(len(a) - 2000) < 50
    pd_testing_equal(a, b)
    assert not a["Hg_levelAdjusted"].equals(c["Hg_levelAdjusted"]) or not a.index.equals(c.index)


def pd_testing_equal(a, b):
    import pandas as pd
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))


def test_stratified_subsample_preserves_label_rate_roughly(df):
    full_rate = df["Thyroid"].mean()
    sub = stratified_subsample(df, "thyroid", 5000, seed=0)
    assert abs(sub["Thyroid"].mean() - full_rate) < 0.01
