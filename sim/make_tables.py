#!/usr/bin/env python3
"""Render the "without FL, with FL, with FL plus DP" table (faculty feedback item 10).

Reads results/summary.json (federated section) and writes results/tables/fl_comparison.md and .csv.
Nothing is typed by hand: every number comes from the results file. Placeholder rows are labeled.

Run: python sim/make_tables.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABEL = "Simulated / preliminary, public and synthetic data, not real deployment data"

# mode -> (setting name, uses FL, uses DP)
MODES = {
    "centralized": ("Without FL: centralized", "no", "no"),
    "local_only": ("Without FL: local only", "no", "no"),
    "fedavg": ("With FL: FedAvg", "yes", "no"),
    "fedprox": ("With FL: FedProx", "yes", "no"),
    "fedper": ("With FL: FedPer (personalized head)", "yes", "no"),
    "fedavg_dp": ("With FL and DP: FedAvg + DP", "yes", "yes"),
}
ORDER = list(MODES)
HEADER = ["Setting", "FL", "DP", "Noise multiplier", "Epsilon (delta)", "AUC", "Accuracy", "Rounds", "Client split"]


def num(x, nd: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{nd}f}"


def rows_from_summary(summary: dict) -> list[list[str]]:
    entries = sorted(
        summary.get("federated", []),
        key=lambda r: (ORDER.index(r["mode"]) if r["mode"] in ORDER else len(ORDER), r.get("noise_multiplier", 0)),
    )
    rows = []
    for r in entries:
        name, fl, dp = MODES.get(r["mode"], (r["mode"], "?", "?"))
        if r.get("placeholder"):
            name += " [PLACEHOLDER]"
        eps = "n/a" if r.get("epsilon") is None else f"{r['epsilon']:.2f} ({r['delta']:g})"
        rows.append([
            name, fl, dp,
            num(r.get("noise_multiplier"), 2) if dp == "yes" else "n/a",
            eps, num(r.get("auc")), num(r.get("accuracy")), str(r.get("rounds", "")),
            "non-IID" if r.get("non_iid") else "IID",
        ])
    return rows


def build_markdown(summary: dict) -> str:
    rows = rows_from_summary(summary)
    lines = ["| " + " | ".join(HEADER) + " |", "|" + "|".join(["---"] * len(HEADER)) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    caption = (
        "Table 1: Without federated learning, with federated learning, and with federated learning plus "
        f"differential privacy. {LABEL}. Source: results/summary.json (run {summary['meta'].get('run_id', '?')})."
    )
    return "\n".join(lines) + "\n\n" + caption + "\n"


def main() -> None:
    summary = json.loads((ROOT / "results" / "summary.json").read_text(encoding="utf-8"))
    out = ROOT / "results" / "tables"
    out.mkdir(parents=True, exist_ok=True)
    (out / "fl_comparison.md").write_text(build_markdown(summary), encoding="utf-8")
    with open(out / "fl_comparison.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows_from_summary(summary))
    print(f"wrote {out / 'fl_comparison.md'} and .csv")


if __name__ == "__main__":
    main()
