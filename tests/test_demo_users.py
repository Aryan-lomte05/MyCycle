"""Demo personas provably trigger their intended flags under the tuned Tier 1 hybrid detector."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sim.detectors import HybridDetector  # noqa: E402

MANIFEST = json.loads((ROOT / "exports/demo_users/manifest.json").read_text(encoding="utf-8"))
PERSONAS = MANIFEST["personas"]
pytestmark = pytest.mark.skipif("expected_flags" not in PERSONAS[0], reason="v0 personas, not simulator-derived yet")


def run(persona):
    logs = json.loads((ROOT / "exports/demo_users" / persona["file"]).read_text(encoding="utf-8"))
    det = HybridDetector(**MANIFEST["meta"]["detector_params"])
    return [det.update(c) for c in logs]


def test_manifest_uses_the_tuned_thresholds():
    t = json.loads((ROOT / "results/thresholds.json").read_text(encoding="utf-8"))
    assert MANIFEST["meta"]["detector_params"] == t["chosen"]["hybrid"]["params"]
    assert MANIFEST["simulated"] is True


@pytest.mark.parametrize("persona", PERSONAS, ids=[p["id"] for p in PERSONAS])
def test_persona_flags_match_manifest(persona):
    outs = run(persona)
    assert [o["flag"] for o in outs] == persona["expected_flags"]
    assert [o["confidence"] for o in outs] == persona["expected_confidence"]


@pytest.mark.parametrize("persona", PERSONAS, ids=[p["id"] for p in PERSONAS])
def test_persona_triggers_intended_flag(persona):
    flags = [o["flag"] for o in run(persona)]
    want = persona["expected_flag"]
    if want == "none":
        assert set(flags) == {"none"}
        return
    onset = persona["first_abnormal_cycle"]
    assert all(f == "none" for f in flags[:onset - 1])
    assert flags[persona["intended_flag_by_cycle"] - 1] == want
    assert flags[-1] == want
    others = {"pcos_pattern", "anemia_pattern", "thyroid_pattern"} - {want}
    assert not others & set(flags)
