"""Tests for the A4 orchestration (sim/gru.py): scoring alignment, tuning guard, personalization, ONNX parity."""
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import pytest
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sim.gru import personalization_experiment, raw_scores, replay, tune_threshold  # noqa: E402
from sim.sequence_models import FeatureScaler, GRUPredictor  # noqa: E402
from sim.simulator import SimConfig, simulate  # noqa: E402


@pytest.fixture(scope="module")
def tiny_sim():
    cycles, users = simulate(SimConfig(n_users=60, min_cycles=10, max_cycles=14), seed=11)
    return cycles, users


def user_raw_dict(cycles):
    from sim.gru import per_user_raw
    return per_user_raw(cycles)


def test_raw_scores_start_at_cycle_2_and_cover_the_rest(tiny_sim):
    cycles, _ = tiny_sim
    train = cycles[cycles.split == "train"]
    raws = user_raw_dict(train)
    scaler = FeatureScaler.fit(np.concatenate(list(raws.values())))
    torch.manual_seed(0)
    model = GRUPredictor(hidden_size=4)
    out = raw_scores(model, raws, scaler)
    for uid, rows in out.items():
        n = len(raws[uid])
        assert [r[0] for r in rows] == list(range(2, n + 1))
        assert all(r[1] >= 0 for r in rows)  # score is an RMSE, never negative


def test_replay_flags_are_valid_and_cycle_one_is_always_none(tiny_sim):
    cycles, _ = tiny_sim
    val = cycles[cycles.split == "val"]
    raws = user_raw_dict(val)
    scaler = FeatureScaler.fit(np.concatenate(list(raws.values())))
    torch.manual_seed(0)
    model = GRUPredictor(hidden_size=4)
    raw = raw_scores(model, raws, scaler)
    df = replay(val, raw, threshold=2.0)
    assert set(df["flag"].unique()) <= {"none", "irregularity", "pcos_pattern", "anemia_pattern", "thyroid_pattern"}
    assert (df[df.cycle_index == 1]["flag"] == "none").all()


def test_tune_threshold_refuses_non_val_split(tiny_sim):
    cycles, _ = tiny_sim
    test = cycles[cycles.split == "test"]
    raws = user_raw_dict(test)
    scaler = FeatureScaler.fit(np.concatenate(list(raws.values())))
    model = GRUPredictor(hidden_size=4)
    raw = raw_scores(model, raws, scaler)
    with pytest.raises(ValueError):
        tune_threshold(test, raw)


def test_personalization_never_mutates_the_shared_model(tiny_sim):
    # personalization_experiment deep-copies the model per user and fine-tunes only the copy's head
    # (sim/gru.py); the shared model passed in must come out bit-identical for the next architecture
    # or user to reuse.
    cycles, _ = tiny_sim
    train = cycles[cycles.split == "train"]
    test = cycles[cycles.split == "test"]
    train_raw = user_raw_dict(train)
    scaler = FeatureScaler.fit(np.concatenate(list(train_raw.values())))
    torch.manual_seed(0)
    model = GRUPredictor(hidden_size=4)
    before_state = {k: v.clone() for k, v in model.state_dict().items()}
    test_raw = user_raw_dict(test)
    users = list(test_raw)[:5]
    before, after = personalization_experiment(model, scaler, test_raw, threshold=2.0, users=users, seed=0)
    assert len(before) > 0 and len(after) > 0
    assert {u for u, _, _ in before} <= set(users)
    for k, v in model.state_dict().items():
        torch.testing.assert_close(v, before_state[k])


def test_personalization_flags_cover_every_cycle_including_cycle_one(tiny_sim):
    # regression: with_truth() (sim/detection_eval.py) rejects any (user, cycle) missing from the
    # flags list; personalization_experiment must emit cycle 1 too, not just the scored cycles.
    cycles, _ = tiny_sim
    train = cycles[cycles.split == "train"]
    test = cycles[cycles.split == "test"]
    train_raw = user_raw_dict(train)
    scaler = FeatureScaler.fit(np.concatenate(list(train_raw.values())))
    torch.manual_seed(0)
    model = GRUPredictor(hidden_size=4)
    test_raw = user_raw_dict(test)
    users = list(test_raw)[:5]
    before, after = personalization_experiment(model, scaler, test_raw, threshold=2.0, users=users, seed=0)
    from sim.detection_eval import with_truth
    subset = test[test.user_id.isin(users)]
    with_truth(subset, before)  # raises if any (user, cycle) pair is missing
    with_truth(subset, after)


def test_personalization_is_deterministic_with_seed(tiny_sim):
    cycles, _ = tiny_sim
    train = cycles[cycles.split == "train"]
    test = cycles[cycles.split == "test"]
    train_raw = user_raw_dict(train)
    scaler = FeatureScaler.fit(np.concatenate(list(train_raw.values())))
    torch.manual_seed(0)
    model = GRUPredictor(hidden_size=4)
    test_raw = user_raw_dict(test)
    users = list(test_raw)[:5]
    b1, a1 = personalization_experiment(model, scaler, test_raw, threshold=2.0, users=users, seed=3)
    b2, a2 = personalization_experiment(model, scaler, test_raw, threshold=2.0, users=users, seed=3)
    assert a1 == a2


def test_onnx_export_matches_pytorch_within_tolerance(tmp_path):
    torch.manual_seed(0)
    model = GRUPredictor(hidden_size=8)
    model.eval()
    onnx_path = tmp_path / "gru.onnx"
    dummy = torch.zeros(1, 5, model.rnn.input_size)
    torch.onnx.export(model, dummy, str(onnx_path), input_names=["sequence"], output_names=["prediction"],
                      dynamic_axes={"sequence": {1: "cycles"}, "prediction": {1: "cycles"}}, opset_version=17,
                      dynamo=False)
    rng = np.random.default_rng(0)
    x = rng.normal(size=(1, 7, model.rnn.input_size)).astype(np.float32)
    with torch.no_grad():
        torch_out = model(torch.from_numpy(x)).numpy()
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    onnx_out = sess.run(None, {"sequence": x})[0]
    assert np.max(np.abs(torch_out - onnx_out)) < 1e-4
