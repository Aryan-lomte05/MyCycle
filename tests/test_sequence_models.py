"""Sequence model tests (package A4): scaling, masking, training reduces loss, determinism."""
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sim.common import FEATURES  # noqa: E402
from sim.sequence_models import (  # noqa: E402
    CNN1DPredictor, ExponentialSmoothingPredictor, FeatureScaler, GRUPredictor, LSTMPredictor,
    build_supervised, masked_mse, pad_batch, to_model_inputs, train_predictor, user_arrays,
)

N = len(FEATURES)


def test_scaler_fit_ignores_nan_and_transform_round_trips():
    rng = np.random.default_rng(0)
    arr = rng.normal(5, 2, size=(200, N))
    arr[arr < -100] = np.nan  # no-op, just exercises the NaN path shape-wise
    arr[0, 0] = np.nan
    scaler = FeatureScaler.fit(arr)
    assert not np.isnan(scaler.mean).any()
    std = scaler.transform(arr)
    back = scaler.inverse(std)
    ok = ~np.isnan(arr)
    np.testing.assert_allclose(back[ok], arr[ok], atol=1e-6)


def test_scaler_serialization_round_trip():
    scaler = FeatureScaler(np.arange(N, dtype=float), np.ones(N))
    back = FeatureScaler.from_dict(scaler.to_dict())
    np.testing.assert_array_equal(back.mean, scaler.mean)
    np.testing.assert_array_equal(back.sd, scaler.sd)


def test_user_arrays_extracts_features_in_order_with_missing_as_nan():
    logs = [{"cycle_index": 1, "cycle_length_days": 29, "flow": 1, "pain": 2,
            "symptoms": {s: 0 for s in FEATURES[3:]}}]
    logs[0]["symptoms"]["acne"] = None
    arr = user_arrays(logs)
    assert arr.shape == (1, N)
    assert arr[0, 0] == 29 and arr[0, 1] == 1 and arr[0, 2] == 2
    assert np.isnan(arr[0, FEATURES.index("acne")])


def test_to_model_inputs_zeroes_missing_and_sets_mask():
    raw = np.array([[29.0, np.nan, 2.0]])
    scaler = FeatureScaler(np.array([29.0, 1.0, 2.0]), np.array([1.0, 1.0, 1.0]))
    std, mask = to_model_inputs(raw, scaler)
    assert mask.tolist() == [[1.0, 0.0, 1.0]]
    assert std[0, 1] == 0.0  # missing -> exactly 0, not NaN
    assert std[0, 0] == pytest.approx(0.0)


def test_pad_batch_pads_and_marks_mask():
    users = [np.zeros((3, N)), np.zeros((5, N))]
    values, mask = pad_batch(users)
    assert values.shape == (2, 5, N)
    assert mask[0, 3:].sum() == 0 and mask[0, :3].sum() == 3 * N
    assert mask[1].sum() == 5 * N


def test_build_supervised_shapes_and_no_leakage_into_loss_mask():
    rng = np.random.default_rng(1)
    raws = [rng.normal(size=(6, N)), rng.normal(size=(4, N))]
    scaler = FeatureScaler.fit(np.concatenate(raws))
    batch = build_supervised(raws, scaler)
    assert batch["x"].shape == (2, 5, 2 * N)  # max_T - 1 = 5
    assert batch["y"].shape == (2, 5, N)
    # user 2 has only 3 target steps (cycles 2..4); the padded tail must be masked out
    assert batch["loss_mask"][1, 3:].sum() == 0
    assert batch["loss_mask"][1, :3].sum() == 3 * N


def test_masked_mse_ignores_masked_entries():
    pred = torch.zeros(1, 2, 3)
    target = torch.tensor([[[10.0, 10.0, 10.0], [1.0, 1.0, 1.0]]])
    mask = torch.tensor([[[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]])
    loss = masked_mse(pred, target, mask)
    assert loss.item() == pytest.approx(1.0)  # only the second (all-observed) row counts: (0-1)^2


@pytest.mark.parametrize("cls", [GRUPredictor, LSTMPredictor, CNN1DPredictor])
def test_training_reduces_masked_loss(cls):
    rng = np.random.default_rng(2)
    raws = [np.tile(rng.normal(size=(1, N)), (12, 1)) + rng.normal(scale=0.05, size=(12, N)) for _ in range(20)]
    scaler = FeatureScaler.fit(np.concatenate(raws))
    batch = build_supervised(raws, scaler)
    model = cls(hidden_size=8) if cls is not CNN1DPredictor else cls(channels=8)
    initial = masked_mse(model(batch["x"]), batch["y"], batch["loss_mask"]).item()
    train_predictor(model, batch, epochs=60, seed=0)
    final = masked_mse(model(batch["x"]), batch["y"], batch["loss_mask"]).item()
    assert final < initial


def test_training_is_deterministic_with_seed():
    # torch.manual_seed must be set before the model is constructed, not just before training,
    # since layer initialization also draws from the global RNG. sim/gru.py does this at each seed.
    rng = np.random.default_rng(3)
    raws = [rng.normal(size=(8, N)) for _ in range(10)]
    scaler = FeatureScaler.fit(np.concatenate(raws))
    batch = build_supervised(raws, scaler)
    torch.manual_seed(7)
    m1 = GRUPredictor(hidden_size=8)
    torch.manual_seed(7)
    m2 = GRUPredictor(hidden_size=8)
    train_predictor(m1, batch, epochs=10, seed=7)
    train_predictor(m2, batch, epochs=10, seed=7)
    for p1, p2 in zip(m1.parameters(), m2.parameters()):
        torch.testing.assert_close(p1, p2)


def test_cnn1d_is_causal():
    """Changing a future timestep must not change the prediction at an earlier timestep."""
    torch.manual_seed(0)
    model = CNN1DPredictor(channels=8)
    x = torch.randn(1, 10, 2 * N)
    out1 = model(x).detach()
    x2 = x.clone()
    x2[0, 8:] = torch.randn(2, 2 * N)  # perturb only the last two timesteps
    out2 = model(x2).detach()
    torch.testing.assert_close(out1[0, :8], out2[0, :8])


def test_exponential_smoothing_predicts_zero_before_first_observation_then_tracks_level():
    scaler = FeatureScaler(np.zeros(N), np.ones(N))
    raw = np.zeros((4, N))
    raw[0] = np.nan
    raw[1:, 0] = [10.0, 10.0, 10.0]
    pred = ExponentialSmoothingPredictor(alpha=0.5).predict_sequence(raw, scaler)
    assert pred.shape == (3, N)
    assert pred[0, 0] == 0.0  # nothing observed yet at cycle 1, so predict the neutral standardized mean
    assert pred[1, 0] == pytest.approx(10.0)  # exactly one observation so far: level = that observation
    assert pred[2, 0] == pytest.approx(10.0)  # constant input: smoothed level stays at 10
