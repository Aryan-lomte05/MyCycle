# Detectors and rule layer (package A2)

Label: Simulated / preliminary, public and synthetic data, not real deployment data.

Code: `sim/detectors.py` (detectors, rule layer), `sim/detection_eval.py` (metrics, tuning, test run).
Rerun: `python -m sim.simulator --seed 42` then `python -m sim.detection_eval`.
Outputs: `results/thresholds.json` (chosen values, full validation sweep), `results/baseline_detection.json` (test metrics).

## How the pieces fit

Each detector turns one cycle into per-feature signals (`cycle_length_high`, `cycle_length_low`, `flow_high`, `pain_high`, `<symptom>_high`). One shared rule layer turns signals into a screening flag. Detectors therefore differ only in how they decide that a feature has left the personal baseline.

The Tier 1 detector used in the app is `hybrid`: signals from the adaptive z-score OR from CUSUM, then the rule layer. So the hybrid is a hybrid of a fast single-cycle test (z-score, catches sudden jumps), a slow accumulating test (CUSUM, catches small sustained drift) and a rule layer (maps signals to a named pattern). The GRU predictor joins it in package A4.

## Formulas

For feature x at cycle t:

- z-score (adaptive baseline): m_t = m_{t-1} + a (x_t - m_{t-1}), v_t = (1 - a)(v_{t-1} + a (x_t - m_{t-1})^2), z_t = (x_t - m_{t-1}) / max(sqrt(v_{t-1}), floor). Signal when z_t >= T (or z_t <= -T for short cycles). a = 0.3.
- Standardized value for the charts: s_t = (x_t - mean_ref) / max(sd_ref, floor), where the reference is the mean and SD of the first 6 non-signalled cycles, then held fixed.
- CUSUM: S+_t = max(0, S+_{t-1} + s_t - k), S-_t = max(0, S-_{t-1} - s_t - k) (cycle length only). Signal when S > h. k = 0.5.
- EWMA chart: e_t = lam s_t + (1 - lam) e_{t-1}, signal when |e_t| > L sqrt(lam / (2 - lam)). lam = 0.3.
- A feature that signals does not update its baseline or reference, so a sustained drift is not absorbed.

## Design constants (chosen, not tuned, not cited)

| Constant | Value | Why |
|---|---|---|
| Minimum history before scoring | 3 cycles (5 for Isolation Forest) | aryan.md A2 says 3 for the z-score; IF cannot fit on fewer |
| SD floor | cycle length 1.0 day, flow 0.3, pain 1.0, each symptom 0.5 | a user with a flat history would otherwise turn any change into an infinite z. Flow 0.3 means a one-level jump from a perfectly flat flow history gives z of about 3.3 |
| EWMA weight a (z-score) and lam (chart) | 0.3 | our choice: histories are short (16 to 30 cycles), so the weight leans fast. Not tuned |
| CUSUM k | 0.5 | aryan.md A2; tuned for a shift of about 1 SD |
| Chart reference window | first 6 non-signalled cycles, then fixed | phase I / phase II control chart practice; an adaptive reference would absorb the slow drift CUSUM exists to catch |
| Rule layer window | last 3 cycles for symptom evidence | symptoms are intermittent, a pattern should not need every symptom in the same cycle |
| Fixed-threshold cutoffs | length outside 21..35 days, flow 3 (heavy), pain 7 or more, symptom 2 (moderate) or more | aryan.md A2 names 21..35 for length; the flow, pain and symptom cutoffs are our choice for the population baseline |
| Isolation Forest | 50 trees, refit every cycle on all past cycles, attribution at 2 SD | comparison only; refit on all history keeps scores independent of the threshold, so the sweep is computed once |

## Rule layer

| Flag | Needs, in the current cycle | Needs, in the last 3 cycles |
|---|---|---|
| pcos_pattern | cycle_length_high | one of acne_high, excess_hair_high, hair_loss_high |
| anemia_pattern | flow_high | one of fatigue_high, dizziness_high, pallor_high |
| thyroid_pattern | cycle_length_high or cycle_length_low | one of fatigue_high, weight_change_high, mood_high |
| irregularity | cycle_length_high or cycle_length_low, and no pattern above | |
| none | anything else (symptom or flow signals alone never raise a flag) | |

When more than one pattern qualifies, the one with more symptom hits wins, ties in the order pcos, anemia, thyroid. Confidence is high with two or more symptom hits and the cycle signal in two of the last three cycles, medium with one of those, low otherwise.

These rules restate the pattern definitions in `project.md` section 4.3. They are not clinical criteria and have not been reviewed by a clinician. Every flag is a screening flag with a suggestion to consider consulting a doctor.

## Tuning protocol

Validation split only (`run_detector(..., tuning=True)` refuses any other split). For each detector: pick the grid value that maximizes the mean detection rate over pcos, anemia and thyroid, subject to at most 5 false alarms per 100 non-drift cycles, ties to the higher correct-pattern rate. The 5 per 100 budget is our design choice (about one false flag every 20 cycles). The whole sweep is saved so a different budget can be read off without rerunning. The z-score at the threshold 2.0 named in aryan.md is also reported on test as a reference row.

## Contract note

Contract 5.2 allows `detector` = zscore | cusum | gru. The hybrid reports `cusum` when any contributing signal came only from CUSUM, otherwise `zscore`. fixed_threshold, ewma and isolation_forest are evaluation-only and write their own name, which the contract does not accept. The results schema also has no `hybrid` detector value. See `docs/OPEN_QUESTIONS.md`.
