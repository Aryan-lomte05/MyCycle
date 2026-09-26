#!/usr/bin/env python3
"""Language and labeling lint. Enforces the non-negotiable rules in CLAUDE.md section 2.

Checks:
  1. No em dashes anywhere in text files.
  2. In user-facing scopes (app, content, docs/slides, docs/paper): "diagnos*" only in allowed
     contexts (negations, describing doctors), and no unsupported superiority wording.
  3. Every results JSON with a "meta" block is labeled simulated with the standard label.

Exit code 1 on any violation. Run: python scripts/lint_language.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EM_DASH = chr(0x2014)
LABEL = "Simulated / preliminary, public and synthetic data, not real deployment data"

TEXT_EXT = {".md", ".json", ".py", ".ts", ".tsx", ".js", ".jsx", ".txt", ".csv", ".yml", ".yaml", ".html", ".css", ".toml"}
SKIP_DIRS = {".git", "node_modules", ".next", "__pycache__", ".pytest_cache", ".venv", "raw", "out"}
SKIP_PATHS = ("docs/source/",)  # verbatim originals, kept unedited
USER_FACING = ["app", "content", "docs/slides", "docs/paper", "docs/video"]

DIAGNOS = re.compile(r"diagnos", re.I)
DIAGNOS_OK = re.compile(
    r"\b(not|never|no|non|without|nor)\b|non-|clinician|doctor|physician|gynecolog|medical professional|hospital",
    re.I,
)
BANNED = re.compile(r"better than|\bbeats?\b|outperform|zero[- ]leak|100% (private|accurate)|perfect(ly)? accura|world.s best|best in the world|rules the world|clinically proven|ai doctor|everything (stays|is stored|is kept) on (your|the) phone", re.I)
BANNED_OK = re.compile(r"\b(never|not|no|do not|don't|without)\b", re.I)


def iter_files():
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXT:
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            continue
        if p.relative_to(ROOT).as_posix().startswith(SKIP_PATHS):
            continue
        yield p


def in_user_facing(p: Path) -> bool:
    rel = p.relative_to(ROOT).as_posix()
    return any(rel == s or rel.startswith(s + "/") for s in USER_FACING)


def main() -> int:
    errors: list[str] = []

    for p in iter_files():
        rel = p.relative_to(ROOT).as_posix()
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if EM_DASH in line:
                errors.append(f"{rel}:{n}: em dash found (use comma, colon or hyphen)")
            if in_user_facing(p):
                if DIAGNOS.search(line) and not DIAGNOS_OK.search(line):
                    errors.append(f"{rel}:{n}: 'diagnos*' outside an allowed context: {line.strip()[:100]}")
                if BANNED.search(line) and not BANNED_OK.search(line):
                    errors.append(f"{rel}:{n}: unsupported superiority or absolute claim: {line.strip()[:100]}")

    for p in sorted((ROOT / "results").glob("*.json")):
        if p.name.endswith(".schema.json"):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"results/{p.name}: invalid JSON ({e})")
            continue
        meta = data.get("meta") if isinstance(data, dict) else None
        if meta is None:
            continue
        if meta.get("simulated") is not True:
            errors.append(f"results/{p.name}: meta.simulated must be true")
        if meta.get("label") != LABEL:
            errors.append(f"results/{p.name}: meta.label missing or not the standard label")

    if errors:
        print(f"lint_language: {len(errors)} problem(s)")
        for e in errors:
            print("  " + e)
        return 1
    print("lint_language: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
