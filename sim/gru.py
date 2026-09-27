"""GRU Tier 2 sequence model, T3 comparison, personalization, ONNX export (package A4).

Trains GRU (hidden 16 and 32), LSTM and CNN1D as global next-cycle predictors on the simulator's
train split, picks the GRU hidden size and the winning architecture by validation loss, then scores
every user by next-step prediction error and runs it through the same rule layer and detection
metrics as sim/detection_eval.py, so it sits in the same comparison table as the A2 detectors.
The classical reference (exponential smoothing, no training) is scored the same way.

Contract 5.2 only accepts detector="gru" (not "lstm" or "cnn1d") for a live screening output, so
only the winning GRU is wired into a streaming-compatible score; the other architectures are
evaluation-only rows in results/baseline_detection.json (same pattern as sim/DETECTORS.md's note
on isolation_forest, ewma and fixed_threshold).

Personalization: freeze every GRU weight except the output head, fine-tune on a held-out test
user's first N cycles only, and compare detection metrics on that user's remaining cycles before
and after.

Run: python -m sim.gru   (needs results/sim/*.parquet from sim.simulator; results/thresholds.json
from sim.detection_eval is extended in place, not required beforehand)
"""
from __future__ import annotations

import argparse
import copy
import json

import numpy as np
import pandas as pd
import torch

from sim.common import FEATURES, ROOT, base_meta
from sim.detection_eval import PATTERN_DRIFTS, detection_metrics, rows_for, user_logs, with_truth
from sim.detectors import FEATURE_SPECS, RuleLayer
from sim.sequence_models import (
    CNN1DPredictor, ExponentialSmoothingPredictor, FeatureScaler, GRUPredictor, LSTMPredictor,
    build_supervised, masked_mse, to_model_inputs, train_predictor, user_arrays,
)

FA_BUDGET = 5.0
GRU_HIDDEN_SIZES = [16, 32]
ARCH_HIDDEN = 32  # hidden size / channel count used for the LSTM and CNN1D comparison rows
THRESH_GRID = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0]
PERSONALIZATION_N = 4  # first N cycles of a held-out user used to fine-tune the output head
N_PERSONALIZATION_USERS = 40


def load_split(sim_dir, split: str) -> pd.DataFrame:
    return pd.read_parquet(sim_dir / f"{split}.parquet")


def per_user_raw(df: pd.DataFrame) -> dict[str, np.ndarray]:
    return {uid: user_arrays(logs) for uid, logs in user_logs(df)}


def raw_scores(model, raws: dict[str, np.ndarray], scaler: FeatureScaler) -> dict[str, list[tuple[int, float, dict]]]:
    """Per user: [(cycle_index, anomaly score, {signal: standardized deviation})], one entry per predicted cycle."""
    out = {}
    model.eval() if hasattr(model, "eval") else None
    for uid, raw in raws.items():
        if isinstance(model, ExponentialSmoothingPredictor):
            preds = model.predict_sequence(raw, scaler)
        else:
            std, mask = to_model_inputs(raw, scaler)
            x = np.concatenate([std[:-1], mask[:-1]], axis=-1)
            with torch.no_grad():
                preds = model(torch.from_numpy(x[None]).float())[0].numpy()
        actual_std, actual_mask = to_model_inputs(raw, scaler)
        actual_std, actual_mask = actual_std[1:], actual_mask[1:]
        rows = []
        for i in range(len(preds)):
            cycle_index = i + 2  # predicting cycle i+2 from cycles 1..i+1
            m = actual_mask[i].astype(bool)
            resid = np.zeros(len(FEATURES))
            resid[m] = actual_std[i, m] - preds[i, m]
            dev = {}
            for j, (f, p, dirs) in enumerate(FEATURE_SPECS):
                if not m[j]:
                    continue
                z = resid[j]  # already standardized by the scaler, so this is directly comparable to a z-score
                if "high" in dirs:
                    dev[f"{p}_high"] = z
                if "low" in dirs:
                    dev[f"{p}_low"] = -z
            # score is the single worst-feature deviation, not an RMSE over every feature: a shift in one
            # or two features (as every drift type here is) should not be diluted by the rest sitting at
            # baseline. This mirrors A2 (sim/detectors.py), where each feature fires independently against
            # its own threshold with no cross-feature aggregate gate.
            score = float(max((abs(v) for v in dev.values()), default=0.0))
            rows.append((cycle_index, score, dev))
        out[uid] = rows
    return out


