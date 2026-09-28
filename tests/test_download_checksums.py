"""Every EXPECTED_SHA256 in a data/download_*.py script is a real 64-char hex digest, and matches
the file on disk when present. Catches transcription bugs (an off-by-one-character truncation
silently makes every future download fail its own check with a false MISMATCH)."""
import hashlib
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def download_scripts():
    return sorted((ROOT / "data").glob("download_*.py"))


@pytest.mark.parametrize("script", download_scripts(), ids=lambda p: p.name)
def test_expected_hashes_are_well_formed(script):
    text = script.read_text(encoding="utf-8")
    hashes = re.findall(r'"([0-9a-fA-F]{40,70})"', text)
    assert hashes, f"{script.name}: no EXPECTED_SHA256 hash found"
    for h in hashes:
        assert HEX64.match(h), f"{script.name}: {h!r} is not a 64-character hex sha256 digest (len={len(h)})"


@pytest.mark.parametrize("script", download_scripts(), ids=lambda p: p.name)
def test_expected_hashes_match_files_on_disk_when_present(script):
    import importlib.util

    spec = importlib.util.spec_from_file_location(script.stem, script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    raw_dir = mod.RAW
    for name, expected in mod.EXPECTED_SHA256.items():
        path = raw_dir / name
        if not path.exists():
            pytest.skip(f"{path} not downloaded in this environment")
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        assert got == expected, f"{script.name}: {name} sha256 mismatch (recorded {expected}, actual {got})"
