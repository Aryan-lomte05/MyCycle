"""Federated learning and Differential Privacy experiments (package A5).

Implements:
  1. Centralized baseline (no FL, pooled training).
  2. Local-only baseline (no FL, clients train in isolation).
  3. FedAvg (McMahan et al., 2017) under IID and non-IID partitions.
  4. FedProx (Li et al., 2020) with proximal term mu for non-IID heterogeneity.
  5. FedPer (Arivazhagan et al., 2019) with personalized local head and federated backbone.
  6. FedAvg + DP-SGD (Abadi et al., 2016): standard DP-SGD form with per-example gradient clipping
     and Gaussian noise added to the sum of clipped gradients, converted to (epsilon, delta)-DP
     via a Renyi DP (RDP) accountant.

Enforces non-negotiable rules:
  - Standard DP-SGD form: noise on the sum of clipped gradients, then divide by batch size.
  - No em dashes anywhere.
  - All outputs carry the simulated / preliminary label.
  - Results conform to results/summary.schema.json.

Run: python -m sim.federated
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from sim.common import LABEL, ROOT, base_meta
from sim.pcos_data import feature_matrix, load

DELTA = 1e-5
SIGMA_LIST = [0.5, 1.0, 1.5, 2.0, 3.0]
CLIP_NORM = 1.0
ROUNDS = 40
LOCAL_EPOCHS = 2
BATCH_SIZE = 16
N_CLIENTS = 8
DIRICHLET_ALPHA = 0.3
LR = 0.02


def _analytical_rdp_epsilon(steps: int, batch_size: int, dataset_size: int, sigma: float, delta: float) -> float:
    """The simplified analytical RDP bound this file used before 2026-09-29. Kept only for the
    disagreement check in tests/test_federated.py; never used to report a result.

    This bound (RDP(alpha) = alpha * q^2 / (2 * sigma^2)) is the RDP of the PLAIN Gaussian
    mechanism, scaled by q^2. It is not the tight subsampled-Gaussian RDP bound (Mironov 2017,
    Wang et al. 2019 give a log-sum-exp expression with binomial terms, not this simple form), and
    it under-states epsilon (claims stronger privacy than actually holds) by roughly 1.5x to 4x at
    the noise multipliers used here, confirmed against Opacus's RDPAccountant (see the module
    docstring and tests/test_federated.py::test_epsilon_matches_opacus). Replaced by compute_epsilon.
    """
    if sigma <= 0.0:
        return float("inf")
    q = min(1.0, batch_size / max(1, dataset_size))
    orders = [1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0, 24.0, 32.0, 64.0]
    eps_list = []
    for alpha in orders:
        rdp_step = (alpha * (q ** 2)) / (2.0 * (sigma ** 2))
        total_rdp = steps * rdp_step
        eps = total_rdp + math.log(1.0 / delta) / (alpha - 1.0)
        eps_list.append(eps)
    return float(min(eps_list))


def compute_epsilon(steps: int, batch_size: int, dataset_size: int, sigma: float, delta: float = DELTA) -> float:
    """(epsilon, delta)-DP for the subsampled Gaussian mechanism (Abadi et al. 2016 moments
    accountant / Mironov 2017 RDP), computed with Opacus's RDPAccountant rather than a homegrown
    formula. aryan.md A5 asks that our own accountant be validated against Opacus or TensorFlow
    Privacy "once and record agreement"; ours did not agree (see _analytical_rdp_epsilon's
    docstring and docs/CHANGELOG.md, 2026-09-29), so this now calls Opacus directly instead of
    trusting an unverified approximation. sample_rate = batch_size / dataset_size, one `step()` per
    SGD step (not per round): `steps` must be the total number of gradient steps across all rounds.
    """
    if sigma <= 0.0:
        return float("inf")
    from opacus.accountants import RDPAccountant

    acc = RDPAccountant()
    sample_rate = min(1.0, batch_size / max(1, dataset_size))
    for _ in range(steps):
        acc.step(noise_multiplier=sigma, sample_rate=sample_rate)
    eps, _ = acc.get_privacy_spent(delta=delta)
    return float(eps)


def clip_per_example_gradients(grads: list[torch.Tensor], clip_norm: float = CLIP_NORM) -> list[torch.Tensor]:
    """Per-example gradient clipping to maximum L2 norm C."""
    out = []
    for g in grads:
        norm = torch.norm(g)
        if norm > clip_norm:
            out.append(g * (clip_norm / norm))
        else:
            out.append(g.clone())
    return out


def add_dp_noise_to_sum(grad_sum: torch.Tensor, sigma: float, clip_norm: float, batch_size: int, seed: int | None = None) -> torch.Tensor:
    """Add Gaussian noise N(0, sigma^2 * C^2 I) to the SUM of clipped gradients, then divide by batch size.

    This matches the standard DP-SGD form (Abadi et al., 2016, faculty feedback item 8):
      g_tilde = (1 / B) * ( sum_{i=1}^B clip(g_i, C) + N(0, sigma^2 * C^2 * I) )
    """
    if sigma <= 0.0:
        return grad_sum / batch_size
    if seed is not None:
        torch.manual_seed(seed)
    noise = torch.randn_like(grad_sum) * (sigma * clip_norm)
    return (grad_sum + noise) / batch_size


def dirichlet_non_iid_partition(labels: np.ndarray, n_clients: int = N_CLIENTS, alpha: float = DIRICHLET_ALPHA, seed: int = 42) -> list[list[int]]:
    """Partition indices across clients using a Dirichlet distribution over classes (label skew)."""
    rng = np.random.default_rng(seed)
    n_classes = len(np.unique(labels))
    client_indices: list[list[int]] = [[] for _ in range(n_clients)]

    for c in range(n_classes):
        c_idx = np.where(labels == c)[0]
        rng.shuffle(c_idx)
        # Draw Dirichlet proportions for this class
        props = rng.dirichlet(np.repeat(alpha, n_clients))
        # Ensure at least 1 sample per client if possible
        counts = np.round(props * len(c_idx)).astype(int)
        diff = len(c_idx) - counts.sum()
        if diff != 0:
            counts[rng.choice(n_clients, abs(diff))] += np.sign(diff)
        counts = np.maximum(0, counts)
        if counts.sum() != len(c_idx):
            counts[-1] += len(c_idx) - counts.sum()

        start = 0
        for i, count in enumerate(counts):
            client_indices[i].extend(c_idx[start:start + count].tolist())
            start += count

    # If any client ended up empty, reassign one sample from the largest client
    for i in range(n_clients):
        if len(client_indices[i]) == 0:
            largest = max(range(n_clients), key=lambda j: len(client_indices[j]))
            client_indices[i].append(client_indices[largest].pop())

    return client_indices


class PCOSClassifierNet(nn.Module):
    """Backbone MLP for tabular symptom-only PCOS classification."""

    def __init__(self, in_features: int, hidden_dim: int = 16):
        super().__init__()
        # Backbone (shared in FedAvg and FedPer)
        self.backbone = nn.Sequential(
            nn.Linear(in_features, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 8),
            nn.ReLU(),
        )
        # Classification head (kept local in FedPer)
        self.head = nn.Linear(8, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.backbone(x)
        return self.head(h).squeeze(-1)


def aggregate_fedavg(client_weights: list[dict[str, torch.Tensor]], client_sizes: list[int]) -> dict[str, torch.Tensor]:
    """Weighted average of model parameters proportional to client dataset sizes."""
    total_size = sum(client_sizes)
    avg_weights = {}
    for key in client_weights[0].keys():
        avg_weights[key] = sum(
            w[key].float() * (size / total_size) for w, size in zip(client_weights, client_sizes)
        )
    return avg_weights


def evaluate_model(model: nn.Module, X: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Evaluate AUC and accuracy on a given dataset."""
    model.eval()
    with torch.no_grad():
        x_t = torch.from_numpy(X).float()
        logits = model(x_t)
        probs = torch.sigmoid(logits).numpy()
    preds = (probs >= 0.5).astype(int)
    auc = float(roc_auc_score(y, probs)) if len(np.unique(y)) > 1 else 0.5
    acc = float(accuracy_score(y, preds))
    return round(auc, 4), round(acc, 4)