def replay(df: pd.DataFrame, raw: dict[str, list], threshold: float) -> pd.DataFrame:
    flags = []
    for uid, rows in raw.items():
        rules = RuleLayer()
        for cycle_index, score, dev in rows:
            signals = {k for k, v in dev.items() if abs(v) >= threshold}
            flags.append((uid, cycle_index, rules.step(signals)[0]))
        flags.append((uid, 1, "none"))  # cycle 1 has no prediction; the detector has not run yet
    return with_truth(df, flags)


def tune_threshold(df_val: pd.DataFrame, raw_val: dict) -> tuple[float, dict]:
    if set(df_val["split"]) != {"val"}:
        raise ValueError("tuning must use the validation split only")
    best = None
    for t in THRESH_GRID:
        m = detection_metrics(replay(df_val, raw_val, t))
        det = np.mean([m[d]["detection_rate"] for d in PATTERN_DRIFTS])
        fa = m["overall"]["false_alarms_per_100_cycles"]
        ok = fa <= FA_BUDGET
        key = (ok, det if ok else -fa)
        if best is None or key > best[0]:
            best = (key, t, m)
    return best[1], best[2]


def fit_arch(name: str, hidden: int, train_batch, val_batch, seed: int = 0):
    torch.manual_seed(seed)
    model = {"gru": GRUPredictor, "lstm": LSTMPredictor}[name](hidden_size=hidden) if name != "cnn1d" \
        else CNN1DPredictor(channels=hidden)
    info = train_predictor(model, train_batch, epochs=300, val_batch=val_batch, seed=seed)
    return model, info


