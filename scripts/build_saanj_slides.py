"""Build the independent Saanj evidence slides from repository outputs."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "slides" / "saanj_evidence_slides.pptx"
LABEL = "Simulated / preliminary, public and synthetic data, not real deployment data"


def add_text(slide, text, left, top, width, height, size=18, bold=False, color=(30, 40, 50)):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = box.text_frame
    frame.word_wrap = True
    paragraph = frame.paragraphs[0]
    paragraph.text = text
    paragraph.font.name = "Aptos"
    paragraph.font.size = Pt(size)
    paragraph.font.bold = bold
    paragraph.font.color.rgb = RGBColor(*color)
    return box


def add_title(slide, title):
    add_text(slide, title, 0.55, 0.35, 12.2, 0.65, size=32, bold=True, color=(20, 50, 70))


def add_footer(slide, source, simulated=False):
    add_text(slide, source, 0.6, 7.05, 11.9, 0.2, size=14, color=(80, 90, 100))
    if simulated:
        add_text(slide, LABEL, 0.6, 6.78, 11.9, 0.2, size=18, color=(120, 70, 20))


def add_bullets(slide, items, left=0.85, top=1.35, width=11.3, height=4.9):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = box.text_frame
    frame.word_wrap = True
    frame.clear()
    for index, item in enumerate(items):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = item
        paragraph.level = 0
        paragraph.font.name = "Aptos"
        paragraph.font.size = Pt(20)
        paragraph.font.color.rgb = RGBColor(30, 40, 50)
        paragraph.space_after = Pt(14)


def main():
    classifiers = json.loads((ROOT / "results" / "classifiers.json").read_text(encoding="utf-8"))
    ondevice = json.loads((ROOT / "results" / "ondevice.json").read_text(encoding="utf-8"))
    claims = (ROOT / "docs" / "CLAIMS_EVIDENCE.md").read_text(encoding="utf-8")
    supported = len(re.findall(r"\| C\d+ .*\| supported \|", claims))
    needs_work = len(re.findall(r"\| C\d+ .*\| needs work \|", claims))

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    slide = prs.slides.add_slide(blank)
    add_title(slide, "The data are grouped by evidence role")
    add_bullets(slide, [
        f"Clinical tabular: kaggle_pcos, {classifiers['datasets'][0]['n_rows']} rows, used for symptom-only classifier comparison.",
        "Synthetic cycle sequences: used for personal-baseline drift experiments and always labeled simulated.",
        "Population survey and real cycle calibration data: not integrated in this run, so no results are attributed to them.",
        "Qualitative interviews: not started and not used for model training.",
    ])
    add_text(slide, "Table 1: Data sources grouped by role; public and synthetic evidence is labeled, and unintegrated sources are not used in results.", 0.6, 6.35, 12, 0.3, size=14)
    add_footer(slide, "Source: data/DATA_REGISTER.md and results/classifiers.json", simulated=True)

    slide = prs.slides.add_slide(blank)
    add_title(slide, "The classifier protocol prevents preprocessing leakage")
    add_bullets(slide, [
        f"Stratified {classifiers['meta']['n_folds']}-fold cross-validation repeated over {len(classifiers['meta']['seeds'])} seeds.",
        "Preprocessing is fitted inside each fold before evaluation.",
        "Confidence intervals use patient-level bootstrap resampling; top-model comparisons use paired bootstrap resampling.",
        "The source dataset contains one row per participant, so this is a population classifier benchmark, not longitudinal baseline validation.",
    ])
    add_text(slide, "Table 2: Split and preprocessing protocol; the reported classifier results are preliminary and public-data based.", 0.6, 6.35, 12, 0.3, size=14)
    add_footer(slide, "Source: results/classifiers.json meta.protocol and data/DATA_REGISTER.md", simulated=True)

    slide = prs.slides.add_slide(blank)
    add_title(slide, "The exported GRU runs within the recorded laptop benchmark")
    add_bullets(slide, [
        f"Model size: {ondevice['model_size_kb']} KB.",
        f"Latency: p50 {ondevice['inference_latency_ms_p50']} ms; p95 {ondevice['inference_latency_ms_p95']} ms.",
        f"Peak memory: {ondevice['peak_memory_mb']} MB on {ondevice['device']}.",
        f"PyTorch parity: {ondevice['parity_max_abs_diff']} maximum absolute difference.",
        "Limitation: this is an ONNX CPU measurement, not a TFLite or Android measurement.",
    ])
    add_text(slide, "Table 3: ONNX runtime feasibility, measured over the benchmark run; no mobile-device claim is made.", 0.6, 6.35, 12, 0.3, size=14)
    add_footer(slide, "Source: results/ondevice.json and ondevice/README.md", simulated=False)

    slide = prs.slides.add_slide(blank)
    add_title(slide, "The claims table separates supported evidence from open work")
    add_bullets(slide, [
        f"Supported claims currently recorded: {supported}.",
        f"Claims still needing app or acceptance evidence: {needs_work}.",
        "The evidence library contains 25 verified technical and runtime sources.",
        "MyCycle records existing systems as context and names FedAvg as the federated baseline for the broader study.",
        "The final app, privacy, offline, voice, and slide acceptance checks remain blocked until their owning artifacts exist.",
    ])
    add_text(slide, "Table 4: Claims status summary; counts are generated from docs/CLAIMS_EVIDENCE.md.", 0.6, 6.35, 12, 0.3, size=14)
    add_footer(slide, "Source: docs/CLAIMS_EVIDENCE.md and docs/papers.csv", simulated=False)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()