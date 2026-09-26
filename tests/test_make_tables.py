"""The FL comparison table is generated from results, ordered, labeled and caption-ready."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sim.make_tables import LABEL, build_markdown  # noqa: E402


def summary():
    return json.loads((ROOT / "results" / "summary.json").read_text(encoding="utf-8"))


def test_table_has_all_three_conditions_in_order():
    md = build_markdown(summary())
    for text in ["Without FL: centralized", "Without FL: local only", "With FL: FedAvg", "With FL and DP: FedAvg + DP"]:
        assert text in md
    assert md.index("Without FL: centralized") < md.index("With FL: FedAvg") < md.index("With FL and DP")


def test_placeholders_are_labeled_and_caption_is_present():
    md = build_markdown(summary())
    assert "[PLACEHOLDER]" in md
    assert md.strip().splitlines()[-1].startswith("Table 1:")
    assert LABEL in md


def test_real_rows_show_epsilon_and_no_placeholder_tag():
    s = summary()
    s["federated"] = [{"mode": "fedavg_dp", "noise_multiplier": 1.0, "clip_norm": 1.0, "epsilon": 3.21,
                       "delta": 1e-5, "auc": 0.81234, "accuracy": 0.77, "rounds": 50, "non_iid": True}]
    md = build_markdown(s)
    assert "PLACEHOLDER" not in md
    assert "3.21 (1e-05)" in md and "0.812" in md and "non-IID" in md
