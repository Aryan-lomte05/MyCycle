"""NFHS classifier orchestration tests (package A3 extension): kept fast with tiny subsamples/seeds."""
import sys
from pathlib import Path

import pytest
from jsonschema import Draft7Validator
import json

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sim.nfhs_data import RAW_CSV, load, stratified_subsample  # noqa: E402

pytestmark = pytest.mark.skipif(not RAW_CSV.exists(), reason="raw NFHS-5 data not present, run data/download_nfhs5.py")

from sim.nfhs_classifiers import MODELS, rows_for_task  # noqa: E402

SCHEMA = json.loads((ROOT / "results/summary.schema.json").read_text(encoding="utf-8"))
CLASSIFIER_ITEM = Draft7Validator(SCHEMA["properties"]["classifiers"]["items"])


def test_svm_rbf_excluded():
    assert "svm_rbf" not in MODELS
    assert len(MODELS) == 7


@pytest.mark.parametrize("task", ["anemia", "thyroid"])
def test_rows_for_task_conform_to_schema_and_cover_both_feature_sets(task):
    full = load()
    small = stratified_subsample(full, task, 400, seed=0)
    rows, comparisons = rows_for_task(small, task, models=["logistic_regression", "naive_bayes"], seeds=[0])
    assert {r["feature_set"] for r in rows} == {"symptom_only", "symptom_plus_vitals"}
    for r in rows:
        CLASSIFIER_ITEM.validate(r)
        assert r["dataset"] == f"nfhs5_{task}"
    assert len(comparisons) == 2
    for c in comparisons:
        assert 0.0 <= c["p_value"] <= 1.0
