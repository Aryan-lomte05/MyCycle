"""Symptom-only classifier comparison on kaggle_pcos (package A3, technique comparison T1).

Protocol (aryan.md A3, requirements.md section 5.1 T1):
  - Feature sets S1 symptom_only, S2 symptom_plus_vitals, S3 with_labs_reference (non-deployable
    upper bound). Column disposition and leakage removal: sim/pcos_data.py, data/DATA_REGISTER.md.
  - Models: logistic regression, random forest, XGBoost, LightGBM, SVM (RBF), MLP, naive Bayes, k-NN.
  - Stratified 5-fold CV repeated over 5 seeds. All preprocessing (imputation, scaling, one-hot
    encoding) is fit inside each training fold only, via a single sklearn Pipeline, so nothing about
    a test fold leaks into its own preprocessing.
  - One row per (dataset, model, feature_set) per contract 5.1. Every patient gets one out-of-fold
    probability per seed (5 numbers per patient); those 5 are averaged into one probability per
    patient, and auc_mean, sens_at_90spec, spec_at_90sens and brier are all computed on that averaged
    probability, so every reported number describes the same estimator. The 95 percent CI is a
    patient-level bootstrap (2000 resamples) of auc_mean on that estimator. The per-seed AUCs are
    also kept (seed_aucs) to show how much a single training run varies before averaging; a model
    whose per-seed spread is wide (a high-variance model such as the MLP here) can have a seed-average
    AUC noticeably different from the mean of its individual seed AUCs. That gap is a finding about
    the model, not a bug in the reporting.
  - Paired comparison: for the two models with the highest auc_mean on each feature set, a paired
    bootstrap test on the AUC difference (same resamples for both models).
  - Class imbalance (177/364, about 33 percent positive): class_weight="balanced" where the model
    supports it, scale_pos_weight / is_unbalance for the boosted trees. No resampling (SMOTE) is
    applied in the primary run; T10 in the technique comparison covers that choice.

Run: python -m sim.classifiers   (needs data/raw/PCOS_data_without_infertility.xlsx, see data/download_pcos.py)
"""
from __future__ import annotations

import argparse
import json
import warnings

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC

from sim.common import ROOT, base_meta
from sim.pcos_data import FEATURE_SETS, load

SEEDS = [0, 1, 2, 3, 4]
N_FOLDS = 5
N_BOOT = 2000
DATASET_ID = "kaggle_pcos"
FEATURE_SET_SCHEMA = {"symptom_only": "symptom_only", "symptom_plus_vitals": "symptom_plus_vitals",
                      "with_labs_reference": "with_labs_reference"}


def _pos_weight(y) -> float:
    y = np.asarray(y)
    return float((y == 0).sum() / max((y == 1).sum(), 1))


def make_model(name: str, y_train, seed: int):
    """A fresh, seeded estimator. Class imbalance handled per model family, not by resampling (see module docstring)."""
    if name == "logistic_regression":
        return LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=seed, n_jobs=1)
    if name == "xgboost":
        from xgboost import XGBClassifier
        return XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05, eval_metric="logloss",
                             scale_pos_weight=_pos_weight(y_train), random_state=seed, n_jobs=1, verbosity=0)
    if name == "lightgbm":
        from lightgbm import LGBMClassifier
        return LGBMClassifier(n_estimators=300, max_depth=-1, learning_rate=0.05, is_unbalance=True,
                              random_state=seed, n_jobs=1, verbose=-1)
    if name == "svm_rbf":
        return SVC(kernel="rbf", probability=True, class_weight="balanced", random_state=seed)
    if name == "mlp":
        return MLPClassifier(hidden_layer_sizes=(32, 16), max_iter=2000, random_state=seed, early_stopping=True)
    if name == "naive_bayes":
        return GaussianNB()
    if name == "knn":
        return KNeighborsClassifier(n_neighbors=15)
    raise ValueError(f"unknown model {name}")


