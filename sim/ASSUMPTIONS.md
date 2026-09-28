# Simulator assumptions (package A1)

Label: Simulated / preliminary, public and synthetic data, not real deployment data.

Code: `sim/simulator.py` (all values live in `SimConfig`). Rerun: `python -m sim.simulator --seed 42`.

## Status of every parameter

**No parameter below is backed by a verified citation yet.** CLAUDE.md rule 6 allows a source only after someone has opened it and read the relevant part. The "candidate source" column lists where each value should be checked. It is a pointer for Saanj and Aryan to read, not a citation. Until a row says VERIFIED with a `docs/papers.csv` id, the value is an **assumption** and must be described that way in the paper and slides.

What the simulator results can show: that a detector finds drifts of this shape and size under these assumptions. What they cannot show: that the detector works on real patients, or that real PCOS, anemia or thyroid changes look like this.

## Population and baseline

| Parameter | Value | Status | Candidate source (UNVERIFIED) |
|---|---|---|---|
| Users | 3000 | design choice (aryan.md A1) | none needed |
| Cycles per user | uniform 16 to 30 | design choice | none needed |
| Personal mean cycle length mu_u | N(29, 2.5), clipped to 21..38 days | assumption | large app-based cycle studies (for example Bull et al. 2019, npj Digital Medicine); FIGO AUB System 1 normal frequency range (Munro et al. 2018) |
| Within-user SD sigma_u | uniform 1.0 to 3.0 days | assumption | same as above; to be checked against the calibration dataset (Marquette/Fehring candidate, existence unverified, see OPEN_QUESTIONS) |
| Cycle length clip | 15 to 90 days | design choice (keeps values inside contract 5.3 range 10..120) | none needed |
| Flow latent level | uniform 1.0 to 2.3, per-cycle noise SD 0.4, rounded and clipped to 1..3 | assumption. Flow 0 is never generated because a logged period with no flow is not meaningful for this experiment | none |
| Pain latent level | uniform 1 to 5, per-cycle noise SD 1.0, clipped 0..10 | assumption | none |
| Baseline symptom probability | uniform 0.02 to 0.15 per symptom per cycle, severity mostly mild (1,1,1,2) | assumption | none |
| Missing values | 2 percent of each observed feature, independently | design choice (robustness test, aryan.md A1) | none needed |
| Start date | 2024-01-01 plus 0 to 364 days | design choice | none needed |

## Drift injection

Common to the three pattern drifts: onset cycle k uniform in 5..10, then a linear ramp over 1, 2 or 3 cycles (1 means an abrupt step) to the full drift, which persists to the end of the sequence. During the ramp, symptom probabilities and severities move toward their drifted values in proportion. The ramp is an **assumption** added so that detection delay is meaningful; aryan.md does not specify onset shape.

| Drift | What changes | Values | Status | Candidate source (UNVERIFIED) |
|---|---|---|---|---|
| pcos_pattern | mean cycle length | +8 to +20 days | assumption (aryan.md A1 range) | Rotterdam consensus 2003 (oligo- or anovulation as a criterion); FIGO frequency definitions |
| pcos_pattern | cycle length variance | doubled (SD times sqrt 2) | assumption | none |
| pcos_pattern | skipped cycles | 10 percent of drifted cycles, length uniform 46 to 75 days; non-skipped cycles capped at 45 so "over 45" means skipped | assumption | none |
| pcos_pattern | acne, excess_hair, hair_loss | probability rises to uniform 0.5 to 0.8, severity (1,2,2,3) | assumption | Rotterdam consensus 2003 (clinical hyperandrogenism) |
| anemia_pattern | flow | +1 to +2 levels on the latent scale, clipped at 3 | assumption | literature on heavy menstrual bleeding and iron deficiency; WHO haemoglobin thresholds apply to lab labels only, not to this simulator |
| anemia_pattern | fatigue, dizziness, pallor | probability rises to uniform 0.5 to 0.8 | assumption | none |
| anemia_pattern | cycle length | unchanged | assumption (aryan.md A1) | none |
| thyroid_pattern | cycle length | 50 percent shorter by 5 to 8 days, 50 percent longer by 6 to 12 days | assumption (aryan.md A1 range); the 50/50 split is our choice | reviews of menstrual disturbance in hypo- and hyperthyroidism (for example Krassas et al.) |
| thyroid_pattern | fatigue, weight_change, mood | probability rises to uniform 0.5 to 0.8 | assumption | none |
| benign_shift | cycle length for 1 or 2 cycles, then back to baseline | 70 percent longer by 7 to 15 days, 30 percent shorter by 4 to 7 days | assumption (travel or stress). The 70/30 split is our choice | none |
| benign_shift | fatigue and mood during the shifted cycles | probability 0.4 | assumption. Added on purpose so a benign shift can look thyroid-like for one or two cycles, which makes the false-alarm test harder, not easier | none |
| none | nothing | none | design choice | none needed |

## Class mix and splits

25 percent none, 20 percent each pcos_pattern, anemia_pattern, thyroid_pattern, 15 percent benign_shift (aryan.md A1). Counts are exact (750, 600, 600, 600, 450 for 3000 users). Split 60/20/20 train/val/test by user, stratified by drift type. A user never appears in two splits.

## Ground truth columns

`drift_type`, `onset_cycle`, `drift_active` (true from onset for the three patterns, true only on the shifted cycles for benign_shift), `skipped` (pcos skipped cycle), `true_length_days` (before missingness). Per-user latent parameters are in `users.parquet`.

## Known limits

- Features are drawn independently given the drift. Real symptoms are correlated (for example pain with flow). This probably makes detection easier than reality.
- Every drift is clean and single. Real people can have more than one condition, or partial patterns.
- No seasonality, contraception, pregnancy, postpartum or perimenopause effects.
- Logging behaviour is perfect apart from 2 percent random missingness. Real users skip logging, and not at random.

## Marginal validation (done, 2026-09-27)

The calibration dataset exists: FedCycleData (Kaggle `nikitabisht/menstrual-cycle-data`), 159 women, 1,665 cycles, natural family planning charting data. Provenance beyond the Kaggle page is UNVERIFIED (no paper cited by the uploader), so it is used only for marginal comparison, never as a cited clinical source. Fetch with `data/download_cycle_calibration.py`, compare with `python -m sim.cycle_calibration` (writes `results/sim_validation.json`).

| Statistic | Real (FedCycleData) | Simulated (baseline cycles) | Abs diff |
|---|---|---|---|
| Cycle length mean | 29.30 days | 29.05 days | 0.25 |
| Cycle length SD (population) | 3.89 days | 3.22 days | 0.67 |
| Within-user SD (median) | 2.17 days | 1.85 days | 0.32 |
| Share outside 24-38 days | 4.44% | 4.55% | 0.11 pp |

Reading this honestly: the mean and the share of unusually short/long cycles match closely. The simulator is somewhat less variable than reality, both in population SD and in within-user SD, meaning real cycles wander a bit more than `SimConfig.sigma_range = U(1.0, 3.0)` assumes. This is a real limit, not something to quietly widen after the fact: if `sigma_range` is revisited, it should be with this comparison in hand, and rerun. What this validates: the baseline (non-drift) shape only. It cannot and does not validate the drift patterns (PCOS/anemia/thyroid), since FedCycleData carries no diagnosis labels.
