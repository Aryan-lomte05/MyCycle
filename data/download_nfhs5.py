#!/usr/bin/env python3
"""Download the NFHS-5 dataset and verify its checksum (package A3 extension, data register D4).

NFHS-5 (National Family Health Survey, Round 5, India, 2019-2021) is a real government health
survey, redistributed on Kaggle as a single cleaned CSV (95 columns, 136,136 women aged 15-49).
Licence: CC0-1.0 (public domain), so unlike kaggle_pcos this file could be committed, but CLAUDE.md
keeps all raw data out of the repo regardless.

Needs a Kaggle API token at ~/.kaggle/kaggle.json.

Run: python data/download_nfhs5.py
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "nfhs5"
DATASET = "ravisinghiitbhu/nfhs5"

# Recorded on first download (2026-09-27) and checked on every rerun.
EXPECTED_SHA256 = {
    "Final.csv": "503e36565b41542ec2df5611919cbf3301caccc73997f1699fee819fb5683ecf",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    zip_path = RAW / "nfhs5.zip"
    have_all = all((RAW / name).exists() for name in EXPECTED_SHA256)
    if not have_all:
        result = subprocess.run([sys.executable, "-m", "kaggle", "datasets", "download", "-d", DATASET,
                                 "-p", str(RAW)], capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stdout, result.stderr)
            print("Download failed. Check ~/.kaggle/kaggle.json and that the Kaggle CLI is installed (`pip install kaggle`).")
            return 1
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(RAW)
        zip_path.unlink(missing_ok=True)

    ok = True
    for name, expected in EXPECTED_SHA256.items():
        got = sha256(RAW / name)
        status = "OK" if got == expected else "MISMATCH"
        if got != expected:
            ok = False
        print(f"{name}: {status} ({got})")
    if not ok:
        print("Checksum mismatch: the upstream dataset changed. Update data/DATA_REGISTER.md and this script before using it.")
        return 1
    print("NFHS-5 ready in data/raw/nfhs5/. See data/DATA_REGISTER.md for the full registration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
