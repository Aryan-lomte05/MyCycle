#!/usr/bin/env python3
"""Download the real cycle-length dataset used to validate the simulator (package A1 follow-up).

This resolves the open question in docs/OPEN_QUESTIONS.md (2026-09-26): does a real cycle-length
dataset exist to check sim/simulator.py's assumptions against. It does: "FedCycleData" on Kaggle
(nikitabisht/menstrual-cycle-data), 159 women, 1,665 cycles, natural family planning charting data.
Provenance beyond the Kaggle page is UNVERIFIED (the uploader gives no paper or citation); use it for
marginal comparison only, not as a cited clinical source. Licence on Kaggle is listed "unknown", so
this file is not committed and is used for read-only comparison, never redistributed.

Needs a Kaggle API token at ~/.kaggle/kaggle.json.

Run: python data/download_cycle_calibration.py
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "menstrual_cycle_data"
DATASET = "nikitabisht/menstrual-cycle-data"
FILENAME = "FedCycleData071012 (2).csv"

EXPECTED_SHA256 = {
    FILENAME: "9fa76583129db58af44adb21a0612217b207120fb61d478fb343a61291732a89",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    have = (RAW / FILENAME).exists()
    if not have:
        result = subprocess.run([sys.executable, "-m", "kaggle", "datasets", "download", "-d", DATASET,
                                 "-p", str(RAW)], capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stdout, result.stderr)
            print("Download failed. Check ~/.kaggle/kaggle.json and that the Kaggle CLI is installed.")
            return 1
        zip_path = RAW / "menstrual-cycle-data.zip"
        if zip_path.exists():
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(RAW)
            zip_path.unlink(missing_ok=True)

    got = sha256(RAW / FILENAME)
    expected = EXPECTED_SHA256[FILENAME]
    if got != expected:
        print(f"{FILENAME}: MISMATCH ({got}), expected {expected}. Upstream file changed; update this script and the data register.")
        return 1
    print(f"{FILENAME}: OK ({got})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
