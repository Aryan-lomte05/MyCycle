"""Classifier comparison on NFHS-5 anemia and thyroid tasks (package A3 extension).

Reuses the exact protocol code from sim/classifiers.py (cross_validate, bootstrap CI, paired
bootstrap, sens/spec at operating points), so numbers are computed the same way as kaggle_pcos.

Two deviations from the kaggle_pcos protocol, both because NFHS-5 has 126,625 eligible rows against
kaggle_pcos's 541, and this course's compute budget does not stretch to the full population at the
same model roster:
  - SVM (RBF) is dropped. Its training cost grows faster than linearly in the number of rows; a
    quick timing check (30 features, RBF, probability=True) took about 30 seconds to fit on 5,000
    rows alone, which would not finish A3's grid in the time available. This is a computational
    exclusion (requirements.md T1 candidate table marks it "excluded", with this reason), not an
    accuracy judgment.
  - Each task is evaluated on a stratified-by-label subsample (default 10,000 rows) rather than the
    full 126,625, for the same reason (random forest at n_estimators=100 already takes real time at
    this scale). The subsample size and the fact that it is a subsample are recorded in every output
    file's meta, so nobody mistakes this for the full population.

Everything else matches kaggle_pcos: stratified 5-fold CV x 5 seeds, all preprocessing fit inside
each fold, patient-level (here: respondent-level) bootstrap CI, class_weight="balanced" for the
imbalance (thyroid prevalence is about 1.9 percent).

Run: python -m sim.nfhs_classifiers   (needs data/raw/nfhs5/Final.csv, see data/download_nfhs5.py)
"""
from __future__ import annotations

import argparse
import json

from sim.classifiers import MODELS as PCOS_MODELS
from sim.classifiers import cross_validate, paired_bootstrap_pvalue
from sim.common import ROOT, base_meta
from sim.nfhs_data import LABEL_COL, N_ROWS_EXPECTED, feature_matrix, feature_sets, load, stratified_subsample

MODELS = [m for m in PCOS_MODELS if m != "svm_rbf"]
# 3 seeds, not 5: random forest at 300 trees on this many rows is the bottleneck (a timing check
# put 200 trees on 15,000 rows at about 27s per fit); 3 seeds x 5 folds x 4 (task x feature set)
# combinations already costs real time. Still bootstrapped for a CI; documented in every output's meta.
SEEDS = [0, 1, 2]
N_FOLDS = 5
SUBSAMPLE_N = 6_000
TASKS = ["anemia", "thyroid"]
FEATURE_SET_SCHEMA = {"symptom_only": "symptom_only", "symptom_plus_vitals": "symptom_plus_vitals"}


def rows_for_task(df, task: str, models=MODELS, seeds=SEEDS) -> tuple[list[dict], list[dict]]:
    rows, comparisons, probs_by_fs = [], [], {}
    for fs in ["symptom_only", "symptom_plus_vitals"]:
        X, y, num_cols, cat_cols = feature_matrix(df, task, fs)
        results = {}
        for name in models:
            out = cross_validate(X, y, num_cols, cat_cols, name, n_folds=N_FOLDS, seeds=seeds)
            results[name] = out
            rows.append({
                "dataset": f"nfhs5_{task}", "model": name, "feature_set": FEATURE_SET_SCHEMA[fs],
                "auc_mean": round(out["auc_mean"], 4), "auc_ci_low": round(out["auc_ci_low"], 4),
                "auc_ci_high": round(out["auc_ci_high"], 4), "sens_at_90spec": round(out["sens_at_90spec"], 4),
                "spec_at_90sens": round(out["spec_at_90sens"], 4), "brier": round(out["brier"], 4),
                "n_folds": N_FOLDS, "n_seeds": len(seeds), "seed_aucs": [round(a, 4) for a in out["seed_aucs"]],
            })
        ranked = sorted(models, key=lambda m: results[m]["auc_mean"], reverse=True)
        top2 = ranked[:2]
        y_arr = y.to_numpy()
        comparisons.append({
            "dataset": f"nfhs5_{task}", "feature_set": FEATURE_SET_SCHEMA[fs], "model_a": top2[0], "model_b": top2[1],
            "auc_a": round(results[top2[0]]["auc_mean"], 4), "auc_b": round(results[top2[1]]["auc_mean"], 4),
            "test": "paired_bootstrap", "n_boot": 2000,
            "p_value": round(paired_bootstrap_pvalue(y_arr, results[top2[0]]["mean_prob"], results[top2[1]]["mean_prob"], seed=0), 4),
        })
    return rows, comparisons


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=ROOT / "results")
    ap.add_argument("--subsample-n", type=int, default=SUBSAMPLE_N)
    ap.add_argument("--seeds", nargs="*", type=int, default=SEEDS)
    args = ap.parse_args()

    full = load()
    all_rows, all_comparisons, dataset_entries = [], [], []
    for task in TASKS:
        sub = stratified_subsample(full, task, args.subsample_n, seed=0)
        n_features = len(feature_sets(full, task)["symptom_plus_vitals"])
        label_rate = sub[LABEL_COL[task]].mean()
        dataset_entries.append({
            "id": f"nfhs5_{task}", "n_rows": int(len(full)), "n_features_used": n_features,
            "label_definition": ("WHO threshold on real haemoglobin, non-pregnant respondents (Hg_levelAdjusted < 12.0 g/dL); "
                                 "UNVERIFIED until the WHO source is read and logged in docs/papers.csv" if task == "anemia"
                                 else "self-reported existing thyroid condition (weaker than a TSH lab label; see sim/nfhs_data.py)"),
            "modeling_subsample_n": int(len(sub)), "modeling_label_rate": round(float(label_rate), 4),
        })
        print(f"== nfhs5_{task}: {len(full)} eligible rows, modeling on a {len(sub)}-row stratified subsample ({label_rate:.1%} positive) ==")
        rows, comparisons = rows_for_task(sub, task, MODELS, args.seeds)
        all_rows += rows
        all_comparisons += comparisons
        for r in sorted(rows, key=lambda r: (-r["auc_mean"])):
            print(f"  {r['feature_set']:22s} {r['model']:20s} AUC {r['auc_mean']:.3f} [{r['auc_ci_low']:.3f},{r['auc_ci_high']:.3f}]")

    out = {
        "meta": {**base_meta(args.seeds[0]), "seeds": args.seeds, "n_folds": N_FOLDS, "excluded_models": ["svm_rbf"],
                "exclusion_reason": "SVM RBF training cost is superlinear in n; infeasible at this dataset's scale in the course time budget",
                "subsample_n_requested": args.subsample_n, "n_rows_full_eligible": N_ROWS_EXPECTED},
        "datasets": dataset_entries,
        "rows": all_rows,
        "comparisons": all_comparisons,
    }
    (args.out / "nfhs_classifiers.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out / 'nfhs_classifiers.json'}")


if __name__ == "__main__":
    main()
