"""Tune detectors on the validation split and measure them on the test split (package A2).

Definitions (per drift type, test split, one user = one sequence):
  non-drift cycle         drift_active is false (none users, cycles before onset, cycles after a benign shift ended)
  false_alarms_per_100    100 * flagged non-drift cycles / non-drift cycles (any flag other than none)
  detection_rate          pattern drifts: share of users with any flag at or after onset
                          benign_shift: share of users flagged during the shifted cycles
  median_delay_cycles     median of (first flagged cycle at or after onset) - onset, over detected users
  correct_pattern_rate    share of users given the correct pattern flag at or after onset
  persistent_flag_rate    benign_shift: share of users flagged on 2 or more cycles after the shift ended
  pattern_flag_rate       benign_shift: share of users given any pattern flag at or after onset

Tuning: for each detector, the grid value that maximizes the mean detection rate over the three pattern
drifts on val, subject to overall false alarms at most FA_BUDGET per 100 non-drift cycles. Ties go to the
higher correct-pattern rate, then fewer false alarms. The test split is never used for tuning.

Run: python -m sim.detection_eval   (needs results/sim/*.parquet from python -m sim.simulator --seed 42)
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from sim.common import FEATURES, ROOT, base_meta
from sim.detectors import INPUTS, IsolationForestDetector, RuleLayer, make_detector

PATTERN_DRIFTS = ["pcos_pattern", "anemia_pattern", "thyroid_pattern"]
FA_BUDGET = 5.0
GRIDS = {
    "fixed_threshold": [{}],
    "zscore": [{"threshold": t} for t in [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]],
    "ewma": [{"L": v} for v in [2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0]],
    "cusum": [{"h": v} for v in [2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]],
    "isolation_forest": [{"threshold": v} for v in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]],
    "hybrid": [{"z_threshold": z, "h": h} for z, h in itertools.product([2.5, 3.0, 3.5, 4.0, 5.0], [3.0, 4.0, 5.0, 6.0, 8.0, 10.0])],
}
SPEC_REFERENCE = ("zscore", {"threshold": 2.0})  # aryan.md A2 names 2.0; reported alongside the tuned value
TRUTH = ["user_id", "cycle_index", "drift_type", "onset_cycle", "drift_active"]
SCHEMA_DRIFT = {"pcos_pattern": "pcos", "anemia_pattern": "anemia", "thyroid_pattern": "thyroid", "benign_shift": "benign_shift"}


def user_logs(cycles: pd.DataFrame) -> list[tuple[str, list[dict]]]:
    """Per user, flat cycle dicts with None for missing values, in cycle order."""
    df = cycles.sort_values(["user_id", "cycle_index"])
    feats = df[FEATURES].astype(object).where(df[FEATURES].notna(), None)
    feats["cycle_index"] = df["cycle_index"].to_numpy()
    recs = feats.to_dict("records")
    out, start = [], 0
    for uid, n in df.groupby("user_id", sort=False).size().items():
        out.append((uid, recs[start:start + n]))
        start += n
    return out


def with_truth(cycles: pd.DataFrame, flags: list[tuple[str, int, str]]) -> pd.DataFrame:
    f = pd.DataFrame(flags, columns=["user_id", "cycle_index", "flag"])
    return cycles[TRUTH].merge(f, on=["user_id", "cycle_index"], how="left")


def run_detector(cycles: pd.DataFrame, name: str, params: dict, tuning: bool = False) -> pd.DataFrame:
    if tuning and set(cycles["split"]) != {"val"}:
        raise ValueError("tuning must use the validation split only")
    flags = []
    for uid, logs in user_logs(cycles):
        det = make_detector(name, **params)
        for c in logs:
            flags.append((uid, c["cycle_index"], det.update(c)["flag"]))
    return with_truth(cycles, flags)


def _if_user(uid: str, logs: list[dict]) -> list[tuple[str, int, float, dict]]:
    det = IsolationForestDetector()
    return [(uid, c["cycle_index"], *det.raw({f: c[f] for f in INPUTS})) for c in logs]


def isolation_forest_raw(cycles: pd.DataFrame) -> list[list[tuple[str, int, float, dict]]]:
    """Threshold-independent scores and deviations, computed once per split (refits are slow)."""
    return Parallel(n_jobs=-1)(delayed(_if_user)(uid, logs) for uid, logs in user_logs(cycles))


def replay_isolation_forest(cycles: pd.DataFrame, raw, threshold: float, tuning: bool = False) -> pd.DataFrame:
    if tuning and set(cycles["split"]) != {"val"}:
        raise ValueError("tuning must use the validation split only")
    probe = IsolationForestDetector(threshold=threshold)
    flags = []
    for user in raw:
        rules = RuleLayer()
        for uid, idx, score, dev in user:
            flags.append((uid, idx, rules.step(probe.signals_from_raw(score, dev))[0]))
    return with_truth(cycles, flags)


def _median(values) -> float | None:
    return float(np.median(values)) if len(values) else None


def detection_metrics(df: pd.DataFrame) -> dict:
    df = df.sort_values(["user_id", "cycle_index"])
    flagged = df["flag"] != "none"
    nd = ~df["drift_active"].astype(bool)
    out = {"overall": {"false_alarms_per_100_cycles": 100 * float(flagged[nd].mean()) if nd.any() else 0.0,
                       "n_non_drift_cycles": int(nd.sum()), "n_users": int(df["user_id"].nunique())}}
    for drift, g in df.groupby("drift_type"):
        g_nd = ~g["drift_active"].astype(bool)
        m = {"n_users": int(g["user_id"].nunique()),
             "false_alarms_per_100_cycles": 100 * float((g["flag"] != "none")[g_nd].mean()) if g_nd.any() else 0.0}
        if drift == "none":
            m["users_with_any_flag_rate"] = float(g.groupby("user_id")["flag"].apply(lambda s: (s != "none").any()).mean())
        else:
            delays, pattern_delays, persistent, pattern_any = [], [], 0, 0
            for _, u in g.groupby("user_id"):
                onset = int(u["onset_cycle"].iloc[0])
                after = u[u["cycle_index"] >= onset]
                window = after[after["drift_active"].astype(bool)] if drift == "benign_shift" else after
                hit = window[window["flag"] != "none"]
                if len(hit):
                    delays.append(int(hit["cycle_index"].iloc[0]) - onset)
                if drift == "benign_shift":
                    ended = after[~after["drift_active"].astype(bool)]
                    persistent += int((ended["flag"] != "none").sum() >= 2)
                    pattern_any += int(after["flag"].isin(PATTERN_DRIFTS).any())
                else:
                    ok = after[after["flag"] == drift]
                    if len(ok):
                        pattern_delays.append(int(ok["cycle_index"].iloc[0]) - onset)
            n = m["n_users"]
            m["detection_rate"] = len(delays) / n
            m["median_delay_cycles"] = _median(delays)
            if drift == "benign_shift":
                m["persistent_flag_rate"] = persistent / n
                m["pattern_flag_rate"] = pattern_any / n
            else:
                m["correct_pattern_rate"] = len(pattern_delays) / n
                m["median_pattern_delay_cycles"] = _median(pattern_delays)
        out[drift] = m
    return out


def objective(m: dict) -> tuple:
    det = np.mean([m[d]["detection_rate"] for d in PATTERN_DRIFTS])
    cor = np.mean([m[d]["correct_pattern_rate"] for d in PATTERN_DRIFTS])
    return float(det), float(cor), -m["overall"]["false_alarms_per_100_cycles"]


def evaluate(cycles: pd.DataFrame, name: str, params: dict, if_raw=None, tuning: bool = False) -> dict:
    if name == "isolation_forest":
        return detection_metrics(replay_isolation_forest(cycles, if_raw, params["threshold"], tuning))
    return detection_metrics(run_detector(cycles, name, params, tuning))


def tune(val: pd.DataFrame, names, if_raw_val=None) -> tuple[dict, list]:
    chosen, sweep = {}, []
    for name in names:
        best = None
        for params in GRIDS[name]:
            m = evaluate(val, name, params, if_raw_val, tuning=True)
            obj = objective(m)
            fa = m["overall"]["false_alarms_per_100_cycles"]
            sweep.append({"detector": name, "params": params, "val_false_alarms_per_100_cycles": round(fa, 4),
                          "val_mean_detection_rate": round(obj[0], 4), "val_mean_correct_pattern_rate": round(obj[1], 4)})
            ok = fa <= FA_BUDGET
            key = (ok, obj if ok else (-fa,))
            if best is None or key > best[0]:
                best = (key, params, ok, m)
        chosen[name] = {"params": best[1], "fa_budget_met_on_val": best[2], "val_metrics": rounded(best[3])}
    return chosen, sweep


def rounded(x):
    if isinstance(x, dict):
        return {k: rounded(v) for k, v in x.items()}
    if isinstance(x, float):
        return round(x, 4)
    return x


def rows_for(name: str, m: dict) -> list[dict]:
    rows = []
    for drift, schema_name in SCHEMA_DRIFT.items():
        if drift not in m:
            continue
        rows.append({"detector": name, "drift_type": schema_name, **rounded(m[drift])})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sim-dir", type=Path, default=ROOT / "results" / "sim")
    ap.add_argument("--out", type=Path, default=ROOT / "results")
    ap.add_argument("--detectors", nargs="*", default=list(GRIDS))
    args = ap.parse_args()

    sim_meta = json.loads((args.sim_dir / "meta.json").read_text(encoding="utf-8"))["meta"]
    val = pd.read_parquet(args.sim_dir / "val.parquet")
    test = pd.read_parquet(args.sim_dir / "test.parquet")
    names = args.detectors
    raw_val = isolation_forest_raw(val) if "isolation_forest" in names else None
    raw_test = isolation_forest_raw(test) if "isolation_forest" in names else None

    chosen, sweep = tune(val, names, raw_val)
    meta = {**base_meta(sim_meta["seed"]), "simulator_seed": sim_meta["seed"], "simulator_commit": sim_meta["git_commit"],
            "tuned_on": "val", "evaluated_on": "test", "fa_budget_per_100_cycles": FA_BUDGET,
            "objective": "max mean detection rate over pcos, anemia, thyroid on val, subject to overall false alarms <= budget",
            "definitions": __doc__.split("Definitions")[1].split("Tuning:")[0].strip()}

    rows, overall = [], {}
    for name in names:
        m = evaluate(test, name, chosen[name]["params"], raw_test)
        rows += rows_for(name, m)
        overall[name] = rounded({**m["overall"], "none_users": m.get("none", {})})
    ref_name, ref_params = SPEC_REFERENCE
    reference = []
    if ref_name in names:
        m = evaluate(test, ref_name, ref_params)
        reference = rows_for(f"{ref_name}_spec_threshold_2", m)
        overall[f"{ref_name}_spec_threshold_2"] = rounded({**m["overall"], "none_users": m.get("none", {})})

    thresholds = {"meta": meta, "chosen": chosen, "grids": {n: GRIDS[n] for n in names}, "val_sweep": sweep}
    detection = {"meta": {**meta, "n_test_users": int(test["user_id"].nunique()), "n_test_cycles": int(len(test))},
                 "rows": rows, "overall": overall, "reference_rows": reference}
    (args.out / "thresholds.json").write_text(json.dumps(thresholds, indent=2) + "\n", encoding="utf-8")
    (args.out / "baseline_detection.json").write_text(json.dumps(detection, indent=2) + "\n", encoding="utf-8")
    for r in rows + reference:
        print(r)


if __name__ == "__main__":
    main()
