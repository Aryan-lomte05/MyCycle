# Saanj: Data, On-Device Feasibility, Evidence and Slides Lead

You own `/data`, `/ondevice`, the datasets register, the citation library, the claims-evidence table and the final slide deck. Your work makes the whole project defensible, because sir will ask for every dataset and every source. All your tasks come with exact steps, scripts to follow and acceptance checks.

Read first: `CLAUDE.md`, `requirements.md` (sections 4, 5, 6, 10).

## Ground rules

- Nothing gets into the register or the citations list without being opened and read.
- Record everything with dates, URLs and checksums.
- Use Claude Code to write scripts, but you verify the output yourself by opening the files.
- Never commit raw data. `data/raw/` is gitignored. Commit scripts, checksums and the register.

## Work packages

### S0 (P0, tonight, 2 hours): Download and register the datasets
For each dataset below, create a section in `data/DATA_REGISTER.md` using the template at the bottom of this file, plus a script `data/download_<id>.py` (or a manual step recorded in `data/MANUAL_STEPS.md` where login is needed), and record SHA-256 checksums in `data/checksums.txt`.

1. **kaggle_pcos** (PCOS dataset without infertility, hospital data, Kerala). Download from Kaggle (needs a Kaggle account and API token, or manual download). Record: rows, columns, column names exactly, missing values per column, label distribution, licence text, any oddities (empty columns, misspelled headers, inconsistent formats). Send Aryan the column list by 22:00 so he can decide the symptom-only feature set.
2. **nhanes**: CDC NHANES public files. Identify and record exact cycles and file names for: demographics, reproductive health questionnaire, complete blood count (hemoglobin), thyroid profile (TSH), body measures. Record how respondent IDs (SEQN) join the files and which survey weights exist. Note variable name changes across cycles. Pick 2 to 3 recent cycles where the files exist and are consistent. Write a data dictionary of the variables Aryan will use. If access is slow, tell Aryan by 23:00 so he can cut this to P1.
3. **cycle_calibration**: search for a public menstrual cycle dataset with real cycle lengths (candidate: Marquette / Fehring). Confirm it exists, check size, licence and access route. If it is not usable, find one alternative and record the search, or record that none was found. Aryan uses it only to compare simulator marginals.
4. **Optional secondary (P2):** UCI thyroid disease, only as a sanity reference. Record why it is limited (lab-based, small).
5. **Datasets considered and rejected:** search for other PCOS, anemia and cycle datasets on Kaggle, UCI, Zenodo, PhysioNet, OpenML, Mendeley Data. For each, record name, link, why rejected (labs-only, ultrasound images, licence, size, unclear provenance). Aim for at least 8 rejected candidates. This proves the choice was deliberate.

Acceptance: register has complete sections for the used datasets, a rejected-list table with reasons, checksums file exists, Aryan has the columns list.

### S1 (P0, Sat night): Papers library and evidence gathering (`docs/papers.csv`)
Columns: id, title, authors, year, venue, DOI or URL, status (VERIFIED or UNVERIFIED), what specific finding it supports, page or section reference, which decision it supports (T1 to T12), notes.

Rules:
- VERIFIED means you opened the source and read the relevant part yourself.
- Start with the 12 papers already in the literature matrix. Open each one and confirm the findings listed for it. Correct any that do not match what the paper actually says.
- Then find sources for each technique decision. Tasks by decision:
  - T1: benchmark studies on tabular data (tree ensembles vs deep models), PCOS ML studies using symptom-only features.
  - T2: control-chart and changepoint methods for personal baselines, anomaly detection in health time series.
  - T4 to T7: FedAvg (McMahan et al.), FedProx, SCAFFOLD, DP-SGD (Abadi et al.), Flower paper, secure aggregation.
  - T8: TFLite, ONNX Runtime web documentation.
  - Clinical criteria for the simulator: Rotterdam criteria for PCOS, WHO hemoglobin thresholds for anemia, thyroid and menstrual cycle relationship reviews, FIGO guidance on abnormal uterine bleeding. Aryan needs these for `sim/ASSUMPTIONS.md`.
  - Comparison with existing apps: public privacy policies and product pages, with access dates. Record what they state, not what you assume.
- Target at least 25 VERIFIED entries by Sunday noon.
- Hand Aryan the entries per decision as they are done, not all at the end.

Acceptance: at least 25 VERIFIED, each with a supported-finding sentence and a page or section reference.

### S2 (P1, Sunday morning): On-device feasibility (`/ondevice`)
- Aryan gives you the GRU model (Sunday 10:00). Convert to TFLite and record: model size (KB), inference latency p50 and p95 over 1000 runs, peak memory, on at least two targets: your laptop CPU and an Android phone if available (Android benchmark tool or a simple test app), otherwise a documented emulator.
- Parity check: run the same fixtures through the Python model and the TFLite model and record the maximum absolute difference.
- Write `results/ondevice.json` following the `ondevice` section of the contract in `CLAUDE.md` 5.1.
- Also record the size and browser latency of the ONNX version Liza uses, to support the PWA decision.
- If the conversion fails, record the error, try the ONNX to TFLite route once, and if still failing report the ONNX web numbers only and state this honestly. Do not fake numbers.

