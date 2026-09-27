"""Demo personas drawn from the simulator and verified against the Tier 1 hybrid detector.

Replaces the hand-shaped v0 personas (scripts/make_demo_users.py). For each persona, simulator draws
are tried in a fixed order and the first one that meets every acceptance rule is kept:
  regular          the hybrid never raises a flag
  pattern personas no flag before onset, the intended flag within 2 cycles of onset, the intended flag
                   on the last cycle, and never a different pattern flag
The hybrid uses the thresholds tuned on the validation split (results/thresholds.json).
The manifest records the expected flag for every cycle so the app and the TypeScript port can be checked.

Run: python -m sim.make_personas   (after python -m sim.detection_eval)
"""
from __future__ import annotations

import json
from dataclasses import replace

import numpy as np

from sim.common import LABEL, ROOT, base_meta
from sim.detectors import HybridDetector
from sim.simulator import SimConfig, draw_user, simulate_user

OUT = ROOT / "exports" / "demo_users"
SEED = 42
N_CYCLES = 12
MAX_TRIES = 20000
PERSONAS = [("regular", "none"), ("pcos_pattern", "pcos_pattern"), ("anemia_pattern", "anemia_pattern"),
            ("thyroid_pattern", "thyroid_pattern")]
PATTERNS = {"pcos_pattern", "anemia_pattern", "thyroid_pattern"}


def hybrid_params() -> dict:
    t = json.loads((ROOT / "results" / "thresholds.json").read_text(encoding="utf-8"))
    return t["chosen"]["hybrid"]["params"]


def to_logs(rows: list[dict]) -> list[dict]:
    keys = ["acne", "excess_hair", "hair_loss", "fatigue", "mood", "weight_change", "dizziness", "pallor"]
    return [{"cycle_index": r["cycle_index"], "start_date": r["start_date"], "cycle_length_days": r["cycle_length_days"],
             "flow": r["flow"], "pain": r["pain"], "symptoms": {k: r[k] for k in keys}} for r in rows]


def flags_for(logs: list[dict], params: dict) -> list[dict]:
    det = HybridDetector(**params)
    return [det.update(c) for c in logs]


def accept(persona: str, expected: str, u: dict, logs: list[dict], outs: list[dict]) -> int | None:
    """Return the first cycle showing the intended flag (0 for regular) if the draw qualifies, else None."""
    flags = [o["flag"] for o in outs]
    if expected == "none":
        ok = all(f == "none" for f in flags) and 26 <= u["mu"] <= 31 and u["sigma"] <= 2.0
        return 0 if ok else None
    k = u["onset_cycle"]
    if k is None or not 5 <= k <= 7:
        return None
    if any(f != "none" for f in flags[:k - 1]):
        return None
    if any(f in PATTERNS and f != expected for f in flags) or flags[-1] != expected:
        return None
    hits = [i + 1 for i, f in enumerate(flags) if f == expected]
    if hits[0] > k + 2:
        return None
    if persona == "pcos_pattern":  # keeps the v0 shape check in tests/test_contracts.py true
        lengths = [c["cycle_length_days"] for c in logs]
        if max(lengths[:5]) > 31 or max(lengths[5:]) < 38:
            return None
    return hits[0]


def find(persona: str, expected: str, params: dict, cfg: SimConfig) -> dict:
    for n in range(MAX_TRIES):
        rng = np.random.default_rng([SEED, 7, PERSONAS.index((persona, expected)), n])
        u = draw_user(cfg, expected if expected != "none" else "none", rng)
        logs = to_logs(simulate_user(cfg, u, rng))
        outs = flags_for(logs, params)
        first = accept(persona, expected, u, logs, outs)
        if first is not None:
            return {"draw": n, "user": u, "logs": logs, "outs": outs, "first": first}
    raise RuntimeError(f"no qualifying draw for {persona} in {MAX_TRIES} tries")


def main() -> None:
    params = hybrid_params()
    cfg = replace(SimConfig(), min_cycles=N_CYCLES, max_cycles=N_CYCLES, missing_rate=0.0)
    manifest = {
        "meta": {**base_meta(SEED), "generator": "sim/make_personas.py", "detector": "hybrid", "detector_params": params,
                 "thresholds_file": "results/thresholds.json"},
        "simulated": True,
        "label": LABEL,
        "note": "Simulator-derived personas. expected_flags is what the Tier 1 hybrid detector returns on each cycle, "
                "checked by tests/test_demo_users.py. Not real people.",
        "personas": [],
    }
    for persona, expected in PERSONAS:
        hit = find(persona, expected, params, cfg)
        (OUT / f"{persona}.json").write_text(json.dumps(hit["logs"], indent=2) + "\n", encoding="utf-8")
        u = hit["user"]
        manifest["personas"].append({
            "id": persona,
            "file": f"{persona}.json",
            "expected_flag": expected,
            "first_abnormal_cycle": u["onset_cycle"],
            "intended_flag_by_cycle": hit["first"] or None,
            "expected_flags": [o["flag"] for o in hit["outs"]],
            "expected_confidence": [o["confidence"] for o in hit["outs"]],
            "simulator_draw": hit["draw"],
            "latent": {"mu": round(u["mu"], 3), "sigma": round(u["sigma"], 3), "length_shift": round(u["length_shift"], 3),
                       "flow_shift": round(u["flow_shift"], 3), "ramp_cycles": u["ramp"]},
        })
        print(persona, "draw", hit["draw"], [o["flag"] for o in hit["outs"]])
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
