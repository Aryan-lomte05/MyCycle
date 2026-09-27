"""Figures for package A3: classifier comparison, calibration, and the imputation ablation table.

Reads results/classifiers.json (written by sim.classifiers). Recomputes calibration curves and the
imputation ablation directly (the dataset is small, so this is cheap), rather than storing every
model's raw out-of-fold predictions in the results JSON.

Outputs (300 dpi, simulated label in the corner of every figure):
  results/figures/classifier_comparison.png
  results/figures/pcos_calibration.png
  results/tables/imputation_ablation.md, .csv

Run: python -m sim.make_figures   (after python -m sim.classifiers)
"""
from __future__ import annotations

import json

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from sklearn.impute import KNNImputer  # noqa: E402

from sim.classifiers import cross_validate  # noqa: E402
from sim.common import LABEL, ROOT  # noqa: E402
from sim.pcos_data import feature_matrix, load  # noqa: E402

FIG_DIR = ROOT / "results" / "figures"
TAB_DIR = ROOT / "results" / "tables"
FEATURE_SET_ORDER = ["symptom_only", "symptom_plus_vitals", "with_labs_reference"]
FEATURE_SET_TITLE = {"symptom_only": "S1 symptom only", "symptom_plus_vitals": "S2 symptom + vitals",
                     "with_labs_reference": "S3 with labs (reference, non-deployable)"}


def stamp(ax_or_fig) -> None:
    ax_or_fig.text(0.995, 0.01, LABEL, transform=getattr(ax_or_fig, "transFigure", None) or ax_or_fig.transAxes,
                   ha="right", va="bottom", fontsize=6, color="0.4", wrap=True)


def classifier_comparison_figure(classifiers: dict) -> None:
    rows = classifiers["rows"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharex=True)
    for ax, fs in zip(axes, FEATURE_SET_ORDER):
        fs_rows = sorted([r for r in rows if r["feature_set"] == fs], key=lambda r: r["auc_mean"])
        names = [r["model"] for r in fs_rows]
        means = [r["auc_mean"] for r in fs_rows]
        lo = [r["auc_mean"] - r["auc_ci_low"] for r in fs_rows]
        hi = [r["auc_ci_high"] - r["auc_mean"] for r in fs_rows]
        ax.barh(names, means, xerr=[lo, hi], color="#4C72B0", ecolor="0.3", capsize=3)
        ax.set_xlim(0.5, 1.0)
        ax.axvline(0.5, color="0.7", linestyle="--", linewidth=1)
        ax.set_title(FEATURE_SET_TITLE[fs], fontsize=11)
        ax.set_xlabel("AUC (mean, 95% bootstrap CI)")
    fig.suptitle("Symptom-only PCOS screening approaches the with-labs reference AUC", fontsize=13)
    fig.text(0.5, -0.03,
             "Fig.: kaggle_pcos, n=541 patients. AUC mean and 95% CI (patient-level bootstrap, 2000 resamples) "
             "from stratified 5-fold CV x 5 seeds, out-of-fold predictions averaged across seeds. " + LABEL,
             ha="center", fontsize=8, wrap=True)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "classifier_comparison.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def calibration_bins(y: np.ndarray, p: np.ndarray, n_bins: int = 8) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    edges = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, n_bins - 1)
    mean_pred = np.array([p[idx == b].mean() if (idx == b).any() else np.nan for b in range(n_bins)])
    frac_pos = np.array([y[idx == b].mean() if (idx == b).any() else np.nan for b in range(n_bins)])
    counts = np.array([(idx == b).sum() for b in range(n_bins)])
    return mean_pred, frac_pos, counts


def calibration_figure(df) -> None:
    X, y, num, cat = feature_matrix(df, "symptom_only")
    y_arr = y.to_numpy()
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="perfect calibration")
    for model, color in [("logistic_regression", "#4C72B0"), ("random_forest", "#DD8452")]:
        out = cross_validate(X, y, num, cat, model, n_folds=5, seeds=[0, 1, 2, 3, 4])
        mean_pred, frac_pos, counts = calibration_bins(y_arr, out["mean_prob"])
        ok = counts >= 5  # drop bins with too few patients to plot a stable point
        ax.plot(mean_pred[ok], frac_pos[ok], marker="o", color=color, label=f"{model} (Brier {out['brier']:.3f})")
    ax.set_xlabel("Predicted probability (mean per bin)")
    ax.set_ylabel("Observed PCOS rate (mean per bin)")
    ax.set_title("Predicted risk tracks observed PCOS rate, symptom-only features")
    ax.legend(loc="upper left", fontsize=9)
    fig.text(0.5, -0.04, "Fig.: kaggle_pcos, n=541, symptom_only feature set, 8 equal-width bins, "
                        "out-of-fold probabilities averaged over 5 seeds x 5-fold CV. " + LABEL,
             ha="center", fontsize=8, wrap=True)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "pcos_calibration.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def imputation_ablation(df) -> list[dict]:
    """Median (primary, used everywhere else) vs a KNN imputer, on the 2 columns that actually have gaps.

    kaggle_pcos has only 2 missing values total (data/DATA_REGISTER.md), so this ablation mainly
    documents that the choice does not matter here, not a meaningful accuracy comparison.
    """
    rows = []
    for fs in FEATURE_SET_ORDER:
        X, y, num, cat = feature_matrix(df, fs)
        for model in ["logistic_regression", "random_forest"]:
            median_auc = cross_validate(X, y, num, cat, model, n_folds=5, seeds=[0, 1, 2])["auc_mean"]
            X_knn = X.copy()
            if num:
                X_knn[num] = KNNImputer(n_neighbors=5).fit_transform(X[num])
            knn_auc = cross_validate(X_knn, y, num, cat, model, n_folds=5, seeds=[0, 1, 2])["auc_mean"]
            rows.append({"feature_set": fs, "model": model, "median_impute_auc": round(median_auc, 4),
                        "knn_impute_auc": round(knn_auc, 4), "abs_diff": round(abs(median_auc - knn_auc), 4)})
    return rows


def write_ablation_table(rows: list[dict]) -> None:
    header = ["Feature set", "Model", "Median impute AUC", "KNN impute AUC", "Abs diff"]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        lines.append(f"| {FEATURE_SET_TITLE[r['feature_set']]} | {r['model']} | {r['median_impute_auc']:.4f} | "
                     f"{r['knn_impute_auc']:.4f} | {r['abs_diff']:.4f} |")
    lines.append("")
    lines.append(f"Table: kaggle_pcos, n=541, 5-fold CV x 3 seeds. Only 2 of 541 rows have any missing value "
                 f"(data/DATA_REGISTER.md), so this table shows the choice barely matters on this dataset, "
                 f"not a general result. {LABEL}")
    (TAB_DIR / "imputation_ablation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    import csv
    with open(TAB_DIR / "imputation_ablation.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TAB_DIR.mkdir(parents=True, exist_ok=True)
    classifiers = json.loads((ROOT / "results" / "classifiers.json").read_text(encoding="utf-8"))
    df = load()
    classifier_comparison_figure(classifiers)
    calibration_figure(df)
    ablation = imputation_ablation(df)
    write_ablation_table(ablation)
    print("wrote classifier_comparison.png, pcos_calibration.png, imputation_ablation.md/.csv")


if __name__ == "__main__":
    main()
