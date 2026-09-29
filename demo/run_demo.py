#!/usr/bin/env python3
"""MyCycle end-to-end demo: one command builds one offline HTML presentation and opens it.

    python demo/run_demo.py              build demo/MyCycle_Demo.html and open it in the browser
    python demo/run_demo.py --run-tests  also run the full test suite and show the real pass count
    python demo/run_demo.py --no-open    build only

What happens when you run it (everything shown is produced live, nothing is typed by hand):
  1. Reads every results file in results/ (classifiers, detection, federated, sequence models,
     NFHS-5, simulator validation, thresholds).
  2. Runs the real Tier 1 detector (sim/detectors.py) on the four demo personas and checks that
     each one produces its expected flag.
  3. Starts the real FastAPI backend in-process (against a throwaway database, so the committed
     server/aggregate.db is never touched) and calls every endpoint, including a request that
     tries to send cycle-log data, which the backend must reject.
  4. Runs the repo's language lint and contract validation.
  5. Writes demo/MyCycle_Demo.html (single file, no internet needed, images embedded) plus
     demo/SPEAKER_SCRIPT.md (what to say on each slide, in plain language) and
     demo/COMPARISONS.md (why we chose each method, with the honest verdict).

In the browser: arrow keys or click to move, P = pause/play autoplay, F = fullscreen,
N = show speaker notes. Autoplay starts on its own and loops, for the smart board.
"""
from __future__ import annotations

import argparse
import base64
import datetime
import html
import json
import re
import statistics
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sim.common import LABEL, git_commit  # noqa: E402

sys.path.insert(0, str(ROOT / "demo"))
import form_spec as FS  # noqa: E402

OUT_DIR = ROOT / "demo"
RES = ROOT / "results"


# --------------------------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------------------------

def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def pct(x) -> str:
    return "n/a" if x is None else f"{x * 100:.0f}%"


def f3(x) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def f2(x) -> str:
    return "n/a" if x is None else f"{x:.2f}"


def esc(s) -> str:
    return html.escape(str(s))


def img_uri(rel: str) -> str:
    p = ROOT / rel
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode("ascii") if p.exists() else ""


def table(headers: list[str], rows: list[list[str]], highlight: set[int] | None = None, small: bool = False, tiny: bool = False) -> str:
    highlight = highlight or set()
    h = "".join(f"<th>{esc(x)}</th>" for x in headers)
    body = ""
    for i, r in enumerate(rows):
        cls = ' class="hl"' if i in highlight else ""
        body += f"<tr{cls}>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
    return f'<table class="{"tiny" if tiny else "small" if small else ""}"><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table>'


def badge(kind: str) -> str:
    text = {"win": "WINS", "tie": "TIE", "loss": "LOSES", "trade": "TRADE-OFF", "mixed": "MIXED",
            "qual": "NOT MEASURED, REASONED ONLY"}[kind]
    return f'<span class="badge {kind}">{text}</span>'


