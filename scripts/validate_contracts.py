#!/usr/bin/env python3
"""Validate the frozen interface contracts (CLAUDE.md section 5).

Validates:
  - results/summary.json against results/summary.schema.json
  - exports/demo_users/*.json (arrays of cycle log objects) against exports/cycle_log.schema.json
  - exports/examples/*.json against exports/screening_output.schema.json
  - every result section is free of the placeholder flag when run with --strict (acceptance test)

Run: python scripts/validate_contracts.py [--strict]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parent.parent


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def validate(instance, schema, where: str, errors: list[str]) -> None:
    for err in sorted(Draft7Validator(schema).iter_errors(instance), key=lambda e: list(e.path)):
        path = "/".join(str(x) for x in err.path) or "(root)"
        errors.append(f"{where} at {path}: {err.message}")


def find_placeholders(node, trail="") -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        if node.get("placeholder") is True:
            found.append(trail or "(root)")
        for k, v in node.items():
            found += find_placeholders(v, f"{trail}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            found += find_placeholders(v, f"{trail}[{i}]")
    return found


def main() -> int:
    strict = "--strict" in sys.argv
    errors: list[str] = []

    summary_schema = load(ROOT / "results/summary.schema.json")
    summary = load(ROOT / "results/summary.json")
    validate(summary, summary_schema, "results/summary.json", errors)

    if strict:
        for where in find_placeholders(summary):
            errors.append(f"results/summary.json: placeholder still present at {where}")

    cycle_schema = load(ROOT / "exports/cycle_log.schema.json")
    demo_files = sorted((ROOT / "exports/demo_users").glob("[!m]*.json"))
    if not demo_files:
        errors.append("exports/demo_users: no demo user files found")
    for f in demo_files:
        arr = load(f)
        if not isinstance(arr, list) or not arr:
            errors.append(f"{f.name}: must be a non-empty array of cycle log objects")
            continue
        for i, item in enumerate(arr):
            validate(item, cycle_schema, f"{f.name}[{i}]", errors)
        idx = [c.get("cycle_index") for c in arr]
        if idx != list(range(1, len(arr) + 1)):
            errors.append(f"{f.name}: cycle_index must run 1..{len(arr)} in order")

    manifest_path = ROOT / "exports/demo_users/manifest.json"
    if manifest_path.exists():
        manifest = load(manifest_path)
        for persona in manifest.get("personas", []):
            if not (ROOT / "exports/demo_users" / persona["file"]).exists():
                errors.append(f"manifest: file {persona['file']} missing")
    else:
        errors.append("exports/demo_users/manifest.json missing")

    screening_schema = load(ROOT / "exports/screening_output.schema.json")
    for f in sorted((ROOT / "exports/examples").glob("*.json")):
        validate(load(f), screening_schema, f"exports/examples/{f.name}", errors)

    if errors:
        print(f"validate_contracts: {len(errors)} problem(s)")
        for e in errors:
            print("  " + e)
        return 1
    note = " (strict: no placeholders)" if strict else " (placeholders allowed until acceptance test)"
    print("validate_contracts: OK" + note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
