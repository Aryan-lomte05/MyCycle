# Dataset Register (D4)

One section per dataset used, plus datasets considered and rejected. No dataset is used before its section here is complete. Written by Aryan ahead of Saanj joining (2026-09-27); Saanj owns this file per CLAUDE.md section 3 and should review it.

## kaggle_pcos

- **Name:** PCOS dataset without infertility (sheet `Full_new`), plus a smaller `PCOS_infertility.csv` (not currently used).
- **Source URL:** https://www.kaggle.com/datasets/prasoonkottarathil/polycystic-ovary-syndrome-pcos
- **Access date:** 2026-09-27
- **Licence and terms:** CC-BY-NC-SA-4.0 (attribution, non-commercial, share-alike). This project is non-commercial coursework. The raw file is not committed to the repo (redistribution is restricted by the licence, and CLAUDE.md keeps raw data out of the repo regardless).
- **File names and SHA-256 checksums:**
  - `PCOS_data_without_infertility.xlsx`: `b663ec9f491be419718e0935eb1c5b6c4923b527282230a73cfc9aca8533f742`
  - `PCOS_infertility.csv`: `2e4f06b6dc68450c0e05d7a433dabd4ff50ad2edb7e9302d6103449a95b63ad3`
  - Verified by `data/download_pcos.py`, which also fetches the file with the Kaggle API.
- **Rows:** 541 (sheet `Full_new`), one row per patient. Label: 364 PCOS (Y/N) = 0 (no PCOS), 177 = 1 (PCOS), about 33 percent positive.
- **Provenance (as stated by the dataset, not independently verified by us):** collected across 10 hospitals in Kerala, India. We have not read a paper describing the collection protocol; this is the dataset's own description on Kaggle, so it is UNVERIFIED as a clinical provenance claim and is not cited as such in the paper.
- **Columns kept and dropped:** full mapping and reasons in `sim/pcos_data.py` (`CLEAN_MAP`, `LEAKAGE_COLS`, `FEATURE_SETS`). Summary:
  - **Dropped always:** `Sl. No`, `Patient File No.` (identifiers), an empty trailing column, `Blood Group` (self-reported but no established relevance to PCOS or to any target here, excluded to avoid scope creep).
  - **Dropped from S1 (symptom_only) and S2 (symptom_plus_vitals), kept only in S3 (with_labs_reference):** hemoglobin, beta-HCG (I and II), FSH, LH, FSH/LH, TSH, AMH, PRL, Vitamin D3, PRG, RBS, follicle count (L/R), average follicle size (L/R), endometrium thickness. These are lab or ultrasound results (CLAUDE.md rule 3: never in a deployable feature set, since the app never asks for a lab value or a scan).
  - **S1 symptom_only (13 features):** age, marriage duration, pregnancy status, number of abortions, cycle regularity, cycle length, weight gain, excess hair growth, skin darkening, hair loss, acne (pimples), fast food habit, regular exercise. All self-reportable without a device or a test.
  - **S2 symptom_plus_vitals:** S1 plus weight, height, BMI, waist, hip, waist:hip ratio, systolic and diastolic blood pressure, pulse rate, respiratory rate. Measurable at home or in a basic check-up, no lab or scan.
  - **S3 with_labs_reference:** S2 plus every lab and ultrasound column above. Reference upper bound only, explicitly marked non-deployable in every result and figure.
- **Label definition:** `PCOS (Y/N)` as recorded in the source data (clinical assessment by the contributing hospitals; the exact diagnostic protocol used by those hospitals, for example whether it followed Rotterdam criteria, is not stated in the dataset documentation and is UNVERIFIED).
- **Missing data summary:** 1 missing value in `Marraige Status (Yrs)`, 1 in `Fast food (Y/N)`, out of 541 rows each. No other column has missing values. Median imputation is used for the primary run; an iterative-imputation ablation is planned (T10) given the missingness is negligible here.
- **Known biases and limitations:** one row per woman, no repeat visits, so it cannot test a personal baseline over time (this is why the simulator exists, see `project.md` section 5). Single-country, hospital-recruited sample, so it does not represent a general population. Class balance (67/33) is moderate, not severe. Whether Rotterdam or another criterion produced the label is unverified.
- **Preprocessing steps in order:** load `Full_new` sheet -> rename columns (`sim/pcos_data.py: CLEAN_MAP`) -> coerce label to int -> coerce all non-categorical columns to numeric -> select the feature set's columns -> per-fold: median-impute numeric columns, most-frequent-impute categorical columns, one-hot encode categorical columns, standard-scale numeric columns for scale-sensitive models.
- **Script that produces the processed file:** `sim/pcos_data.py` (`load()`, `feature_matrix()`). No separate processed file is written; the pipeline reads the raw Excel file directly and applies preprocessing inside each cross-validation fold, so nothing about the test fold leaks into the training preprocessing.
- **Used for:** `sim/classifiers.py` (package A3, T1 technique comparison, `results/classifiers.json`).
- **Which results depend on it:** `results/classifiers.json`, `results/figures/classifier_comparison.png`, `results/figures/pcos_calibration.png`.

