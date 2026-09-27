#!/usr/bin/env python3
"""Download the Kaggle PCOS dataset and verify its checksum (package A3, data register D4).

Needs a Kaggle API token at ~/.kaggle/kaggle.json (https://www.kaggle.com/docs/api). Not committed:
raw data is gitignored (CLAUDE.md rule: no raw data in the repo) and the dataset licence
(CC-BY-NC-SA-4.0) restricts redistribution anyway.

Run: python data/download_pcos.py
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DATASET = "prasoonkottarathil/polycystic-ovary-syndrome-pcos"

# Recorded on first download (2026-09-27) and checked on every rerun so a changed upstream file is caught.
EXPECTED_SHA256 = {
    "PCOS_data_without_infertility.xlsx": "b663ec9f491be419718e0935eb1c5b6c4923b527282230a73cfc9aca8533f742",
    "PCOS_infertility.csv": "2e4f06b6dc68450c0e05d7a433dabd4ff50ad2edb7e9302d6103449a95b63ad3",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    zip_path = RAW / "polycystic-ovary-syndrome-pcos.zip"
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
    print("PCOS dataset ready in data/raw/. See data/DATA_REGISTER.md for the full registration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
