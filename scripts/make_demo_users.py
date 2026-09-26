#!/usr/bin/env python3
"""Generate crude v0 demo personas in the cycle-log contract (CLAUDE.md 5.3).

These are hand-shaped placeholders so the app can be built tonight. They are replaced by
simulator-derived personas once sim/simulator.py exists (package A1). Deterministic: seed 7.

Run: python scripts/make_demo_users.py
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "exports" / "demo_users"
N_CYCLES = 12
ONSET = 6  # first abnormal cycle (1-based) for the three pattern personas
INTENDED_FLAG_BY = 8  # the app should show the pattern flag by this cycle

SYMPTOMS = ["acne", "excess_hair", "hair_loss", "fatigue", "mood", "weight_change", "dizziness", "pallor"]


def base_symptoms(rng: random.Random) -> dict[str, int]:
    s = {k: 0 for k in SYMPTOMS}
    if rng.random() < 0.25:
        s["mood"] = 1
    return s


def build(persona: str, rng: random.Random) -> list[dict]:
    start = date(2025, 1, 6)
    cycles = []
    for i in range(1, N_CYCLES + 1):
        abnormal = persona != "regular" and i >= ONSET
        length = rng.randint(27, 31)
        flow = rng.choice([1, 2, 2])
        pain = rng.randint(1, 4)
        s = base_symptoms(rng)

        if abnormal and persona == "pcos_pattern":
            length = rng.choice([38, 41, 44, 47, 52])
            pain = rng.randint(2, 5)
            s.update(acne=rng.choice([2, 3]), excess_hair=rng.choice([2, 3]), hair_loss=rng.choice([1, 2]), weight_change=1)
        elif abnormal and persona == "anemia_pattern":
            length = rng.randint(27, 30)
            flow = 3
            pain = rng.randint(3, 6)
            s.update(fatigue=rng.choice([2, 3]), dizziness=2, pallor=rng.choice([2, 3]))
        elif abnormal and persona == "thyroid_pattern":
            length = rng.choice([21, 22, 23, 24])
            pain = rng.randint(2, 5)
            s.update(fatigue=2, weight_change=2, mood=2, hair_loss=1)

        cycles.append({
            "cycle_index": i,
            "start_date": start.isoformat(),
            "cycle_length_days": length,
            "flow": flow,
            "pain": pain,
            "symptoms": s,
        })
        start += timedelta(days=length)
    return cycles


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    personas = [
        ("regular", "none"),
        ("pcos_pattern", "pcos_pattern"),
        ("anemia_pattern", "anemia_pattern"),
        ("thyroid_pattern", "thyroid_pattern"),
    ]
    manifest = {
        "simulated": True,
        "label": "Simulated / preliminary, public and synthetic data, not real deployment data",
        "note": "v0 hand-shaped personas. expected_flag is the intent, not yet verified against the detector.",
        "personas": [],
    }
    for name, flag in personas:
        rng = random.Random(f"7-{name}")
        (OUT / f"{name}.json").write_text(json.dumps(build(name, rng), indent=2) + "\n", encoding="utf-8")
        manifest["personas"].append({
            "id": name,
            "file": f"{name}.json",
            "expected_flag": flag,
            "first_abnormal_cycle": None if flag == "none" else ONSET,
            "intended_flag_by_cycle": None if flag == "none" else INTENDED_FLAG_BY,
        })
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(personas)} personas and manifest to {OUT}")


if __name__ == "__main__":
    main()
