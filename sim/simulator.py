"""Synthetic per-user cycle simulator with known drift ground truth (package A1).

Each user has a latent personal baseline (cycle length mean and SD, flow level, pain level,
symptom probabilities). From an onset cycle k in 5..10 a drift is injected: pcos_pattern,
anemia_pattern, thyroid_pattern, benign_shift (one or two cycles, then back to baseline), or none.
Every parameter range is listed in sim/ASSUMPTIONS.md with its source or marked "assumption".

Outputs (split by user, never by cycle):
  results/sim/train.parquet, val.parquet, test.parquet   one row per cycle
  results/sim/users.parquet                              one row per user with latent parameters
  results/sim/meta.json                                  seed, git commit, class mix, marginals

Run: python -m sim.simulator --seed 42
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from sim.common import FEATURES, ROOT, SYMPTOMS, base_meta

DRIFTS = ["none", "pcos_pattern", "anemia_pattern", "thyroid_pattern", "benign_shift"]
ANDROGEN = ["acne", "excess_hair", "hair_loss"]
ANEMIA_SYMPTOMS = ["fatigue", "dizziness", "pallor"]
THYROID_SYMPTOMS = ["fatigue", "weight_change", "mood"]
STRESS_SYMPTOMS = ["fatigue", "mood"]
SPLITS = ["train", "val", "test"]


@dataclass(frozen=True)
class SimConfig:
    n_users: int = 3000
    min_cycles: int = 16
    max_cycles: int = 30
    missing_rate: float = 0.02
    class_mix: dict = field(default_factory=lambda: {
        "none": 0.25, "pcos_pattern": 0.20, "anemia_pattern": 0.20, "thyroid_pattern": 0.20, "benign_shift": 0.15,
    })
    split_fractions: tuple = (0.6, 0.2, 0.2)
    # latent baseline
    mu_mean: float = 29.0
    mu_sd: float = 2.5
    mu_clip: tuple = (21.0, 38.0)
    sigma_range: tuple = (1.0, 3.0)
    length_clip: tuple = (15, 90)
    flow_range: tuple = (1.0, 2.3)
    flow_noise_sd: float = 0.4
    pain_range: tuple = (1.0, 5.0)
    pain_noise_sd: float = 1.0
    symptom_base_prob: tuple = (0.02, 0.15)
    symptom_drift_prob: tuple = (0.5, 0.8)
    # drift
    onset_range: tuple = (5, 10)
    ramp_cycles: tuple = (1, 2, 3)
    pcos_shift: tuple = (8.0, 20.0)
    pcos_var_factor: float = 2.0
    pcos_skip_prob: float = 0.10
    pcos_skip_length: tuple = (46, 75)
    anemia_flow_shift: tuple = (1.0, 2.0)
    thyroid_shorter: tuple = (-8.0, -5.0)
    thyroid_longer: tuple = (6.0, 12.0)
    benign_duration: tuple = (1, 2)
    benign_longer_prob: float = 0.7
    benign_longer: tuple = (7.0, 15.0)
    benign_shorter: tuple = (-7.0, -4.0)
    benign_symptom_prob: float = 0.4


def assign_types(cfg: SimConfig, rng: np.random.Generator) -> tuple[list[str], list[str]]:
    """Exact class counts, then a user-level split stratified by drift type."""
    counts = {k: int(round(cfg.n_users * v)) for k, v in cfg.class_mix.items()}
    counts["none"] += cfg.n_users - sum(counts.values())
    types = np.array([k for k in DRIFTS for _ in range(counts[k])], dtype=object)
    rng.shuffle(types)
    splits = np.empty(cfg.n_users, dtype=object)
    for k in DRIFTS:
        idx = np.flatnonzero(types == k)
        rng.shuffle(idx)
        n_tr = int(round(len(idx) * cfg.split_fractions[0]))
        n_va = int(round(len(idx) * cfg.split_fractions[1]))
        splits[idx[:n_tr]] = "train"
        splits[idx[n_tr:n_tr + n_va]] = "val"
        splits[idx[n_tr + n_va:]] = "test"
    return list(types), list(splits)


def draw_user(cfg: SimConfig, drift: str, rng: np.random.Generator) -> dict:
    """Latent baseline and drift parameters for one user."""
    u = {
        "drift_type": drift,
        "n_cycles": int(rng.integers(cfg.min_cycles, cfg.max_cycles + 1)),
        "mu": float(np.clip(rng.normal(cfg.mu_mean, cfg.mu_sd), *cfg.mu_clip)),
        "sigma": float(rng.uniform(*cfg.sigma_range)),
        "flow_level": float(rng.uniform(*cfg.flow_range)),
        "pain_level": float(rng.uniform(*cfg.pain_range)),
        "symptom_prob": {s: float(rng.uniform(*cfg.symptom_base_prob)) for s in SYMPTOMS},
        "start": date(2024, 1, 1) + timedelta(days=int(rng.integers(0, 365))),
        "onset_cycle": None, "ramp": 1, "length_shift": 0.0, "flow_shift": 0.0,
        "drift_symptom_prob": {}, "benign_duration": 0,
    }
    if drift == "none":
        return u
    u["onset_cycle"] = int(rng.integers(cfg.onset_range[0], cfg.onset_range[1] + 1))
    if drift == "benign_shift":
        u["benign_duration"] = int(rng.integers(cfg.benign_duration[0], cfg.benign_duration[1] + 1))
        rng_range = cfg.benign_longer if rng.random() < cfg.benign_longer_prob else cfg.benign_shorter
        u["length_shift"] = float(rng.uniform(*rng_range))
        u["drift_symptom_prob"] = {s: cfg.benign_symptom_prob for s in STRESS_SYMPTOMS}
        return u
    u["ramp"] = int(rng.choice(cfg.ramp_cycles))
    if drift == "pcos_pattern":
        u["length_shift"] = float(rng.uniform(*cfg.pcos_shift))
        u["drift_symptom_prob"] = {s: float(rng.uniform(*cfg.symptom_drift_prob)) for s in ANDROGEN}
    elif drift == "anemia_pattern":
        u["flow_shift"] = float(rng.uniform(*cfg.anemia_flow_shift))
        u["drift_symptom_prob"] = {s: float(rng.uniform(*cfg.symptom_drift_prob)) for s in ANEMIA_SYMPTOMS}
    elif drift == "thyroid_pattern":
        rng_range = cfg.thyroid_shorter if rng.random() < 0.5 else cfg.thyroid_longer
        u["length_shift"] = float(rng.uniform(*rng_range))
        u["drift_symptom_prob"] = {s: float(rng.uniform(*cfg.symptom_drift_prob)) for s in THYROID_SYMPTOMS}
    return u


def drift_fraction(u: dict, i: int) -> float:
    """How far the drift has progressed at 1-based cycle i (0 = baseline, 1 = full drift)."""
    k = u["onset_cycle"]
    if k is None or i < k:
        return 0.0
    if u["drift_type"] == "benign_shift":
        return 1.0 if i < k + u["benign_duration"] else 0.0
    return min(1.0, (i - k + 1) / u["ramp"])


def draw_symptom(p: float, drifted: bool, rng: np.random.Generator) -> int:
    if rng.random() >= p:
        return 0
    return int(rng.choice([1, 2, 2, 3])) if drifted else int(rng.choice([1, 1, 1, 2]))


def simulate_user(cfg: SimConfig, u: dict, rng: np.random.Generator) -> list[dict]:
    rows = []
    start = u["start"]
    for i in range(1, u["n_cycles"] + 1):
        f = drift_fraction(u, i)
        active = f > 0
        mean_len = u["mu"] + f * u["length_shift"]
        sd_len = u["sigma"]
        skipped = False
        if u["drift_type"] == "pcos_pattern" and active:
            sd_len *= np.sqrt(1 + f * (cfg.pcos_var_factor - 1))
            skipped = bool(rng.random() < f * cfg.pcos_skip_prob)
        if skipped:
            length = int(rng.integers(cfg.pcos_skip_length[0], cfg.pcos_skip_length[1] + 1))
        else:
            length = int(np.clip(round(rng.normal(mean_len, sd_len)), *cfg.length_clip))
            if u["drift_type"] == "pcos_pattern":
                length = min(length, cfg.pcos_skip_length[0] - 1)  # over 45 days is reserved for skipped cycles
        flow = int(np.clip(round(rng.normal(u["flow_level"] + f * u["flow_shift"], cfg.flow_noise_sd)), 1, 3))
        pain = int(np.clip(round(rng.normal(u["pain_level"], cfg.pain_noise_sd)), 0, 10))
        symptoms = {}
        for s in SYMPTOMS:
            p = u["symptom_prob"][s]
            target = u["drift_symptom_prob"].get(s)
            drifted = active and target is not None
            if drifted:
                p = p + f * (target - p)
            symptoms[s] = draw_symptom(p, drifted and rng.random() < f, rng)
        rows.append({
            "cycle_index": i, "start_date": start.isoformat(), "cycle_length_days": length,
            "true_length_days": length, "flow": flow, "pain": pain, **symptoms,
            "drift_active": active, "skipped": skipped,
        })
        start += timedelta(days=length)
    for r in rows:  # missingness applies to observed features only, never to dates or ground truth
        for col in FEATURES:
            if rng.random() < cfg.missing_rate:
                r[col] = None
    return rows


def simulate(cfg: SimConfig, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (cycles, users). Each user has its own RNG stream, so a user does not depend on the others."""
    types, splits = assign_types(cfg, np.random.default_rng(seed))
    cycle_rows, user_rows = [], []
    for n, (drift, split) in enumerate(zip(types, splits)):
        rng = np.random.default_rng([seed, 1, n])
        u = draw_user(cfg, drift, rng)
        uid = f"u{n:05d}"
        for r in simulate_user(cfg, u, rng):
            cycle_rows.append({"user_id": uid, "split": split, "drift_type": drift, "onset_cycle": u["onset_cycle"], **r})
        user_rows.append({
            "user_id": uid, "split": split, "drift_type": drift, "n_cycles": u["n_cycles"],
            "onset_cycle": u["onset_cycle"], "ramp_cycles": u["ramp"], "benign_duration": u["benign_duration"],
            "mu": u["mu"], "sigma": u["sigma"], "flow_level": u["flow_level"], "pain_level": u["pain_level"],
            "length_shift": u["length_shift"], "flow_shift": u["flow_shift"],
            **{f"p_{s}": v for s, v in u["symptom_prob"].items()},
            **{f"drift_p_{s}": u["drift_symptom_prob"].get(s, np.nan) for s in SYMPTOMS},
        })
    cycles = pd.DataFrame(cycle_rows)
    for col in [*FEATURES, "onset_cycle"]:
        cycles[col] = cycles[col].astype("Int64")
    users = pd.DataFrame(user_rows)
    users["onset_cycle"] = users["onset_cycle"].astype("Int64")
    return cycles, users


