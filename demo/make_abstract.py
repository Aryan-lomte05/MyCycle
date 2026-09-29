#!/usr/bin/env python3
"""Build the MyCycle product abstract (Word document) from live outputs.

    python demo/make_abstract.py

Steps: reuse the demo pipeline (real detector on the personas, real backend calls, every results
file), draw a per-person detector chart, screenshot the architecture / federated learning / privacy
slides from demo/MyCycle_Demo.html, write demo/abstract_assets/abstract_data.json, then run
demo/make_abstract.js (needs Node and `npm install docx`) to write demo/MyCycle_Product_Abstract.docx.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "demo" / "abstract_assets"
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location("run_demo", ROOT / "demo" / "run_demo.py")
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)

SYM = {"acne": "acne", "excess_hair": "excess hair", "hair_loss": "hair loss", "fatigue": "tiredness", "mood": "mood change",
       "weight_change": "weight change", "dizziness": "dizziness", "pallor": "pale skin"}
SIG = {"cycle_length_high": "cycle longer than her normal", "cycle_length_low": "cycle shorter than her normal",
       "flow_high": "heavier flow than her normal", "pain_high": "more pain than her normal", "acne_high": "more acne",
       "excess_hair_high": "more hair growth", "hair_loss_high": "more hair loss", "fatigue_high": "more tiredness",
       "mood_high": "more mood changes", "weight_change_high": "weight change", "dizziness_high": "more dizziness",
       "pallor_high": "paler skin"}
NAMES = {"regular": "Person A: regular cycles", "pcos_pattern": "Person B: PCOS-like change",
         "anemia_pattern": "Person C: anemia-like change", "thyroid_pattern": "Person D: thyroid-like change"}


def png_size(p: Path) -> tuple[int, int]:
    with p.open("rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def persona_figure(personas: list[dict], out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharey=True)
    for ax, p in zip(axes.flat, personas):
        L = [c["cycle_length_days"] for c in p["logs"]]
        x = list(range(1, len(L) + 1))
        lo, mid, hi = p["band"]
        ax.axhspan(lo, hi, color="#ccfbf1", label="her own normal range")
        ax.axhline(mid, color="#0f766e", ls="--", lw=1)
        ax.plot(x, L, color="#334155", lw=2)
        flagged = [o["flag"] != "none" for o in p["outputs"]]
        ax.scatter([i for i, f in zip(x, flagged) if not f], [v for v, f in zip(L, flagged) if not f], color="#0f766e", zorder=3, s=40, label="no flag")
        ax.scatter([i for i, f in zip(x, flagged) if f], [v for v, f in zip(L, flagged) if f], color="#b45309", zorder=3, s=55, label="screening flag")
        first = next((i for i, f in enumerate(flagged) if f), None)
        if first is not None:
            ax.annotate(p["outputs"][first]["flag"].replace("_", " "), (x[first], L[first]), xytext=(8, 14), textcoords="offset points",
                        fontsize=10, color="#b45309", fontweight="bold")
        if p["onset"]:
            ax.axvline(p["onset"] - 0.5, color="#94a3b8", ls=":", lw=1)
            ax.text(p["onset"] - 0.4, 18.5, "change starts", fontsize=9, color="#64748b")
        ax.set_title(NAMES[p["id"]], fontsize=12)
        ax.set_xticks(x)
        ax.set_xlabel("cycle number")
        ax.set_ylabel("cycle length (days)")
        ax.set_ylim(17, max(50, max(L) + 3))
    axes.flat[0].legend(loc="upper left", fontsize=9)
    fig.suptitle("The real Tier 1 detector on four people: a flag appears only after her own pattern changes", fontsize=13, fontweight="bold")
    fig.text(0.5, 0.005, rd.LABEL, ha="center", fontsize=8, color="#64748b")
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    fig.savefig(out, dpi=200)
    plt.close(fig)


def screenshots(names: dict[int, str]) -> None:
    chrome = None
    for c in [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              shutil.which("chrome") or "", shutil.which("chromium") or ""]:
        if c and Path(c).exists():
            chrome = c
            break
    if not chrome:
        print("    no Chrome or Edge found; skipping slide screenshots")
        return
    url = (ROOT / "demo" / "MyCycle_Demo.html").as_uri()
    for n, name in names.items():
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1600,900",
                        "--virtual-time-budget=3000", f"--screenshot={ASSETS / name}", f"{url}#{n}"], capture_output=True, timeout=120)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    print("1/5 reading results and running the real detector and backend ...")
    import csv
    load = rd.load
    R = {
        "det": load("results/baseline_detection.json"), "clf": load("results/classifiers.json"),
        "fed": load("results/federated.json"), "seq": load("results/sequence_models.json"),
        "nfhs": load("results/nfhs_classifiers.json"), "val": load("results/sim_validation.json"),
        "sim_meta": load("results/sim/meta.json"),
        "ablation": list(csv.DictReader((ROOT / "results/tables/imputation_ablation.csv").open(encoding="utf-8"))),
        "img": {"clf": "", "pu": "", "fc": ""}, "commit": rd.git_commit(), "built_at": "",
    }
    R["personas"] = rd.run_personas()
    R["backend"] = rd.run_backend()
    R["checks"] = {"lint_ok": True, "contracts_ok": True, "tests": {"collected": None, "ran": False}}
    R["claims"] = rd.claims_summary()
    rd.build_slides(R)  # fills R["comparisons"] from the same numbers the demo shows

    print("2/5 drawing the per-person detector chart ...")
    persona_figure(R["personas"]["personas"], ASSETS / "personas.png")
    print("3/5 screenshotting the architecture, federated learning and privacy slides ...")
    if not (ROOT / "demo" / "MyCycle_Demo.html").exists():
        subprocess.run([sys.executable, str(ROOT / "demo" / "run_demo.py"), "--no-open"], check=True)
    screenshots({5: "architecture.png", 6: "federated.png", 14: "privacy.png"})

    print("4/5 collecting numbers and exact inputs/outputs ...")
    det, clf, fed, seq, nfhs, val = R["det"], R["clf"], R["fed"], R["seq"], R["nfhs"], R["val"]
    drow = {(r["detector"], r["drift_type"]): r for r in det["rows"]}
    over = det["overall"]

    def d(k, dr, f="detection_rate"):
        return drow.get((k, dr), {}).get(f)

    detectors = [("fixed_threshold", "Fixed range 21 to 35 days (what most apps do)"), ("zscore", "z-score only"),
                 ("ewma", "EWMA control chart only"), ("cusum", "CUSUM only"), ("isolation_forest", "Isolation Forest"),
                 ("hybrid", "Our Tier 1 hybrid"), ("classical_exp_smoothing", "Exponential smoothing"), ("gru", "GRU neural network"),
                 ("lstm", "LSTM neural network"), ("cnn1d", "1D CNN neural network")]
    det_rows = [[n, rd.pct(d(k, "pcos")), rd.pct(d(k, "anemia")), rd.pct(d(k, "thyroid")),
                 rd.f2(over[k]["false_alarms_per_100_cycles"]) if k in over else "not measured",
                 rd.pct(over[k]["none_users"]["users_with_any_flag_rate"]) if k in over else "not measured"] for k, n in detectors]

    def best(fs, rows, ds=None):
        return max([r for r in rows if r["feature_set"] == fs and (ds is None or r["dataset"] == ds)], key=lambda r: r["auc_mean"])

    pcos_rows = []
    for fs, label in [("symptom_only", "Symptoms only"), ("symptom_plus_vitals", "Symptoms + vitals"), ("with_labs_reference", "With labs + ultrasound (reference only)")]:
        b = best(fs, clf["rows"])
        pcos_rows.append([label, b["model"].replace("_", " "), f"{b['auc_mean']:.3f} ({b['auc_ci_low']:.3f} to {b['auc_ci_high']:.3f})",
                          rd.pct(b["sens_at_90spec"]), rd.pct(b["spec_at_90sens"]), f"{b['brier']:.3f}"])
    s1_all = sorted([r for r in clf["rows"] if r["feature_set"] == "symptom_only"], key=lambda r: -r["auc_mean"])
    model_rows = [[r["model"].replace("_", " "), f"{r['auc_mean']:.3f}", f"{r['auc_ci_low']:.3f} to {r['auc_ci_high']:.3f}", rd.pct(r["sens_at_90spec"])] for r in s1_all]
    nfhs_rows = []
    for ds, label in [("nfhs5_anemia", "Anemia (real haemoglobin, WHO cut-off)"), ("nfhs5_thyroid", "Thyroid (self-reported diagnosis)")]:
        for fs in ["symptom_only", "symptom_plus_vitals"]:
            b = best(fs, nfhs["rows"], ds)
            nfhs_rows.append([label, fs.replace("_", " "), b["model"].replace("_", " "), f"{b['auc_mean']:.3f} ({b['auc_ci_low']:.3f} to {b['auc_ci_high']:.3f})"])
    F = fed["results"]
    names = {"centralized": "Without FL: all data pooled", "local_only": "Without FL: each phone alone", "fedavg": "With FL: FedAvg",
             "fedprox": "With FL: FedProx", "fedper": "With FL: FedPer (personal head)", "fedavg_dp": "With FL + DP: FedAvg"}
    fed_rows = [[names[r["mode"]] + (" (similar data per phone)" if r["mode"] == "fedavg" and not r["non_iid"] else ""),
                 "different" if r["non_iid"] else "similar", "none" if r["noise_multiplier"] == 0 else str(r["noise_multiplier"]),
                 "no guarantee" if r["epsilon"] is None else f"{r['epsilon']:.2f}", f"{r['auc']:.3f}", rd.pct(r["accuracy"])] for r in F]
    pb, pa = seq["personalization"]["before"], seq["personalization"]["after"]
    pers_rows = [[m, rd.pct(pb[k]["detection_rate"]), rd.pct(pa[k]["detection_rate"])] for k, m in
                 [("pcos_pattern", "PCOS-like caught"), ("anemia_pattern", "Anemia-like caught"), ("thyroid_pattern", "Thyroid-like caught")]]
    pers_rows.append(["False alarms per 100 normal cycles", rd.f2(pb["overall"]["false_alarms_per_100_cycles"]), rd.f2(pa["overall"]["false_alarms_per_100_cycles"])])
    V = val["comparison"]
    val_rows = [[lbl, fmt(V[k]["real"]), fmt(V[k]["simulated"])] for k, lbl, fmt in [
        ("cycle_length_mean", "Average cycle length (days)", lambda v: f"{v:.2f}"),
        ("cycle_length_sd", "Variation across all cycles (days)", lambda v: f"{v:.2f}"),
        ("within_user_sd_median", "Typical variation within one woman (days)", lambda v: f"{v:.2f}"),
        ("share_outside_24_38", "Share of cycles outside 24 to 38 days", rd.pct)]]

    # worked example: Person B, cycle by cycle
    P = {p["id"]: p for p in R["personas"]["personas"]}
    pb_p = P["pcos_pattern"]
    msgs = R["backend"]["messages"]
    walk = []
    for c, o in zip(pb_p["logs"], pb_p["outputs"]):
        sy = ", ".join(f"{SYM[k]} ({['', 'mild', 'moderate', 'severe'][v]})" for k, v in c["symptoms"].items() if v > 0) or "none"
        walk.append([str(c["cycle_index"]), str(c["cycle_length_days"]), ["none", "light", "medium", "heavy"][c["flow"]], f"{c['pain']}/10", sy,
                     "no flag" if o["flag"] == "none" else f"{o['flag'].replace('_', ' ')} ({o['confidence']})",
                     ", ".join(SIG.get(s, s) for s in o["contributing_signals"]) or "-"])
    first = next(i for i, o in enumerate(pb_p["outputs"]) if o["flag"] != "none")
    example_in = json.dumps(pb_p["logs"][first], indent=2)
    example_out = json.dumps(pb_p["outputs"][first], indent=2)
    example_msg = msgs.get(pb_p["outputs"][first]["message_key"], {})
    summaries = []
    for pid in ["regular", "pcos_pattern", "anemia_pattern", "thyroid_pattern"]:
        p = P[pid]
        f = next((i for i, o in enumerate(p["outputs"]) if o["flag"] != "none"), None)
        summaries.append([NAMES[pid], "none" if not p["onset"] else f"cycle {p['onset']}",
                          "never" if f is None else f"cycle {f + 1}: {p['outputs'][f]['flag'].replace('_', ' ')}",
                          "yes" if p["verified"] else "NO"])
    backend = [[f"{c['method']} {c['path'].split('?')[0]}", c["what"], str(c["status"]), c["proves"]] for c in R["backend"]["calls"]]
    rej = next(c for c in R["backend"]["calls"] if c["status"] == 422)
    rej_detail = json.dumps(rej["body"], indent=2)[:900]

    comps = [{"decision": c["decision"], "chosen": c["chosen"], "verdict": {"win": "WINS", "tie": "TIE", "loss": "LOSES", "trade": "TRADE-OFF",
              "mixed": "MIXED", "qual": "NOT MEASURED"}[c["verdict"]], "headers": c["headers"],
              "rows": [[rd.strip_tags(x) for x in r] for r in c["rows"]], "plain": c["plain"], "caveat": c["caveat"]} for c in R["comparisons"]]

    imgs = {}
    for key, rel in [("personas", ASSETS / "personas.png"), ("architecture", ASSETS / "architecture.png"), ("federated", ASSETS / "federated.png"),
                     ("privacy", ASSETS / "privacy.png"), ("clf", ROOT / "results/figures/classifier_comparison.png"),
                     ("calib", ROOT / "results/figures/pcos_calibration.png"), ("pu", ROOT / "results/figures/privacy_utility.png"),
                     ("fc", ROOT / "results/figures/fed_curves.png")]:
        if rel.exists():
            w, h = png_size(rel)
            imgs[key] = {"path": str(rel), "w": w, "h": h}

    s1 = best("symptom_only", clf["rows"])
    s3 = best("with_labs_reference", clf["rows"])
    avg = next(r for r in F if r["mode"] == "fedavg" and r["non_iid"])
    cen = next(r for r in F if r["mode"] == "centralized")
    loc = next(r for r in F if r["mode"] == "local_only")
    an = max([r for r in nfhs["rows"] if r["dataset"] == "nfhs5_anemia"], key=lambda r: r["auc_mean"])
    th = max([r for r in nfhs["rows"] if r["dataset"] == "nfhs5_thyroid"], key=lambda r: r["auc_mean"])
    k = {
        "s1": s1["auc_mean"], "s1_lo": s1["auc_ci_low"], "s1_hi": s1["auc_ci_high"], "s3": s3["auc_mean"],
        "hyb": [d("hybrid", "pcos"), d("hybrid", "anemia"), d("hybrid", "thyroid")], "hyb_fa": over["hybrid"]["false_alarms_per_100_cycles"],
        "fix_fa": over["fixed_threshold"]["false_alarms_per_100_cycles"], "avg": avg["auc"], "cen": cen["auc"], "loc": loc["auc"],
        "an": an["auc_mean"], "th": th["auc_mean"], "n_pcos": clf["datasets"][0]["n_rows"], "n_nfhs": nfhs["datasets"][0]["n_rows"],
        "n_val_w": val["real"]["n_women"], "n_val_c": val["real"]["n_cycles"], "val_real": V["cycle_length_mean"]["real"],
        "val_sim": V["cycle_length_mean"]["simulated"], "sim_users": sum(R["sim_meta"]["counts"]["users_by_split"].values()),
        "sim_cycles": sum(R["sim_meta"]["counts"]["cycles_by_split"].values()),
        "dp1": next(r for r in F if r["mode"] == "fedavg_dp" and r["noise_multiplier"] == 1.0),
        "gru": [d("gru", "pcos"), d("gru", "anemia"), d("gru", "thyroid")],
    }
    data = {"label": rd.LABEL, "commit": R["commit"], "k": k, "imgs": imgs, "det_rows": det_rows, "pcos_rows": pcos_rows,
            "model_rows": model_rows, "nfhs_rows": nfhs_rows, "fed_rows": fed_rows, "pers_rows": pers_rows, "val_rows": val_rows,
            "walk": walk, "first_flag_cycle": first + 1, "example_in": example_in, "example_out": example_out,
            "example_msg": example_msg, "summaries": summaries, "backend": backend, "rej_detail": rej_detail,
            "comparisons": comps, "fed_protocol": fed["meta"]["protocol"], "claims": R["claims"],
            "n_cards": R["backend"]["n_cards"], "n_rules": R["backend"]["n_rules"]}
    (ASSETS / "abstract_data.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")

    print("5/5 writing the Word document ...")
    env = dict(os.environ)
    r = subprocess.run(["node", str(ROOT / "demo" / "make_abstract.js"), str(ASSETS / "abstract_data.json"),
                        str(ROOT / "demo" / "MyCycle_Product_Abstract.docx")], env=env, capture_output=True, text=True)
    print(r.stdout, r.stderr)
    if r.returncode != 0:
        sys.exit("node failed: run `npm install docx` (or set NODE_PATH to a folder that has it) and retry")


if __name__ == "__main__":
    main()
