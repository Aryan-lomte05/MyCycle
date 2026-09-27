# Changelog

Two lines per change: what changed, how to rerun.

- 2026-09-26 Aryan: repo scaffold, contracts frozen (schema v1), lint and validator, placeholder results, demo users v0. Rerun: `make check`.
- 2026-09-26 Aryan: Contract enums extended additively (fedprox, fedper, ewma, isolation_forest, lstm, cnn1d) in schema and CLAUDE.md. Rerun: `make check`.
- 2026-09-26 Aryan: added scripts/check.py (cross-platform `make check`), project name left TBD in README. Rerun: `python scripts/check.py`.
- 2026-09-26 Aryan: project named MyCycle in README, CLAUDE.md, CONTEXT.md and schema title. Rerun: `python scripts/check.py`.
- 2026-09-26 Aryan: added public-facing features FR11 to FR17, new storyboard, acceptance tests 9 to 13, copy rules (requirements.md section 11), CLAUDE.md rules 11 and 12, lint banned phrases. Rerun: `python scripts/check.py`.
- 2026-09-26 Aryan: voice logging switched to on-device Whisper (FR11, L14, acceptance test 14, claims C007); approved privacy sentence fixed (copy rules, FR1, FR13, claims C008, lint). Rerun: `python scripts/check.py`.
- 2026-09-26 Aryan: faculty feedback added (docs/SIR_FEEDBACK.md), deck plan now 17 slides, slide standards (requirements.md section 12), CLAUDE.md rule 13, local_only federated mode, formula-check note, packages A12 to A14 and updated slide numbers in task files. Rerun: `python scripts/check.py`.
- 2026-09-26 Aryan: A1 synthetic cycle simulator (sim/simulator.py, sim/common.py), 14 tests (one per drift type plus reproducibility, splits, ranges), sim/ASSUMPTIONS.md with every parameter marked assumption until sources are verified. docs/source/ kept out of git (un-anonymized interview details).
  Rerun: `python -m sim.simulator --seed 42` (writes results/sim/*.parquet and meta.json, byte-identical per seed and commit), then `python scripts/check.py`.
- 2026-09-27 Aryan: A2 detectors (sim/detectors.py: fixed_threshold, zscore, ewma, cusum, isolation_forest, hybrid, rule layer), sim/detection_eval.py (tune on val, measure on test), sim/DETECTORS.md. 21 new tests. Wrote results/thresholds.json and results/baseline_detection.json.
  Rerun: `python -m sim.detection_eval` (needs results/sim/*.parquet from sim.simulator first).
- 2026-09-27 Aryan: replaced hand-shaped v0 demo personas with simulator-derived ones (sim/make_personas.py) verified against the tuned Tier 1 hybrid detector: each pattern persona is flagged none before onset and the intended pattern by the manifest's cycle, never a different pattern. 9 new tests, all previously skipped demo-user tests now pass.
  Rerun: `python -m sim.make_personas` (needs results/thresholds.json).
- 2026-09-27 Aryan: A3 classifier comparison. Downloaded the real Kaggle PCOS dataset (data/download_pcos.py, checksums and full column disposition in data/DATA_REGISTER.md), wrote sim/pcos_data.py (leakage-removal feature sets S1/S2/S3) and sim/classifiers.py (8 models, stratified 5-fold CV x 5 seeds, patient-level bootstrap CI, paired bootstrap top-2 test). 16 new tests. Wrote results/classifiers.json.
  Rerun: `python data/download_pcos.py` then `python -m sim.classifiers`.
- 2026-09-27 Aryan: A3 figures and ablation. sim/make_figures.py writes results/figures/classifier_comparison.png (AUC by model/feature set with CI bars), results/figures/pcos_calibration.png, results/tables/imputation_ablation.md/.csv (median vs KNN imputation, negligible difference since only 2/541 rows have missing values). Added claims C009-C013 to docs/CLAIMS_EVIDENCE.md, all measured and supported.
  Rerun: `python -m sim.make_figures` (after sim.classifiers).
