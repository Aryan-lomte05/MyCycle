"""Sequence models for Tier 2 next-cycle prediction (package A4, T3 technique comparison).

All models solve the same task: given cycles 1..t, predict the standardized feature vector at
cycle t+1. The anomaly score at t+1 is the size of the prediction error. This makes GRU, LSTM,
CNN1D and the classical reference directly comparable under one protocol (aryan.md A4).

Framework choice: PyTorch, not Keras (CLAUDE.md section 4 leaves this open, "Aryan decides, one
only"). Reason: mature, single-call ONNX export (torch.onnx.export) and easy custom masking for
missing values, both needed here. Recorded in docs/OPEN_QUESTIONS.md and T3 of the technique
comparison.

Missing values: each input step is (standardized value with NaN set to 0, a same-size mask of
1 = observed, 0 = missing), so the network is told what it must not trust. Training and evaluation
loss only ever look at observed targets.
"""
from __future__ import annotations

import numpy as np
import torch
from torch import nn

from sim.common import FEATURES

N_FEATURES = len(FEATURES)
INPUT_DIM = 2 * N_FEATURES  # standardized value + observed mask, concatenated
SD_FLOOR = 1e-3


class FeatureScaler:
    """Per-feature mean and SD fit on one split (train), used to standardize every other split."""

    def __init__(self, mean: np.ndarray, sd: np.ndarray):
        self.mean, self.sd = mean, np.maximum(sd, SD_FLOOR)

    @classmethod
    def fit(cls, arr: np.ndarray) -> "FeatureScaler":
        """arr: (n_rows, n_features), NaN for missing. Fit ignores NaN (np.nanmean/nanstd)."""
        return cls(np.nanmean(arr, axis=0), np.nanstd(arr, axis=0))

    def transform(self, arr: np.ndarray) -> np.ndarray:
        return (arr - self.mean) / self.sd

    def inverse(self, arr: np.ndarray) -> np.ndarray:
        return arr * self.sd + self.mean

    def to_dict(self) -> dict:
        return {"mean": self.mean.tolist(), "sd": self.sd.tolist(), "features": FEATURES}

    @classmethod
    def from_dict(cls, d: dict) -> "FeatureScaler":
        return cls(np.asarray(d["mean"]), np.asarray(d["sd"]))


def user_arrays(cycles: list[dict]) -> np.ndarray:
    """Cycle logs (or flat dicts with the feature keys) -> (n_cycles, n_features) array, NaN for missing."""
    out = np.full((len(cycles), N_FEATURES), np.nan)
    for i, c in enumerate(cycles):
        src = dict(c)
        if isinstance(src.get("symptoms"), dict):
            src.update(src.pop("symptoms"))
        for j, f in enumerate(FEATURES):
            v = src.get(f)
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                out[i, j] = float(v)
    return out


def to_model_inputs(raw: np.ndarray, scaler: FeatureScaler) -> tuple[np.ndarray, np.ndarray]:
    """raw: (T, n_features) with NaN for missing -> (values with NaN->0, mask). Both (T, n_features)."""
    mask = (~np.isnan(raw)).astype(np.float32)
    std = scaler.transform(raw)
    std = np.where(np.isnan(std), 0.0, std).astype(np.float32)
    return std, mask