Acceptance: `results/ondevice.json` validates against the schema, a short `ondevice/README.md` explains the exact commands and hardware.

### S3 (P0, Sunday): Claims-evidence table (`docs/CLAIMS_EVIDENCE.md`)
- Create the table with the columns in `requirements.md` section 10.
- Sweep every slide, paper section, README line and app string for claims: numbers, comparisons, "first", "novel", "private", "works offline", "no labs needed". Each gets a row.
- Chase owners for missing evidence. A claim without evidence is rewritten or deleted.
- Final pass Sunday 21:00. Print the summary counts (supported, needs work, removed) on the last slide.

### S4 (P0, Sunday): Slide deck (`docs/slides/`)
- Build the deck following `requirements.md` section 4. Use one clean template, consistent fonts, high-contrast charts, large text. Slide titles state findings.
- Take figures from `results/figures/` via `make figures` (Aryan provides `INDEX.md`). Never re-draw a chart by hand.
- Put speaker notes on every slide: what it shows, the number that matters, one limitation. Aryan supplies notes for slides 6 to 12, Aditya for 1-3 and 15-16, Liza for 14.
- Each chart footer: dataset, n, metric, CI method, simulated label.
- Slides you author: 4 (data grouped by category, leakage-removal table), 5 (preprocessing and split protocol), 13 (on-device feasibility), 17 (claims summary). You place Aryan's slides 6 and 7 and Aditya's text for slides 1-3 and 15-16.
- Final consistency pass Sunday 20:00: numbers match `summary.json`, terminology consistent, no "diagnosis", no em dashes, slide numbers match the storyboard.

Acceptance: complete deck, exported to PDF, every number traceable to a claims row.

### S5 (P0): QA and acceptance test runner
- Run the acceptance test in `requirements.md` section 9 on Sunday at 19:00 and again at 22:00. Log results in `docs/ACCEPTANCE_LOG.md`, one line per check with pass or fail and who fixes.
- Verify on a clean machine (or fresh clone in a temp folder) that `make all` works. Report failures to the owner with the exact error.
- Grep checks: "diagnos", em dashes, "better than", "beats", "outperform", "zero leak", "guarantee", "perfect", "world's best", "100% private", "clinically proven", "detects PCOS". Report every hit.
- Feature checks (acceptance tests 9 to 14 in `requirements.md`): airplane-mode run, netClient rejection test, disguise mode, doctor visit card, and the public-facing copy check. Log each one in `docs/ACCEPTANCE_LOG.md`.
- Every claim on the poster and in Aditya's copy pack has a row in the claims table before Sunday 21:00.
- Slide standards (`requirements.md` section 12): export the deck to `docs/slides/` as .pptx and run `python scripts/check_slides.py` at 19:00 and 22:00. Fix every error. Then work through `docs/SIR_FEEDBACK.md` with a second person and tick each row only when the check for it passes.

### S6 (P1): Paper sections
- **Datasets and Preprocessing:** describe each dataset, leakage removal, splits, preprocessing, limits. Use the register as the source.
- **Methodology: On-device implementation:** conversion, runtime choices, size and latency results, parity check, limitations.
- Also compile the reference list in IEEE numeric format from VERIFIED entries only, ordered by first appearance, and check that every in-text number resolves.

### S7 (P2)
- Add the second Android device result, energy measurement notes, ARM vs x86 latency comparison.

## Interfaces you owe and receive

| From or to | What | By |
|---|---|---|
| To Aryan | Kaggle PCOS column list and first data summary | Sat 22:00 |
| To Aryan | Cycle calibration dataset status | Sat 23:30 |
| To Aryan | NHANES data dictionary or a cut decision | Sun 09:00 |
| To Aryan | VERIFIED clinical criteria for simulator assumptions | Sun 09:00 |
| From Aryan | GRU model for conversion | Sun 10:00 |
| To Aryan | `results/ondevice.json` | Sun 14:00 |
| From Aryan | Figures and `INDEX.md` | Sun 16:00 |
| From all | Slide content | Sun 17:00 |
| To all | Acceptance log with owners | Sun 19:00 and 22:00 |

## Register template (copy for every dataset)

```
## <id>: <name>
- Source URL:
- Access date:
- Licence and terms:
- Files and SHA-256:
- Rows and columns:
- Label definition:
- Columns kept (with reason):
- Columns dropped (with reason):
- Missing data summary:
- Known biases and limitations:
- Preprocessing steps in order:
- Script that creates the processed file:
- Used for:
- Results that depend on it:
- Verified by (name, date):
```

## Hard questions to prepare for

1. Why these datasets and not others? (rejected-candidates table)
2. Are there leakage risks? (dropped-column list and reasons)
3. Who collected this data, when, and how does that limit our claims? (register limitations)
4. Does the model run on a phone? (ondevice numbers, honest about hardware)
5. Where does this claim come from? (open the claims table live)
