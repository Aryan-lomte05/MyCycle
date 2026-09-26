#!/usr/bin/env python3
"""Check a .pptx deck against the slide standards in requirements.md section 12.

These come from the faculty feedback in docs/SIR_FEEDBACK.md.

Errors (exit code 1):
  - text smaller than 18 pt (captions and sources 14 pt; footers and slide numbers 12 pt)
  - a picture, chart or table without a numbered caption ("Fig. N:" or "Table N:") on the same slide
  - the deck never mentions MyCycle, the word "existing", or FedAvg
Warnings (do not fail):
  - a slide with more than 90 words of body text
  - a table with more than 6 data rows or 4 columns
  - text whose size is inherited, so it cannot be checked (set sizes explicitly)

Decorative pictures: name the shape starting with "decor" to exempt it. Slide 1 is exempt from captions.

Run: python scripts/check_slides.py [deck.pptx ...]   (default: every .pptx in docs/slides/)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
except ImportError:
    print("python-pptx is required: pip install python-pptx")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
MIN_BODY, MIN_CAPTION, MIN_FOOTER = 18, 14, 12
MAX_WORDS, MAX_ROWS, MAX_COLS = 90, 6, 4
CAPTION_RE = re.compile(r"^\s*(Fig\.|Figure|Table)\s*\d+\s*[:.]", re.I)
FOOTER_TYPES = {PP_PLACEHOLDER.FOOTER, PP_PLACEHOLDER.SLIDE_NUMBER, PP_PLACEHOLDER.DATE}
REQUIRED_WORDS = {
    "mycycle": "the app name (MyCycle)",
    "existing": 'the word "existing" (existing systems or apps)',
    "fedavg": "the named algorithm FedAvg",
}


def walk(shapes):
    for s in shapes:
        yield s
        if s.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from walk(s.shapes)


def is_footer(shape) -> bool:
    if not shape.is_placeholder:
        return False
    try:
        return shape.placeholder_format.type in FOOTER_TYPES
    except (ValueError, AttributeError):
        return False


def paragraphs_of(shape):
    if shape.has_text_frame:
        yield from shape.text_frame.paragraphs
    if getattr(shape, "has_table", False) and shape.has_table:
        for row in shape.table.rows:
            for cell in row.cells:
                yield from cell.text_frame.paragraphs


def check_deck(path: Path) -> tuple[list[str], list[str]]:
    prs = Presentation(str(path))
    errors: list[str] = []
    warnings: list[str] = []
    all_text: list[str] = []

    for n, slide in enumerate(prs.slides, 1):
        shapes = list(walk(slide.shapes))
        caption_present = any(
            s.has_text_frame and CAPTION_RE.match(s.text_frame.text or "") for s in shapes
        )
        needs_caption = False
        body_words = 0
        inherited = 0

        for s in shapes:
            name = (s.name or "").lower()
            is_visual = s.shape_type == MSO_SHAPE_TYPE.PICTURE or getattr(s, "has_chart", False) and s.has_chart
            is_table = getattr(s, "has_table", False) and s.has_table
            if (is_visual or is_table) and not name.startswith("decor") and n != 1:
                needs_caption = True

            if is_table:
                rows, cols = len(s.table.rows), len(s.table.columns)
                if rows - 1 > MAX_ROWS or cols > MAX_COLS:
                    warnings.append(f"slide {n}: table is {rows - 1} data rows x {cols} columns (max {MAX_ROWS} x {MAX_COLS}); split it or move it to an appendix")

            footer = is_footer(s)
            for p in paragraphs_of(s):
                text = "".join(r.text for r in p.runs).strip()
                if not text:
                    continue
                all_text.append(text)
                is_caption = bool(CAPTION_RE.match(text)) or text.lower().startswith("source")
                limit = MIN_FOOTER if footer else (MIN_CAPTION if is_caption else MIN_BODY)
                if not footer and not is_caption and not is_table:
                    body_words += len(text.split())
                for r in p.runs:
                    if not r.text.strip():
                        continue
                    size = r.font.size or p.font.size
                    if size is None:
                        inherited += 1
                    elif size.pt < limit:
                        errors.append(f"slide {n}: text at {size.pt:g} pt is below {limit} pt: \"{text[:50]}\"")
                        break

        if needs_caption and not caption_present and n != 1:
            errors.append(f'slide {n}: a figure, chart or table has no numbered caption (start a text box with "Fig. N:" or "Table N:")')
        if body_words > MAX_WORDS:
            warnings.append(f"slide {n}: about {body_words} words of body text (aim for 60 or fewer)")
        if inherited:
            warnings.append(f"slide {n}: {inherited} text run(s) inherit their size, so it cannot be verified; set font sizes explicitly")

    blob = " ".join(all_text).lower()
    for word, meaning in REQUIRED_WORDS.items():
        if word not in blob:
            errors.append(f"deck: never mentions {meaning}")
    return errors, warnings


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    decks = [Path(a) for a in args] or sorted((ROOT / "docs" / "slides").glob("*.pptx"))
    if not decks:
        print("check_slides: no .pptx found in docs/slides/ (export the deck as .pptx first)")
        return 1
    failed = False
    for d in decks:
        errors, warnings = check_deck(d)
        print(f"{d.name}: {len(errors)} error(s), {len(warnings)} warning(s)")
        for w in warnings:
            print("  warning: " + w)
        for e in errors:
            print("  ERROR: " + e)
        failed = failed or bool(errors)
    print("check_slides: FAILED" if failed else "check_slides: OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
