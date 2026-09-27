"""Detector tests (package A2): contract output, warm-up, each flag, CUSUM vs z-score, missing data, metrics."""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sim.common import SYMPTOMS  # noqa: E402
from sim.detection_eval import detection_metrics, run_detector  # noqa: E402
from sim.detectors import (  # noqa: E402
    CONTRACT_DETECTORS, CusumDetector, EwmaChartDetector, FixedThresholdDetector, HybridDetector,
    IsolationForestDetector, RuleLayer, ZScoreDetector, make_detector,
)
from sim.simulator import SimConfig, simulate, to_cycle_logs  # noqa: E402

SCHEMA = Draft7Validator(json.loads((ROOT / "exports/screening_output.schema.json").read_text(encoding="utf-8")))


def cycle(i, length=29, flow=2, pain=3, **sym):
    return {"cycle_index": i, "start_date": "2025-01-01", "cycle_length_days": length, "flow": flow, "pain": pain,
            "symptoms": {s: sym.get(s, 0) for s in SYMPTOMS}}


def baseline(n=6):
    lengths = [28, 30, 29, 28, 30, 29, 28, 30]
    return [cycle(i + 1, lengths[i % len(lengths)]) for i in range(n)]


def feed(det, cycles):
    return [det.update(c) for c in cycles]


# contract and warm-up ------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["zscore", "cusum", "hybrid"])
def test_contract_detectors_emit_valid_screening_output(name):
    cycles, _ = simulate(SimConfig(n_users=10, missing_rate=0.0), seed=3)
    for _, df in cycles.groupby("user_id"):
        det = make_detector(name)
        for out in feed(det, to_cycle_logs(df)):
            SCHEMA.validate(out)
            assert out["simulated"] is True
            assert out["message_key"] == f"flag.{out['flag']}.v1"
            assert out["detector"] in CONTRACT_DETECTORS


def test_no_flags_during_warm_up():
    det = ZScoreDetector(threshold=2.0)
    outs = feed(det, [cycle(1, 29), cycle(2, 29), cycle(3, 60, flow=3, acne=3)])
    assert all(o["flag"] == "none" for o in outs)


def test_regular_history_stays_none():
    for name in ["fixed_threshold", "zscore", "ewma", "cusum", "hybrid"]:
        outs = feed(make_detector(name), baseline(8))
        assert all(o["flag"] == "none" for o in outs), name


# each flag -----------------------------------------------------------------------------------

def test_single_long_cycle_without_symptoms_is_irregularity():
    out = feed(ZScoreDetector(threshold=2.0), baseline(6) + [cycle(7, 40)])[-1]
    assert out["flag"] == "irregularity"
    assert out["contributing_signals"] == ["cycle_length_high"]


def test_pcos_like_history_gives_pcos_pattern():
    drift = [cycle(7, 44, acne=2, excess_hair=2), cycle(8, 46, acne=3, hair_loss=2)]
    out = feed(HybridDetector(), baseline(6) + drift)[-1]
    assert out["flag"] == "pcos_pattern"
    assert "cycle_length_high" in out["contributing_signals"] and "acne_high" in out["contributing_signals"]
    assert out["confidence"] == "high"


def test_anemia_like_history_gives_anemia_pattern():
    drift = [cycle(7, 29, flow=3, fatigue=2, pallor=2), cycle(8, 28, flow=3, dizziness=2, fatigue=3)]
    out = feed(HybridDetector(), baseline(6) + drift)[-1]
    assert out["flag"] == "anemia_pattern"
    assert "flow_high" in out["contributing_signals"]


def test_thyroid_like_history_gives_thyroid_pattern():
    drift = [cycle(7, 22, fatigue=2, weight_change=2), cycle(8, 21, mood=2, fatigue=2)]
    out = feed(HybridDetector(), baseline(6) + drift)[-1]
    assert out["flag"] == "thyroid_pattern"
    assert "cycle_length_low" in out["contributing_signals"]


def test_rule_layer_needs_cycle_signal_and_symptom_signal():
    rl = RuleLayer()
    assert rl.step({"acne_high": 3.0, "excess_hair_high": 3.0})[0] == "none"  # symptoms alone: no pattern
    rl = RuleLayer()
    assert rl.step({"cycle_length_high": 3.0})[0] == "irregularity"
    rl = RuleLayer()
    assert rl.step({"cycle_length_high": 3.0, "hair_loss_high": 2.5})[0] == "pcos_pattern"
    rl = RuleLayer()
    assert rl.step({"flow_high": 3.0})[0] == "none"  # heavy flow alone is not a pattern


def test_rule_layer_uses_recent_symptoms_within_window():
    rl = RuleLayer(window=3)
    rl.step({"acne_high": 3.0})
    rl.step({})
    assert rl.step({"cycle_length_high": 3.0})[0] == "pcos_pattern"
    rl = RuleLayer(window=3)
    rl.step({"acne_high": 3.0})
    rl.step({})
    rl.step({})
    assert rl.step({"cycle_length_high": 3.0})[0] == "irregularity"


# detector behaviour --------------------------------------------------------------------------

