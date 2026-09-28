"""Loader for NFHS-5 (package A3 extension): real anemia and thyroid screening tasks.

Source: ravisinghiitbhu/nfhs5 on Kaggle, a cleaned single-file redistribution of India's National
Family Health Survey Round 5 (2019-2021), 136,136 women aged 15-49, licence CC0-1.0. Full
registration in data/DATA_REGISTER.md. Not committed (CLAUDE.md: no raw data in the repo). Fetch
with data/download_nfhs5.py.

Two tasks, both symptom-only in spirit (no lab value used as a feature, only as an anemia label):

  anemia   label: WHO threshold on real haemoglobin (Hg_levelAdjusted < 12.0 g/dL, i.e. < 120 in
           this file's tenths-of-a-g/dL units), among non-pregnant respondents only (Curr_Preg == 0).
           The WHO cutoff is a widely cited threshold, not yet independently verified against the
           original WHO document by this team (UNVERIFIED until read and logged in docs/papers.csv).
  thyroid  label: self-reported existing thyroid condition (`Thyroid`, 0/1). This is weaker than a
           TSH lab-based label (aryan.md A3's original NHANES plan): it depends on the respondent
           already having been diagnosed and remembering to report it, so it undercounts true
           thyroid dysfunction. Reported as a limitation, not smoothed over.

Both tasks exclude Hg_levelAdjusted, Anemia_level (NFHS's own precomputed anemia category, derived
from the same haemoglobin value) and `ultrasound` (imaging-adjacent) from every feature set, on top
of excluding the task's own label column.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from sim.common import ROOT

RAW_CSV = ROOT / "data" / "raw" / "nfhs5" / "Final.csv"
N_ROWS_EXPECTED = 136136
WHO_ANEMIA_CUTOFF_NONPREGNANT = 120  # 12.0 g/dL, tenths-of-g/dL units used by this file. UNVERIFIED, see module docstring.

LABEL_COL = {"anemia": "anemia", "thyroid": "Thyroid"}
# imaging-adjacent, plus every lab-derived value (the anemia label's own source and NFHS's own anemia
# category): none of these may appear as a FEATURE in either task, on top of that task's own label.
ALWAYS_DROP = ["ultrasound", "Hg_levelAdjusted", "Anemia_level", "anemia"]
VITALS_COLS = ["Resp_weight", "Resp_height", "bmi"]


def load(path: Path = RAW_CSV) -> pd.DataFrame:
    """Full cleaned dataframe, non-pregnant respondents only, with an engineered BMI column."""
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run `python data/download_nfhs5.py` first (needs Kaggle credentials).")
    df = pd.read_csv(path, low_memory=False)
    if len(df) != N_ROWS_EXPECTED:
        raise ValueError(f"expected {N_ROWS_EXPECTED} rows, got {len(df)}: dataset may have changed")
    df = df[df["Curr_Preg"] == 0].drop(columns=["Curr_Preg"]).reset_index(drop=True)
    df["bmi"] = df["Resp_weight"] / df["Resp_height"] ** 2  # Resp_height is already in metres in this file
    df["anemia"] = (df["Hg_levelAdjusted"] < WHO_ANEMIA_CUTOFF_NONPREGNANT).astype(int)
    return df


def feature_sets(df: pd.DataFrame, task: str) -> dict[str, list[str]]:
    """symptom_only and symptom_plus_vitals column lists for `task` ('anemia' or 'thyroid').

    The other task's label is kept as a feature when it is self-reported (Thyroid, for the anemia
    task): a self-reported condition is allowed input, same as any other symptom. `anemia` is
    dropped everywhere since it is lab-derived (ALWAYS_DROP), even though it is not the label for
    the thyroid task, to keep no lab-derived value in any feature set.
    """
    drop = set(ALWAYS_DROP) | {LABEL_COL[task]}
    symptom_only = [c for c in df.columns if c not in drop and c not in VITALS_COLS]
    return {
        "symptom_only": symptom_only,
        "symptom_plus_vitals": symptom_only + ["Resp_weight", "Resp_height", "bmi"],
    }


def feature_matrix(df: pd.DataFrame, task: str, feature_set: str) -> tuple[pd.DataFrame, pd.Series, list[str], list[str]]:
    """(X, y, numeric_cols, categorical_cols) for `task` ('anemia' or 'thyroid') and the named feature set."""
    cols = feature_sets(df, task)[feature_set]
    X = df[cols].copy()
    y = df[LABEL_COL[task]].copy()
    cat = [c for c in cols if X[c].dtype == object]
    num = [c for c in cols if c not in cat]
    return X, y, num, cat


def stratified_subsample(df: pd.DataFrame, task: str, n: int, seed: int) -> pd.DataFrame:
    """A stratified-by-label subsample of size n, for computational tractability at this scale."""
    rng = np.random.default_rng(seed)
    frac = n / len(df)
    parts = []
    for _, g in df.groupby(LABEL_COL[task]):
        k = max(1, round(len(g) * frac))
        parts.append(g.iloc[rng.choice(len(g), size=min(k, len(g)), replace=False)])
    return pd.concat(parts).sample(frac=1, random_state=seed).reset_index(drop=True)
