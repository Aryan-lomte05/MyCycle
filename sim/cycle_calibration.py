"""Validate the simulator's cycle-length assumptions against real data (package A1 follow-up).

Real source: FedCycleData (data/download_cycle_calibration.py), 159 women, 1,665 cycles. Compares
population and within-user cycle-length statistics against sim/simulator.py's baseline (non-drift)
marginals. This checks whether the simulator's assumed shape is realistic; it does not and cannot
show that the simulator's drift patterns (PCOS/anemia/thyroid) look like real disease, because
FedCycleData carries no diagnosis labels. See sim/ASSUMPTIONS.md.

Run: python -m sim.cycle_calibration   (needs data/raw/menstrual_cycle_data/, and results/sim/ from
python -m sim.simulator)
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from sim.common import ROOT, base_meta

RAW_CSV = ROOT / "data" / "raw" / "menstrual_cycle_data" / "FedCycleData071012 (2).csv"
N_ROWS_EXPECTED = 1665
N_WOMEN_EXPECTED = 159


def load() -> pd.DataFrame:
    if not RAW_CSV.exists():
        raise FileNotFoundError(f"{RAW_CSV} not found. Run `python data/download_cycle_calibration.py` first.")
    df = pd.read_csv(RAW_CSV, low_memory=False)
    if len(df) != N_ROWS_EXPECTED or df.ClientID.nunique() != N_WOMEN_EXPECTED:
        raise ValueError(f"expected {N_ROWS_EXPECTED} cycles from {N_WOMEN_EXPECTED} women, "
                         f"got {len(df)} cycles from {df.ClientID.nunique()} women: dataset may have changed")
    return df


def real_marginals(df: pd.DataFrame) -> dict:
    length = df["LengthofCycle"].astype(float)
    within = df.groupby("ClientID")["LengthofCycle"].apply(lambda s: s.astype(float).std())
    return {
        "n_women": int(df.ClientID.nunique()), "n_cycles": int(len(df)),
        "cycle_length_mean": round(float(length.mean()), 4),
        "cycle_length_sd": round(float(length.std()), 4),
        "within_user_sd_median": round(float(within.dropna().median()), 4),
        "share_outside_24_38": round(float(((length < 24) | (length > 38)).mean()), 4),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sim-meta", default=ROOT / "results" / "sim" / "meta.json")
    ap.add_argument("--out", default=ROOT / "results" / "sim_validation.json")
    args = ap.parse_args()

    real_df = load()
    real = real_marginals(real_df)
    sim_meta = json.loads(args.sim_meta.read_text(encoding="utf-8"))
    sim = sim_meta["meta"].get("marginals") or sim_meta.get("marginals")

    comparison = {
        "cycle_length_mean": {"real": real["cycle_length_mean"], "simulated": sim["baseline_cycle_length_mean"],
                              "abs_diff": round(abs(real["cycle_length_mean"] - sim["baseline_cycle_length_mean"]), 4)},
        "cycle_length_sd": {"real": real["cycle_length_sd"], "simulated": sim["baseline_cycle_length_sd"],
                            "abs_diff": round(abs(real["cycle_length_sd"] - sim["baseline_cycle_length_sd"]), 4)},
        "within_user_sd_median": {"real": real["within_user_sd_median"], "simulated": sim["baseline_within_user_sd_median"],
                                  "abs_diff": round(abs(real["within_user_sd_median"] - sim["baseline_within_user_sd_median"]), 4)},
        "share_outside_24_38": {"real": real["share_outside_24_38"], "simulated": sim["baseline_share_outside_24_38"],
                                "abs_diff": round(abs(real["share_outside_24_38"] - sim["baseline_share_outside_24_38"]), 4)},
    }
    out = {
        "meta": {**base_meta(sim_meta["meta"]["seed"]), "real_source": "FedCycleData (Kaggle nikitabisht/menstrual-cycle-data)",
                "real_source_provenance": "UNVERIFIED beyond the Kaggle page, see data/DATA_REGISTER.md",
                "limits": "validates only the baseline (non-drift) cycle-length shape, not the drift patterns, "
                         "since FedCycleData carries no PCOS/anemia/thyroid labels"},
        "real": real,
        "simulated": sim,
        "comparison": comparison,
    }
    args.out.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(comparison, indent=2))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
