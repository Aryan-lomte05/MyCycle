# On-device feasibility notes

This folder records the honest runtime numbers for the exported GRU model used by the prototype.

## What we measured

- Model file: `exports/gru_v1.onnx`
- Runtime: ONNX Runtime CPUExecutionProvider on the current Windows laptop
- Input shape: `(1, 7, 22)` matching the exported model contract used by the web prototype
- Metric: p50 and p95 inference latency over 1000 runs, plus export parity against a fresh PyTorch export of the same GRU architecture

## Commands

```bash
cd "E:\MyCycle\MyCycle"
"C:\Users\smitp\AppData\Local\Programs\Python\Python311\python.exe" ondevice/benchmark_onnx.py
```

The script writes the measured numbers to `results/ondevice.json`.

## Honest note

TFLite conversion was not run in this workspace because the TensorFlow Lite conversion toolchain was not configured here. The project therefore records the measured ONNX export numbers as the current, reproducible on-device runtime evidence, and the TFLite path remains a separate device benchmark to be run on a mobile toolchain when available.

On 2026-09-28, one local ONNX-to-TFLite attempt was made with `onnx2tf`. The first run stopped because `tf_keras` was missing. After installing the TensorFlow 2.19-compatible `tf-keras` package, the retry stopped because ONNX 1.19.1 required a newer protobuf runtime than the environment provided. No TFLite or Android metric was generated, so the ONNX measurements remain the only reported runtime evidence.