MODELS = ["logistic_regression", "random_forest", "xgboost", "lightgbm", "svm_rbf", "mlp", "naive_bayes", "knn"]


def make_pipeline(model_name: str, num_cols, cat_cols, y_train, seed: int) -> Pipeline:
    pre = ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), num_cols),
        ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore"))]), cat_cols),
    ])
    return Pipeline([("pre", pre), ("clf", make_model(model_name, y_train, seed))])


def sens_at_spec(y, p, target_spec: float) -> float:
    """Sensitivity at the operating point with specificity >= target_spec (linear interpolation on the ROC curve)."""
    fpr, tpr, _ = roc_curve(y, p)
    target_fpr = 1 - target_spec
    return float(np.interp(target_fpr, fpr, tpr))


def spec_at_sens(y, p, target_sens: float) -> float:
    """Specificity at the operating point with sensitivity >= target_sens."""
    fpr, tpr, _ = roc_curve(y, p)
    order = np.argsort(tpr)
    return float(1 - np.interp(target_sens, tpr[order], fpr[order]))


def brier_score(y, p) -> float:
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    return float(np.mean((p - y) ** 2))


def bootstrap_ci(y, p, metric_fn, seed: int = 0, n_boot: int = N_BOOT, alpha: float = 0.05) -> tuple[float, float]:
    y, p = np.asarray(y), np.asarray(p)
    rng = np.random.default_rng(seed)
    n = len(y)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        if len(np.unique(y[idx])) < 2:
            continue
        vals.append(metric_fn(y[idx], p[idx]))
    lo, hi = np.percentile(vals, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def paired_bootstrap_pvalue(y, p1, p2, seed: int = 0, n_boot: int = N_BOOT) -> float:
    """Two-sided paired bootstrap p-value for AUC(p1) - AUC(p2) != 0, resampling patients (not folds)."""
    y, p1, p2 = np.asarray(y), np.asarray(p1), np.asarray(p2)
    rng = np.random.default_rng(seed)
    n = len(y)
    diffs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        if len(np.unique(y[idx])) < 2:
            continue
        diffs.append(roc_auc_score(y[idx], p1[idx]) - roc_auc_score(y[idx], p2[idx]))
    diffs = np.asarray(diffs)
    observed = roc_auc_score(y, p1) - roc_auc_score(y, p2)
    centered = diffs - diffs.mean()  # null: no difference; test how extreme the observed value is
    return float(np.mean(np.abs(centered) >= abs(observed)))


def cross_validate(X, y, num_cols, cat_cols, model_name: str, n_folds: int = N_FOLDS, seeds=SEEDS) -> dict:
    y_arr = y.to_numpy()
    oof = np.full((len(seeds), len(y)), np.nan)
    for si, seed in enumerate(seeds):
        kf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
        for tr, te in kf.split(X, y_arr):
            pipe = make_pipeline(model_name, num_cols, cat_cols, y_arr[tr], seed)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pipe.fit(X.iloc[tr], y_arr[tr])
                oof[si, te] = pipe.predict_proba(X.iloc[te])[:, 1]
    seed_aucs = [roc_auc_score(y_arr, oof[si]) for si in range(len(seeds))]
    mean_prob = oof.mean(axis=0)
    auc_mean = roc_auc_score(y_arr, mean_prob)  # same estimator (seed-averaged probability) as the CI below
    ci_lo, ci_hi = bootstrap_ci(y_arr, mean_prob, roc_auc_score, seed=0)
    return {
        "oof_prob": oof, "mean_prob": mean_prob, "seed_aucs": seed_aucs,
        "auc_mean": float(auc_mean), "auc_ci_low": ci_lo, "auc_ci_high": ci_hi,
        "sens_at_90spec": sens_at_spec(y_arr, mean_prob, 0.90), "spec_at_90sens": spec_at_sens(y_arr, mean_prob, 0.90),
        "brier": brier_score(y_arr, mean_prob),
    }


def rows_for_feature_set(df, feature_set: str, models=MODELS, seeds=SEEDS) -> tuple[list[dict], dict, dict]:
    from sim.pcos_data import feature_matrix
    X, y, num_cols, cat_cols = feature_matrix(df, feature_set)
    rows, results, probs = [], {}, {}
    for name in models:
        out = cross_validate(X, y, num_cols, cat_cols, name, seeds=seeds)
        results[name] = out
        probs[name] = out["mean_prob"]
        rows.append({
            "dataset": DATASET_ID, "model": name, "feature_set": FEATURE_SET_SCHEMA[feature_set],
            "auc_mean": round(out["auc_mean"], 4), "auc_ci_low": round(out["auc_ci_low"], 4),
            "auc_ci_high": round(out["auc_ci_high"], 4), "sens_at_90spec": round(out["sens_at_90spec"], 4),
            "spec_at_90sens": round(out["spec_at_90sens"], 4), "brier": round(out["brier"], 4), "n_folds": N_FOLDS,
            "n_seeds": len(seeds), "seed_aucs": [round(a, 4) for a in out["seed_aucs"]],
        })
    ranked = sorted(models, key=lambda m: results[m]["auc_mean"], reverse=True)
    top2 = ranked[:2]
    y_arr = y.to_numpy()
    comparison = {
        "feature_set": FEATURE_SET_SCHEMA[feature_set], "model_a": top2[0], "model_b": top2[1],
        "auc_a": round(results[top2[0]]["auc_mean"], 4), "auc_b": round(results[top2[1]]["auc_mean"], 4),
        "test": "paired_bootstrap", "n_boot": N_BOOT,
        "p_value": round(paired_bootstrap_pvalue(y_arr, probs[top2[0]], probs[top2[1]], seed=0), 4),
    }
    return rows, comparison, results


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=ROOT / "results")
    ap.add_argument("--models", nargs="*", default=MODELS)
    ap.add_argument("--seeds", nargs="*", type=int, default=SEEDS)
    args = ap.parse_args()

    df = load()
    all_rows, comparisons, all_results = [], [], {}
    for fs in ["symptom_only", "symptom_plus_vitals", "with_labs_reference"]:
        rows, comparison, results = rows_for_feature_set(df, fs, args.models, args.seeds)
        all_rows += rows
        comparisons.append(comparison)
        all_results[fs] = results
        print(f"-- {fs} --")
        for r in sorted(rows, key=lambda r: -r["auc_mean"]):
            print(f"  {r['model']:20s} AUC {r['auc_mean']:.3f} [{r['auc_ci_low']:.3f},{r['auc_ci_high']:.3f}]  "
                 f"sens@90spec {r['sens_at_90spec']:.3f}  spec@90sens {r['spec_at_90sens']:.3f}  brier {r['brier']:.3f}")
        print(f"  top-2 paired bootstrap: {comparison['model_a']} vs {comparison['model_b']}, "
             f"p={comparison['p_value']}")

    dataset_row = {"id": DATASET_ID, "n_rows": int(len(df)), "n_features_used": len(FEATURE_SETS["with_labs_reference"]),
                  "label_definition": "PCOS (Y/N) as recorded by the contributing hospitals (diagnostic protocol UNVERIFIED, see data/DATA_REGISTER.md)"}
    out = {
        "meta": {**base_meta(args.seeds[0]), "seeds": args.seeds, "n_folds": N_FOLDS,
                "protocol": "stratified 5-fold CV x 5 seeds, preprocessing fit per fold, "
                "patient-level bootstrap CI (2000 resamples), paired bootstrap for the top-2 models per feature set"},
        "datasets": [dataset_row],
        "rows": all_rows,
        "comparisons": comparisons,
    }
    out_dir = args.out
    (out_dir / "classifiers.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_dir / 'classifiers.json'}")


if __name__ == "__main__":
    main()
