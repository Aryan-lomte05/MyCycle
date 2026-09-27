"""Loader for the Kaggle PCOS dataset (package A3), with the leakage-removal feature sets.

Source: prasoonkottarathil/polycystic-ovary-syndrome-pcos on Kaggle, sheet "Full_new" of
PCOS_data_without_infertility.xlsx (541 rows, one per patient, Kerala hospital data).
Full registration (license, checksums, column disposition) is in data/DATA_REGISTER.md.
The raw file is not committed (CLAUDE.md rule: no raw data in the repo; also the dataset's
CC-BY-NC-SA-4.0 licence restricts redistribution). Fetch it with data/download_pcos.py.

CLAUDE.md rule 3 non-negotiables for this loader:
  - drop every lab and ultrasound column from the deployable feature sets (S1, S2)
  - keep them only in S3, the with-labs reference upper bound, explicitly marked non-deployable

Feature sets (aryan.md A3):
  S1 symptom_only          self-reportable history and symptoms, nothing measured
  S2 symptom_plus_vitals   S1 + weight, height, BMI, waist, hip, blood pressure, pulse, resp rate
  S3 with_labs_reference   S2 + every lab and ultrasound column (reference only, never deployed)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from sim.common import ROOT

RAW_XLSX = ROOT / "data" / "raw" / "PCOS_data_without_infertility.xlsx"
SHEET = "Full_new"
LABEL_COL = "pcos"
N_ROWS_EXPECTED = 541

# raw column -> clean name. "drop" columns are identifiers or empty and are never used.
CLEAN_MAP = {
    "Sl. No": "drop", "Patient File No.": "drop", "Unnamed: 44": "drop",
    "PCOS (Y/N)": LABEL_COL,
    " Age (yrs)": "age_years", "Weight (Kg)": "weight_kg", "Height(Cm) ": "height_cm", "BMI": "bmi",
    "Blood Group": "blood_group", "Pulse rate(bpm) ": "pulse_rate_bpm", "RR (breaths/min)": "resp_rate",
    "Hb(g/dl)": "hemoglobin", "Cycle(R/I)": "cycle_regularity", "Cycle length(days)": "cycle_length_days",
    "Marraige Status (Yrs)": "marriage_years", "Pregnant(Y/N)": "pregnant", "No. of aborptions": "n_abortions",
    "  I   beta-HCG(mIU/mL)": "beta_hcg_1", "II    beta-HCG(mIU/mL)": "beta_hcg_2",
    "FSH(mIU/mL)": "fsh", "LH(mIU/mL)": "lh", "FSH/LH": "fsh_lh_ratio",
    "Hip(inch)": "hip_inch", "Waist(inch)": "waist_inch", "Waist:Hip Ratio": "waist_hip_ratio",
    "TSH (mIU/L)": "tsh", "AMH(ng/mL)": "amh", "PRL(ng/mL)": "prl", "Vit D3 (ng/mL)": "vit_d3",
    "PRG(ng/mL)": "prg", "RBS(mg/dl)": "rbs",
    "Weight gain(Y/N)": "weight_gain", "hair growth(Y/N)": "excess_hair_growth",
    "Skin darkening (Y/N)": "skin_darkening", "Hair loss(Y/N)": "hair_loss", "Pimples(Y/N)": "acne",
    "Fast food (Y/N)": "fast_food", "Reg.Exercise(Y/N)": "regular_exercise",
    "BP _Systolic (mmHg)": "bp_systolic", "BP _Diastolic (mmHg)": "bp_diastolic",
    "Follicle No. (L)": "follicle_l", "Follicle No. (R)": "follicle_r",
    "Avg. F size (L) (mm)": "follicle_size_l", "Avg. F size (R) (mm)": "follicle_size_r",
    "Endometrium (mm)": "endometrium",
}

LEAKAGE_COLS = [  # labs and ultrasound: never in S1 or S2 (CLAUDE.md rule 3, aryan.md A3)
    "hemoglobin", "beta_hcg_1", "beta_hcg_2", "fsh", "lh", "fsh_lh_ratio", "tsh", "amh", "prl",
    "vit_d3", "prg", "rbs", "follicle_l", "follicle_r", "follicle_size_l", "follicle_size_r", "endometrium",
]
VITALS_COLS = ["weight_kg", "height_cm", "bmi", "pulse_rate_bpm", "resp_rate", "hip_inch", "waist_inch",
              "waist_hip_ratio", "bp_systolic", "bp_diastolic"]
SYMPTOM_COLS = ["age_years", "marriage_years", "pregnant", "n_abortions", "cycle_regularity", "cycle_length_days",
               "weight_gain", "excess_hair_growth", "skin_darkening", "hair_loss", "acne", "fast_food", "regular_exercise"]
EXCLUDED_COLS = ["blood_group"]  # self-reported but not used: no established relevance to any target here

FEATURE_SETS = {
    "symptom_only": list(SYMPTOM_COLS),
    "symptom_plus_vitals": SYMPTOM_COLS + VITALS_COLS,
    "with_labs_reference": SYMPTOM_COLS + VITALS_COLS + LEAKAGE_COLS,
}
CATEGORICAL_COLS = {"cycle_regularity", "pregnant", "weight_gain", "excess_hair_growth", "skin_darkening",
                   "hair_loss", "acne", "fast_food", "regular_exercise"}


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    missing = set(df.columns) - set(CLEAN_MAP)
    if missing:
        raise ValueError(f"unmapped columns in raw PCOS file, update CLEAN_MAP: {sorted(missing)}")
    df = df.rename(columns=CLEAN_MAP)
    return df.drop(columns=[c for c in df.columns if c == "drop"])


def load(path: Path = RAW_XLSX) -> pd.DataFrame:
    """Cleaned PCOS dataframe: one row per patient, label as int 0/1, numeric columns coerced."""
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run `python data/download_pcos.py` first (needs Kaggle credentials).")
    df = pd.read_excel(path, sheet_name=SHEET)
    df = _clean_columns(df)
    if len(df) != N_ROWS_EXPECTED:
        raise ValueError(f"expected {N_ROWS_EXPECTED} rows, got {len(df)}: dataset may have changed")
    df[LABEL_COL] = df[LABEL_COL].astype(int)
    for col in df.columns:
        if col not in CATEGORICAL_COLS and col not in ("blood_group",):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def feature_matrix(df: pd.DataFrame, feature_set: str) -> tuple[pd.DataFrame, pd.Series, list[str], list[str]]:
    """(X, y, numeric_cols, categorical_cols) for the named feature set."""
    cols = FEATURE_SETS[feature_set]
    X = df[cols].copy()
    y = df[LABEL_COL].copy()
    cat = [c for c in cols if c in CATEGORICAL_COLS]
    num = [c for c in cols if c not in CATEGORICAL_COLS]
    return X, y, num, cat
