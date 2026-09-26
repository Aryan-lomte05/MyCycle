"""Constants and run metadata shared by every sim/ script."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABEL = "Simulated / preliminary, public and synthetic data, not real deployment data"
SYMPTOMS = ["acne", "excess_hair", "hair_loss", "fatigue", "mood", "weight_change", "dizziness", "pallor"]
FEATURES = ["cycle_length_days", "flow", "pain", *SYMPTOMS]


def git_commit() -> str:
    """HEAD commit, suffixed with -dirty when the working tree has uncommitted changes."""
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return head + ("-dirty" if dirty else "")


def base_meta(seed: int) -> dict:
    """Meta block carried by every results file. No timestamp here so outputs stay byte-identical."""
    return {"seed": seed, "git_commit": git_commit(), "simulated": True, "label": LABEL}
