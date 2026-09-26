"""Simulator tests (package A1): reproducibility, class mix, one test per drift type, splits, ranges."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sim.common import LABEL, SYMPTOMS  # noqa: E402
from sim.simulator import SimConfig, run, simulate, to_cycle_logs  # noqa: E402

N = 1000  # large enough for stable pooled checks, small enough to run in seconds


@pytest.fixture(scope="module")
def sim():
    cycles, users = simulate(SimConfig(n_users=N), seed=42)
    return cycles, users


def pre_post(cycles: pd.DataFrame, users: pd.DataFrame, drift: str, col: str):
    """Mean of col before onset and while the drift is active, per user."""
    ids = users.loc[users.drift_type == drift, "user_id"]
    sub = cycles[cycles.user_id.isin(ids)]
    pre = sub[sub.cycle_index < sub.onset_cycle].groupby("user_id")[col].mean()
    post = sub[sub.drift_active].groupby("user_id")[col].mean()
    return pre.astype(float), post.astype(float)


def symptom_rate(df: pd.DataFrame, cols) -> float:
    vals = df[list(cols)].astype(float)
    return float((vals > 0).sum().sum() / vals.notna().sum().sum())


# reproducibility -----------------------------------------------------------------------------

def test_same_seed_identical_and_different_seed_differs():
    a, ua = simulate(SimConfig(n_users=50), seed=42)
    b, ub = simulate(SimConfig(n_users=50), seed=42)
    c, _ = simulate(SimConfig(n_users=50), seed=43)
    pd.testing.assert_frame_equal(a, b)
    pd.testing.assert_frame_equal(ua, ub)
    assert not a["cycle_length_days"].equals(c["cycle_length_days"])


def test_cli_output_is_byte_identical(tmp_path):
    def digest(out: Path) -> dict:
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir())}

    run(seed=42, out=tmp_path / "a", config=SimConfig(n_users=60))
    run(seed=42, out=tmp_path / "b", config=SimConfig(n_users=60))
    da, db = digest(tmp_path / "a"), digest(tmp_path / "b")
    assert set(da) == {"train.parquet", "val.parquet", "test.parquet", "users.parquet", "meta.json"}
    assert da == db


def test_meta_is_labeled_and_logs_seed_commit_mix(tmp_path):
    run(seed=42, out=tmp_path, config=SimConfig(n_users=60))
    meta = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))["meta"]
    assert meta["simulated"] is True and meta["label"] == LABEL
    assert meta["seed"] == 42 and meta["git_commit"]
    assert meta["class_mix"] == {"none": 0.25, "pcos_pattern": 0.20, "anemia_pattern": 0.20,
                                 "thyroid_pattern": 0.20, "benign_shift": 0.15}


# population structure ------------------------------------------------------------------------

def test_class_mix_and_sequence_lengths(sim):
    cycles, users = sim
    counts = users.drift_type.value_counts().to_dict()
    assert counts == {"none": 250, "pcos_pattern": 200, "anemia_pattern": 200,
                      "thyroid_pattern": 200, "benign_shift": 150}
    n_per_user = cycles.groupby("user_id").size()
    assert n_per_user.min() >= 16 and n_per_user.max() <= 30
    onsets = users.loc[users.drift_type != "none", "onset_cycle"]
    assert onsets.min() >= 5 and onsets.max() <= 10
    assert users.loc[users.drift_type == "none", "onset_cycle"].isna().all()


def test_latent_baseline_ranges(sim):
    _, users = sim
    assert users.mu.between(21, 38).all()
    assert users.sigma.between(1.0, 3.0).all()
    assert abs(users.mu.mean() - 29) < 0.5


def test_splits_are_by_user_disjoint_and_stratified(sim):
    cycles, users = sim
    per_user = cycles.groupby("user_id").split.nunique()
    assert (per_user == 1).all()
    frac = users.groupby("drift_type").split.value_counts(normalize=True).unstack()
    assert np.allclose(frac["train"], 0.6, atol=0.02)
    assert np.allclose(frac["val"], 0.2, atol=0.02)
    assert np.allclose(frac["test"], 0.2, atol=0.02)


def test_values_within_contract_ranges_and_dates_consistent(sim):
    cycles, _ = sim
    assert cycles.cycle_length_days.dropna().between(10, 120).all()
    assert cycles.flow.dropna().between(0, 3).all()
    assert cycles.pain.dropna().between(0, 10).all()
    for s in SYMPTOMS:
        assert cycles[s].dropna().between(0, 3).all()
    one = cycles[cycles.user_id == cycles.user_id.iloc[0]]
    d = pd.to_datetime(one.start_date)
    gaps = d.diff().dt.days.iloc[1:].to_numpy()
    assert (gaps == one.true_length_days.iloc[:-1].to_numpy()).all()


def test_missing_rate_near_two_percent(sim):
    cycles, _ = sim
    cols = ["cycle_length_days", "flow", "pain", *SYMPTOMS]
    rate = cycles[cols].isna().to_numpy().mean()
    assert 0.015 < rate < 0.025


def test_exported_logs_match_contract():
    cycles, _ = simulate(SimConfig(n_users=20, missing_rate=0.0), seed=1)
    schema = Draft7Validator(json.loads((ROOT / "exports/cycle_log.schema.json").read_text(encoding="utf-8")))
    for uid, df in cycles.groupby("user_id"):
        logs = to_cycle_logs(df)
        assert [c["cycle_index"] for c in logs] == list(range(1, len(logs) + 1))
        for c in logs:
            schema.validate(c)


# one test per drift type ---------------------------------------------------------------------

def test_none_has_no_drift_and_stable_features(sim):
    cycles, users = sim
    ids = users.loc[users.drift_type == "none", "user_id"]
    sub = cycles[cycles.user_id.isin(ids)]
    assert not sub.drift_active.any()
    first, second = sub[sub.cycle_index <= 8], sub[sub.cycle_index > 8]
    assert abs(first.cycle_length_days.mean() - second.cycle_length_days.mean()) < 0.5
    assert abs(symptom_rate(first, SYMPTOMS) - symptom_rate(second, SYMPTOMS)) < 0.02


def test_pcos_longer_more_variable_skips_and_androgen_symptoms(sim):
    cycles, users = sim
    pre, post = pre_post(cycles, users, "pcos_pattern", "cycle_length_days")
    shift = post - pre
    assert shift.median() > 8
    assert (shift > 3).mean() > 0.95
    ids = users.loc[users.drift_type == "pcos_pattern", "user_id"]
    sub = cycles[cycles.user_id.isin(ids)]
    act, base = sub[sub.drift_active], sub[sub.cycle_index < sub.onset_cycle]
    assert 0.05 < act.skipped.mean() < 0.15
    assert (act.loc[act.skipped, "true_length_days"] > 45).all()
    assert not base.skipped.any()
    andro = ["acne", "excess_hair", "hair_loss"]
    assert symptom_rate(act, andro) > symptom_rate(base, andro) + 0.3
    within_act = act[~act.skipped].groupby("user_id").true_length_days.std().median()
    within_base = base.groupby("user_id").true_length_days.std().median()
    assert within_act > within_base


def test_anemia_heavier_flow_symptoms_length_unchanged(sim):
    cycles, users = sim
    pre, post = pre_post(cycles, users, "anemia_pattern", "flow")
    assert (post - pre).median() > 0.6
    pre_l, post_l = pre_post(cycles, users, "anemia_pattern", "cycle_length_days")
    assert abs((post_l - pre_l).median()) < 1.0
    ids = users.loc[users.drift_type == "anemia_pattern", "user_id"]
    sub = cycles[cycles.user_id.isin(ids)]
    act, base = sub[sub.drift_active], sub[sub.cycle_index < sub.onset_cycle]
    anem = ["fatigue", "dizziness", "pallor"]
    assert symptom_rate(act, anem) > symptom_rate(base, anem) + 0.3


def test_thyroid_shift_in_both_directions_with_symptoms(sim):
    cycles, users = sim
    pre, post = pre_post(cycles, users, "thyroid_pattern", "cycle_length_days")
    shift = post - pre
    th = users[users.drift_type == "thyroid_pattern"].set_index("user_id")
    shorter = th.index[th.length_shift < 0]
    longer = th.index[th.length_shift > 0]
    assert len(shorter) > 50 and len(longer) > 50
    assert (shift[shorter] < -2).mean() > 0.9
    assert (shift[longer] > 3).mean() > 0.9
    assert th.loc[shorter, "length_shift"].between(-8, -5).all()
    assert th.loc[longer, "length_shift"].between(6, 12).all()
    sub = cycles[cycles.user_id.isin(th.index)]
    act, base = sub[sub.drift_active], sub[sub.cycle_index < sub.onset_cycle]
    thy = ["fatigue", "weight_change", "mood"]
    assert symptom_rate(act, thy) > symptom_rate(base, thy) + 0.3


def test_benign_shift_is_short_and_returns_to_baseline(sim):
    cycles, users = sim
    ids = users.loc[users.drift_type == "benign_shift", "user_id"]
    sub = cycles[cycles.user_id.isin(ids)]
    n_active = sub.groupby("user_id").drift_active.sum()
    assert n_active.isin([1, 2]).all()
    pre = sub[sub.cycle_index < sub.onset_cycle].groupby("user_id").cycle_length_days.mean()
    after = sub[(sub.cycle_index >= sub.onset_cycle) & ~sub.drift_active].groupby("user_id").cycle_length_days.mean()
    during = sub[sub.drift_active].groupby("user_id").cycle_length_days.mean()
    assert abs((after - pre).median()) < 0.5
    assert ((during - pre).abs() > 3).mean() > 0.8
