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

- **Status:** cut from the current run and not used in any result. This is the documented P1 cut decision for the current deadline.
- **Decision date:** 2026-09-28.
- **Reason:** no verified multi-file download, variable dictionary, join, weighting, and label pipeline was completed in the current run. Keeping it out prevents unsupported anemia or thyroid classifier claims from entering the results.
- **Current substitute:** symptom-pattern experiments for anemia and thyroid use the explicitly labeled synthetic simulator only, through `results/baseline_detection.json`.
- **If revisited:** would need NHANES demographics, body measures, a reproductive/general health questionnaire, complete blood count (hemoglobin) and thyroid profile (TSH) files, matched by respondent sequence number, with sample weights applied in evaluation and pregnant respondents excluded. No file has been downloaded or verified yet.

## cycle_calibration

- **Status:** a relevant published source was verified, but no reusable cycle-level download and licence were verified, so it is not registered as a used dataset.
- **Source publication:** Bull et al., "Real-world menstrual cycle characteristics of more than 600,000 menstrual cycles," https://www.nature.com/articles/s41746-019-0152-7, accessed 2026-09-27.
- **What it supports:** an external reference for cycle-length and cycle-variability context. It does not by itself provide a committed or downloadable calibration file for this repository.
- **Licence and terms:** not recorded as a dataset licence because a reusable cycle-level data package was not verified.
- **Decision:** keep simulator parameters explicitly marked as assumptions; do not claim independent calibration from this publication.

## simulator

- Fully synthetic, generated by `sim/simulator.py`. See `sim/ASSUMPTIONS.md`. Always labeled simulated.

## interviews

- Not started. Qualitative only, never used for model training. `docs/source/` contains an un-anonymized primary persona description and is gitignored (see `docs/OPEN_QUESTIONS.md`, 2026-09-26 entry); it must be redacted to a P-code before anything in it is used or cited.

## Datasets considered and rejected

| Dataset | Considered for | Reason rejected |
|---|---|---|
| PCOS_infertility.csv (same Kaggle source) | Supplementary PCOS features | Smaller, overlapping cohort with a different focus (infertility workup); not merged in this pass to avoid an unverified join on patient identity. Left in `data/raw/` for a future look. |
| NHANES ultrasound/imaging derived features | Symptom-only screening | Contradicts the symptom-only, no-lab, no-scan design goal; excluded by the same hard constraint that removes labs and ultrasound from kaggle_pcos S1/S2. |
| UCI thyroid disease | Supplementary thyroid reference | Lab-based clinical diagnosis dataset; too dependent on tests and not aligned with symptom-only screening design. |
| MIMIC or eICU clinical datasets | Anemia and thyroid risk reference | Not a menstrual-cycle or symptom-first dataset, and patient linkage and de-identification requirements exceed the course scope. |
| PhysioNet MESA / sleep and menstrual datasets | Cycle-pattern calibration | Missing public, clearly licensed cycle-length tables; more oriented to sleep or physiology than daily symptom logging. |
| OpenML PCOS and endocrine benchmark sets | PCOS benchmark comparison | Mostly small, weakly documented, or lab-heavy sets without a clean symptom-only mirror. |
| Kaggle fertility and hormone datasets | Additional PCOS signal | Often lab-only or infertility-focused, with unclear provenance and no deployable symptom-only feature set. |
| Zenodo menstrual diary archives | Real cycle calibration | Useful for pattern exploration but not a clear licence or reproducible benchmark for this project’s baseline detector. |
| Mendeley menstrual health datasets | Population calibration | Some are private or single-site samples; often missing clean metadata or a direct symptom-only mapping. |
| UCI breast cancer and other tabular health benchmarks | Algorithm benchmark | Not relevant to the stated problem and adds no menstrual health signal. |
| Image-based ovarian ultrasound datasets | PCOS status model | Requires imaging hardware and would violate the symptom-only, no-scan design goal. |
| Public app datasets from consumer wellness apps | Benchmark and fairness comparison | Not available under a transparent licence or open participant-consent record for research use. |

The project uses `kaggle_pcos` for the symptom-only classifier benchmark and the simulator for pattern detection experiments. The rest are intentionally excluded because they do not match the no-lab, no-scan, privacy-preserving design target or because the provenance and licence are not clear enough to cite defensibly.
