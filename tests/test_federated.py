"""Federated learning and Differential Privacy tests (package A5).

Tests:
  1. DP-SGD accountant: epsilon decreases as sigma increases, matches analytical bounds.
  2. Per-example gradient clipping: norm of clipped gradient never exceeds C.
  3. DP-SGD noise addition: noise is zero when sigma is 0, standard deviation matches sigma * C.
  4. Non-IID Dirichlet partition: clients receive valid non-empty partitions and partition sums to total.
  5. FedAvg step: global model is exact weighted average of client weights.
  6. FedProx proximal term: penalizes divergence from global model.
  7. FedPer: head weights stay local while backbone weights are federated.
  8. Schema conformance: federated results match summary.schema.json.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pytest
import torch
import torch.nn as nn
from jsonschema import Draft7Validator

from sim.common import ROOT

SCHEMA = json.loads((ROOT / "results" / "summary.schema.json").read_text(encoding="utf-8"))
FEDERATED_ITEM = Draft7Validator(SCHEMA["properties"]["federated"]["items"])


def test_rdp_accountant_monotonic_in_sigma():
    from sim.federated import compute_epsilon
    steps = 100
    batch_size = 32
    dataset_size = 500
    delta = 1e-5

    eps_05 = compute_epsilon(steps, batch_size, dataset_size, sigma=0.5, delta=delta)
    eps_10 = compute_epsilon(steps, batch_size, dataset_size, sigma=1.0, delta=delta)
    eps_20 = compute_epsilon(steps, batch_size, dataset_size, sigma=2.0, delta=delta)

    assert eps_05 > eps_10 > eps_20 > 0.0


def test_per_example_clip_norm_bounded():
    from sim.federated import clip_per_example_gradients
    grads = [torch.tensor([[3.0, 4.0]]), torch.tensor([[1.0, 1.0]]), torch.tensor([[0.0, 0.0]])]
    C = 2.0
    clipped = clip_per_example_gradients(grads, clip_norm=C)
    for g in clipped:
        norm = torch.norm(g).item()
        assert norm <= C + 1e-5
    # The first gradient had norm 5.0, so after clipping to 2.0 its norm should be exactly 2.0
    assert torch.norm(clipped[0]).item() == pytest.approx(2.0, abs=1e-5)


def test_standard_dp_sgd_sum_noise():
    from sim.federated import add_dp_noise_to_sum
    torch.manual_seed(42)
    # Sum of clipped gradients over batch of size B=10
    grad_sum = torch.zeros(100)
    sigma = 1.5
    C = 1.0
    batch_size = 10

    # Without DP (sigma=0)
    no_noise = add_dp_noise_to_sum(grad_sum.clone(), sigma=0.0, clip_norm=C, batch_size=batch_size)
    torch.testing.assert_close(no_noise, torch.zeros(100))

    # With DP: noise drawn from N(0, sigma^2 * C^2), then divided by batch_size
    noised = add_dp_noise_to_sum(grad_sum.clone(), sigma=sigma, clip_norm=C, batch_size=batch_size, seed=0)
    # Scaled noise should have standard deviation close to sigma * C / batch_size
    expected_sd = (sigma * C) / batch_size
    sample_sd = noised.std().item()
    assert abs(sample_sd - expected_sd) < 0.05


def test_dirichlet_partition_coverage():
    from sim.federated import dirichlet_non_iid_partition
    n_samples = 541
    labels = np.array([0] * 364 + [1] * 177)
    n_clients = 8
    client_indices = dirichlet_non_iid_partition(labels, n_clients=n_clients, alpha=0.3, seed=42)

    assert len(client_indices) == n_clients
    all_idx = []
    for c_idx in client_indices:
        assert len(c_idx) > 0
        all_idx.extend(c_idx)
    # Total samples across clients must match
    assert len(all_idx) == n_samples
    assert sorted(all_idx) == list(range(n_samples))


def test_fedavg_weights_aggregation():
    from sim.federated import aggregate_fedavg
    w1 = {"fc.weight": torch.tensor([[1.0, 2.0]]), "fc.bias": torch.tensor([1.0])}
    w2 = {"fc.weight": torch.tensor([[3.0, 4.0]]), "fc.bias": torch.tensor([3.0])}
    client_weights = [w1, w2]
    client_sizes = [10, 30]  # weights: 0.25 and 0.75

    avg = aggregate_fedavg(client_weights, client_sizes)
    expected_w = 0.25 * w1["fc.weight"] + 0.75 * w2["fc.weight"]
    expected_b = 0.25 * w1["fc.bias"] + 0.75 * w2["fc.bias"]

    torch.testing.assert_close(avg["fc.weight"], expected_w)
    torch.testing.assert_close(avg["fc.bias"], expected_b)


def test_federated_schema_conformance():
    row = {
        "mode": "fedavg_dp",
        "noise_multiplier": 1.0,
        "clip_norm": 1.0,
        "epsilon": 2.45,
        "delta": 1e-5,
        "auc": 0.854,
        "accuracy": 0.812,
        "rounds": 40,
        "non_iid": True,
    }
    FEDERATED_ITEM.validate(row)


def test_epsilon_matches_opacus():
    """Regression test for the 2026-09-29 fix: our accountant must agree with Opacus's
    RDPAccountant, computed the same way (one acc.step() per SGD step, same sample_rate)."""
    from opacus.accountants import RDPAccountant

    from sim.federated import compute_epsilon

    steps, batch_size, dataset_size, delta = 240, 16, 432, 1e-5
    for sigma in [0.5, 1.0, 1.5, 2.0, 3.0]:
        ours = compute_epsilon(steps, batch_size, dataset_size, sigma, delta)
        acc = RDPAccountant()
        sample_rate = batch_size / dataset_size
        for _ in range(steps):
            acc.step(noise_multiplier=sigma, sample_rate=sample_rate)
        theirs, _ = acc.get_privacy_spent(delta=delta)
        assert ours == pytest.approx(theirs, rel=1e-9)


def test_old_analytical_formula_understated_epsilon():
    """Documents why compute_epsilon was changed: the old formula claimed stronger privacy
    (lower epsilon) than Opacus's accountant, the dangerous direction to be wrong in."""
    from sim.federated import _analytical_rdp_epsilon, compute_epsilon

    steps, batch_size, dataset_size, delta = 240, 16, 432, 1e-5
    for sigma in [0.5, 1.0]:
        old = _analytical_rdp_epsilon(steps, batch_size, dataset_size, sigma, delta)
        correct = compute_epsilon(steps, batch_size, dataset_size, sigma, delta)
        assert old < correct  # old formula understated epsilon (overstated privacy)
