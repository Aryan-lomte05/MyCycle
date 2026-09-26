"""The slide checker passes a good deck and rejects the problems sir flagged."""
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

pptx = pytest.importorskip("pptx")
from pptx.util import Inches, Pt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_slides.py"


def make_png(path: Path) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"\x00\xff\xff\xff"
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def add_text(slide, text, size, top=1.0):
    box = slide.shapes.add_textbox(Inches(0.5), Inches(top), Inches(9), Inches(1))
    run = box.text_frame.paragraphs[0].add_run()
    run.text = text
    run.font.size = Pt(size)
    return box


def build(path: Path, *, font=20, caption=True, name=True, existing=True) -> Path:
    prs = pptx.Presentation()
    blank = prs.slide_layouts[6]
    s1 = prs.slides.add_slide(blank)
    add_text(s1, "MyCycle: private screening" if name else "Private screening", 36)
    s2 = prs.slides.add_slide(blank)
    add_text(s2, "Existing apps use population averages" if existing else "Apps use averages", font)
    add_text(s2, "FedAvg with differential privacy", font, top=2.0)
    s3 = prs.slides.add_slide(blank)
    png = path.parent / "x.png"
    make_png(png)
    s3.shapes.add_picture(str(png), Inches(1), Inches(1), width=Inches(2))
    if caption:
        add_text(s3, "Fig. 1: Cycle length with personal band. Simulated / preliminary.", 14, top=4.0)
    prs.save(str(path))
    return path


def run(deck: Path):
    return subprocess.run([sys.executable, str(SCRIPT), str(deck)], capture_output=True, text=True)


def test_good_deck_passes(tmp_path):
    r = run(build(tmp_path / "good.pptx"))
    assert r.returncode == 0, r.stdout
    assert "check_slides: OK" in r.stdout


def test_small_font_fails(tmp_path):
    r = run(build(tmp_path / "small.pptx", font=10))
    assert r.returncode == 1
    assert "below 18 pt" in r.stdout


def test_missing_caption_fails(tmp_path):
    r = run(build(tmp_path / "nocap.pptx", caption=False))
    assert r.returncode == 1
    assert "no numbered caption" in r.stdout


def test_missing_name_and_existing_fail(tmp_path):
    r = run(build(tmp_path / "words.pptx", name=False, existing=False))
    assert r.returncode == 1
    assert "MyCycle" in r.stdout and "existing" in r.stdout