def to_cycle_logs(df: pd.DataFrame) -> list[dict]:
    """Convert one user's rows to cycle log objects (contract 5.3). Requires no missing values."""
    out = []
    for r in df.sort_values("cycle_index").itertuples(index=False):
        out.append({
            "cycle_index": int(r.cycle_index), "start_date": r.start_date,
            "cycle_length_days": int(r.cycle_length_days), "flow": int(r.flow), "pain": int(r.pain),
            "symptoms": {s: int(getattr(r, s)) for s in SYMPTOMS},
        })
    return out


def marginals(cycles: pd.DataFrame) -> dict:
    """Cycle length marginals on baseline cycles (no drift active), for comparison with real data."""
    base = cycles[~cycles.drift_active].dropna(subset=["cycle_length_days"])
    length = base.cycle_length_days.astype(float)
    within = base.groupby("user_id").cycle_length_days.apply(lambda s: s.astype(float).std())
    return {
        "baseline_cycle_length_mean": round(float(length.mean()), 4),
        "baseline_cycle_length_sd": round(float(length.std()), 4),
        "baseline_within_user_sd_median": round(float(within.median()), 4),
        "baseline_share_outside_24_38": round(float(((length < 24) | (length > 38)).mean()), 4),
    }


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    pq.write_table(pa.Table.from_pandas(df.reset_index(drop=True), preserve_index=False), path, compression="snappy")


