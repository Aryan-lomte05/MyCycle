#!/usr/bin/env python3
"""Cross-platform equivalent of `make check` (works on Windows without make).

Runs: language lint, contract validation, unit tests. Add --strict for the Sunday acceptance
test (fails if any placeholder remains in results/summary.json).

Run: python scripts/check.py [--strict]
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
strict = ["--strict"] if "--strict" in sys.argv else []

steps = [
    ("language lint", [sys.executable, "scripts/lint_language.py"]),
    ("contracts", [sys.executable, "scripts/validate_contracts.py", *strict]),
]
if list((ROOT / "docs" / "slides").glob("*.pptx")):
    steps.append(("slide standards", [sys.executable, "scripts/check_slides.py"]))
if list((ROOT / "tests").glob("test_*.py")):
    steps.append(("tests", [sys.executable, "-m", "pytest", "-q", "tests"]))

failed = []
for name, cmd in steps:
    print(f"== {name}")
    if subprocess.run(cmd, cwd=ROOT).returncode != 0:
        failed.append(name)

print()
if failed:
    print("CHECK FAILED: " + ", ".join(failed))
    sys.exit(1)
print("CHECK OK")