def train_client_step(
    model: nn.Module,
    X_client: np.ndarray,
    y_client: np.ndarray,
    global_model: nn.Module | None = None,
    mu: float = 0.0,
    dp_sigma: float = 0.0,
    clip_norm: float = CLIP_NORM,
    epochs: int = LOCAL_EPOCHS,
    batch_size: int = BATCH_SIZE,
    lr: float = LR,
    frozen_keys: set[str] | None = None,
    seed: int = 0,
) -> dict[str, torch.Tensor]:
    """Train client locally with optional Proximal term or DP-SGD."""
    model.train()
    dataset = TensorDataset(torch.from_numpy(X_client).float(), torch.from_numpy(y_client).float())
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    criterion = nn.BCEWithLogitsLoss(reduction="none" if dp_sigma > 0 else "mean")

    for epoch in range(epochs):
        for b_idx, (bx, by) in enumerate(loader):
            if dp_sigma > 0.0:
                # Per-example gradient clipping
                model.zero_grad()
                preds = model(bx)
                losses = criterion(preds, by)
                per_param_clipped_sum = {k: torch.zeros_like(p) for k, p in model.named_parameters() if p.requires_grad}
                # Compute gradient for each sample individually
                for i in range(len(bx)):
                    model.zero_grad()
                    sample_loss = losses[i]
                    sample_loss.backward(retain_graph=(i < len(bx) - 1))
                    # Clip sample gradients
                    sample_norm = torch.sqrt(sum((p.grad ** 2).sum() for p in model.parameters() if p.grad is not None))
                    clip_factor = max(1.0, (sample_norm / clip_norm).item())
                    for k, p in model.named_parameters():
                        if p.grad is not None:
                            per_param_clipped_sum[k] += p.grad / clip_factor

                # Add Gaussian noise to the sum of clipped gradients, then divide by batch size
                with torch.no_grad():
                    for k, p in model.named_parameters():
                        if k in per_param_clipped_sum:
                            noisy_avg_grad = add_dp_noise_to_sum(
                                per_param_clipped_sum[k], sigma=dp_sigma, clip_norm=clip_norm, batch_size=len(bx)
                            )
                            p.data -= lr * noisy_avg_grad
            else:
                # Standard mini-batch SGD with optional FedProx penalty
                preds = model(bx)
                loss = criterion(preds, by)
                if mu > 0.0 and global_model is not None:
                    prox = sum(((p - gp) ** 2).sum() for p, gp in zip(model.parameters(), global_model.parameters()))
                    loss = loss + (mu / 2.0) * prox
                model.zero_grad()
                loss.backward()
                with torch.no_grad():
                    for k, p in model.named_parameters():
                        if frozen_keys is None or k not in frozen_keys:
                            if p.grad is not None:
                                p.data -= lr * p.grad

    return {k: v.clone() for k, v in model.state_dict().items()}