def run(seed: int, out: Path, config: SimConfig | None = None) -> dict:
    cfg = config or SimConfig()
    out.mkdir(parents=True, exist_ok=True)
    cycles, users = simulate(cfg, seed)
    for split in SPLITS:
        write_parquet(cycles[cycles.split == split], out / f"{split}.parquet")
    write_parquet(users, out / "users.parquet")
    meta = {
        "meta": {
            **base_meta(seed),
            "generator": "sim/simulator.py",
            "n_users": cfg.n_users,
            "class_mix": cfg.class_mix,
            "split_fractions": dict(zip(SPLITS, cfg.split_fractions)),
            "missing_rate": cfg.missing_rate,
        },
        "counts": {
            "users_by_split": users.split.value_counts().reindex(SPLITS).astype(int).to_dict(),
            "users_by_drift": users.drift_type.value_counts().reindex(DRIFTS).astype(int).to_dict(),
            "cycles_by_split": cycles.split.value_counts().reindex(SPLITS).astype(int).to_dict(),
        },
        "marginals": marginals(cycles),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n-users", type=int, default=SimConfig.n_users)
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "sim")
    args = ap.parse_args()
    meta = run(args.seed, args.out, SimConfig(n_users=args.n_users))
    print(json.dumps(meta["counts"], indent=2))
    print(json.dumps(meta["marginals"], indent=2))


if __name__ == "__main__":
    main()
