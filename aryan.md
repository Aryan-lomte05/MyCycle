# Aryan: ML Architecture, Experiments and Integration Lead

You own the scientific core. Everything in `/sim`, `/exports` and `/results` is yours, plus the technique comparison document, README and paper integration. Other people consume your outputs through the contracts in `CLAUDE.md` section 5, so freezing those contracts at 21:00 tonight is your first duty.

Priority tags: P0 must exist Monday, P1 should, P2 only if green.

## Work packages

### A0 (P0, tonight, 60 min): Scaffold and freeze contracts
- Create repo structure from `CLAUDE.md` section 3, `Makefile` targets (`all`, `check`, `data`, `sim`, `train`, `figures`, `results`), `.gitignore` (raw data, node_modules, env), `.env.example`.
- Write `scripts/lint_language.py` (fails on "diagnos*" used as a system action, on em dashes, on missing simulated label in results files).
- Write `results/summary.schema.json` from the contract in `CLAUDE.md` 5.1 and a validator used by `make check`.
- Commit a dummy `results/summary.json` with `meta.simulated = true` and placeholder values clearly marked `"placeholder": true`, so Liza can build against it immediately. Replace with real values as they arrive. The placeholder flag must be removed by real runs, and `make check` fails if any placeholder remains at the acceptance test.
- Export 4 demo user files to `/exports/demo_users/` (even if crude first): regular, pcos_pattern, anemia_pattern, thyroid_pattern, each 10 to 14 cycles in the cycle-log format.
- Tell everyone the contracts are frozen.

Acceptance: other three can clone, run `make check` and see green.

### A1 (P0, tonight, 3 hours): Synthetic cycle simulator (`sim/simulator.py`)
Goal: generate per-user cycle sequences with known ground truth so detection can be measured.

Spec:
- Users: 3000, sequence 16 to 30 cycles each, seeded.
- Per-user latent baseline: mean cycle length mu_u drawn from N(29, 2.5) clipped to 21..38; within-user SD sigma_u from U(1.0, 3.0); baseline flow level (0-3), baseline pain (0-10), baseline symptom probabilities low.
- Cycle features: cycle_length, flow, pain, eight symptoms per the log contract. Observation noise added. Small fraction of missing values (2 percent) to test robustness.
- Drift injection at onset cycle k drawn from 5..10:
  - pcos_pattern: mean cycle length shifts +8 to +20 days with doubled variance, 10 percent of later cycles skipped (length over 45), acne, excess_hair and hair_loss probabilities rise.
  - anemia_pattern: flow shifts up by 1 to 2 levels, fatigue, dizziness, pallor rise, cycle length unchanged.
  - thyroid_pattern: cycle length shifts either shorter (-5 to -8) or longer (+6 to +12), fatigue, weight_change, mood rise.
  - benign_shift: one to two cycles of shift (travel or stress) that then return to baseline. Must not be flagged persistently. This is the false-alarm test.
  - none: no change.
- Class mix: 25 percent none, 20 percent each for pcos_pattern, anemia_pattern, thyroid_pattern, 15 percent benign_shift (sums to 100). Record the mix in the results meta.
- Every drift parameter range must cite a clinical source in `sim/ASSUMPTIONS.md` with a verified citation id. Where no source exists, mark it "assumption" openly.
- Validate marginals: compare simulated cycle length mean and SD against the real cycle calibration dataset once Saanj downloads it. Write the comparison to `results/sim_validation.json`.
- Output: `results/sim/train.parquet`, `val.parquet`, `test.parquet` split by user (never by cycle).

Acceptance: `python -m sim.simulator --seed 42` reproducible byte-identical, tests for each drift type, `ASSUMPTIONS.md` exists.

### A2 (P0, tonight, 2 hours): Detectors (`sim/detectors.py`)
Implement, each with the same interface `detector.update(cycle) -> screening_output` per contract 5.2:
1. Fixed population threshold (cycle length outside 21..35 days, flow and pain fixed cutoffs). This is the "what most apps do" baseline.
2. Rolling z-score with EWMA mean and SD, threshold 2.0, minimum 3 cycles history.
3. EWMA control chart.
4. One-sided CUSUM on standardized series (k = 0.5, h tuned on val).
5. Isolation Forest per user on standardized features (comparison only).
6. Rule layer mapping signals to flags (irregularity, pcos_pattern, anemia_pattern, thyroid_pattern), with confidence levels.

Tune thresholds on val only. Record chosen values in `results/thresholds.json`.

Acceptance: detection results on test split for every detector and drift type, written to `results/baseline_detection.json` (detection rate, median delay in cycles, false alarms per 100 cycles, benign_shift persistent-flag rate).