def personalization_experiment(model: GRUPredictor, scaler: FeatureScaler, test_raw: dict[str, np.ndarray],
                               threshold: float, users: list[str], seed: int = 0) -> dict:
    """Freeze all weights but the output head, fine-tune on each user's first PERSONALIZATION_N cycles,
    and compare detection metrics on the remaining cycles, before vs after, pooled over `users`."""
    torch.manual_seed(seed)
    before_flags, after_flags = [], []
    for uid in users:
        raw = test_raw[uid]
        if len(raw) <= PERSONALIZATION_N + 1:
            continue
        head_raw = raw[:PERSONALIZATION_N]
        personal = copy.deepcopy(model)
        for p in personal.rnn.parameters():
            p.requires_grad_(False)
        batch = build_supervised([head_raw], scaler)
        if batch["loss_mask"].sum() > 0:
            opt = torch.optim.Adam(personal.head.parameters(), lr=1e-2)
            for _ in range(100):
                opt.zero_grad()
                loss = masked_mse(personal(batch["x"]), batch["y"], batch["loss_mask"])
                loss.backward()
                opt.step()
        for tag, m, store in [("before", model, before_flags), ("after", personal, after_flags)]:
            rows = raw_scores(m, {uid: raw}, scaler)[uid]
            rules = RuleLayer()
            store.append((uid, 1, "none"))  # cycle 1 has no prediction, same convention as replay()
            for cycle_index, score, dev in rows:
                signals = {k for k, v in dev.items() if abs(v) >= threshold}
                store.append((uid, cycle_index, rules.step(signals)[0]))
    return before_flags, after_flags


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sim-dir", default=ROOT / "results" / "sim")
    ap.add_argument("--out", default=ROOT / "results")
    args = ap.parse_args()

    sim_meta = json.loads((args.sim_dir / "meta.json").read_text(encoding="utf-8"))["meta"]
    train_df, val_df, test_df = (load_split(args.sim_dir, s) for s in ["train", "val", "test"])
    train_raw = list(per_user_raw(train_df).values())
    scaler = FeatureScaler.fit(np.concatenate(train_raw))
    val_raw_arr, test_raw_arr = per_user_raw(val_df), per_user_raw(test_df)

    val_batch = build_supervised(list(val_raw_arr.values()), scaler)

    gru_sizes = {}
    for h in GRU_HIDDEN_SIZES:
        train_batch = build_supervised(train_raw, scaler)
        model, info = fit_arch("gru", h, train_batch, val_batch, seed=0)
        gru_sizes[h] = {"model": model, "val_loss": info["best_val_loss"], "stopped_epoch": info["stopped_epoch"]}
        print(f"gru hidden={h}: val_loss={info['best_val_loss']:.4f} (epoch {info['stopped_epoch']})")
    best_hidden = min(gru_sizes, key=lambda h: gru_sizes[h]["val_loss"])
    gru_model = gru_sizes[best_hidden]["model"]
    print(f"selected GRU hidden size: {best_hidden}")

    train_batch = build_supervised(train_raw, scaler)
    lstm_model, lstm_info = fit_arch("lstm", ARCH_HIDDEN, train_batch, val_batch, seed=0)
    cnn_model, cnn_info = fit_arch("cnn1d", ARCH_HIDDEN, train_batch, val_batch, seed=0)
    classical = ExponentialSmoothingPredictor(alpha=0.3)
    print(f"lstm val_loss={lstm_info['best_val_loss']:.4f}  cnn1d val_loss={cnn_info['best_val_loss']:.4f}")

    models = {"gru": gru_model, "lstm": lstm_model, "cnn1d": cnn_model, "classical_exp_smoothing": classical}
    test_raw_dict = test_raw_arr
    chosen, rows, sweep = {}, [], []
    for name, model in models.items():
        raw_val = raw_scores(model, val_raw_arr, scaler)
        t, val_metrics = tune_threshold(val_df, raw_val)
        chosen[name] = {"threshold": t, "val_metrics": val_metrics}
        raw_test = raw_scores(model, test_raw_dict, scaler)
        test_metrics = detection_metrics(replay(test_df, raw_test, t))
        # "classical_exp_smoothing" is not in the results schema's detector enum (gru, lstm, cnn1d are);
        # this file is not itself schema-validated, so the real name is kept and flagged in OPEN_QUESTIONS.
        rows_out = rows_for(name, test_metrics)
        rows += rows_out
        print(f"-- {name} (threshold={t}) --")
        for r in rows_out:
            print(f"  {r['drift_type']:12s} detection_rate={r.get('detection_rate')}  "
                 f"false_alarms/100={r['false_alarms_per_100_cycles']}")

    first_drift = test_df.groupby("user_id").drift_type.first()
    personalization_users = first_drift[first_drift != "none"].index.tolist()[:N_PERSONALIZATION_USERS]
    before_flags, after_flags = personalization_experiment(
        gru_model, scaler, test_raw_dict, chosen["gru"]["threshold"], personalization_users)
    personalization_df = test_df[test_df.user_id.isin(personalization_users)]
    before_metrics = detection_metrics(with_truth(personalization_df, before_flags))
    after_metrics = detection_metrics(with_truth(personalization_df, after_flags))

    meta = {**base_meta(sim_meta["seed"]), "simulator_seed": sim_meta["seed"], "simulator_commit": sim_meta["git_commit"],
            "framework": "pytorch", "gru_hidden_sizes_tried": GRU_HIDDEN_SIZES, "selected_gru_hidden_size": best_hidden,
            "arch_hidden_or_channels": ARCH_HIDDEN, "fa_budget_per_100_cycles": FA_BUDGET,
            "personalization_n_cycles": PERSONALIZATION_N}
    out = {
        "meta": meta,
        "gru_hidden_size_sweep": {str(h): {"val_loss": gru_sizes[h]["val_loss"], "stopped_epoch": gru_sizes[h]["stopped_epoch"]}
                                  for h in GRU_HIDDEN_SIZES},
        "chosen_thresholds": {k: v["threshold"] for k, v in chosen.items()},
        "rows": rows,
        "personalization": {
            "n_users": N_PERSONALIZATION_USERS, "n_cycles_used_for_finetune": PERSONALIZATION_N,
            "before": {d: {k: v for k, v in m.items() if k != "n_users"} for d, m in before_metrics.items()},
            "after": {d: {k: v for k, v in m.items() if k != "n_users"} for d, m in after_metrics.items()},
        },
    }
    (args.out / "sequence_models.json").write_text(json.dumps(out, indent=2, default=float) + "\n", encoding="utf-8")

    baseline_path = args.out / "baseline_detection.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline["rows"] = [r for r in baseline["rows"] if r["detector"] not in models] + rows
    baseline_path.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")

    torch.onnx.export(gru_model, torch.zeros(1, 5, gru_model.rnn.input_size), str(ROOT / "exports" / "gru_v1.onnx"),
                      input_names=["sequence"], output_names=["prediction"],
                      dynamic_axes={"sequence": {1: "cycles"}, "prediction": {1: "cycles"}}, opset_version=17,
                      dynamo=False)
    (ROOT / "exports" / "gru_v1.scaler.json").write_text(json.dumps(scaler.to_dict(), indent=2) + "\n", encoding="utf-8")
    print("wrote results/sequence_models.json, updated results/baseline_detection.json, exports/gru_v1.onnx")


if __name__ == "__main__":
    main()
