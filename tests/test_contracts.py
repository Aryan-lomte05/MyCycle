"""Contract tests: the frozen schemas accept valid objects and reject invalid ones."""
import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parent.parent


def schema(rel):
    return Draft7Validator(json.loads((ROOT / rel).read_text(encoding="utf-8")))


def test_placeholder_summary_is_valid():
    v = schema("results/summary.schema.json")
    v.validate(json.loads((ROOT / "results/summary.json").read_text(encoding="utf-8")))


def test_summary_rejects_unlabeled_or_non_simulated():
    v = schema("results/summary.schema.json")
    data = json.loads((ROOT / "results/summary.json").read_text(encoding="utf-8"))
    bad = copy.deepcopy(data)
    bad["meta"]["simulated"] = False
    with pytest.raises(Exception):
        v.validate(bad)
    bad = copy.deepcopy(data)
    bad["meta"]["label"] = "real data"
    with pytest.raises(Exception):
        v.validate(bad)


def test_cycle_log_ranges_enforced():
    v = schema("exports/cycle_log.schema.json")
    good = json.loads((ROOT / "exports/demo_users/regular.json").read_text(encoding="utf-8"))[0]
    v.validate(good)
    for field, value in [("flow", 4), ("pain", 11)]:
        bad = copy.deepcopy(good)
        bad[field] = value
        with pytest.raises(Exception):
            v.validate(bad)
    bad = copy.deepcopy(good)
    bad["symptoms"]["acne"] = 4
    with pytest.raises(Exception):
        v.validate(bad)
    bad = copy.deepcopy(good)
    bad["symptoms"]["extra_field"] = 1
    with pytest.raises(Exception):
        v.validate(bad)


def test_demo_personas_shape():
    manifest = json.loads((ROOT / "exports/demo_users/manifest.json").read_text(encoding="utf-8"))
    flags = {p["id"]: p["expected_flag"] for p in manifest["personas"]}
    assert flags == {
        "regular": "none",
        "pcos_pattern": "pcos_pattern",
        "anemia_pattern": "anemia_pattern",
        "thyroid_pattern": "thyroid_pattern",
    }
    pcos = json.loads((ROOT / "exports/demo_users/pcos_pattern.json").read_text(encoding="utf-8"))
    assert max(c["cycle_length_days"] for c in pcos[5:]) >= 38
    assert all(c["cycle_length_days"] <= 31 for c in pcos[:5])