def test_fixed_threshold_uses_population_cutoffs_not_history():
    det = FixedThresholdDetector()
    assert det.update(cycle(1, 40))["flag"] == "irregularity"  # no warm-up for a population rule
    assert det.update(cycle(2, 34))["flag"] == "none"
    det = FixedThresholdDetector()
    long_normal = [cycle(i + 1, 37) for i in range(8)]  # a stable 37-day person is flagged every cycle
    assert all(o["flag"] == "irregularity" for o in feed(det, long_normal))
    assert all(o["flag"] == "none" for o in feed(ZScoreDetector(threshold=2.0), [cycle(i + 1, 37 + (i % 2)) for i in range(8)]))


def test_cusum_catches_small_sustained_shift_that_zscore_misses():
    small = [cycle(7 + i, 31) for i in range(6)]
    z = feed(ZScoreDetector(threshold=3.0), baseline(6) + small)
    c = feed(CusumDetector(h=4.0), baseline(6) + small)
    assert all(o["flag"] == "none" for o in z)
    assert any(o["flag"] == "irregularity" for o in c[6:])


def test_ewma_chart_detects_sustained_shift():
    outs = feed(EwmaChartDetector(L=3.0), baseline(6) + [cycle(7 + i, 36) for i in range(4)])
    assert any(o["flag"] == "irregularity" for o in outs[6:])


def test_flagged_cycles_do_not_move_the_baseline():
    det = ZScoreDetector(threshold=2.0)
    outs = feed(det, baseline(6) + [cycle(7 + i, 45) for i in range(5)])
    assert all(o["flag"] == "irregularity" for o in outs[6:])  # drift is not absorbed


def test_missing_values_are_skipped_without_error():
    c = cycle(7, 45)
    c["cycle_length_days"] = None
    c["symptoms"]["acne"] = None
    out = feed(HybridDetector(), baseline(6) + [c])[-1]
    assert out["flag"] == "none"


def test_isolation_forest_flags_a_gross_outlier_after_warm_up():
    # With few, mostly constant per-user features, IF scores stay close to 0.5 even for gross outliers.
    det = IsolationForestDetector(threshold=0.55)
    outs = feed(det, baseline(8) + [cycle(9, 60, flow=3, pain=9, acne=3, excess_hair=3)])
    assert all(o["flag"] == "none" for o in outs[:8])
    assert outs[-1]["flag"] != "none"
    assert outs[-1]["score"] > max(o["score"] for o in outs[:8])


# metrics -------------------------------------------------------------------------------------

def test_detection_metrics_hand_example():
    # two pcos users (onset 5), one none user. Flags chosen by hand.
    rows = []
    def add(uid, drift, onset, flags):
        for i, f in enumerate(flags, 1):
            active = onset is not None and i >= onset
            rows.append({"user_id": uid, "drift_type": drift, "onset_cycle": onset, "cycle_index": i,
                         "drift_active": active, "flag": f})
    add("a", "pcos_pattern", 5, ["none"] * 4 + ["none", "irregularity", "pcos_pattern", "pcos_pattern"])
    add("b", "pcos_pattern", 5, ["irregularity"] + ["none"] * 7)  # false alarm pre-onset, never detected
    add("c", "none", None, ["none"] * 7 + ["irregularity"])
    m = detection_metrics(pd.DataFrame(rows))
    p = m["pcos_pattern"]
    assert p["detection_rate"] == 0.5
    assert p["median_delay_cycles"] == 1.0
    assert p["correct_pattern_rate"] == 0.5
    assert p["median_pattern_delay_cycles"] == 2.0
    assert m["overall"]["false_alarms_per_100_cycles"] == pytest.approx(100 * 2 / 16)  # 4 + 4 + 8 non-drift cycles


def test_benign_persistence_metric():
    rows = []
    flags = ["none"] * 4 + ["irregularity", "none", "irregularity", "irregularity", "none"]
    for i, f in enumerate(flags, 1):
        rows.append({"user_id": "b", "drift_type": "benign_shift", "onset_cycle": 5, "cycle_index": i,
                     "drift_active": i == 5, "flag": f})
    m = detection_metrics(pd.DataFrame(rows))["benign_shift"]
    assert m["detection_rate"] == 1.0
    assert m["persistent_flag_rate"] == 1.0  # flagged on 2 cycles after the shift ended


def test_run_detector_refuses_test_split_for_tuning():
    cycles, _ = simulate(SimConfig(n_users=20), seed=5)
    with pytest.raises(ValueError):
        run_detector(cycles[cycles.split == "test"], "zscore", {"threshold": 2.0}, tuning=True)


def test_isolation_forest_replay_matches_streaming():
    from sim.detection_eval import isolation_forest_raw, replay_isolation_forest

    cycles, _ = simulate(SimConfig(n_users=12), seed=9)
    val = cycles[cycles.split == "val"]
    replay = replay_isolation_forest(val, isolation_forest_raw(val), 0.55, tuning=True)
    stream = run_detector(val, "isolation_forest", {"threshold": 0.55}, tuning=True)
    assert replay["flag"].tolist() == stream["flag"].tolist()