## nhanes

- **Status:** superseded by nfhs5 (below) as of 2026-09-27. NHANES (US) was the original plan (aryan.md A3), but NFHS-5 is a real, large, India-specific survey that better matches this project's population, and was found and integrated instead. NHANES was never downloaded. If NHANES is wanted later for a US-population comparison, the plan in the previous version of this file (demographics, body measures, a reproductive/general health questionnaire, complete blood count and TSH files, matched by respondent sequence number, sample weights, pregnant respondents excluded) still applies.

## nfhs5

- **Name:** National Family Health Survey, Round 5 (India, 2019-2021), redistributed as a single cleaned CSV.
- **Source URL:** https://www.kaggle.com/datasets/ravisinghiitbhu/nfhs5
- **Access date:** 2026-09-27
- **Licence and terms:** CC0-1.0 (public domain). Could be committed under this licence, but CLAUDE.md keeps all raw data out of the repo regardless.
- **File names and SHA-256 checksums:** `Final.csv`: `503e36565b41542ec2df5611919cbf3301caccc73997f1699fee819fb5683ecf`. Verified by `data/download_nfhs5.py`.
- **Rows:** 136,136 women aged 15-49, one row per respondent. No missing values in any column (the file was already cleaned by the uploader; we cannot verify what imputation, if any, they used before we received it, which is itself a limitation).
- **Provenance:** NFHS is India's official Demographic and Health Survey, run by the Ministry of Health and Family Welfare. The Kaggle redistribution's own preprocessing (which of the many official NFHS-5 variables were kept, how they were renamed and cleaned) has not been cross-checked against the official microdata by this team; treat the exact variable definitions as UNVERIFIED until someone reads the official NFHS-5 recode manual and confirms them, particularly `Hg_levelAdjusted` (assumed to be haemoglobin in tenths of a g/dL, altitude/smoking-adjusted, consistent with standard DHS/NFHS practice) and `Anemia_level` (assumed to be the standard WHO/DHS four-level classification; not used as a feature or label, both computed independently, see below).
- **Two tasks, both built by us, not columns already in the file:**
  - **anemia** (binary): `Hg_levelAdjusted < 120` (WHO cutoff, 12.0 g/dL, for non-pregnant women), among respondents with `Curr_Preg == 0`. The WHO cutoff itself is UNVERIFIED (widely cited, not yet independently confirmed by reading the WHO source; to be marked VERIFIED in `docs/papers.csv` once someone does).
  - **thyroid** (binary): the file's own `Thyroid` column, a self-reported existing diagnosis. This is weaker evidence than a TSH lab-based label: it requires the respondent to already have been diagnosed and to remember to report it, so it undercounts real thyroid dysfunction. Stated as a limitation in every result that uses it.
