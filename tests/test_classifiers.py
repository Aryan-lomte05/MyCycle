"""Classifier pipeline tests (package A3): leakage removal, CV protocol, metrics, schema conformance.

Skipped on a clone without the raw PCOS file (data/raw/PCOS_data_without_infertility.xlsx), since
CLAUDE.md keeps raw data out of the repo. Run `python data/download_pcos.py` first.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sim.pcos_data import CATEGORICAL_COLS, FEATURE_SETS, LEAKAGE_COLS, RAW_XLSX, feature_matrix, load  # noqa: E402

pytestmark = pytest.mark.skipif(not RAW_XLSX.exists(), reason="raw PCOS data not present, run data/download_pcos.py")

from sim.classifiers import (  # noqa: E402
    bootstrap_ci, brier_score, cross_validate, paired_bootstrap_pvalue, rows_for_feature_set,
    sens_at_spec, spec_at_sens,
)

SCHEMA = json.loads((ROOT / "results/summary.schema.json").read_text(encoding="utf-8"))
CLASSIFIER_ITEM = Draft7Validator(SCHEMA["properties"]["classifiers"]["items"])


@pytest.fixture(scope="module")
def df():
    return load()


# data and leakage -----------------------------------------------------------------------------

def test_loaded_shape_and_label_balance(df):
    assert len(df) == 541
    assert set(df["pcos"].unique()) == {0, 1}
    assert df["pcos"].sum() == 177


def test_leakage_columns_absent_from_deployable_sets():
    for fs in ["symptom_only", "symptom_plus_vitals"]:
        assert not set(FEATURE_SETS[fs]) & set(LEAKAGE_COLS)
    assert set(LEAKAGE_COLS) <= set(FEATURE_SETS["with_labs_reference"])


def test_feature_sets_are_nested():
    s1, s2, s3 = FEATURE_SETS["symptom_only"], FEATURE_SETS["symptom_plus_vitals"], FEATURE_SETS["with_labs_reference"]
    assert set(s1) <= set(s2) <= set(s3)


def test_feature_matrix_shapes(df):
    X, y, num, cat = feature_matrix(df, "symptom_only")
    assert len(X) == len(y) == 541
    assert set(num) | set(cat) == set(X.columns)
    assert set(cat) <= CATEGORICAL_COLS


# metrics ----------------------------------------------------------------------------------------

def test_sens_spec_hand_example():
    # perfectly alternating ranks (P,N,P,N,...) by descending score: every second negative outranks
    # the positive just below it, giving a clean ROC staircase with no ties to disambiguate.
    y = np.array([1, 0, 1, 0, 1, 0, 1, 0, 1, 0])
    p = np.array([1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1])
    assert sens_at_spec(y, p, 0.7) == pytest.approx(0.4, abs=1e-6)
    assert spec_at_sens(y, p, 0.7) == pytest.approx(0.4, abs=1e-6)


def test_brier_score_hand_example():
    y = np.array([1, 0])
    p = np.array([0.8, 0.3])
    assert brier_score(y, p) == pytest.approx((0.2**2 + 0.3**2) / 2)


def test_bootstrap_ci_contains_point_estimate():
    rng = np.random.default_rng(0)
    y = (rng.random(200) < 0.3).astype(int)
    p = np.clip(y * 0.6 + rng.random(200) * 0.4, 0, 1)
    from sklearn.metrics import roc_auc_score
    point = roc_auc_score(y, p)
    lo, hi = bootstrap_ci(y, p, roc_auc_score, seed=1, n_boot=200)
    assert lo <= point <= hi


def test_paired_bootstrap_pvalue_in_range():
    rng = np.random.default_rng(0)
    y = (rng.random(200) < 0.3).astype(int)
    p1 = np.clip(y * 0.6 + rng.random(200) * 0.4, 0, 1)
    p2 = rng.random(200)  # near-random second model
    pval = paired_bootstrap_pvalue(y, p1, p2, seed=1, n_boot=300)
    assert 0.0 <= pval <= 1.0


# CV protocol --------------------------------------------------------------------------------------

def test_cross_validate_deterministic_with_seed(df):
    X, y, num, cat = feature_matrix(df, "symptom_only")
    a = cross_validate(X, y, num, cat, "logistic_regression", n_folds=5, seeds=[0])
    b = cross_validate(X, y, num, cat, "logistic_regression", n_folds=5, seeds=[0])
    np.testing.assert_array_equal(a["oof_prob"], b["oof_prob"])


def test_cross_validate_every_row_gets_exactly_one_oof_prediction_per_seed(df):
    X, y, num, cat = feature_matrix(df, "symptom_only")
    out = cross_validate(X, y, num, cat, "logistic_regression", n_folds=5, seeds=[0, 1])
    assert out["oof_prob"].shape == (2, len(y))
    assert not np.isnan(out["oof_prob"]).any()


def test_auc_mean_and_ci_describe_the_same_estimator(df):
    # auc_mean must be the AUC of the same seed-averaged probability the CI bootstraps, so ci_low
    # and ci_high always straddle it, even for a high-variance model with a wide per-seed AUC spread.
    X, y, num, cat = feature_matrix(df, "symptom_only")
    out = cross_validate(X, y, num, cat, "mlp", n_folds=5, seeds=[0, 1, 2])
    from sklearn.metrics import roc_auc_score
    assert out["auc_mean"] == pytest.approx(roc_auc_score(y.to_numpy(), out["mean_prob"]))
    assert out["auc_ci_low"] <= out["auc_mean"] <= out["auc_ci_high"]


def test_metrics_in_valid_ranges(df):
    X, y, num, cat = feature_matrix(df, "symptom_only")
    out = cross_validate(X, y, num, cat, "logistic_regression", n_folds=5, seeds=[0, 1])
    for seed_auc in out["seed_aucs"]:
        assert 0.0 <= seed_auc <= 1.0
    assert 0.0 <= out["sens_at_90spec"] <= 1.0
    assert 0.0 <= out["spec_at_90sens"] <= 1.0
    assert 0.0 <= out["brier"] <= 1.0


def test_row_conforms_to_schema(df):
    X, y, num, cat = feature_matrix(df, "symptom_only")
    out = cross_validate(X, y, num, cat, "naive_bayes", n_folds=5, seeds=[0])
    row = {
        "dataset": "kaggle_pcos", "model": "naive_bayes", "feature_set": "symptom_only",
        "auc_mean": out["auc_mean"], "auc_ci_low": out["auc_ci_low"], "auc_ci_high": out["auc_ci_high"],
        "sens_at_90spec": out["sens_at_90spec"], "spec_at_90sens": out["spec_at_90sens"],
        "brier": out["brier"], "n_folds": 5,
    }
    CLASSIFIER_ITEM.validate(row)
    assert 0 <= row["auc_ci_low"] <= row["auc_mean"] <= row["auc_ci_high"] <= 1


def test_symptom_only_auc_beats_chance(df):
    # sanity: acne, hair growth, hair loss, skin darkening, cycle irregularity are known PCOS correlates,
    # so even the weakest reasonable model should clear a coin flip by a wide margin on this data
    X, y, num, cat = feature_matrix(df, "symptom_only")
    out = cross_validate(X, y, num, cat, "random_forest", n_folds=5, seeds=[0, 1])
    assert out["auc_mean"] > 0.7


def test_with_labs_reference_beats_symptom_only(df):
    # ablation sanity: adding labs and ultrasound should not hurt an AUC-oriented model on this data
    X1, y, num1, cat1 = feature_matrix(df, "symptom_only")
    X3, _, num3, cat3 = feature_matrix(df, "with_labs_reference")
    o1 = cross_validate(X1, y, num1, cat1, "random_forest", n_folds=5, seeds=[0, 1])
    o3 = cross_validate(X3, y, num3, cat3, "random_forest", n_folds=5, seeds=[0, 1])
    assert o3["auc_mean"] >= o1["auc_mean"] - 0.05  # allow small CV noise, but no big regression


def test_rows_for_feature_set_produces_one_row_per_model_and_a_comparison(df):
    rows, comparison, _ = rows_for_feature_set(df, "symptom_only", models=["logistic_regression", "naive_bayes"], seeds=[0])
    assert {r["model"] for r in rows} == {"logistic_regression", "naive_bayes"}
    for row in rows:
        CLASSIFIER_ITEM.validate(row)
    assert comparison["model_a"] in {"logistic_regression", "naive_bayes"}
    assert comparison["model_b"] in {"logistic_regression", "naive_bayes"}
    assert comparison["model_a"] != comparison["model_b"]
    assert 0.0 <= comparison["p_value"] <= 1.0
