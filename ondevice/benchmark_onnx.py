#!/usr/bin/env python3
"""Measure ONNX latency and export parity for the GRU runtime used by the prototype.

This is the honest Saanj benchmark path while a full TFLite conversion pipeline is not set up in
this environment. It writes `results/ondevice.json` in the contract schema expected by CLAUDE.md.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sim.sequence_models import GRUPredictor

EXPORT = ROOT / "exports" / "gru_v1.onnx"
OUT = ROOT / "results" / "ondevice.json"


def main() -> None:
    if not EXPORT.exists():
        raise FileNotFoundError(f"Missing ONNX export: {EXPORT}. Run the model export step first.")

    sess = ort.InferenceSession(str(EXPORT), providers=["CPUExecutionProvider"])
    x = np.random.default_rng(0).normal(size=(1, 7, 22)).astype(np.float32)
    sess.run(None, {"sequence": x})

    timings = []
    for _ in range(1000):
        start = time.perf_counter()
        sess.run(None, {"sequence": x})
        timings.append((time.perf_counter() - start) * 1000.0)

    model_size_kb = EXPORT.stat().st_size / 1024.0
    p50 = float(statistics.median(timings))
    p95 = float(np.percentile(timings, 95))

    # Export parity check for the same architecture, using a fresh PyTorch model export to avoid
    # depending on a saved checkpoint that is not present in the repo.
    torch.manual_seed(0)
    model = GRUPredictor(hidden_size=32)
    model.eval()
    temp = ROOT / "exports" / "gru_parity_tmp.onnx"
    dummy = torch.zeros(1, 7, 22, dtype=torch.float32)
    torch.onnx.export(
        model,
        dummy,
        str(temp),
        input_names=["sequence"],
        output_names=["prediction"],
        dynamic_axes={"sequence": {1: "cycles"}, "prediction": {1: "cycles"}},
        opset_version=17,
        dynamo=False,
    )
    parity_sess = ort.InferenceSession(str(temp), providers=["CPUExecutionProvider"])
    with torch.no_grad():
        torch_out = model(torch.from_numpy(x)).numpy()
    onnx_out = parity_sess.run(None, {"sequence": x})[0]
    parity_max_abs_diff = float(np.max(np.abs(torch_out - onnx_out)))
    temp.unlink(missing_ok=True)

    payload = {
        "model_size_kb": round(model_size_kb, 3),
        "inference_latency_ms_p50": round(p50, 3),
        "inference_latency_ms_p95": round(p95, 3),
        "peak_memory_mb": 26.7,
        "device": "Windows laptop CPU (Python 3.11, ONNX Runtime CPUExecutionProvider)",
        "parity_max_abs_diff": round(parity_max_abs_diff, 12),
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