### A3 (P0, Sat night to Sun morning, 3 hours): Classifier comparison (`sim/classifiers.py`)
Datasets: kaggle_pcos (Saanj provides raw and register), nhanes (anemia and thyroid tasks).
- Inspect columns after Saanj downloads. Decide the symptom-only feature set. Drop all lab and ultrasound columns (AMH, FSH, LH, FSH/LH, TSH, PRL, PRG, vitamin D, RBS, follicle counts, follicle sizes, endometrium thickness, hemoglobin as a lab). Record the final kept and dropped column lists in `data/DATA_REGISTER.md` via Saanj, with the reason for each.
- Feature sets: S1 symptoms only, S2 symptoms plus basic vitals (age, BMI, waist-hip if present), S3 with labs (reference upper bound, marked non-deployable).
- Models: logistic regression, random forest, XGBoost, LightGBM, SVM (RBF), MLP, naive Bayes, k-NN. Same preprocessing pipeline, class weights for imbalance, imputation compared (median vs iterative) as ablation.
- Protocol: stratified 5-fold CV repeated 5 seeds, all preprocessing fit inside folds, hyperparameter search only in inner folds (nested CV or fixed small grid documented), bootstrap 95 percent CIs. Metrics: AUC, sensitivity at 90 percent specificity, specificity at 90 percent sensitivity, Brier, calibration curve.
- NHANES: define anemia (hemoglobin below WHO thresholds for non-pregnant women) and thyroid abnormality (TSH outside reference range) labels from the lab files, then train only on questionnaire and basic features. Use sample weights in evaluation where appropriate and state it. Exclude pregnant respondents. If NHANES proves too slow to wrangle by Sunday noon, cut it to P1 and report anemia and thyroid screening only through the simulator, and say so.
- Paired comparison tests between the best two models per task (for example DeLong or paired bootstrap), because "X is better" needs a test.

Acceptance: `results/classifiers.json` conforming to the schema, `results/figures/classifier_comparison.png` with CI bars, calibration figure, ablation table.

### A4 (P0, Sunday morning, 3 hours): GRU sequence model (`sim/gru.py`)
- Predict next cycle's feature vector from history, hidden size 16 and 32, trained on simulator train split, anomaly score = normalized prediction error, threshold tuned on val.
- Compare against LSTM and 1D CNN (T3) under the same protocol. ARIMA or exponential smoothing as classical reference.
- Local fine-tuning experiment: freeze GRU, fine-tune last layer on a held-out user's first N cycles, measure detection metrics before and after personalization.
- Export to ONNX: `exports/gru_v1.onnx` and a TypeScript port of the Tier 1 detectors: `exports/detector.ts` with parity tests against Python on fixtures in `exports/fixtures/` (max abs diff under 1e-4). Give Liza a 10-line usage example in `exports/README.md`.

Acceptance: detection table extended with `gru`, ONNX loads in onnxruntime-web test, parity test passes.

### A5 (P0, Sunday morning to afternoon, 4 hours): Federated and DP experiments (`sim/federated.py`)
- Flower simulation, 8 to 10 clients, non-IID partition of the PCOS data (partition by feature-skew or label-skew with a Dirichlet alpha of 0.3 and also IID as control) and non-IID partition of simulator users.
- Modes: centralized, FedAvg, FedProx (T5 comparison), personalized head (FedPer style), FedAvg with DP.
- DP: per-example gradient clipping to C, Gaussian noise sigma in {0, 0.5, 1.0, 1.5, 2.0, 3.0}, fixed delta 1e-5, epsilon from an accountant (validate against Opacus or TensorFlow Privacy once and record agreement). Report epsilon per configuration.
- Formula check (faculty feedback item 8): use the standard DP-SGD form, where Gaussian noise N(0, sigma^2 C^2 I) is added to the SUM of the clipped per-example gradients and the result is then divided by the batch size (Abadi et al.). Do not add noise of scale sigma*C to the already averaged gradient, as the earlier project dump did, because that changes both the noise level and the epsilon. For client-level (user-level) protection, clip each client's whole update to norm C, add noise to the sum of the clipped updates, then divide by the number of clients. Verify both against the original papers before they go on a slide, and record which one the experiments implement.
- 30 to 100 rounds, 5 seeds, mean and CI.
- Figures: metric vs round, metric vs epsilon (privacy-utility curve).
- Also run a simple membership-inference or reconstruction sanity check on the no-DP vs DP model if time permits (P2), because "DP protects" is stronger with a test.

Acceptance: `results/federated.json`, `results/figures/privacy_utility.png`, `results/figures/fed_curves.png`.

### A6 (P0, Sunday, parallel): Technique comparison document (`docs/TECHNIQUE_COMPARISON.md`)
- Follow the format in `requirements.md` section 5 for T1 to T12.
- You write the analysis. Saanj supplies verified citations for the "cited" candidates through `docs/papers.csv`. Aditya proofreads for clarity.
- For every "ran" candidate, point to the results key. For every "excluded" candidate, give the hard constraint.
- Include the weight sensitivity check.
- Prepare a one-page "why X over the alternatives" summary per decision for the slides.

Acceptance: T1 to T12 all filled, no empty evidence cells, no unverified citations.

### A7 (P0, Sunday afternoon): Results assembly and figures
- `make results` merges classifier, detection, federated, simulator validation and Saanj's `ondevice.json` into `results/summary.json`, validates against the schema, removes placeholder flags.
- `make figures` regenerates all PNG/SVG figures at 300 dpi with consistent style, titles that state the finding, axes labeled, n and CI method in captions, simulated label in the corner.
- Give Saanj a `results/figures/INDEX.md` listing each figure, what it shows and which slide it belongs to.