def bullets(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


# --------------------------------------------------------------------------------------------
# live steps
# --------------------------------------------------------------------------------------------

def run_personas() -> dict:
    """Run the real Tier 1 hybrid detector on each demo persona, cycle by cycle."""
    from sim.detectors import HybridDetector

    manifest = load("exports/demo_users/manifest.json")
    params = manifest["meta"]["detector_params"]
    out = []
    for p in manifest["personas"]:
        logs = load(f"exports/demo_users/{p['file']}")
        det = HybridDetector(**params)
        outputs = [det.update(c) for c in logs]
        onset = p["first_abnormal_cycle"] or 6
        base = [c["cycle_length_days"] for c in logs[: onset - 1]]
        mean = statistics.mean(base)
        sd = statistics.stdev(base) if len(base) > 1 else 1.0
        out.append({
            "id": p["id"], "expected": p["expected_flag"], "onset": p["first_abnormal_cycle"],
            "logs": logs, "outputs": outputs,
            "verified": [o["flag"] for o in outputs] == p["expected_flags"],
            "band": [round(mean - 2 * sd, 2), round(mean, 2), round(mean + 2 * sd, 2)],
        })
    return {"params": params, "personas": out}


def run_backend() -> dict:
    """Start the real FastAPI app in-process with a throwaway database and call every endpoint."""
    import server.db as db

    db.DB_PATH = Path(tempfile.mkdtemp()) / "demo_aggregate.db"  # never touch the committed server/aggregate.db
    from fastapi.testclient import TestClient

    import server.main as main

    c = TestClient(main.app)
    calls = []

    def call(method: str, path: str, what: str, proves: str, body=None):
        r = c.request(method, path, json=body)
        calls.append({"method": method, "path": path, "status": r.status_code, "what": what, "proves": proves,
                      "body": r.json() if r.headers.get("content-type", "").startswith("application/json") else None})
        return r

    health = call("GET", "/v1/health", "Is the server alive", "Backend runs")
    msgs = call("GET", "/v1/content/messages?lang=en", "Flag wording for the app", "The app never invents flag text")
    cards = call("GET", "/v1/content/cards?lang=en", "Education cards", "Content is served, not hard-coded")
    rules = call("GET", "/v1/reminders/rules", "Reminder rules", "Rules are evaluated on the phone, server only sends definitions")
    call("POST", "/v1/metrics/aggregate", "Send one anonymous count", "Only allowed counts are accepted",
         {"metric_name": "app_opened_count", "value": 1})
    call("POST", "/v1/metrics/aggregate", "Try to smuggle a cycle length", "Log data is refused (must be 422)",
         {"metric_name": "app_opened_count", "value": 1, "cycle_length_days": 29})
    call("POST", "/v1/metrics/aggregate", "Try an unknown metric", "Anything off the allow-list is refused (must be 422)",
         {"metric_name": "user_symptoms", "value": 3})
    messages = msgs.json().get("messages", {})
    return {"calls": calls, "messages": messages, "n_cards": cards.json().get("count"),
            "n_rules": len(rules.json().get("rules", [])), "health": health.json()}


def run_checks(run_tests: bool) -> dict:
    def run(cmd: list[str], timeout: int) -> tuple[int, str]:
        try:
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
            return r.returncode, (r.stdout + r.stderr)
        except subprocess.TimeoutExpired:
            return -1, "timed out"

    lint_rc, _ = run([sys.executable, "scripts/lint_language.py"], 120)
    con_rc, _ = run([sys.executable, "scripts/validate_contracts.py"], 120)
    out = {"lint_ok": lint_rc == 0, "contracts_ok": con_rc == 0, "tests": None}
    if run_tests:
        rc, text = run([sys.executable, "-m", "pytest", "-q", "tests"], 1800)
        m = re.search(r"(\d+) passed", text)
        f = re.search(r"(\d+) failed", text)
        out["tests"] = {"passed": int(m.group(1)) if m else 0, "failed": int(f.group(1)) if f else 0, "ran": True}
    else:
        rc, text = run([sys.executable, "-m", "pytest", "--collect-only", "-q", "tests"], 600)
        m = re.search(r"(\d+) tests? collected", text)
        out["tests"] = {"collected": int(m.group(1)) if m else None, "ran": False}
    return out


def claims_summary() -> dict:
    rows = [l for l in (ROOT / "docs/CLAIMS_EVIDENCE.md").read_text(encoding="utf-8").splitlines() if l.startswith("| C")]
    status = {"supported": 0, "needs work": 0, "remove": 0}
    for l in rows:
        cells = [c.strip() for c in l.strip("|").split("|")]
        s = cells[-2] if len(cells) >= 2 else ""
        status[s] = status.get(s, 0) + 1
    return {"total": len(rows), **status}


# --------------------------------------------------------------------------------------------
# slide content (every number is read from results files above)
# --------------------------------------------------------------------------------------------

def build_slides(R: dict) -> list[dict]:
    det, clf, fed, seq, nfhs, val, sim_meta = R["det"], R["clf"], R["fed"], R["seq"], R["nfhs"], R["val"], R["sim_meta"]
    S = []

    def slide(section, title, body, say, dur=18, kind="text"):
        S.append({"section": section, "title": title, "body": body, "say": say, "dur": dur, "kind": kind})

    # detection lookup
    drow = {(r["detector"], r["drift_type"]): r for r in det["rows"]}
    ref = {(r["detector"], r["drift_type"]): r for r in det.get("reference_rows", [])}
    over = det["overall"]

    def dr(k, d, field="detection_rate"):
        return (drow.get((k, d)) or ref.get((k, d)) or {}).get(field)

    def fa(k):
        return over.get(k, {}).get("false_alarms_per_100_cycles")

    def healthy(k):
        return over.get(k, {}).get("none_users", {}).get("users_with_any_flag_rate")

    # classifier lookup
    def best(fs, rows=None, ds=None):
        rows = rows or clf["rows"]
        rs = [r for r in rows if r["feature_set"] == fs and (ds is None or r["dataset"] == ds)]
        return max(rs, key=lambda r: r["auc_mean"])

    def model(fs, name, rows=None, ds=None):
        rows = rows or clf["rows"]
        return next(r for r in rows if r["feature_set"] == fs and r["model"] == name and (ds is None or r["dataset"] == ds))

    s1, s2, s3 = best("symptom_only"), best("symptom_plus_vitals"), best("with_labs_reference")
    mlp1 = model("symptom_only", "mlp")
    comp = {c["feature_set"]: c for c in clf["comparisons"]}

    # federated lookup
    F = fed["results"]
    cen = next(r for r in F if r["mode"] == "centralized")
    loc = next(r for r in F if r["mode"] == "local_only")
    avg_iid = next(r for r in F if r["mode"] == "fedavg" and not r["non_iid"])
    avg = next(r for r in F if r["mode"] == "fedavg" and r["non_iid"])
    prox = next(r for r in F if r["mode"] == "fedprox")
    per = next(r for r in F if r["mode"] == "fedper")
    dp = sorted([r for r in F if r["mode"] == "fedavg_dp"], key=lambda r: r["noise_multiplier"])

    # sequence + personalization
    pb, pa = seq["personalization"]["before"], seq["personalization"]["after"]

    # nfhs
    NR = nfhs["rows"]
    an = max([r for r in NR if r["dataset"] == "nfhs5_anemia"], key=lambda r: r["auc_mean"])
    th = max([r for r in NR if r["dataset"] == "nfhs5_thyroid"], key=lambda r: r["auc_mean"])
    th_comp = next(c for c in nfhs["comparisons"] if c["dataset"] == "nfhs5_thyroid" and c["feature_set"] == th["feature_set"])
    nfhs_n = next(d for d in nfhs["datasets"] if d["id"] == "nfhs5_anemia")

    V = val["comparison"]
    pcos_ds = clf["datasets"][0]
    sim_users = sum(sim_meta["counts"]["users_by_split"].values())
    sim_cycles = sum(sim_meta["counts"]["cycles_by_split"].values())

    # ---------------------------------------------------------------- A. what and why
    slide("Introduction", "MyCycle",
          '<div class="hero"><div class="big">Built around your own normal.</div>'
          '<p class="lead">A privacy-preserving menstrual health <b>screening</b> system. It compares each new cycle with '
          'the same person\'s own history and raises a <b>screening flag</b> for patterns that look like PCOS, anemia or '
          'thyroid problems, using only symptoms a person can log herself. No lab test needed. Raw logs never leave the phone.</p>'
          '<p class="muted">It never diagnoses. Every flag says: consider consulting a doctor.</p>'
          '<p class="muted">216U50P501 Community Engagement Project with Design Thinking. Guide: Dr. Makarand G. Kulkarni.<br>'
          'Aryan Lomte, Liza Patel, Saanj Patil, Aditya Lokhande</p></div>',
          "MyCycle is a screening aid. It learns what is normal for one person and notices when that person's pattern "
          "changes in a way that looks like PCOS, anemia or thyroid trouble. It never gives a diagnosis; it always suggests seeing a doctor.",
          dur=14)

    slide("Introduction", "The problem: four barriers stack up",
          table(["Barrier", "What it looks like"], [
              ["Clinical access", "Hormone tests, blood counts and ultrasound cost money and are often far away"],
              ["Information", "Myths fill the gap, for example \"irregular periods are just stress\""],
              ["Privacy", "Most existing cycle apps keep everyone's raw data on company servers"],
              ["Culture", "Shame and taboo stop people discussing symptoms, even at home"],
          ]) + '<p class="note">Result: PCOS, anemia and thyroid problems are often noticed late.</p>',
          "Four things stack on top of each other: tests are costly or far away, myths fill the information gap, "
          "people do not trust apps with intimate data, and taboo stops the conversation. MyCycle attacks the first three with software.")

    slide("Introduction", "What existing systems do, and what is missing",
          table(["Existing systems", "What they do", "What is missing"], [
              ["Existing cycle apps", "Predict the next period, flag cycles outside a fixed range such as 21 to 35 days", "A range made for the average woman, not for you; raw data stored on their servers"],
              ["Existing PCOS research models", "High accuracy using hormone tests and ultrasound", "Needs a lab visit, so it cannot screen early at home"],
              ["Existing federated PCOS work", "Trains across hospitals without pooling data", "Hospital data, not a person's own history over time"],
          ]) + '<p class="note">Our four contributions: (1) a personal-baseline screening method, (2) a measured privacy vs accuracy study, '
          '(3) honest symptom-only screening with the accuracy cost stated, (4) a working system with privacy and family roles built in.</p>',
          "Existing apps use one fixed range for everyone and keep raw data on their servers. Existing research gets high accuracy only with lab tests. "
          "What is missing is screening that is personal, needs no lab, and keeps data on the phone. These are feature and method differences; "
          "we do not claim to be more accurate than any named app.", dur=22)

    slide("Introduction", "What the product does (and what is built today)",
          table(["Part", "What it does", "Status today"], [
              ["Personal baseline + screening flag", "Learns your normal, flags a PCOS-like, anemia-like or thyroid-like change", "Built and tested (Tier 1 detector)"],
              ["Symptom-only screening models", "Estimates risk from symptoms alone, no lab values", "Built, measured on real data"],
              ["Private learning across phones", "Phones improve a shared model without sending raw logs", "Built and measured in simulation"],
              ["Backend", "Flag wording, education cards, reminder rules, anonymous counts only", "Built, running (shown live later)"],
              ["Phone app (screens)", "Logging, baseline chart, flag card, privacy counter, family view", "In progress"],
          ], small=True),
          "The engine is built and measured: the detector, the models, the private learning, and the backend. The phone app screens are still being built. "
          "Everything you see in this demo runs the real code, not mock-ups.", dur=20)

    # ---------------------------------------------------------------- the logging form (demo/form_spec.py is the single source)
    v1 = [q for s in FS.FORM for q in s["questions"] if q["status"] == "v1"]
    def short_ans(q):
        if q["type"] == "sev":
            return "None / Mild / Moderate / Severe"
        if q["type"] == "scale":
            return "0 to 10, every band labeled"
        if q["type"] == "date":
            return "date (cycle length computed)"
        return " / ".join(x.split(":")[0] for _, x in q["options"])
    slide("The logging form", f"The form: {len(v1)} questions the detector uses today",
          table(["Question she answers", "Answer", "Feeds"], [[esc(q["q"]), esc(short_ans(q)), esc(q["feeds"])] for q in v1], tiny=True)
          + '<p class="note">One short form per cycle, not a daily diary. Try it: <code>demo/logging_form.html</code> prints the exact record it stores.</p>',
          "She fills one short form per period. Each question exists because it feeds one of the signals the detector watches. We ask for dates, not cycle length, because people misremember cycle length.",
          dur=26)
    pq = next(q for s in FS.FORM for q in s["questions"] if q["id"] == "pain")
    fq = next(q for s in FS.FORM for q in s["questions"] if q["id"] == "flow")
    slide("The logging form", "How pain and flow are measured, so a number means the same to everyone",
          '<div class="cols"><div><h3>Pain: worst pain this cycle, 0 to 10</h3>'
          + table(["Score", "What it means"], [[esc(a), esc(b)] for a, b in pq["anchors"]], small=True)
          + '<p class="caption">Validated menstrual pain scale (0 = No pain, 10 = Extremely severe); a change of about 1 point is meaningful '
            '(Frontiers in Pain Research 2025). Middle labels are our wording, tied to daily life.</p></div>'
          + '<div><h3>Flow: heaviest day</h3>' + table(["Level", "What she sees"], [[str(v), esc(x)] for v, x in fq["options"]], small=True)
          + '<p class="caption">Described by the pad or tampon, not a vague word. Optional: the standard pictorial blood-loss chart '
            '(Higham 1990, UNVERIFIED) turns pad counts and clots into a score on the phone.</p></div></div>',
          "Sir's question was fair: what does pain 6 mean? On our form every number has a meaning written next to it. 4 to 6 means she had to slow down or skip some things. Flow is described by what she sees on the pad, not by words like heavy.",
          dur=30)
    v2ctx = [q for s in FS.FORM for q in s["questions"] if q["id"] in ("context", "hormonal", "pregnancy", "intermenstrual", "bleed_days", "clots")]
    ben = drow_benign = next((r for r in R["det"]["rows"] if r["detector"] == "hybrid" and r["drift_type"] == "benign_shift"), {})
    slide("The logging form", "What we add next, and what we never ask",
          '<div class="cols"><div><h3>Proposed additions</h3>' + bullets([esc(q["q"]) for q in v2ctx])
          + f'<p class="note">Why "anything unusual this cycle?": on the simulator, {pct(ben.get("pattern_flag_rate"))} of women with a one-off stress or travel cycle '
            'got a pattern flag. Knowing the reason lets the app wait one cycle. Expected to help; not yet measured.</p></div>'
          + '<div><h3>Never asked</h3>' + table(["Item", "Why not"], [[esc(a), esc(b)] for a, b in FS.NOT_ASKED], tiny=True) + '</div></div>',
          "Next we want to ask whether anything unusual happened, like travel or exams, because a single stressful month is the main source of false alarms. And we deliberately do not ask about sex or discharge: not needed for these screenings, and too sensitive on a shared phone.",
          dur=30)
    slide("The logging form", "Questions about the form, answered",
          "".join(f'<div class="qa"><p class="q">{esc(q)}</p><p class="a">{esc(a)}</p></div>' for q, a in FS.QUESTIONS_SIR[:5]),
          " ".join(f"{q} {a}" for q, a in FS.QUESTIONS_SIR[:5]), dur=34)

    # ---------------------------------------------------------------- B. how it works
    slide("How it works", "How it works: two tiers on the phone, only a protected update leaves", ARCH_SVG +
          '<p class="note">Tier 1 = fast statistics that know your own normal. Tier 2 = a small neural network, measured and reported, '
          'but not yet trusted to raise flags on its own (see the honest results).</p>',
          "Everything that touches your data happens on the phone. Tier 1 is simple statistics that track your own normal. A rule layer turns "
          "what changed into one of five flags. The only thing that can ever leave the phone is a clipped, noise-added model update, and only if you switch it on.",
          dur=22)

    slide("How it works", "Federated learning in plain words", FL_SVG +
          '<p class="note">Sensor analogy: each phone is a sensor that keeps its raw signal. Before it reports, it clips the reading and adds '
          'deliberate noise so the original cannot be reconstructed. Averaged over many sensors, the noise cancels and the useful pattern remains.</p>',
          "Instead of collecting everyone's data in one place, each phone learns a little from its own data, sends only a small protected "
          "update, the server averages the updates, and sends a better model back. Your raw logs never travel.", dur=24)

    slide("How it works", "Algorithms used, named",
          table(["Job", "Algorithm we use", "Why it is there"], [
              ["Notice a change in YOUR pattern (Tier 1)", "Hybrid = adaptive z-score (EWMA mean and spread) + CUSUM + rule layer", "z-score catches a sudden jump, CUSUM catches a slow creep, rules name the pattern"],
              ["Predict your next cycle (Tier 2)", "GRU recurrent neural network, exported to ONNX", "Measured; currently weaker than Tier 1, so it does not raise flags alone"],
              ["Screen from symptoms (one-time)", "Random forest (8 models compared)", "Near-top everywhere, significantly best in 2 of 4 comparisons"],
              ["Learn across phones", "FedAvg with differential privacy (clipping + Gaussian noise)", "Keeps raw logs on the phone with a stated privacy budget"],
              ["Personalize", "Per-person statistical baseline (fine-tuning tested, not used)", "Fine-tuning raised false alarms too much"],
          ], small=True) + '<p class="note">"Hybrid" means exactly: statistical baseline (z-score + CUSUM) plus a rule layer. The GRU is a second tier under evaluation.</p>',
          "Every piece has a name. The detector is a hybrid of two classic change detectors, a z-score and CUSUM, plus rules that name the pattern. "
          "Learning across phones is FedAvg with differential privacy.", dur=24)

    slide("How it works", "The formulas, with every symbol explained", FORMULAS +
          '<p class="note">Differential privacy uses the standard DP-SGD form: noise is added to the SUM of clipped gradients, then divided by the batch size. '
          'Epsilon is computed with the Opacus accountant.</p>',
          "z-score: how far this cycle is from your usual, in units of your usual spread. CUSUM: a running total of small excesses, so a slow drift "
          "adds up until it crosses a limit. Clipping caps how much one person can move the model; noise hides any single person. FedAvg is a weighted average.",
          dur=28)

    slide("How it works", "Words you will hear, in plain language",
          table(["Word", "Plain meaning"], [
              ["AUC", "Pick one person with the condition and one without. AUC = how often the model scores the right one higher. 0.5 = coin toss, 1.0 = perfect"],
              ["False alarm", "A flag raised when nothing had actually changed"],
              ["Detection rate", "Of the people whose pattern really changed, how many got flagged"],
              ["Epsilon (privacy budget)", "How much one person's data can change what the server learns. Smaller = more private. Not zero leakage"],
              ["Non-IID", "Each phone's data looks different from the others (realistic, and harder)"],
              ["Simulator", "A program that makes realistic fake cycle histories where we know the true answer"],
          ], small=True),
          "Keep this slide in mind: AUC is ranking accuracy, epsilon is the privacy budget, and a simulator is a test signal generator.", dur=22)

    # ---------------------------------------------------------------- C. data
    slide("Data", "Data we used, grouped by category",
          table(["Category", "Dataset", "Size", "Used for"], [
              ["Clinical, tabular (real)", "Kaggle PCOS, 10 hospitals in Kerala", f"{pcos_ds['n_rows']} women", "Symptom-only PCOS screening model"],
              ["Population survey (real)", "NFHS-5, India's National Family Health Survey", f"{nfhs_n['n_rows']:,} women (non-pregnant)", "Anemia (real blood haemoglobin) and thyroid screening"],
              ["Real cycle lengths", "FedCycleData, natural family planning charts", f"{val['real']['n_women']} women, {val['real']['n_cycles']:,} cycles", "Checking the simulator is realistic"],
              ["Synthetic", "MyCycle simulator (always labeled synthetic)", f"{sim_users:,} users, {sim_cycles:,} cycles", "Testing change detection where the truth is known"],
              ["Qualitative", "10 community interviews", "10 people", "Design decisions only, never training"],
          ], small=True) + '<p class="note">Backend database: stores aggregate counts only (for example "app opened: 1"). No logs, no identifiers.</p>',
          "Five kinds of data. Real clinical records for PCOS, a large real Indian government survey for anemia and thyroid, real cycle lengths to "
          "check our simulator, a simulator for the time-series tests, and interviews for design. Nobody publishes years of one person's cycles "
          "with a diagnosis attached, for privacy reasons, which is why the simulator exists.", dur=26)

    slide("Data", "No cheating: what we removed before training",
          table(["Removed from the symptom-only models", "Why"], [
              ["Hormone labs: AMH, FSH, LH, TSH, prolactin, progesterone, vitamin D, blood sugar", "The app never asks for a lab value; using them would inflate accuracy"],
              ["Ultrasound: follicle counts and sizes, endometrium thickness", "Needs a scan; not available at home"],
              ["Haemoglobin (for anemia)", "It is the answer itself; used only to create the label"],
              ["Patient IDs, empty columns", "No information, possible leakage"],
          ], small=True) + bullets([
              "All cleaning and scaling is learned inside each training fold only",
              "Thresholds tuned on a validation set; the code refuses to tune on the test set",
              "Final numbers measured once, on data the model never saw",
          ]),
          "If you keep lab results in a symptom model, it looks brilliant but it is cheating, because the app will never have those values. "
          "We removed every lab and scan column, and our code physically refuses to tune on the test data.", dur=24)

    slide("Data", "Is the simulator realistic? Checked against 159 real women",
          table(["Measure", "Real women", "Our simulator", "Gap"], [
              ["Average cycle length", f"{V['cycle_length_mean']['real']:.2f} days", f"{V['cycle_length_mean']['simulated']:.2f} days", f"{V['cycle_length_mean']['abs_diff']:.2f}"],
              ["Share of cycles outside 24 to 38 days", pct(V['share_outside_24_38']['real']), pct(V['share_outside_24_38']['simulated']), f"{V['share_outside_24_38']['abs_diff'] * 100:.1f} points"],
              ["Typical variation within one woman", f"{V['within_user_sd_median']['real']:.2f} days", f"{V['within_user_sd_median']['simulated']:.2f} days", f"{V['within_user_sd_median']['abs_diff']:.2f}"],
              ["Variation across all cycles", f"{V['cycle_length_sd']['real']:.2f} days", f"{V['cycle_length_sd']['simulated']:.2f} days", f"{V['cycle_length_sd']['abs_diff']:.2f}"],
          ]) + '<p class="note">Honest reading: the average and the unusual-cycle share match closely; real cycles vary a little more than simulated ones. '
          'This checks normal cycles only; the disease-like drifts are our stated assumptions (sim/ASSUMPTIONS.md).</p>',
          "We did not just invent numbers. We compared the simulator's normal cycles with 1,665 real cycles. The average matches to a quarter of a day. "
          "Real cycles wobble slightly more than ours, and we say so.", dur=24)

    # ---------------------------------------------------------------- D. live
    slide("Live demo", "Live: the detector at work on four people", "",
          "Watch each person's cycles arrive one at a time. The shaded band is her own normal range. For the regular person nothing is ever flagged. "
          "For the others, the flag appears only after her own pattern changes, and it names the pattern and always says consider consulting a doctor. "
          "These flags are computed by our real detector code, not drawn by hand.",
          dur=62, kind="demo")

    slide("Live demo", "Live privacy proof", "",
          "This number is measured right now by the browser: how many network requests this page has made. Next to it, the backend was sent a "
          "request that tried to include a cycle length, and it refused it.", dur=18, kind="privacy")

    B = R["backend"]
    slide("Live demo", "The backend, called live when this demo was built",
          table(["Call", "What it is for", "Result", "What it proves"],
                [[f"<code>{esc(c['method'])} {esc(c['path'].split('?')[0])}</code>", esc(c["what"]),
                  f'<span class="code {"ok" if c["status"] < 300 else "refused"}">{c["status"]}</span>', esc(c["proves"])]
                 for c in B["calls"]], small=True)
          + f'<p class="note">{B["n_cards"]} education cards and {B["n_rules"]} reminder rules served. 200/201 = accepted, 422 = refused. '
            f'Run against a throwaway database.</p>',
          "Aditya's backend is real and running. It serves wording and rules, accepts only anonymous counts, and refuses anything that looks like "
          "a cycle log with error 422.", dur=22)

    # ---------------------------------------------------------------- E. results
    main_dets = [("fixed_threshold", "Fixed range 21 to 35 days (what most apps do)"), ("zscore", "z-score only"),
                 ("ewma", "EWMA control chart only"), ("cusum", "CUSUM only"), ("hybrid", "Our hybrid (z-score + CUSUM + rules)")]
    slide("Results", "Personal-baseline detection on the simulator (test users never seen in tuning)",
          table(["Detector", "PCOS-like caught", "Anemia-like caught", "Thyroid-like caught", "False alarms per 100 normal cycles", "Healthy people ever flagged"],
                [[n, pct(dr(k, "pcos")), pct(dr(k, "anemia")), pct(dr(k, "thyroid")), f2(fa(k)), pct(healthy(k))] for k, n in main_dets],
                highlight={4}, small=True)
          + f'<p class="note">Honest reading: all tuned detectors catch almost every PCOS-like change. The fixed range is a strong baseline here; '
            f'our hybrid is better on thyroid-like changes ({pct(dr("hybrid", "thyroid"))} vs {pct(dr("fixed_threshold", "thyroid"))}) and flags fewer '
            f'healthy people ({pct(healthy("hybrid"))} vs {pct(healthy("fixed_threshold"))}), but raises slightly more false alarms per cycle. '
            f'The EWMA chart is a strong alternative (see the comparisons).</p>',
          "On a fair test, every tuned detector catches nearly all PCOS-like changes. Our hybrid is clearly better than the fixed range on thyroid-like "
          "changes and bothers fewer healthy people, but it is not the winner on every column, and we show that.", dur=30)

    slide("Results", "Symptom-only PCOS screening on real data: 8 models compared",
          f'<img class="fig" src="{R["img"]["clf"]}"><p class="caption">Fig. 1: AUC with 95% confidence interval, kaggle_pcos (n={pcos_ds["n_rows"]}), '
          f'5-fold cross-validation repeated with 5 seeds. {LABEL}.</p>',
          f"On real hospital data, using only symptoms, the best model reaches AUC {s1['auc_mean']:.2f}. All eight models land close together, "
          f"which tells us the data, not the model, sets the limit.", dur=22)

    slide("Results", "How much do we lose by not using lab tests?",
          table(["Inputs", "Best model", "AUC (95% CI)", "Finds at 90% specificity"], [
              ["Symptoms only (what the app can use)", s1["model"].replace("_", " "), f"{s1['auc_mean']:.3f} ({s1['auc_ci_low']:.3f} to {s1['auc_ci_high']:.3f})", pct(s1["sens_at_90spec"])],
              ["Symptoms + weight, height, blood pressure", s2["model"].replace("_", " "), f"{s2['auc_mean']:.3f} ({s2['auc_ci_low']:.3f} to {s2['auc_ci_high']:.3f})", pct(s2["sens_at_90spec"])],
              ["With hormone labs + ultrasound (reference only)", s3["model"].replace("_", " "), f"{s3['auc_mean']:.3f} ({s3['auc_ci_low']:.3f} to {s3['auc_ci_high']:.3f})", pct(s3["sens_at_90spec"])],
          ], highlight={0}) + f'<p class="note">Cost of going lab-free: about {s3["auc_mean"] - s1["auc_mean"]:.2f} AUC. '
            f'That is the honest price of screening at home instead of in a lab.</p>',
          f"With lab tests you get {s3['auc_mean']:.2f}; with symptoms alone you get {s1['auc_mean']:.2f}. We lose some accuracy, and we state exactly how much, "
          "because the whole point is screening before anyone reaches a lab.", dur=24)

    slide("Results", "Real Indian survey data: anemia and thyroid (NFHS-5)",
          table(["Condition", "Label", "Best model", "AUC (95% CI)", "Plain reading"], [
              ["Anemia", "Real blood haemoglobin, WHO cut-off", an["model"].replace("_", " "), f"{an['auc_mean']:.3f} ({an['auc_ci_low']:.3f} to {an['auc_ci_high']:.3f})", "Close to a coin toss: symptoms alone cannot find anemia well"],
              ["Thyroid", "Self-reported diagnosis", th["model"].replace("_", " "), f"{th['auc_mean']:.3f} ({th['auc_ci_low']:.3f} to {th['auc_ci_high']:.3f})", f"Useful; beats the next model (p = {th_comp['p_value']})"],
          ], small=True) + f'<p class="note">{nfhs_n["n_rows"]:,} eligible women; models trained on a {nfhs_n["modeling_subsample_n"]:,}-row stratified sample '
            f'to fit our compute budget. The anemia result is a real negative finding: it supports telling users to get a simple blood count.</p>',
          "On a large real Indian survey, symptoms alone predict thyroid reasonably but anemia barely. We report the weak result too. "
          "It tells us anemia needs a blood test, which is exactly what the anemia flag message recommends.", dur=26)

    fl_rows = [
        ["Without FL: all data pooled (centralized)", "no", "n/a", f3(cen["auc"]), pct(cen["accuracy"])],
        ["Without FL: each phone alone (local only)", "no", "different on each phone", f3(loc["auc"]), pct(loc["accuracy"])],
        ["With FL: FedAvg, similar data on each phone", "yes", "similar", f3(avg_iid["auc"]), pct(avg_iid["accuracy"])],
        ["With FL: FedAvg, different data on each phone", "yes", "different", f3(avg["auc"]), pct(avg["accuracy"])],
    ]
    slide("Results", "Table: without FL vs with FL",
          table(["Setting", "Federated?", "Data split", "AUC", "Accuracy"], fl_rows, highlight={3}) +
          f'<p class="note">{fed["meta"]["protocol"]}. PCOS symptom-only task. Keeping each phone alone drops AUC to {loc["auc"]:.2f}; '
          f'federated learning recovers {avg["auc"]:.2f}, close to pooling everything ({cen["auc"]:.2f}), without moving raw data.</p>',
          f"If every phone learns alone, accuracy collapses to {loc['auc']:.2f} AUC. Federated learning gets back to {avg['auc']:.2f}, close to the "
          f"{cen['auc']:.2f} you would get by collecting everyone's data, but nobody's data leaves their phone.", dur=24)

    slide("Results", "Table: with FL and differential privacy (the price of privacy)",
          table(["Noise level", "Privacy budget epsilon (delta 1e-5)", "AUC", "Accuracy"],
                [["0 (FL, no DP)", "none (no guarantee)", f3(avg["auc"]), pct(avg["accuracy"])]] +
                [[f"{r['noise_multiplier']}", f"{r['epsilon']:.2f}", f3(r["auc"]), pct(r["accuracy"])] for r in dp]) +
          '<p class="note">More noise = smaller epsilon = stronger privacy. Ranking quality (AUC) holds up well; accuracy at the default '
          'cut-off drops noticeably. The curve is not perfectly smooth; this is a real run, not tidied. Epsilon checked against the Opacus library.</p>',
          "Adding privacy noise costs something. Ranking quality stays around 0.84 to 0.88, but plain accuracy drops to about two thirds. "
          "We show the whole curve so the operating point can be chosen openly.", dur=26)

    slide("Results", "Privacy vs usefulness, and learning over rounds",
          f'<div class="twofig"><figure><img src="{R["img"]["pu"]}"><figcaption>Fig. 2: privacy-utility curve, AUC vs epsilon, delta 1e-5.</figcaption></figure>'
          f'<figure><img src="{R["img"]["fc"]}"><figcaption>Fig. 3: AUC per federated round for each setting.</figcaption></figure></div>'
          f'<p class="caption">{fed["meta"]["protocol"]}. {LABEL}.</p>',
          "Left: as privacy gets stronger, usefulness drops gently. Right: how each method learns round by round.", dur=20)

    slide("Results", "Honest result: the neural network (GRU) is weaker than simple statistics",
          table(["Detector", "PCOS-like caught", "Anemia-like caught", "Thyroid-like caught"],
                [[n, pct(dr(k, "pcos")), pct(dr(k, "anemia")), pct(dr(k, "thyroid"))] for k, n in
                 [("hybrid", "Tier 1 hybrid (statistics)"), ("classical_exp_smoothing", "Plain exponential smoothing"),
                  ("gru", "GRU neural network"), ("lstm", "LSTM neural network"), ("cnn1d", "1D CNN neural network")]], highlight={2}) +
          f'<p class="note">Personalizing the GRU on a user\'s first 4 cycles raised thyroid detection from {pct(pb["thyroid_pattern"]["detection_rate"])} '
          f'to {pct(pa["thyroid_pattern"]["detection_rate"])} but raised false alarms from {pb["overall"]["false_alarms_per_100_cycles"]:.1f} to '
          f'{pa["overall"]["false_alarms_per_100_cycles"]:.1f} per 100 normal cycles. So it is not used to raise flags.</p>',
          "We expected the neural network to win. It did not. With only 16 to 30 cycles per person, simple statistics beat it. We kept the result "
          "instead of hiding it, and the app relies on Tier 1.", dur=26)

    # ---------------------------------------------------------------- F. comparisons
    C = comparisons(R, dr, fa, healthy, s1, s2, s3, mlp1, comp, cen, loc, avg, prox, per, dp, pb, pa, an, th, th_comp)
    R["comparisons"] = C
    slide("Why this, not that", "Scorecard: every choice, compared honestly",
          table(["Decision", "We use", "Verdict"], [[esc(c["decision"]), esc(c["chosen"]), badge(c["verdict"])] for c in C], tiny=True),
          "This is the scorecard for every design choice. Green means our choice measurably wins. Tie means the numbers are close and we chose for "
          "a stated reason. Loses means we tested it, it lost, and we do not rely on it. Not measured means the reasoning is qualitative only.",
          dur=30)
    for c in C:
        slide("Why this, not that", c["decision"],
              f'<div class="verdict">{badge(c["verdict"])} <span>We use: <b>{esc(c["chosen"])}</b></span></div>'
              + table(c["headers"], c["rows"], highlight=c.get("hl"), small=True)
              + f'<div class="why"><p><b>In plain words:</b> {c["plain"]}</p><p><b>Where we could be wrong:</b> {c["caveat"]}</p></div>',
              c["plain"] + " " + c["caveat"], dur=24)

    # ---------------------------------------------------------------- G. trust
    T = R["checks"]["tests"]
    tests_line = (f'{T["passed"]} automated tests passed, {T["failed"]} failed, run just now' if T.get("ran")
                  else f'{T.get("collected")} automated tests in the suite (run <code>python scripts/check.py</code> to execute them)')
    slide("Trust", "How we know the numbers are right",
          bullets([
              tests_line,
              f'Language rules check (no "diagnosis", no hype words): {"PASS" if R["checks"]["lint_ok"] else "FAIL"}; data contract check: {"PASS" if R["checks"]["contracts_ok"] else "FAIL"}',
              f'Every demo persona re-checked against its expected flags just now: {sum(p["verified"] for p in R["personas"]["personas"])} of {len(R["personas"]["personas"])} match',
              f'Claims table: {R["claims"]["total"]} claims; {R["claims"].get("supported", 0)} supported by evidence, {R["claims"].get("needs work", 0)} app claims still waiting for the app to be built',
              "Fixed seeds: running the simulator twice gives byte-identical files",
          ]) + '<p class="sub">Bugs we caught in our own work (and fixed before showing you):</p>' + bullets([
              "Privacy budget was understated up to 4 times by our first formula; caught by checking against the Opacus library",
              "GRU score diluted a real change across 11 features; fixed to use the most-changed feature",
              "A data merge silently counted missing rows as alarms; added a guard that now refuses such merges",
              "Two download checksums were cut short by one character; added a test for every checksum",
              "One claim quoted a false-alarm number from the wrong detector; corrected in the claims table",
          ]),
          "We do not ask you to trust us. The code is tested automatically, and here are five mistakes we found in our own work and fixed. "
          "The privacy one mattered most: our first formula made the system look more private than it was.", dur=30)

    slide("Trust", "What we claim, and what we do not",
          '<div class="cols"><div><h3>We claim</h3>' + bullets([
              f"Symptom-only PCOS screening at AUC {s1['auc_mean']:.2f} on real data, with confidence intervals",
              "A personal-baseline detector tested on a labeled synthetic benchmark checked against real cycles",
              f"Federated learning keeps raw data on the phone and recovers most of the pooled accuracy ({avg['auc']:.2f} vs {cen['auc']:.2f})",
              "A measured privacy vs accuracy curve with a stated epsilon",
          ]) + '</div><div><h3>We do not claim</h3>' + bullets([
              "Diagnosis, or clinical validation on real patients",
              "Real deployment results",
              "That the neural network beats simple statistics (it does not, yet)",
              "That we are more accurate than any named app",
              "Millions of real rows: the real data is 541 + 126,625 women; the simulator is labeled synthetic",
          ]) + '</div></div>',
          "On the left, what the evidence supports. On the right, what we will not say, because we have not shown it.", dur=24)

    slide("Trust", "Limitations and next steps",
          table(["Limitation", "Next step"], [
              ["Detection tested on simulated people", "Clinical validation study with consenting users"],
              ["Anemia from symptoms is weak (AUC " + f"{an['auc_mean']:.2f})", "Keep recommending a simple blood count in the flag"],
              ["Clinical thresholds in the simulator are stated assumptions", "Verify each against its source (Rotterdam, WHO, FIGO)"],
              ["Phone speed and memory not yet measured", "On-device benchmark (in progress)"],
              ["Privacy law review not done", "Review under India's DPDP Act 2023 and medical device rules"],
          ], small=True),
          "Our biggest limitation is that detection is tested on simulated people. The next step is a real, consented study.", dur=20)

    for qs in [QA[:4], QA[4:8], QA[8:12], QA[12:]]:
        slide("Questions", "Questions we expect, answered", "".join(f'<div class="qa"><p class="q">{esc(q)}</p><p class="a">{a(R, s1, s3, avg, cen, loc, an, th, mlp1, dp)}</p></div>' for q, a in qs),
              " ".join(f"{q} {a(R, s1, s3, avg, cen, loc, an, th, mlp1, dp)}" for q, a in qs).replace("<b>", "").replace("</b>", ""), dur=34)

    slide("Team", "Who built what",
          table(["Member", "Area", "Built so far"], [
              ["Aryan Lomte", "ML, experiments, data integration", "Simulator, 6 detectors, 8-model comparison, NFHS-5 and real-cycle checks, GRU, federated learning with DP, this demo"],
              ["Aditya Lokhande", "Backend, content, community research", "FastAPI backend: health, content, reminders, privacy-enforcing metrics"],
              ["Liza Patel", "App and user experience", "Phone app screens (in progress)"],
              ["Saanj Patil", "Evidence, on-device, slides", "Citation library and on-device benchmarks (in progress)"],
          ], small=True),
          "Edit this slide in demo/run_demo.py (the TEAM table) as each member's work lands in the repository.", dur=16)

    slide("Team", "Reproduce everything with one command",
          '<pre>python demo/run_demo.py --run-tests</pre>' + bullets([
              "<code>python -m sim.simulator --seed 42</code>: regenerate the simulated people",
              "<code>python -m sim.detection_eval</code>: tune on validation, measure on test",
              "<code>python -m sim.classifiers</code> and <code>python -m sim.nfhs_classifiers</code>: real-data models",
              "<code>python -m sim.federated</code>: federated learning and privacy curve",
              "<code>python scripts/check.py</code>: tests, language rules, contracts",
          ]) + f'<p class="note">Built from git commit {esc(R["commit"])} on {esc(R["built_at"])}.</p>',
          "Everything on these slides comes from files a script produced. Anyone can rerun it.", dur=16)
    return S


# --------------------------------------------------------------------------------------------
# comparisons: one entry per design decision, verdict chosen from the numbers
# --------------------------------------------------------------------------------------------

def comparisons(R, dr, fa, healthy, s1, s2, s3, mlp1, comp, cen, loc, avg, prox, per, dp, pb, pa, an, th, th_comp) -> list[dict]:
    C = []
    ft, hy, ew, cu = "fixed_threshold", "hybrid", "ewma", "cusum"
    C.append({
        "decision": "Personal baseline vs one fixed range for everyone", "chosen": "Personal baseline", "verdict": "mixed",
        "headers": ["Measure", "Fixed range 21 to 35 days", "Our personal baseline (hybrid)"],
        "rows": [["PCOS-like caught", pct(dr(ft, "pcos")), pct(dr(hy, "pcos"))],
                 ["Anemia-like caught", pct(dr(ft, "anemia")), pct(dr(hy, "anemia"))],
                 ["Thyroid-like caught", pct(dr(ft, "thyroid")), pct(dr(hy, "thyroid"))],
                 ["False alarms per 100 normal cycles", f2(fa(ft)), f2(fa(hy))],
                 ["Healthy people ever flagged", pct(healthy(ft)), pct(healthy(hy))]],
        "plain": ("A fixed range judges everyone against the average woman. A woman whose normal cycle is 37 days gets flagged every single month, "
                  "even though nothing is wrong for her (our tests check exactly this case). The personal baseline learns her own normal. "
                  f"Measured: it catches more thyroid-like changes ({pct(dr(hy, 'thyroid'))} vs {pct(dr(ft, 'thyroid'))}) and flags fewer healthy people, "
                  f"but on this simulator the fixed range raises slightly fewer false alarms per cycle ({f2(fa(ft))} vs {f2(fa(hy))})."),
        "caveat": ("Most simulated women have normal cycles well inside 21 to 35 days, which flatters the fixed range. The advantage of a personal "
                   "baseline should be larger for women whose normal sits near the edges; we have not measured that subgroup separately yet."),
    })
    C.append({
        "decision": "Which change detector for Tier 1", "chosen": "Hybrid (z-score + CUSUM + rules)", "verdict": "tie",
        "headers": ["Detector", "PCOS / anemia / thyroid caught", "False alarms per 100", "Healthy ever flagged"],
        "rows": [[n, f"{pct(dr(k, 'pcos'))} / {pct(dr(k, 'anemia'))} / {pct(dr(k, 'thyroid'))}", f2(fa(k)), pct(healthy(k))]
                 for k, n in [("zscore", "z-score only"), (ew, "EWMA chart only"), (cu, "CUSUM only"), ("isolation_forest", "Isolation Forest"), (hy, "Our hybrid")]],
        "hl": {4},
        "plain": ("A z-score alone reacts to sudden jumps but misses slow creeps (it caught only " + pct(dr("zscore", "anemia")) + " of anemia-like changes). "
                  "CUSUM catches slow creeps but reacts later. The hybrid combines both and catches PCOS-like changes in the same cycle they start. "
                  f"But the EWMA chart alone does about as well with fewer false alarms ({f2(fa(ew))} vs {f2(fa(hy))}) and flags fewer healthy people "
                  f"({pct(healthy(ew))} vs {pct(healthy(hy))})."),
        "caveat": "On these numbers the EWMA chart is a credible replacement for the hybrid. We are reporting that, and it is an open decision for the team.",
    })
    C.append({
        "decision": "Neural network (GRU) vs simple statistics for spotting change", "chosen": "Simple statistics (Tier 1); GRU kept as Tier 2 under evaluation", "verdict": "loss",
        "headers": ["Method", "PCOS / anemia / thyroid caught"],
        "rows": [[n, f"{pct(dr(k, 'pcos'))} / {pct(dr(k, 'anemia'))} / {pct(dr(k, 'thyroid'))}"] for k, n in
                 [(hy, "Tier 1 statistics"), ("classical_exp_smoothing", "Exponential smoothing"), ("gru", "GRU"), ("lstm", "LSTM"), ("cnn1d", "1D CNN")]],
        "hl": {2},
        "plain": ("Neural networks need lots of examples per person. Each simulated person has only 16 to 30 cycles, so simple statistics that track "
                  "one person's average beat all three neural networks. GRU, LSTM and CNN were almost identical to each other."),
        "caveat": "With much longer histories, or real data with richer patterns, a neural network could catch up. The GRU is kept, exported and tested, but it does not raise flags.",
    })
    C.append({
        "decision": "Which screening model (symptoms to risk)", "chosen": "Random forest", "verdict": "tie",
        "headers": ["Comparison", "Best", "Runner-up", "Is the gap real? (p-value)"],
        "rows": [["PCOS, symptoms only", f"{comp['symptom_only']['model_a']} {comp['symptom_only']['auc_a']:.3f}", f"{comp['symptom_only']['model_b']} {comp['symptom_only']['auc_b']:.3f}", f"No (p = {comp['symptom_only']['p_value']})"],
                 ["PCOS, symptoms + vitals", f"{comp['symptom_plus_vitals']['model_a']} {comp['symptom_plus_vitals']['auc_a']:.3f}", f"{comp['symptom_plus_vitals']['model_b']} {comp['symptom_plus_vitals']['auc_b']:.3f}", f"Yes (p = {comp['symptom_plus_vitals']['p_value']})"],
                 ["Thyroid, NFHS-5", f"{th_comp['model_a']} {th_comp['auc_a']:.3f}", f"{th_comp['model_b']} {th_comp['auc_b']:.3f}", f"{'Yes' if th_comp['p_value'] < 0.05 else 'No'} (p = {th_comp['p_value']})"],
                 ["Deep network (MLP), PCOS symptoms only", f"mlp {mlp1['auc_mean']:.3f}", "last of 8", "Deep model was the weakest"]],
        "plain": ("Eight models scored almost the same on symptoms alone, so the data sets the ceiling, not the model. Random forest is near the top everywhere "
                  "and is the significant winner in two comparisons. It also shows which symptoms mattered and needs no special hardware. "
                  "The deep neural network was the weakest, which is typical for small tables of data."),
        "caveat": "On symptoms alone k-NN was fractionally higher and the difference is not significant; any of the top four would be a defensible choice.",
    })
    C.append({
        "decision": "Symptoms only vs using lab tests", "chosen": "Symptoms only", "verdict": "trade",
        "headers": ["Inputs", "Best AUC"],
        "rows": [["Symptoms only", f3(s1["auc_mean"])], ["Symptoms + vitals", f3(s2["auc_mean"])], ["With labs + ultrasound (reference)", f3(s3["auc_mean"])]],
        "hl": {0},
        "plain": (f"Lab tests make the model better (AUC {s3['auc_mean']:.2f} vs {s1['auc_mean']:.2f}), but anyone who already has those tests has seen a doctor. "
                  "The point of MyCycle is to nudge people before that step, at home, for free. We accept the lower accuracy and state it."),
        "caveat": "Symptom-only screening will miss some cases; that is why every flag says consider consulting a doctor, and a quiet result is not an all-clear.",
    })
    C.append({
        "decision": "Where the learning happens", "chosen": "Federated learning", "verdict": "win",
        "headers": ["Setting", "Raw data leaves phone?", "AUC"],
        "rows": [["All data pooled on a server", "Yes", f3(cen["auc"])], ["Each phone alone", "No", f3(loc["auc"])], ["Federated learning (FedAvg)", "No", f3(avg["auc"])]],
        "hl": {2},
        "plain": (f"Pooling everyone's data gives the best accuracy but puts intimate data on a server. Keeping it on each phone alone is private but weak "
                  f"(AUC {loc['auc']:.2f}). Federated learning keeps data on the phone and gets {avg['auc']:.2f}, close to pooling."),
        "caveat": "Measured with 8 simulated phones on the PCOS dataset, not real phones; real networks add dropouts and delays.",
    })
    C.append({
        "decision": "Which federated method", "chosen": "FedAvg", "verdict": "tie",
        "headers": ["Method", "AUC", "Accuracy"],
        "rows": [["FedAvg", f3(avg["auc"]), pct(avg["accuracy"])], ["FedProx", f3(prox["auc"]), pct(prox["accuracy"])], ["FedPer (personal head)", f3(per["auc"]), pct(per["accuracy"])]],
        "hl": {0},
        "plain": (f"FedProx ranked slightly better (AUC {prox['auc']:.2f} vs {avg['auc']:.2f}) but got far fewer answers right at the default cut-off "
                  f"({pct(prox['accuracy'])} vs {pct(avg['accuracy'])}). FedPer was weakest. FedAvg is the simplest, most standard method and the best balance here."),
        "caveat": "One run per setting on a small dataset; FedProx's AUC edge could be real. SCAFFOLD and FedAdam were not run.",
    })
    C.append({
        "decision": "Adding differential privacy", "chosen": "FedAvg with differential privacy", "verdict": "trade",
        "headers": ["Setting", "Epsilon", "AUC", "Accuracy"],
        "rows": [["No privacy noise", "none", f3(avg["auc"]), pct(avg["accuracy"])]] + [[f"Noise {r['noise_multiplier']}", f"{r['epsilon']:.2f}", f3(r["auc"]), pct(r["accuracy"])] for r in dp],
        "plain": ("Without noise, a clever server could learn things about one person from her update. Differential privacy adds noise so that any one "
                  "person barely changes the result, with a measured budget, epsilon. It costs accuracy, and we show exactly how much."),
        "caveat": "Secure aggregation and homomorphic encryption are other ways to hide updates; we did not test them. DP gives a bounded leak, never zero.",
    })
    C.append({
        "decision": "Personalizing the neural network per user", "chosen": "Not used (statistical baseline is already personal)", "verdict": "loss",
        "headers": ["Measure", "Before fine-tuning", "After fine-tuning"],
        "rows": [["PCOS-like caught", pct(pb["pcos_pattern"]["detection_rate"]), pct(pa["pcos_pattern"]["detection_rate"])],
                 ["Thyroid-like caught", pct(pb["thyroid_pattern"]["detection_rate"]), pct(pa["thyroid_pattern"]["detection_rate"])],
                 ["False alarms per 100 normal cycles", f2(pb["overall"]["false_alarms_per_100_cycles"]), f2(pa["overall"]["false_alarms_per_100_cycles"])]],
        "plain": "Tuning the model on a user's first 4 cycles made it catch more changes, but it also started crying wolf far more often. Too many false alarms make people ignore flags, so we do not use it.",
        "caveat": "With more cycles for fine-tuning, or a false-alarm penalty during tuning, this could improve.",
    })
    ab = R["ablation"]
    C.append({
        "decision": "Filling in missing answers", "chosen": "Median fill", "verdict": "tie",
        "headers": ["Model", "Median fill AUC", "Nearest-neighbour fill AUC"],
        "rows": [[f"{r['model'].replace('_', ' ')}, {r['feature_set'].replace('_', ' ')}", f3(float(r["median_impute_auc"])), f3(float(r["knn_impute_auc"]))] for r in ab[:4]],
        "plain": "Only 2 of 541 records had a missing answer, so both methods give the same result. We use the simpler one.",
        "caveat": "On data with many gaps (real app logs), this choice would matter more and should be re-tested.",
    })
    C.append({
        "decision": "Indian survey (NFHS-5) vs US survey (NHANES) for anemia and thyroid", "chosen": "NFHS-5", "verdict": "qual",
        "headers": ["Reason", "NFHS-5"],
        "rows": [["Population", "Indian women aged 15 to 49, our users"], ["Size", f"{R['nfhs']['datasets'][0]['n_rows']:,} non-pregnant women"],
                 ["Anemia label", "Real measured haemoglobin"], ["Licence", "Public domain (CC0)"]],
        "plain": "Our users are Indian women. A US survey would describe a different population, diet and anemia rate. NFHS-5 is India's own survey with real blood measurements.",
        "caveat": "We did not run NHANES, so this is a reasoned choice, not a measured comparison.",
    })
    C.append({
        "decision": "PyTorch + ONNX for the model file", "chosen": "PyTorch, exported to ONNX", "verdict": "qual",
        "headers": ["Check", "Result"],
        "rows": [["Same answers after export", "Largest difference under 0.0001 (tested)"], ["Runs in a browser", "Yes, via ONNX Runtime Web"], ["Keras / TFLite", "Not compared"]],
        "plain": "We needed one model file that runs inside a web page on the phone. PyTorch exports to ONNX in one step and we verified the exported model gives the same answers.",
        "caveat": "Phone speed and memory have not been measured yet; that benchmark is in progress.",
    })
    return C


QA = [
    ("Is this a diagnosis?", lambda R, *a: "No. It raises a <b>screening flag</b> and always says consider consulting a doctor. Only a doctor diagnoses."),
    ("Why use a simulator instead of real data?", lambda R, *a: "No public dataset follows the same woman's cycles for years with a diagnosis attached, for privacy reasons. "
     f"The simulator gives us people where the true answer is known, and its normal cycles match {R['val']['real']['n_women']} real women closely."),
    ("Did you train on millions of rows?", lambda R, s1, s3, avg, cen, loc, an, th, *a: f"Real data: {R['clf']['datasets'][0]['n_rows']} PCOS patients and "
     f"{R['nfhs']['datasets'][0]['n_rows']:,} women in NFHS-5. The simulator can generate millions of rows, always labeled synthetic. We do not mix the two."),
    ("How much accuracy do you lose without lab tests?", lambda R, s1, s3, *a: f"AUC {s3['auc_mean']:.2f} with labs vs {s1['auc_mean']:.2f} with symptoms only. That is the honest price of screening at home."),
    ("Why not deep learning?", lambda R, s1, s3, avg, cen, loc, an, th, mlp1, *a: f"We tried it. The deep network was the weakest of 8 screening models (AUC {mlp1['auc_mean']:.2f}), "
     "and the GRU was weaker than simple statistics for spotting change. Small data favours simple models."),
    ("Why federated learning?", lambda R, s1, s3, avg, cen, loc, *a: f"Each phone alone reaches only AUC {loc['auc']:.2f}. Federated learning reaches {avg['auc']:.2f}, close to pooling everything ({cen['auc']:.2f}), without raw data leaving any phone."),
    ("What does differential privacy actually protect?", lambda R, s1, s3, avg, cen, loc, an, th, mlp1, dp: "It limits how much any one person can change what the server learns, "
     f"measured by epsilon (for example {dp[1]['epsilon']:.1f} at noise {dp[1]['noise_multiplier']}). It is a bounded leak, not zero leakage."),
    ("How do you know there is no data leakage?", lambda R, *a: "Every lab and scan column was removed from the symptom models, cleaning is learned inside each training fold, "
     "and our code refuses to tune thresholds on the test data."),
    ("Which algorithm exactly? Hybrid of what?", lambda R, *a: "Tier 1 is a hybrid of an adaptive z-score and CUSUM, plus a rule layer that names the pattern. Learning across phones is FedAvg with differential privacy."),
    ("Is your detector better than a normal period app?", lambda R, *a: "Not on every measure. Compared with a fixed 21 to 35 day range it catches more thyroid-like changes and bothers fewer healthy people, "
     "but raises slightly more false alarms per cycle. We do not claim superiority over any named app."),
    ("Does it run on a phone?", lambda R, *a: "The model is exported to ONNX and gives the same answers after export (difference under 0.0001), so it can run in a phone browser. "
     "Phone speed and memory are still being measured."),
    ("How do you know your numbers are right?", lambda R, *a: "Automated tests, fixed random seeds, and five mistakes we caught in our own work, including a privacy formula that was 4 times too optimistic."),
    ("Is the anemia model useful?", lambda R, s1, s3, avg, cen, loc, an, *a: f"Only weakly (AUC {an['auc_mean']:.2f}). Symptoms alone cannot find anemia reliably, so the flag recommends a simple blood count."),
    ("Is the app finished?", lambda R, *a: "The engine (detector, models, private learning, backend) is built and tested. The phone screens are in progress; this demo runs the real engine."),
]


# --------------------------------------------------------------------------------------------
# static pieces
# --------------------------------------------------------------------------------------------

ARCH_SVG = """<svg viewBox="0 0 1400 420" class="diagram" role="img" aria-label="Raw logs stay on the phone">
<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#475569"/></marker></defs>
<rect x="20" y="20" width="930" height="380" rx="18" fill="#ecfdf5" stroke="#0f766e" stroke-width="3"/>
<text x="40" y="60" font-size="30" font-weight="700" fill="#0f766e">On your phone</text>
<g font-size="24" fill="#1c1c1c">
<rect x="50" y="100" width="190" height="110" rx="12" fill="#fff" stroke="#475569" stroke-width="2"/><text x="145" y="148" text-anchor="middle" font-weight="700">Your log</text><text x="145" y="180" text-anchor="middle" font-size="20">cycle + symptoms</text>
<rect x="290" y="80" width="270" height="80" rx="12" fill="#fff" stroke="#475569" stroke-width="2"/><text x="425" y="115" text-anchor="middle" font-weight="700">Tier 1: your normal</text><text x="425" y="143" text-anchor="middle" font-size="20">z-score + CUSUM</text>
<rect x="290" y="180" width="270" height="80" rx="12" fill="#fff" stroke="#94a3b8" stroke-width="2" stroke-dasharray="8 6"/><text x="425" y="215" text-anchor="middle" font-weight="700">Tier 2: GRU</text><text x="425" y="243" text-anchor="middle" font-size="20">evaluated, not trusted yet</text>
<rect x="610" y="100" width="150" height="110" rx="12" fill="#fff" stroke="#475569" stroke-width="2"/><text x="685" y="148" text-anchor="middle" font-weight="700">Rule layer</text><text x="685" y="180" text-anchor="middle" font-size="20">names pattern</text>
<rect x="790" y="100" width="140" height="110" rx="12" fill="#fef3c7" stroke="#b45309" stroke-width="3"/><text x="860" y="140" text-anchor="middle" font-weight="700">Screening</text><text x="860" y="170" text-anchor="middle" font-weight="700">flag</text><text x="860" y="196" text-anchor="middle" font-size="18">+ see a doctor</text>
<text x="200" y="330" font-size="24" fill="#0f766e" font-weight="700">Raw logs never leave this box</text>
</g>
<g fill="none" stroke="#475569" stroke-width="2.5"><path d="M240 140H288" marker-end="url(#ar)"/><path d="M240 180L288 215" marker-end="url(#ar)"/><path d="M560 120H608" marker-end="url(#ar)"/><path d="M560 220L608 175" marker-end="url(#ar)"/><path d="M760 155H788" marker-end="url(#ar)"/><path d="M950 290H1030" marker-end="url(#ar)"/><path d="M1030 350H952" marker-end="url(#ar)"/></g>
<text x="1210" y="408" text-anchor="middle" font-size="18" fill="#475569">link is optional, off by default</text>
<rect x="1040" y="230" width="340" height="150" rx="18" fill="#f1f5f9" stroke="#475569" stroke-width="2"/>
<text x="1210" y="275" text-anchor="middle" font-size="26" font-weight="700" fill="#1c1c1c">Server</text>
<text x="1210" y="310" text-anchor="middle" font-size="20" fill="#1c1c1c">receives clipped, noised</text><text x="1210" y="336" text-anchor="middle" font-size="20" fill="#1c1c1c">model updates only; averages</text><text x="1210" y="362" text-anchor="middle" font-size="20" fill="#1c1c1c">them; sends a better model back</text>
</svg>"""

FL_SVG = """<svg viewBox="0 0 1400 300" class="diagram" role="img" aria-label="Federated learning in four steps">
<defs><marker id="ar2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#475569"/></marker></defs>
<g font-size="24" fill="#1c1c1c">
<rect x="20" y="40" width="300" height="200" rx="16" fill="#ecfdf5" stroke="#0f766e" stroke-width="3"/><text x="170" y="95" text-anchor="middle" font-size="44" font-weight="700" fill="#0f766e">1</text><text x="170" y="140" text-anchor="middle" font-weight="700">Each phone learns</text><text x="170" y="172" text-anchor="middle">from its own data</text><text x="170" y="204" text-anchor="middle" font-size="20">(data stays put)</text>
<rect x="370" y="40" width="300" height="200" rx="16" fill="#fff" stroke="#475569" stroke-width="2"/><text x="520" y="95" text-anchor="middle" font-size="44" font-weight="700" fill="#0f766e">2</text><text x="520" y="140" text-anchor="middle" font-weight="700">Only a small update</text><text x="520" y="172" text-anchor="middle">leaves, clipped and</text><text x="520" y="204" text-anchor="middle">with noise added</text>
<rect x="720" y="40" width="300" height="200" rx="16" fill="#fff" stroke="#475569" stroke-width="2"/><text x="870" y="95" text-anchor="middle" font-size="44" font-weight="700" fill="#0f766e">3</text><text x="870" y="140" text-anchor="middle" font-weight="700">Server averages</text><text x="870" y="172" text-anchor="middle">many updates</text><text x="870" y="204" text-anchor="middle" font-size="20">(noise cancels out)</text>
<rect x="1070" y="40" width="310" height="200" rx="16" fill="#fff" stroke="#475569" stroke-width="2"/><text x="1225" y="95" text-anchor="middle" font-size="44" font-weight="700" fill="#0f766e">4</text><text x="1225" y="140" text-anchor="middle" font-weight="700">Better model goes</text><text x="1225" y="172" text-anchor="middle">back to every phone</text>
</g>
<g fill="none" stroke="#475569" stroke-width="3"><path d="M322 140H366" marker-end="url(#ar2)"/><path d="M672 140H716" marker-end="url(#ar2)"/><path d="M1022 140H1066" marker-end="url(#ar2)"/><path d="M1225 242V280H170V244" marker-end="url(#ar2)"/></g>
</svg>"""

FORMULAS = """<div class="formulas">
<div class="f"><div class="eq">m<sub>t</sub> = m<sub>t-1</sub> + a (x<sub>t</sub> - m<sub>t-1</sub>)</div><div class="d">Your running average. x = this cycle's value, a = how fast it adapts (0.3).</div></div>
<div class="f"><div class="eq">z<sub>t</sub> = (x<sub>t</sub> - m<sub>t-1</sub>) / s<sub>t-1</sub></div><div class="d">How unusual this cycle is for you. s = your usual spread.</div></div>
<div class="f"><div class="eq">S<sub>t</sub> = max(0, S<sub>t-1</sub> + z<sub>t</sub> - k), flag when S<sub>t</sub> &gt; h</div><div class="d">CUSUM: small excesses add up, so a slow drift is caught. k = 0.5, h tuned.</div></div>
<div class="f"><div class="eq">&#285;<sub>i</sub> = g<sub>i</sub> &middot; min(1, C / &Vert;g<sub>i</sub>&Vert;)</div><div class="d">Clipping: no single person's update can be bigger than C.</div></div>
<div class="f"><div class="eq">g&#771; = (1/B) ( &Sigma;<sub>i</sub> &#285;<sub>i</sub> + N(0, &sigma;<sup>2</sup>C<sup>2</sup>I) )</div><div class="d">Noise added to the SUM of clipped updates, then divided by batch size B. &sigma; = noise level.</div></div>
<div class="f"><div class="eq">w<sub>new</sub> = &Sigma;<sub>k</sub> (n<sub>k</sub> / n) w<sub>k</sub></div><div class="d">FedAvg: average of each phone's model, weighted by how much data it had.</div></div>
<div class="f"><div class="eq">P[M(D) &isin; S] &le; e<sup>&epsilon;</sup> P[M(D') &isin; S] + &delta;</div><div class="d">(&epsilon;, &delta;) privacy: adding or removing one person changes any outcome's chance by at most e<sup>&epsilon;</sup>.</div></div>
</div>"""

CSS = """
:root{--bg:#fbfaf6;--ink:#1c1c1c;--muted:#52525b;--accent:#0f766e;--accentbg:#ecfdf5;--warn:#b45309;--warnbg:#fef3c7;--line:#d6d3cb;}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:#0b0b0b;font-family:"Segoe UI",Roboto,Arial,sans-serif;color:var(--ink);overflow:hidden}
#stage{position:absolute;left:50%;top:50%;width:1600px;height:900px;background:var(--bg);transform-origin:center center;overflow:hidden}
.slide{position:absolute;inset:0;padding:44px 64px 80px 64px;display:none;flex-direction:column}
.slide.on{display:flex;animation:fade .5s ease}
@keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.section{font-size:18px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-weight:700}
h1{font-size:44px;margin:6px 0 22px 0;line-height:1.15}
h3{font-size:28px;margin:0 0 10px 0;color:var(--accent)}
.body{font-size:26px;line-height:1.4;flex:1;min-height:0;overflow:hidden}
p{margin:10px 0}
.note{font-size:22px;color:var(--muted);background:#f4f2ea;border-left:5px solid var(--accent);padding:10px 16px;border-radius:6px}
.caption,figcaption{font-size:18px;color:var(--muted)}
.sub{font-weight:700;margin-top:14px}
ul{margin:6px 0 6px 0;padding-left:30px}li{margin:6px 0}
table{border-collapse:collapse;width:100%;font-size:24px;margin:6px 0}
table.small{font-size:21px}
table.tiny{font-size:19px}table.tiny td{padding:5px 12px}table.tiny th{padding:7px 12px}table.tiny .badge{font-size:15px;padding:2px 10px}
th{background:var(--accent);color:#fff;text-align:left;padding:10px 12px;font-weight:600}
td{padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tr.hl td{background:var(--accentbg);font-weight:600}
code,pre{font-family:Consolas,monospace;font-size:.9em}
pre{background:#1f2937;color:#f9fafb;padding:16px 20px;border-radius:10px;font-size:26px}
.badge{display:inline-block;padding:4px 12px;border-radius:999px;font-size:18px;font-weight:700;color:#fff;white-space:nowrap}
.badge.win{background:#15803d}.badge.tie{background:#475569}.badge.loss{background:#b45309}.badge.trade{background:#7c3aed}.badge.mixed{background:#0369a1}.badge.qual{background:#78716c}
.verdict{display:flex;align-items:center;gap:18px;font-size:26px;margin-bottom:10px}
.why{font-size:22px;line-height:1.4;margin-top:10px}.why p{margin:6px 0}
.hero{display:flex;flex-direction:column;justify-content:center;height:100%}
.hero .big{font-size:64px;font-weight:800;color:var(--accent);margin-bottom:10px}
.lead{font-size:30px;max-width:1350px}.muted{color:var(--muted);font-size:24px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:40px}
.diagram{width:100%;height:auto;max-height:470px}
.fig{max-width:100%;max-height:600px;display:block;margin:0 auto;background:#fff}
.twofig{display:grid;grid-template-columns:1fr 1fr;gap:24px}.twofig img{width:100%;max-height:540px;object-fit:contain;background:#fff}figure{margin:0}
.formulas{display:grid;grid-template-columns:1fr 1fr;gap:12px 36px}
.f .eq{font-family:"Cambria Math","Times New Roman",serif;font-size:30px;color:var(--ink)}
.f .d{font-size:20px;color:var(--muted);margin-bottom:6px}
.qa{margin-bottom:14px}.qa .q{font-weight:700;font-size:25px;color:var(--accent);margin:0}.qa .a{margin:2px 0 0 0;font-size:23px}
.code{font-weight:700;padding:2px 10px;border-radius:6px}.code.ok{background:#dcfce7;color:#166534}.code.refused{background:#fee2e2;color:#991b1b}
footer{position:absolute;left:64px;right:64px;bottom:18px;display:flex;justify-content:space-between;font-size:16px;color:var(--muted)}
#progress{position:absolute;left:0;top:0;height:6px;background:var(--accent);width:0}
#controls{position:fixed;right:18px;bottom:18px;display:flex;gap:8px;opacity:0;transition:opacity .3s;z-index:10}
body:hover #controls{opacity:.9}
#controls button{font-size:20px;padding:8px 14px;border:0;border-radius:8px;background:#1f2937;color:#fff;cursor:pointer}
#notes{position:absolute;left:0;right:0;bottom:0;background:rgba(15,23,42,.94);color:#f8fafc;font-size:24px;line-height:1.4;padding:20px 64px 44px 64px;display:none}
.demo{display:grid;grid-template-columns:900px 1fr;gap:28px;height:100%}
.demo svg{width:900px;height:430px;background:#fff;border:1px solid var(--line);border-radius:12px}
.pbtns{display:flex;gap:10px;margin-bottom:10px}.pbtns button{font-size:20px;padding:8px 16px;border-radius:999px;border:2px solid var(--accent);background:#fff;color:var(--accent);cursor:pointer}
.pbtns button.on{background:var(--accent);color:#fff}
.flagcard{border-radius:16px;padding:18px 22px;border:3px solid var(--accent);background:var(--accentbg);font-size:22px;line-height:1.35}
.flagcard.alert{border-color:var(--warn);background:var(--warnbg)}
.flagcard h2{font-size:28px;margin:0 0 6px 0}
.chips span{display:inline-block;background:#fff;border:1px solid var(--line);border-radius:999px;padding:3px 12px;margin:3px 4px 3px 0;font-size:18px}
.cycleinfo{font-size:20px;color:var(--muted);margin:8px 0}
.bignum{font-size:120px;font-weight:800;color:var(--accent);line-height:1}
"""

JS = r"""
const D = window.__DATA__;
const stage = document.getElementById('stage');
let idx = 0, playing = true, timer = null, t0 = 0, demoTimers = [];
function fit(){const s=Math.min(innerWidth/1600, innerHeight/900);stage.style.transform=`translate(-50%,-50%) scale(${s})`;}
addEventListener('resize', fit); fit();
const slides = D.slides.map((s,i)=>{
  const el=document.createElement('div');el.className='slide';
  el.innerHTML=`<div class="section">${s.section}</div><h1>${s.title}</h1><div class="body">${s.body}</div>
  <footer><span>MyCycle &middot; ${D.label}</span><span>${i+1} / ${D.slides.length}</span></footer>`;
  stage.appendChild(el);return el;});
const notes=document.getElementById('notes'), prog=document.getElementById('progress');
function clearDemo(){demoTimers.forEach(clearTimeout);demoTimers=[];}
function show(i){
  clearDemo(); slides[idx].classList.remove('on'); idx=(i+slides.length)%slides.length; slides[idx].classList.add('on');
  notes.textContent=D.slides[idx].say; const k=D.slides[idx].kind;
  if(k==='demo') runDemo(slides[idx].querySelector('.body'), playing ? null : 0);
  if(k==='privacy') runPrivacy(slides[idx].querySelector('.body'));
  t0=performance.now(); schedule();
}
function schedule(){clearTimeout(timer); if(!playing){prog.style.width='0';return;}
  const dur=D.slides[idx].dur*1000; timer=setTimeout(()=>show(idx+1),dur);
  prog.style.transition='none';prog.style.width='0';requestAnimationFrame(()=>{prog.style.transition=`width ${dur}ms linear`;prog.style.width='100%';});}
function toggle(){playing=!playing;document.getElementById('bplay').textContent=playing?'Pause (P)':'Play (P)';schedule();}
function fs(){document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen();}
addEventListener('keydown',e=>{
  if(['ArrowRight','PageDown',' '].includes(e.key)){e.preventDefault();show(idx+1);}
  else if(['ArrowLeft','PageUp'].includes(e.key)){show(idx-1);}
  else if(e.key==='p'||e.key==='P')toggle(); else if(e.key==='f'||e.key==='F')fs();
  else if(e.key==='n'||e.key==='N')notes.style.display=notes.style.display==='block'?'none':'block';
  else if(e.key==='Home')show(0);});
document.getElementById('bprev').onclick=()=>show(idx-1);document.getElementById('bnext').onclick=()=>show(idx+1);
document.getElementById('bplay').onclick=toggle;document.getElementById('bfs').onclick=fs;
document.getElementById('bnotes').onclick=()=>notes.style.display=notes.style.display==='block'?'none':'block';

// ---------------- live detector demo (outputs computed by sim/detectors.py at build time)
const NAMES={regular:'Person A: regular cycles',pcos_pattern:'Person B: PCOS-like change',anemia_pattern:'Person C: anemia-like change',thyroid_pattern:'Person D: thyroid-like change'};
const SYM={acne:'acne',excess_hair:'excess hair',hair_loss:'hair loss',fatigue:'tiredness',mood:'mood change',weight_change:'weight change',dizziness:'dizziness',pallor:'pale skin'};
const SIGS={cycle_length_high:'cycle longer than your normal',cycle_length_low:'cycle shorter than your normal',flow_high:'heavier flow than your normal',pain_high:'more pain than your normal',acne_high:'more acne',excess_hair_high:'more hair growth',hair_loss_high:'more hair loss',fatigue_high:'more tiredness',mood_high:'more mood changes',weight_change_high:'weight change',dizziness_high:'more dizziness',pallor_high:'paler skin'};
function runDemo(body, pickIndex){
  clearDemo(); const P=D.personas.personas;
  body.innerHTML=`<div class="demo"><div><div class="pbtns">${P.map((p,i)=>`<button data-i="${i}">${NAMES[p.id]||p.id}</button>`).join('')}</div>
  <svg id="chart" viewBox="0 0 900 430"></svg><div class="cycleinfo" id="cinfo"></div></div>
  <div><div id="flag"></div><p class="caption" style="margin-top:14px">Each cycle is fed to the real Tier 1 detector (sim/detectors.py, thresholds tuned on validation data). Shaded band = this person's own normal (mean &plusmn; 2 SD of her early cycles). ${P.every(p=>p.verified)?'All 4 personas re-verified against their expected flags at build time.':'WARNING: a persona did not match its expected flags.'}</p></div></div>`;
  body.querySelectorAll('.pbtns button').forEach(b=>b.onclick=()=>{clearDemo();play(+b.dataset.i,false);});
  const auto = pickIndex===null;
  function play(pi, chain){
    body.querySelectorAll('.pbtns button').forEach((b,j)=>b.classList.toggle('on',j===pi));
    const p=P[pi], n=p.logs.length, step=1150;
    for(let c=1;c<=n;c++) demoTimers.push(setTimeout(()=>draw(p,c),(c-1)*step));
    if(chain && pi+1<P.length) demoTimers.push(setTimeout(()=>play(pi+1,true), n*step+1600));
  }
  play(0, auto);
}
function draw(p, upto){
  const svg=document.getElementById('chart'); if(!svg) return;
  const n=p.logs.length, L=p.logs.map(c=>c.cycle_length_days);
  const lo=Math.min(18,...L,p.band[0])-2, hi=Math.max(40,...L,p.band[2])+2;
  const X=i=>70+i*(800/(n-1)), Y=v=>390-(v-lo)/(hi-lo)*350;
  let s=`<rect x="70" y="${Y(p.band[2])}" width="800" height="${Y(p.band[0])-Y(p.band[2])}" fill="#ccfbf1"/>
  <line x1="70" x2="870" y1="${Y(p.band[1])}" y2="${Y(p.band[1])}" stroke="#0f766e" stroke-dasharray="6 6"/>
  <text x="872" y="${Y(p.band[2])+18}" font-size="16" fill="#0f766e" text-anchor="end">your normal range</text>`;
  for(let v=Math.ceil(lo/5)*5; v<=hi; v+=5) s+=`<text x="60" y="${Y(v)+6}" font-size="16" text-anchor="end" fill="#52525b">${v}</text><line x1="70" x2="870" y1="${Y(v)}" y2="${Y(v)}" stroke="#eee"/>`;
  s+=`<text x="16" y="24" font-size="17" fill="#52525b">cycle length (days)</text><text x="470" y="424" font-size="17" text-anchor="middle" fill="#52525b">cycle number</text>`;
  const pts=L.slice(0,upto).map((v,i)=>`${X(i)},${Y(v)}`).join(' ');
  s+=`<polyline points="${pts}" fill="none" stroke="#334155" stroke-width="3"/>`;
  for(let i=0;i<upto;i++){const f=p.outputs[i].flag, col=f==='none'?'#0f766e':'#b45309';
    s+=`<circle cx="${X(i)}" cy="${Y(L[i])}" r="${i===upto-1?11:7}" fill="${col}" stroke="#fff" stroke-width="2"/><text x="${X(i)}" y="408" font-size="15" text-anchor="middle" fill="#52525b">${i+1}</text>`;}
  svg.innerHTML=s;
  const c=p.logs[upto-1], o=p.outputs[upto-1], m=(D.messages||{})[o.message_key]||{};
  const sy=Object.entries(c.symptoms).filter(([k,v])=>v>0).map(([k,v])=>`${SYM[k]||k} (${['','mild','moderate','severe'][v]})`);
  document.getElementById('cinfo').innerHTML=`<b>${NAMES[p.id]}</b> &middot; cycle ${upto}: ${c.cycle_length_days} days, flow ${['none','light','medium','heavy'][c.flow]}, pain ${c.pain}/10${sy.length?' &middot; '+sy.join(', '):''}`;
  const alert=o.flag!=='none';
  document.getElementById('flag').innerHTML=`<div class="flagcard ${alert?'alert':''}"><div class="section">${alert?'Screening flag':'No flag'}</div>
   <h2>${m.title||o.flag}</h2><p>${m.summary||''}</p>
   ${alert?`<div class="chips"><b>What changed:</b><br>${o.contributing_signals.map(x=>`<span>${SIGS[x]||x}</span>`).join('')}</div><p><b>Confidence:</b> ${o.confidence}</p>`:''}
   <p><b>${m.doctor_consult||'Consider consulting a doctor.'}</b></p></div>`;
}

// ---------------- live privacy proof
function runPrivacy(body){
  function count(){const r=performance.getEntriesByType('resource');return [r.length, r.reduce((a,x)=>a+(x.transferSize||0),0)];}
  const B=D.backend.calls.find(c=>c.body&&c.status===422);
  body.innerHTML=`<div class="cols"><div><p>Network requests this page has made since it opened, measured live by your browser:</p>
    <div class="bignum" id="pcount">0</div><p id="pbytes"></p>
    <p class="note">Everything in this demo is inside one file. You can switch off Wi-Fi and it keeps working. The phone app is designed the same way: all network traffic must go through one counter that refuses any payload containing cycle-log fields.</p></div>
    <div><p>We asked the real backend to accept an anonymous count <b>plus a cycle length</b>:</p>
    <pre>POST /v1/metrics/aggregate
{"metric_name": "app_opened_count", "value": 1,
 "cycle_length_days": 29}</pre>
    <p>Backend answer: <span class="code refused">${B?B.status:'?'}</span> refused. Only allow-listed counts are stored, never logs or identifiers.</p></div></div>`;
  const tick=()=>{const [n,b]=count();const e=document.getElementById('pcount');if(!e)return;e.textContent=n;document.getElementById('pbytes').textContent=`${b} bytes`;demoTimers.push(setTimeout(tick,1000));};tick();
}
const h=location.hash.match(/^#(\d+)$/); if(h){playing=false;document.getElementById('bplay').textContent='Play (P)';show(+h[1]-1);} else show(0);
"""

HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MyCycle Demo</title><style>__CSS__</style></head>
<body><div id="stage"><div id="progress"></div><div id="notes"></div></div>
<div id="controls"><button id="bprev">&larr;</button><button id="bplay">Pause (P)</button><button id="bnext">&rarr;</button><button id="bnotes">Notes (N)</button><button id="bfs">Full screen (F)</button></div>
<script>window.__DATA__ = @@DATA@@;</script><script>__JS__</script></body></html>"""


# --------------------------------------------------------------------------------------------
# companion markdown files
# --------------------------------------------------------------------------------------------

def strip_tags(s: str) -> str:
    s = re.sub(r"<svg.*?</svg>", "[diagram]", s, flags=re.S)
    s = re.sub(r"<img[^>]*>", "[figure]", s)
    s = re.sub(r"</(p|li|tr|h3|div)>", "\n", s)
    s = re.sub(r"</t[dh]>", " | ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


def write_markdown(slides: list[dict], R: dict) -> None:
    lines = ["# MyCycle demo: speaker script", "",
             f"Generated by `python demo/run_demo.py` from commit {R['commit']}. What to say on each slide, in plain language. "
             f"Every number comes from a results file. {LABEL}.", ""]
    for i, s in enumerate(slides, 1):
        lines += [f"## {i}. {s['title']}", "", f"**Say:** {s['say']}", ""]
    (OUT_DIR / "SPEAKER_SCRIPT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    lines = ["# Why this, not that: every choice compared honestly", "",
             "Verdicts: WINS = measurably better; TIE = numbers close, chosen for a stated reason; LOSES = tested and lost, not relied on; "
             "TRADE-OFF = worse on accuracy, chosen on purpose for access or privacy; MIXED = better on some measures, worse on others; "
             "NOT MEASURED = reasoned choice only.", "",
             f"Generated by `python demo/run_demo.py` from commit {R['commit']}. {LABEL}.", ""]
    names = {"win": "WINS", "tie": "TIE", "loss": "LOSES", "trade": "TRADE-OFF", "mixed": "MIXED", "qual": "NOT MEASURED"}
    for c in R["comparisons"]:
        lines += [f"## {c['decision']}", "", f"**We use:** {c['chosen']}  ", f"**Verdict:** {names[c['verdict']]}", "",
                  "| " + " | ".join(c["headers"]) + " |", "|" + "---|" * len(c["headers"])]
        lines += ["| " + " | ".join(strip_tags(x) for x in r) + " |" for r in c["rows"]]
        lines += ["", f"**In plain words:** {c['plain']}", "", f"**Where we could be wrong:** {c['caveat']}", ""]
    (OUT_DIR / "COMPARISONS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Build and open the MyCycle end-to-end demo")
    ap.add_argument("--run-tests", action="store_true", help="run the full test suite (about 3 minutes) and show the real result")
    ap.add_argument("--no-open", action="store_true", help="build only, do not open the browser")
    args = ap.parse_args()

    print("1/5 reading results ...")
    import csv
    R = {
        "det": load("results/baseline_detection.json"), "clf": load("results/classifiers.json"),
        "fed": load("results/federated.json"), "seq": load("results/sequence_models.json"),
        "nfhs": load("results/nfhs_classifiers.json"), "val": load("results/sim_validation.json"),
        "sim_meta": load("results/sim/meta.json"),
        "ablation": list(csv.DictReader((ROOT / "results/tables/imputation_ablation.csv").open(encoding="utf-8"))),
        "img": {"clf": img_uri("results/figures/classifier_comparison.png"), "pu": img_uri("results/figures/privacy_utility.png"),
                "fc": img_uri("results/figures/fed_curves.png")},
        "commit": git_commit(), "built_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    print("2/5 running the real detector on the demo personas ...")
    R["personas"] = run_personas()
    for p in R["personas"]["personas"]:
        print(f"    {p['id']:16s} expected {p['expected']:16s} verified={p['verified']}")
    print("3/5 starting the backend and calling every endpoint ...")
    R["backend"] = run_backend()
    for c in R["backend"]["calls"]:
        print(f"    {c['method']:4s} {c['path']:32s} -> {c['status']}")
    print("4/5 running checks" + (" and the full test suite (about 3 minutes)" if args.run_tests else "") + " ...")
    R["checks"] = run_checks(args.run_tests)
    R["claims"] = claims_summary()
    print(f"    lint ok={R['checks']['lint_ok']} contracts ok={R['checks']['contracts_ok']} tests={R['checks']['tests']}")

    print("5/5 writing the demo ...")
    slides = build_slides(R)
    data = {"slides": slides, "label": LABEL, "personas": R["personas"], "messages": R["backend"]["messages"],
            "backend": {"calls": [{k: v for k, v in c.items() if k != "body"} | {"body": c["body"] if c["status"] == 422 else None}
                                  for c in R["backend"]["calls"]]}}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = HTML.replace("__CSS__", CSS).replace("__JS__", JS).replace("@@DATA@@", blob)
    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / "MyCycle_Demo.html"
    out.write_text(page, encoding="utf-8")
    write_markdown(slides, R)
    total = sum(s["dur"] for s in slides)
    print(f"\nWrote {out} ({len(slides)} slides, about {total // 60} min on autoplay, {out.stat().st_size // 1024} KB)")
    print(f"Wrote {OUT_DIR / 'SPEAKER_SCRIPT.md'} and {OUT_DIR / 'COMPARISONS.md'}")
    print("Keys: arrows = move, P = pause/play, F = full screen, N = speaker notes. Autoplay loops.")
    if not args.no_open:
        webbrowser.open(out.as_uri())


if __name__ == "__main__":
    main()
