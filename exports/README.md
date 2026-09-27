# Exports for the app (Liza)

Everything here is versioned and produced by scripts in `sim/`, never hand-edited. Simulated /
preliminary, public and synthetic data, not real deployment data (all model files were trained on
`results/sim/` and `data/raw/PCOS_data_without_infertility.xlsx`; see `data/DATA_REGISTER.md`).

## Files

- `cycle_log.schema.json`, `screening_output.schema.json`: contracts 5.2 and 5.3.
- `demo_users/`: four personas (`regular`, `pcos_pattern`, `anemia_pattern`, `thyroid_pattern`), each
  provably triggering its intended flag under the tuned Tier 1 hybrid detector (`sim/make_personas.py`,
  `tests/test_demo_users.py`). `manifest.json` lists, per persona, the expected flag on every cycle.
- `examples/`: one example screening output object per flag type.
- `gru_v1.onnx`: the Tier 2 GRU next-cycle predictor (package A4), hidden size chosen by validation
  loss (`results/sequence_models.json`), exported with `torch.onnx.export(..., dynamo=False)` for
  broad onnxruntime-web compatibility. Input `sequence`: float32 tensor `(1, T, 22)` for T past
  cycles, where the last dimension is 11 standardized feature values followed by 11 observed-masks
  (1 = value present, 0 = missing), in the feature order below. Output `prediction`: `(1, T, 11)`,
  the predicted standardized feature vector for cycle t+1 at each position t.
- `gru_v1.scaler.json`: the per-feature `mean` and `sd` used to standardize inputs and to invert
  predictions back to real units, in the same `features` order as the model's last dimension.

## Feature order (11 features, matches `sim/common.py: FEATURES`)

```
cycle_length_days, flow, pain, acne, excess_hair, hair_loss, fatigue, mood, weight_change, dizziness, pallor
```

## Usage example (pseudocode, mirrors `sim/gru.py: raw_scores`)

```ts
// 1. Load gru_v1.scaler.json once: { mean: number[11], sd: number[11], features: string[11] }
// 2. For a user's cycle history (array of cycle-log objects, contract 5.3), build the input tensor:
//    for each cycle: standardize each feature as (value - mean[i]) / sd[i], or 0 if missing,
//    and append a parallel mask (1 if present, 0 if missing). Concatenate into a 22-length vector.
//    Stack all but the last cycle into shape (1, T-1, 22).
// 3. Run the ONNX model (onnxruntime-web) to get `prediction`, shape (1, T-1, 11).
// 4. The anomaly score for the cycle just logged (predicting cycle index i+2 from cycles 1..i+1)
//    is the largest |standardized_actual - standardized_predicted| over features actually observed
//    at i+2, per direction (see sim/detectors.py FEATURE_SPECS for the high/low signal names).
//    Feed the fired signals into the same rule layer as Tier 1 (sim/detectors.py: RuleLayer) to get
//    a flag, confidence and contributing_signals for the screening output object (contract 5.2).
```

Do not feed raw (non-standardized) values into the model, and do not average GRU and Tier 1 (z-score
+ CUSUM) scores directly: they are on different scales. `sim/gru.py: raw_scores` / `replay` is the
reference implementation; port that logic, do not re-derive it.

## Honest note on accuracy (see `results/sequence_models.json`, `docs/CLAIMS_EVIDENCE.md`)

On the simulator's test split, tuned the same way as the A2 detectors (validation-only, 5 false
alarms per 100 non-drift cycles budget), the GRU is **less** accurate than the Tier 1 z-score/CUSUM
hybrid at detecting the three drift patterns, and is not clearly better than a plain exponential
smoothing baseline. It exists in the app as the second tier of a hybrid, not as a replacement for
Tier 1. Do not present the GRU alone as more accurate than Tier 1 without checking
`results/baseline_detection.json` first.