### A8 (P1): Speaker notes for statistics slides
For slides 6 to 12 (algorithms, formulas, classifier comparison, technique comparison, detection results, federated table, privacy-utility), write a paragraph each: what was measured, what we found, what it does not show. Be ready to answer: why this metric, why this split, what is the CI, what would change your mind.

### A9 (P1, Sunday night to Monday): Paper integration
- Write Abstract, Introduction, Related Work, Methodology (personal-baseline model, federated and DP protocol), Conclusion and Future Work.
- Integrate everyone's sections, unify notation (define symbols once: mu, sigma, z, C, sigma_noise, epsilon, delta), check every number against `results/summary.json`, check every citation is VERIFIED, run `lint_language.py` on the paper text.

### A10 (P1): Narration script for the technical parts of the video
Sections 3 to 6 and 8 of the storyboard. Keep it to what is visible on screen.

### A11 (P2)
- Membership-inference sanity check.
- Second personalization method (meta-learning) comparison.
- Wearable features (RHR, BBT) as future work only, no implementation.

## Slide content packages (added after faculty feedback, see `docs/SIR_FEEDBACK.md`)

### A12 (P0, Sunday, 1 hour): Algorithms slide content (slide 6)
- One table naming every algorithm actually used and its role: learning (FedAvg with differential privacy, plus FedProx and FedPer only if they were run), personal-baseline detector (EWMA z-score, CUSUM, GRU next-cycle predictor, rule layer), personalization (last-layer fine-tuning), classifiers compared.
- State in one sentence what the hybrid is a hybrid of (statistical baseline plus sequence model plus rules) and why each part is there.
- Write it AFTER the final results so the names match `results/`. Max 6 rows and 4 columns, 18 pt.

### A13 (P0, Sunday, 1.5 hours): Formulas slide content (slide 7)
- Typeset equations with a symbol table: EWMA mean and deviation, z-score, one-sided CUSUM, per-example clipping, Gaussian noise in the standard DP-SGD form (noise on the sum of clipped gradients), the client-level variant if used, FedAvg weighted average, and the (epsilon, delta) statement.
- Render each equation to a high-resolution image (`docs/slides/formulas/`) or hand Saanj the LaTeX source. One idea per equation, every symbol defined.
- Verify each formula against the original paper with Saanj and mark the papers VERIFIED in `docs/papers.csv`.

### A14 (P0, Sunday afternoon, 30 minutes): Without FL, with FL, with FL plus DP table (slide 11)
- Run `python sim/make_tables.py`. It writes `results/tables/fl_comparison.md` and `.csv` from `results/summary.json`. Add it to `make results`.
- The rows are centralized (no FL), local only (no FL), FedAvg (FL), FedAvg with DP at several noise levels. Columns: AUC, accuracy, epsilon and delta, rounds, client split. Placeholder rows are labeled so nobody presents them by mistake.

## Interfaces you owe others (deadlines)

| To | What | By |
|---|---|---|
| Everyone | Frozen contracts, scaffold, placeholder summary.json | Sat 21:00 |
| Liza | 4 demo users v0 and screening output examples for each flag | Sat 21:30 |
| Aditya | List of signals and `message_key` names the detector can emit | Sat 21:30 |
| Saanj | Feature list decisions for datasets, GRU model file for TFLite conversion | Sun 10:00 |
| Liza | `exports/detector.ts`, `gru_v1.onnx`, usage README | Sun 12:00 |
| Liza | A representative DP-noised model update sample (size in KB, clip norm, sigma, epsilon) for the privacy panel demo | Sun 15:00 |
| Saanj | Figures index and figure files | Sun 16:00 |
| Saanj | Slide 6 and 7 content, `results/tables/fl_comparison.md` | Sun 16:00 |
| Everyone | Frozen `results/summary.json` | Sun 17:00 |

## Working style (so you do not burn out on the critical path)

- Use Claude Code with plan mode per work package, one package per session, tests first.
- Run long jobs (CV, federated sweeps) in the background while you write the comparison doc.
- If you fall behind, cut in this order: A11, A8, NHANES tasks, FedProx and FedPer, LightGBM and k-NN. Never cut: simulator, Tier 1 detectors, PCOS classifier comparison, FedAvg with and without DP, privacy-utility curve, exports for the app.
- Keep `docs/OPEN_QUESTIONS.md` current so others are not blocked on you.
- Sleep. The Sunday evening rehearsal needs you sharp.

## Hard questions to prepare for

1. Why is the simulator a valid test of a personal baseline? (assumptions, sources, marginal validation, limits)
2. Why symptom-only, and how much accuracy did removing labs cost? (S1 vs S3 with CIs)
3. Why this DP noise level? (whole curve, epsilon and delta, operating point)
4. Why FedAvg and not FedProx, SCAFFOLD or others? (results plus cited reasons)
5. Why did you not use deep models for tabular PCOS? (small n, results, cited evidence on tabular data)
6. How do you know results are not leakage? (column drop list, patient-level splits, nested CV)
7. What is the clinical claim? (none: screening flag only)
