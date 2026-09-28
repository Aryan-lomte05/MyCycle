# MyCycle: What It Actually Is, Plain and Simple

**Updated:** 2026-09-29
**Context:** Coursework presentation (216U50P501, guide Dr. Makarand G. Kulkarni), faculty review
**Status:** Working research pipeline (simulator, detectors, classifiers, sequence model, federated/DP experiments). App prototype (`app/`) not yet built.

Every number below has a source file in `results/`. Where a claim is not yet backed by a `docs/papers.csv` VERIFIED citation, it says UNVERIFIED. This file is a source document for slides and NotebookLM, not itself a slide; check `docs/CLAIMS_EVIDENCE.md` before quoting any figure from it.

---

## 1. The one-line pitch

> MyCycle screens for patterns that look like PCOS, anemia or thyroid problems by comparing a person's new cycle against their own history, not a population average, using only symptoms they log themselves, and never sends raw logs off the phone.

It never diagnoses. Every result is a screening flag with a suggestion to consult a doctor.

### The problem it responds to (project.md section 2)

1. **Clinical access:** labs (AMH, LH, FSH, TSH, hemoglobin) and ultrasound needed for a full PCOS/anemia/thyroid workup are not always affordable or reachable.
2. **Information gap:** myths fill the space where reliable, local-language content should be ("irregular periods are just stress").
3. **Privacy:** mainstream cycle apps centralize sensitive reproductive data on company servers.
4. **Cultural taboo:** shame and stigma stop people discussing symptoms, even with family.
5. **Population thresholds miss personal patterns:** a fixed cutoff like "21 to 35 days is normal" mislabels people whose own normal sits near that edge, and can miss a real shift for someone whose own normal is narrower. This is a design motivation, not yet a measured claim about any specific commercial app (no commercial app's real thresholds have been tested here).

## 2. What the product actually does (user-facing)

1. **Log a cycle:** start date, cycle length, flow (0-3), pain (0-10), 8 symptoms (acne, excess hair, hair loss, fatigue, mood, weight change, dizziness, pallor). Stored only on the device (contract 5.3).
2. **Personal baseline:** an adaptive statistical model of that person's own cycle-length, flow and symptom pattern, built from their own history.
3. **Screening flag**, never a diagnosis: none, irregularity, pcos_pattern, anemia_pattern, or thyroid_pattern, with the contributing signals in plain words and always a line suggesting the person consider seeing a doctor (contract 5.2).
4. **Audio myth card** in English, Hindi or Marathi explaining the flag and correcting a related myth (content not yet written).
5. **Privacy panel:** counts bytes sent in real time, meant to read 0 for log data (not yet built; `app/lib/netClient.ts` does not exist yet).
6. **Family circle:** cycle phase and general tips only, never raw logs (not yet built).
7. **Planned, not yet built:** doctor-visit summary card, voice logging, disguise mode.

## 3. How it works, without jargon

```
Your phone: log store -> Tier 1 (fast personal-baseline stats) + Tier 2 (GRU) -> rule layer -> screening flag (shown to you only)
                                              |
                              (raw logs never leave this box)
                                              |
                                  clipped, noised model update (optional, off by default)
                                              v
                                    server: averages updates only
```

**Tier 1** is two statistical detectors run together: an adaptive z-score (fast, catches a sudden jump) and CUSUM (a change-detector, catches a small sustained drift the z-score misses). A rule layer turns their signals into one flag.

**Tier 2** is a small GRU (recurrent neural net) that tries to predict a person's next cycle from their history; a bigger-than-expected miss is a second signal, combined with Tier 1 by the same rule layer. See section 5 for the honest result on this: it currently underperforms Tier 1 alone.

**Federated learning** (optional, off by default) is how many phones could improve the shared Tier 2 model together without pooling raw data: each phone trains a little locally, clips and adds Gaussian noise to its update (this is what makes it differentially private, not "zero-knowledge" in the cryptographic sense, which this system does not use), and only that noised update goes to a server, which averages everyone's updates. See section 5 for measured privacy-utility numbers.

## 4. What data we use and why

Real menstrual-health datasets at real scale are rare in public: this is a privacy-sensitive domain, and no company with millions of real cycles (Flo, Clue) publishes raw data, which is itself part of this project's argument for on-device design. Two kinds of data are used on purpose, and the difference is never blurred:

| Dataset | Real or synthetic | Size | Role |
|---|---|---|---|
| kaggle_pcos | Real, public (10 Kerala hospitals; the exact diagnostic protocol used is UNVERIFIED) | 541 patients | Symptom-only PCOS classifier vs a with-labs reference upper bound |
| FedCycleData | Real, public (natural family planning charting; provenance beyond the Kaggle page UNVERIFIED) | 159 women, 1,665 cycles | Validates the simulator's baseline cycle-length shape against real data |
| NFHS-5 | Real, public (India's National Family Health Survey, Round 5) | 136,136 women; 126,625 after excluding pregnant respondents | Real anemia label from real hemoglobin (WHO threshold, UNVERIFIED pending a read of the source), and a real self-reported thyroid label |
| Simulator (`sim/simulator.py`) | Synthetic, always labeled as such | 3,000 users today (about 69,000 cycles); tested feasible at 20,000 users in 18 seconds, so millions of rows is a config change away, not yet run at that scale | Personal-baseline drift detection: does the detector catch a shift in someone's own pattern, with known ground truth |

No commercial app publishes multi-year, per-person, diagnosis-linked cycle histories, so a synthetic simulator is how detection is tested with known ground truth. Its assumptions are listed openly in `sim/ASSUMPTIONS.md`, most marked "assumption" pending a citation, and its baseline shape is checked against FedCycleData (section 5).

## 5. What is actually built and measured (not placeholders)

Everything below is a number written by a script into `results/`, never typed by hand. `results/summary.json` (the frozen, cross-team contract file) is still a placeholder; these numbers live in their own results files pending the A7 merge step.

**A1 Simulator** (`sim/simulator.py`, `results/sim/`): deterministic, byte-identical per seed. Baseline cycle-length marginals checked against FedCycleData: mean 29.05 days (simulated) vs 29.30 (real), share of cycles outside 24-38 days 4.55% (simulated) vs 4.44% (real). The simulator is somewhat less variable than real cycles (within-user SD 1.85 vs 2.17 days), a stated, not hidden, limit (`results/sim_validation.json`).

**A2 Detectors** (`sim/detectors.py`, `results/baseline_detection.json`): the Tier 1 hybrid, tuned on a validation split and measured on a held-out test split, detects 99% of simulated pcos_pattern users, 92% of anemia_pattern, 99% of thyroid_pattern, at 1.5 to 2.7 false alarms per 100 non-drift cycles. A naive fixed-threshold baseline (what most apps do) reaches similar detection rates but at higher false alarms (16 to 26 per 100 non-drift cycles at a fixed z-threshold of 2.0).

**A3 Classifiers** (`sim/classifiers.py`, `results/classifiers.json`, real kaggle_pcos data, n=541): 8 models compared under stratified 5-fold CV x 5 seeds with bootstrap CIs. Best symptom-only AUC 0.891 (k-NN, 95% CI 0.862-0.918), tightly clustered with 7 other models (0.86 to 0.89). A with-labs reference (non-deployable) reaches 0.959 AUC (LightGBM). No model is a clear winner on symptom-only, which is itself a finding.

**A3 extension, NFHS-5** (`sim/nfhs_classifiers.py`, real government survey data, 126,625 eligible non-pregnant women, modeled on a stratified 6,000-row subsample for compute reasons, 3 seeds, SVM excluded as computationally infeasible at this row count): real anemia (WHO hemoglobin threshold, UNVERIFIED pending a source read) reaches only AUC 0.620 (logistic regression) from symptom and demographic features alone, close to chance, an honest negative result: self-reportable features barely predict lab-confirmed anemia. Real thyroid (self-reported diagnosis, a weaker label than a TSH lab test) reaches AUC 0.768 (random forest), notably better, and the top model beats the next-best significantly on one feature set (p=0.024, paired bootstrap).

**A4 Sequence model** (`sim/gru.py`, `results/sequence_models.json`, `exports/gru_v1.onnx`): GRU exported to ONNX with verified numerical parity to PyTorch (max abs diff under 1e-4). **Honest result, not a flattering one**: the GRU alone detects only 85% / 48% / 27% of pcos/anemia/thyroid patterns, worse than Tier 1 (99%/92%/99%) and not clearly better than a plain exponential-smoothing baseline (90%/63%/30%). Personalizing the GRU (fine-tuning the output head on a user's first 4 cycles) raises detection but also raises false alarms substantially (overall false-alarm rate rose from 0.8% to 18.6% of non-drift cycles on the personalization test set). Two real bugs were found and fixed while measuring this; the result held after fixing them. Tier 2 is presented as a second signal that has not yet earned its place alone, not a headline result.

**A5 Federated learning and differential privacy** (`sim/federated.py`, `results/federated.json`, `results/figures/fed_curves.png`, `results/figures/privacy_utility.png`): on the PCOS classification task, centralized training reaches AUC 0.892; local-only training on non-IID clients (no sharing at all) drops to AUC 0.740; FedAvg on the same non-IID split recovers to AUC 0.878, close to centralized. Adding differential privacy (Gaussian noise on clipped per-client updates) costs some accuracy and buys a stated privacy budget: at noise multiplier 1.0, epsilon is about 2.9 (delta 1e-5) and AUC is 0.842; at noise multiplier 3.0, epsilon drops to about 0.94 and AUC is 0.859. The curve is not perfectly monotonic (a real, stochastic simulation, not smoothed), which should be shown honestly, not hidden.

**Repository health**: 120 tests passing, language lint and contract checks green, as of 2026-09-29.

## 6. What we can and cannot honestly claim to the faculty guide

**Can claim:** a working symptom-only PCOS classifier at 0.89 AUC on real data with confidence intervals; a personal-baseline detector that beats a naive fixed-threshold baseline on false alarms at similar detection rates, on a clearly labeled synthetic benchmark validated against real cycle-length data; a real, large (136,136-row) government survey integrated for anemia and thyroid; a measured federated learning and differential privacy tradeoff curve, not just a claimed one.

**Cannot claim yet:** that the sequence model (GRU) improves on the simpler statistical detector (it currently does not, by our own numbers); that any of this has been tested on real patients or deployed; that we have trained on "millions of real rows" (the real datasets are in the hundreds to low hundred-thousands; the simulator can reach millions of synthetic, clearly labeled rows, but has not yet been run at that scale for these results); superiority over any named commercial app (no such comparison has been run).