def run_federated_experiments(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    seed: int = 42,
    n_rounds: int = ROUNDS,
) -> tuple[list[dict], dict[str, list[float]]]:
    """Run centralized, local_only, FedAvg, FedProx, FedPer, and FedAvg+DP configurations."""
    torch.manual_seed(seed)
    in_features = X_train.shape[1]
    results: list[dict] = []
    curves: dict[str, list[float]] = {}

    # 1. Centralized baseline
    central_model = PCOSClassifierNet(in_features)
    for _ in range(n_rounds * LOCAL_EPOCHS):
        train_client_step(central_model, X_train, y_train, epochs=1, lr=LR)
    auc_c, acc_c = evaluate_model(central_model, X_test, y_test)
    results.append({
        "mode": "centralized", "noise_multiplier": 0.0, "clip_norm": CLIP_NORM,
        "epsilon": None, "delta": DELTA, "auc": auc_c, "accuracy": acc_c,
        "rounds": n_rounds, "non_iid": False,
    })

    # Partitions for federated clients
    iid_partition = [np.array_split(np.random.default_rng(seed).permutation(len(X_train)), N_CLIENTS)[i].tolist() for i in range(N_CLIENTS)]
    non_iid_partition = dirichlet_non_iid_partition(y_train, n_clients=N_CLIENTS, alpha=DIRICHLET_ALPHA, seed=seed)

    # 2. Local only baseline (non-IID)
    local_aucs, local_accs = [], []
    for c_idx in non_iid_partition:
        loc_model = PCOSClassifierNet(in_features)
        train_client_step(loc_model, X_train[c_idx], y_train[c_idx], epochs=n_rounds * LOCAL_EPOCHS, lr=LR)
        auc_l, acc_l = evaluate_model(loc_model, X_test, y_test)
        local_aucs.append(auc_l)
        local_accs.append(acc_l)
    results.append({
        "mode": "local_only", "noise_multiplier": 0.0, "clip_norm": CLIP_NORM,
        "epsilon": None, "delta": DELTA, "auc": round(float(np.mean(local_aucs)), 4),
        "accuracy": round(float(np.mean(local_accs)), 4), "rounds": n_rounds, "non_iid": True,
    })

    # 3. FedAvg (IID and non-IID)
    for partition, is_non_iid, tag in [(iid_partition, False, "fedavg_iid"), (non_iid_partition, True, "fedavg")]:
        global_model = PCOSClassifierNet(in_features)
        client_sizes = [len(idx) for idx in partition]
        round_aucs = []
        for r in range(n_rounds):
            client_weights = []
            for c_idx in partition:
                client_m = copy.deepcopy(global_model)
                w = train_client_step(client_m, X_train[c_idx], y_train[c_idx], epochs=LOCAL_EPOCHS, lr=LR, seed=seed + r)
                client_weights.append(w)
            global_model.load_state_dict(aggregate_fedavg(client_weights, client_sizes))
            auc_r, _ = evaluate_model(global_model, X_test, y_test)
            round_aucs.append(auc_r)
        curves[tag] = round_aucs
        results.append({
            "mode": "fedavg", "noise_multiplier": 0.0, "clip_norm": CLIP_NORM,
            "epsilon": None, "delta": DELTA, "auc": round_aucs[-1],
            "accuracy": evaluate_model(global_model, X_test, y_test)[1],
            "rounds": n_rounds, "non_iid": is_non_iid,
        })

    # 4. FedProx (non-IID)
    global_model = PCOSClassifierNet(in_features)
    client_sizes = [len(idx) for idx in non_iid_partition]
    round_aucs_prox = []
    for r in range(n_rounds):
        client_weights = []
        for c_idx in non_iid_partition:
            client_m = copy.deepcopy(global_model)
            w = train_client_step(client_m, X_train[c_idx], y_train[c_idx], global_model=global_model, mu=0.01, epochs=LOCAL_EPOCHS, lr=LR, seed=seed + r)
            client_weights.append(w)
        global_model.load_state_dict(aggregate_fedavg(client_weights, client_sizes))
        auc_r, _ = evaluate_model(global_model, X_test, y_test)
        round_aucs_prox.append(auc_r)
    curves["fedprox"] = round_aucs_prox
    results.append({
        "mode": "fedprox", "noise_multiplier": 0.0, "clip_norm": CLIP_NORM,
        "epsilon": None, "delta": DELTA, "auc": round_aucs_prox[-1],
        "accuracy": evaluate_model(global_model, X_test, y_test)[1],
        "rounds": n_rounds, "non_iid": True,
    })

    # 5. FedPer (Personalized local head, federated backbone)
    client_models = [PCOSClassifierNet(in_features) for _ in range(N_CLIENTS)]
    client_sizes = [len(idx) for idx in non_iid_partition]
    round_aucs_per = []
    backbone_keys = [k for k in client_models[0].state_dict().keys() if k.startswith("backbone")]
    for r in range(n_rounds):
        # Local updates
        for i, c_idx in enumerate(non_iid_partition):
            train_client_step(client_models[i], X_train[c_idx], y_train[c_idx], epochs=LOCAL_EPOCHS, lr=LR, seed=seed + r)
        # Server aggregates only backbone
        backbone_weights = [{k: m.state_dict()[k] for k in backbone_keys} for m in client_models]
        avg_backbone = aggregate_fedavg(backbone_weights, client_sizes)
        # Broadcast backbone to all clients while preserving their local head
        for m in client_models:
            state = m.state_dict()
            state.update(avg_backbone)
            m.load_state_dict(state)
        # Average AUC across personalized client models on test set
        test_aucs = [evaluate_model(m, X_test, y_test)[0] for m in client_models]
        round_aucs_per.append(round(float(np.mean(test_aucs)), 4))
    curves["fedper"] = round_aucs_per
    results.append({
        "mode": "fedper", "noise_multiplier": 0.0, "clip_norm": CLIP_NORM,
        "epsilon": None, "delta": DELTA, "auc": round_aucs_per[-1],
        "accuracy": round(float(np.mean([evaluate_model(m, X_test, y_test)[1] for m in client_models])), 4),
        "rounds": n_rounds, "non_iid": True,
    })

    # 6. FedAvg + DP-SGD over sigma sweep
    for sigma in SIGMA_LIST:
        global_model = PCOSClassifierNet(in_features)
        client_sizes = [len(idx) for idx in non_iid_partition]
        total_steps = n_rounds * LOCAL_EPOCHS * (len(X_train) // (N_CLIENTS * BATCH_SIZE))
        eps = compute_epsilon(steps=total_steps, batch_size=BATCH_SIZE, dataset_size=len(X_train), sigma=sigma, delta=DELTA)
        round_aucs_dp = []
        for r in range(n_rounds):
            client_weights = []
            for c_idx in non_iid_partition:
                client_m = copy.deepcopy(global_model)
                w = train_client_step(
                    client_m, X_train[c_idx], y_train[c_idx], dp_sigma=sigma, clip_norm=CLIP_NORM,
                    epochs=LOCAL_EPOCHS, lr=LR, seed=seed + r
                )
                client_weights.append(w)
            global_model.load_state_dict(aggregate_fedavg(client_weights, client_sizes))
            auc_r, _ = evaluate_model(global_model, X_test, y_test)
            round_aucs_dp.append(auc_r)
        curves[f"fedavg_dp_sigma_{sigma}"] = round_aucs_dp
        results.append({
            "mode": "fedavg_dp", "noise_multiplier": float(sigma), "clip_norm": CLIP_NORM,
            "epsilon": round(eps, 2), "delta": DELTA, "auc": round_aucs_dp[-1],
            "accuracy": evaluate_model(global_model, X_test, y_test)[1],
            "rounds": n_rounds, "non_iid": True,
        })

    return results, curves


def plot_privacy_utility(results: list[dict], out_path: Path) -> None:
    """Plot AUC vs epsilon (privacy-utility curve)."""
    dp_rows = [r for r in results if r["mode"] == "fedavg_dp" and r.get("epsilon") is not None]
    no_dp_row = next((r for r in results if r["mode"] == "fedavg" and r.get("non_iid")), None)

    fig, ax = plt.subplots(figsize=(7, 5))
    epsilons = [r["epsilon"] for r in dp_rows]
    aucs = [r["auc"] for r in dp_rows]

    ax.plot(epsilons, aucs, marker="o", color="#2b5c8f", linewidth=2, label="FedAvg + DP-SGD")
    for r in dp_rows:
        ax.annotate(
            f"sigma={r['noise_multiplier']}", (r["epsilon"], r["auc"]),
            textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8
        )

    if no_dp_row:
        ax.axhline(no_dp_row["auc"], color="#c0392b", linestyle="--", label=f"FedAvg no-DP (AUC {no_dp_row['auc']:.3f})")

    ax.set_xlabel("Privacy budget epsilon (delta = 1e-5, lower is more private)")
    ax.set_ylabel("ROC AUC on test split")
    ax.set_title("Privacy-Utility Trade-off: Menstrual Anomaly Screening under DP-SGD")
    ax.set_ylim(0.5, 1.0)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="lower right")

    fig.text(0.5, -0.04, f"Fig. 12: kaggle_pcos symptom_only, 8 clients, non-IID (alpha=0.3). {LABEL}", ha="center", fontsize=8, wrap=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_fed_curves(curves: dict[str, list[float]], out_path: Path) -> None:
    """Plot convergence curves across communication rounds."""
    fig, ax = plt.subplots(figsize=(8, 5))
    palette = {
        "fedavg_iid": ("#27ae60", "FedAvg (IID)"),
        "fedavg": ("#2980b9", "FedAvg (Non-IID)"),
        "fedprox": ("#8e44ad", "FedProx (Non-IID, mu=0.01)"),
        "fedper": ("#d35400", "FedPer (Personalized head)"),
        "fedavg_dp_sigma_1.0": ("#e67e22", "FedAvg + DP (sigma=1.0)"),
        "fedavg_dp_sigma_2.0": ("#c0392b", "FedAvg + DP (sigma=2.0)"),
    }
    for tag, (color, label_name) in palette.items():
        if tag in curves:
            ax.plot(range(1, len(curves[tag]) + 1), curves[tag], label=label_name, color=color, linewidth=1.8)

    ax.set_xlabel("Communication Round")
    ax.set_ylabel("ROC AUC on test split")
    ax.set_title("Federated Convergence: Comparing Algorithms and Privacy Noise")
    ax.set_ylim(0.5, 0.95)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="lower right", fontsize=8)

    fig.text(0.5, -0.04, f"Fig. 11: 8 clients, 40 rounds, 2 local epochs per round. {LABEL}", ha="center", fontsize=8, wrap=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=ROOT / "results")
    ap.add_argument("--rounds", type=int, default=ROUNDS)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # Load PCOS symptom_only features
    df = load()
    X, y, num_cols, cat_cols = feature_matrix(df, "symptom_only")
    from sklearn.impute import SimpleImputer
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(imputer.fit_transform(X))
    y_arr = y.to_numpy()

    # Train/test split (80/20 stratified)
    rng = np.random.default_rng(args.seed)
    pos_idx = np.where(y_arr == 1)[0]
    neg_idx = np.where(y_arr == 0)[0]
    rng.shuffle(pos_idx)
    rng.shuffle(neg_idx)

    n_pos_test = int(0.2 * len(pos_idx))
    n_neg_test = int(0.2 * len(neg_idx))

    test_idx = np.concatenate([pos_idx[:n_pos_test], neg_idx[:n_neg_test]])
    train_idx = np.concatenate([pos_idx[n_pos_test:], neg_idx[n_neg_test:]])

    X_train, y_train = X_scaled[train_idx], y_arr[train_idx]
    X_test, y_test = X_scaled[test_idx], y_arr[test_idx]

    print(f"Running federated experiments: train={len(X_train)}, test={len(X_test)}, rounds={args.rounds}...")
    results, curves = run_federated_experiments(X_train, y_train, X_test, y_test, seed=args.seed, n_rounds=args.rounds)

    for r in results:
        print(f"  {r['mode']:12s} sigma={r['noise_multiplier']:<4} eps={str(r['epsilon']):<6} AUC={r['auc']:.3f} Acc={r['accuracy']:.3f}")

    out_payload = {
        "meta": {
            **base_meta(args.seed),
            "protocol": f"{args.rounds} rounds, {N_CLIENTS} clients, Dirichlet alpha={DIRICHLET_ALPHA}, clip_norm={CLIP_NORM}, delta={DELTA}",
        },
        "results": results,
    }
    (out_dir / "federated.json").write_text(json.dumps(out_payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_dir / 'federated.json'}")

    # Generate figures
    plot_privacy_utility(results, fig_dir / "privacy_utility.png")
    plot_fed_curves(curves, fig_dir / "fed_curves.png")
    print("wrote results/figures/privacy_utility.png and results/figures/fed_curves.png")


if __name__ == "__main__":
    main()
