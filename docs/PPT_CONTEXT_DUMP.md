# PPT Context Dump: paste into NotebookLM or slides directly

Every number here has a source file in `results/`. Nothing is invented. Generated 2026-09-29.

---

## SLIDE SET 1-2: ARYAN: ML core (simulator, detectors, classifiers, sequence model, federated/DP)

**Slide 1: What was built**

- Synthetic cycle simulator (`sim/simulator.py`): generates per-user cycle histories with known drift ground truth (PCOS-like, anemia-like, thyroid-like, benign false-alarm test). 3,000 users, ~69,000 cycles at current scale; tested feasible to 20,000 users in 18 seconds, so millions of rows is a config change away. Validated against real data: FedCycleData (159 real women, 1,665 real cycles): simulated baseline cycle length 29.05 days vs real 29.30 days; share of unusual cycles (outside 24-38 days) 4.55% simulated vs 4.44% real.
- Personal-baseline detector, Tier 1 (`sim/detectors.py`): adaptive z-score + CUSUM change-detection + rule layer. Tuned on a validation split, measured on a held-out test split: detects 99% of pcos_pattern, 92% of anemia_pattern, 99% of thyroid_pattern, at 1.5-2.7 false alarms per 100 normal cycles. Beats a naive fixed-threshold baseline (what most apps do), which reaches similar detection but at 16-26 false alarms per 100.
- Symptom-only PCOS classifier (`sim/classifiers.py`), real data (kaggle_pcos, n=541 patients): 8 models compared, 5-fold CV x 5 seeds, bootstrap 95% CI. Best AUC 0.891 (k-NN), tightly clustered with 7 other models (0.86-0.89). With-labs reference (non-deployable) reaches 0.959 AUC.
- Real anemia + thyroid screening on NFHS-5 (India's National Family Health Survey, 136,136 real women, 126,625 after excluding pregnant respondents, modeled on a 6,000-row stratified subsample for compute reasons): anemia (real hemoglobin, WHO threshold) reaches only AUC 0.62 (logistic regression) from symptoms/demographics alone, an honest near-chance result. Thyroid (self-reported diagnosis) reaches AUC 0.77 (random forest), clearly better than anemia and statistically significant vs the next model on one feature set (p=0.024).

**Slide 2: The honest findings (this is what survives a hard question)**

- Tier 2 GRU sequence model (`exports/gru_v1.onnx`): alone, detects only 85%/48%/27% of pcos/anemia/thyroid patterns: WORSE than Tier 1 (99%/92%/99%) and not clearly better than plain exponential smoothing (90%/63%/30%). This is a real, reproducible result (two real bugs were found and fixed while measuring it; the result held after fixing them). Presented as a limitation, not a headline win.
- Personalizing the GRU (fine-tune on a user's first 4 cycles) raises detection but also raises false alarms a lot: overall false-alarm rate went from 0.8% to 18.6% of normal cycles.
- Federated learning + differential privacy (`sim/federated.py`, real Opacus-validated epsilon accounting): centralized AUC 0.892; local-only (no sharing, non-IID clients) drops to AUC 0.740; FedAvg recovers to AUC 0.878. Adding DP costs accuracy for privacy: noise multiplier 1.0 gives epsilon about 4.3 (delta 1e-5) at AUC 0.842; noise multiplier 3.0 gives epsilon about 0.8 at AUC 0.859. IMPORTANT: an earlier version of our own epsilon accountant had a bug that understated epsilon (claimed stronger privacy than was true) by up to 4x; this was caught by validating against Opacus (a standard library) as required, and fixed. Numbers above are the corrected ones.
- 130 automated tests passing, all repo honesty/contract checks green.
- What we do NOT claim: clinical validation, real deployment, that GRU beats the simpler detector, that we trained on millions of real rows (real data is in the hundreds to low hundred-thousands; the simulator can reach millions of SYNTHETIC clearly-labeled rows but hasn't been run at that scale yet for these specific results).

---

## SLIDE 3: ADITYA: Backend

- FastAPI backend scaffold exists in `server/`: `main.py`, `db.py`, routes for content, metrics and reminders (`server/routes/content.py`, `metrics.py`, `reminders.py`), an OpenAPI spec (`docs/openapi.json`), and a test file (`tests/test_server.py`).
- Content folder (`content/`) and interview synthesis (`docs/INTERVIEWS.md`) not yet populated as of this dump: check with Aditya directly for current status, do not guess.

---

## SLIDE 4: LIZA: App / prototype

- `app/` is currently empty (only a placeholder file). No PWA prototype exists yet in the repo as of this dump.
- Assets ready for the app to consume once built: `exports/demo_users/` (4 verified personas), `exports/gru_v1.onnx` + `exports/gru_v1.scaler.json` (Tier 2 model), `exports/cycle_log.schema.json`, `exports/screening_output.schema.json`, `exports/README.md` (usage guide).
- Check with Liza directly for current build status; this dump reflects only what's committed to the repo.

---

## SLIDE 5: SAANJ: Data register, on-device, QA

- `data/DATA_REGISTER.md` has full entries for 4 datasets (kaggle_pcos, nfhs5, cycle_calibration/FedCycleData, plus the simulator), each with source, license, checksum, row count, column disposition and known limits.
- `results/ondevice.json` (model size, latency, memory) not yet produced as of this dump.
- Some earlier commits from Saanj ("add evidence and on-device deliverables", "record citation verification blocker") were reverted in git history; current status unclear from the repo alone, check with Saanj directly.

---

## THE ONE THING TO SAY IF ASKED "DID YOU TRAIN ON MILLIONS OF ROWS"

"We use real public datasets for the classifiers: kaggle_pcos (541 rows) and NFHS-5, India's own government health survey (136,136 real women): and a synthetic simulator, clearly labeled as synthetic, for the personal-baseline detection experiments, which is designed to scale to millions of rows because no one publishes millions of real menstrual cycles for privacy reasons. That's not a workaround, it's the same privacy argument this whole project is making."

## SOURCE FILES (for NotebookLM upload)

Upload these directly, they are plain JSON/markdown, no login needed:
`results/classifiers.json`, `results/baseline_detection.json`, `results/federated.json`, `results/sequence_models.json`, `results/sim_validation.json`, `data/DATA_REGISTER.md`, `docs/PRODUCT_OVERVIEW.md`, `docs/CLAIMS_EVIDENCE.md`, this file.