def pad_batch(users: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """List of (T_i, n_features) arrays -> (values, mask) padded to (N, max_T, n_features), pad = missing."""
    max_t = max(len(u) for u in users)
    values = np.zeros((len(users), max_t, N_FEATURES), dtype=np.float32)
    mask = np.zeros((len(users), max_t, N_FEATURES), dtype=np.float32)
    for i, u in enumerate(users):
        values[i, :len(u)] = u
        mask[i, :len(u)] = 1.0
    return values, mask


def build_supervised(raw_list: list[np.ndarray], scaler: FeatureScaler) -> dict[str, torch.Tensor]:
    """Per-user raw arrays -> padded input (x_1..x_{T-1}), target (x_2..x_T), and a loss mask.

    Padding never leaks: a padded target position has mask 0 (like a missing value), so it never
    contributes to the loss regardless of what the model outputs there.
    """
    std_list, obs_list = [], []
    for raw in raw_list:
        std, mask = to_model_inputs(raw, scaler)
        std_list.append(std)
        obs_list.append(mask)
    std_pad, obs_pad = pad_batch(std_list), pad_batch(obs_list)[0]
    values, in_mask = std_pad
    x = np.concatenate([values[:, :-1], in_mask[:, :-1]], axis=-1)
    y = values[:, 1:]
    loss_mask = obs_pad[:, 1:]  # target must be an observed real value, not padding and not missing
    return {"x": torch.from_numpy(x), "y": torch.from_numpy(y), "loss_mask": torch.from_numpy(loss_mask)}


def masked_mse(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    sq = (pred - target) ** 2 * mask
    return sq.sum() / mask.sum().clamp_min(1.0)


class GRUPredictor(nn.Module):
    def __init__(self, hidden_size: int = 32):
        super().__init__()
        self.hidden_size = hidden_size
        self.rnn = nn.GRU(INPUT_DIM, hidden_size, batch_first=True)
        self.head = nn.Linear(hidden_size, N_FEATURES)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.rnn(x)
        return self.head(out)


class LSTMPredictor(nn.Module):
    def __init__(self, hidden_size: int = 32):
        super().__init__()
        self.rnn = nn.LSTM(INPUT_DIM, hidden_size, batch_first=True)
        self.head = nn.Linear(hidden_size, N_FEATURES)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.rnn(x)
        return self.head(out)


class CNN1DPredictor(nn.Module):
    """Causal dilated convolutions: output at t depends only on inputs at times <= t."""

    def __init__(self, channels: int = 32, kernel_size: int = 3, n_layers: int = 3):
        super().__init__()
        self.kernel_size = kernel_size
        self.dilations = [2 ** i for i in range(n_layers)]
        layers = []
        in_ch = INPUT_DIM
        for d in self.dilations:
            layers.append(nn.Conv1d(in_ch, channels, kernel_size, dilation=d))
            in_ch = channels
        self.convs = nn.ModuleList(layers)
        self.act = nn.ReLU()
        self.head = nn.Linear(channels, N_FEATURES)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = x.transpose(1, 2)  # (N, C, T)
        for conv, d in zip(self.convs, self.dilations):
            pad = (self.kernel_size - 1) * d
            h = self.act(conv(nn.functional.pad(h, (pad, 0))))
        return self.head(h.transpose(1, 2))


def train_predictor(model: nn.Module, batch: dict[str, torch.Tensor], epochs: int = 200, lr: float = 5e-3,
                    seed: int = 0, val_batch: dict[str, torch.Tensor] | None = None, patience: int = 20) -> dict:
    torch.manual_seed(seed)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    best_val, best_state, bad_epochs = float("inf"), None, 0
    history = []
    for epoch in range(epochs):
        model.train()
        opt.zero_grad()
        pred = model(batch["x"])
        loss = masked_mse(pred, batch["y"], batch["loss_mask"])
        loss.backward()
        opt.step()
        val_loss = loss.item()
        if val_batch is not None:
            model.eval()
            with torch.no_grad():
                val_loss = masked_mse(model(val_batch["x"]), val_batch["y"], val_batch["loss_mask"]).item()
        history.append({"epoch": epoch, "train_loss": loss.item(), "val_loss": val_loss})
        if val_loss < best_val - 1e-5:
            best_val, best_state, bad_epochs = val_loss, {k: v.clone() for k, v in model.state_dict().items()}, 0
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                break
    if best_state is not None:
        model.load_state_dict(best_state)
    return {"history": history, "best_val_loss": best_val, "stopped_epoch": history[-1]["epoch"]}


class ExponentialSmoothingPredictor:
    """Classical reference (T3): per-user, per-feature simple exponential smoothing, causal.

    pred_t = smoothed estimate using only cycles 1..t-1. No trainable parameters, alpha fixed.
    Not a nn.Module: this is the "ARIMA or exponential smoothing" classical baseline named in
    aryan.md A4, evaluated by the same next-step prediction-error protocol as the neural models.
    """

    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha

    def predict_sequence(self, raw: np.ndarray, scaler: FeatureScaler) -> np.ndarray:
        """raw: (T, n_features) -> (T-1, n_features) standardized predictions for cycles 2..T.

        preds[i] predicts cycle i+2 using cycles 1..i+1 (0-based raw indices 0..i), so the level is
        updated with std[i] and mask[i] BEFORE preds[i] is read off, not after.
        """
        std, mask = to_model_inputs(raw, scaler)
        t, n = std.shape
        level = np.zeros(n)
        seen = np.zeros(n, dtype=bool)
        preds = np.zeros((t - 1, n))
        for i in range(t - 1):
            m = mask[i].astype(bool)
            level = np.where(m, np.where(seen, (1 - self.alpha) * level + self.alpha * std[i], std[i]), level)
            seen = seen | m
            preds[i] = np.where(seen, level, 0.0)  # 0 (the standardized mean) until a feature is first observed
        return preds