- **Columns kept and dropped:** full logic in `sim/nfhs_data.py`. `Hg_levelAdjusted`, `Anemia_level` (both lab-derived) and `ultrasound` (imaging-adjacent) are dropped from every feature set for both tasks, on top of each task's own label. The other task's label is kept as a feature only when self-reported (`Thyroid` is a legitimate feature for the anemia task; the engineered `anemia` column is not used as a feature for the thyroid task, since it is lab-derived). `Curr_Preg` is used only as a filter, then dropped.
- **Label definitions:** see the two tasks above.
- **Missing data summary:** none (see provenance caveat above).
- **Known biases and limitations:** self-reported thyroid diagnosis undercounts true prevalence (thyroid label). India-only, so results describe this population, not a global one; that is a fit for the project's own India focus, not a limitation for this project's purposes, but should not be generalized elsewhere without saying so. The survey samples ever-married women aged 15-49 in most rounds; check this before quoting prevalence rates as general population rates.
- **Preprocessing steps in order:** load `Final.csv` -> filter to `Curr_Preg == 0` -> engineer `bmi = Resp_weight / Resp_height^2` (`Resp_height` is already in metres in this file, confirmed by its summary statistics, not assumed) -> engineer `anemia` label -> per task, per fold: median-impute (there is nothing to impute in practice, given no missing values), one-hot encode `State` (the only true categorical column, 36 India states/UTs; every other column is already numeric, including several ordinal-coded ones such as `Edu_level` and `Wealth_Idx_Lb` that are used as plain numeric features, a simplification), standard-scale numeric columns.
- **Computational deviations from the kaggle_pcos protocol**, both documented in `sim/nfhs_classifiers.py` and in every output file's `meta`: SVM (RBF) excluded (training cost is superlinear in row count; infeasible at this scale in the course time budget, a computational exclusion under requirements.md T1, not an accuracy judgment); each task modeled on a stratified-by-label 6,000-row subsample of the 126,625 eligible rows, not the full population, and reduced to 3 seeds instead of 5 (still bootstrap-CI'd), for the same reason.
- **Script that produces the processed file:** `sim/nfhs_data.py` (`load()`, `feature_matrix()`, `stratified_subsample()`). No separate processed file is written.
- **Used for:** `sim/nfhs_classifiers.py`, `results/nfhs_classifiers.json`.
- **Which results depend on it:** `results/nfhs_classifiers.json`.

## cycle_calibration

- **Name:** FedCycleData, natural family planning cycle charts.
- **Source URL:** https://www.kaggle.com/datasets/nikitabisht/menstrual-cycle-data
- **Access date:** 2026-09-27. Resolves the open question from 2026-09-26 (does a real cycle-length dataset exist).
- **Licence and terms:** listed "unknown" on Kaggle. Used read-only for marginal comparison (mean, SD, share of unusual cycles); never redistributed, never committed to the repo.
- **File names and SHA-256 checksums:** `FedCycleData071012 (2).csv`: `9fa76583129db58af44adb21a0612217b207120fb61d478fb343a61291732a89`. Verified by `data/download_cycle_calibration.py`.
- **Rows:** 1,665 cycles from 159 women (median 12 cycles per woman). The exact clinical or research context behind the original collection is UNVERIFIED (the Kaggle page names no paper); this is used as a plausibility check only, never cited as a clinical source.
- **Label definition:** none used; this is a validation dataset, not a training dataset.
- **Missing data summary:** not audited in detail; only `LengthofCycle` is used.
- **Known biases and limitations:** women using natural family planning charting are not a random sample of all menstruating women (likely more engaged with tracking, possibly more likely to be trying to conceive or avoid pregnancy), so its marginals are a plausibility check, not ground truth for the general population.
- **Preprocessing steps:** load, group by `ClientID`, compute population and within-user cycle-length statistics. Script: `sim/cycle_calibration.py`.
- **Used for:** validating `sim/simulator.py`'s baseline (non-drift) marginals only, per `sim/ASSUMPTIONS.md`.
- **Which results depend on it:** `results/sim_validation.json`.

## simulator

- Fully synthetic, generated by `sim/simulator.py`. See `sim/ASSUMPTIONS.md`. Always labeled simulated.

## interviews

- Not started. Qualitative only, never used for model training. `docs/source/` contains an un-anonymized primary persona description and is gitignored (see `docs/OPEN_QUESTIONS.md`, 2026-09-26 entry); it must be redacted to a P-code before anything in it is used or cited.

## Datasets considered and rejected

| Dataset | Considered for | Reason rejected |
|---|---|---|
| PCOS_infertility.csv (same Kaggle source) | Supplementary PCOS features | Smaller, overlapping cohort with a different focus (infertility workup); not merged in this pass to avoid an unverified join on patient identity. Left in `data/raw/` for a future look. |
| NHANES ultrasound/imaging derived features | Symptom-only screening | Contradicts the symptom-only, no-lab, no-scan design goal; excluded by the same hard constraint that removes labs and ultrasound from kaggle_pcos S1/S2. |
