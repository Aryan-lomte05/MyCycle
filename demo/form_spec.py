#!/usr/bin/env python3
"""The MyCycle logging form: every question, its answers, its scale anchors, why we ask it and what it feeds.

One definition, three outputs (run `python demo/form_spec.py`):
  docs/LOGGING_FORM.md      the specification, for the team and for sir's questions
  demo/logging_form.html    a clickable offline mock of the form that prints the exact record it would store
  (demo/run_demo.py imports FORM for the "logging form" slides)

Status of each question:
  "v1"  in the frozen cycle-log contract today (CLAUDE.md 5.3), used by the detector now
  "v2"  proposed addition; needs all four team members to agree and a contract version bump (docs/OPEN_QUESTIONS.md)

Sources are listed in SOURCES. Anything not read in full by a team member is marked UNVERIFIED.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SOURCES = {
    "NRS": ("Numerical rating scale of menstrual pain severity: minimally important difference and responsiveness, "
            "Frontiers in Pain Research 2025 (PMC12745389). 0 = \"No pain\", 10 = \"Extremely severe\"; a change of about 1 point is meaningful. "
            "Read online by Claude on 2026-09-29; a team member should confirm before marking VERIFIED in docs/papers.csv.",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC12745389"),
    "PBAC": ("Higham, O'Brien, Shaw. Assessment of menstrual blood loss using a pictorial chart. BJOG 1990: counts pads and tampons by "
             "how soaked they are, plus clots and flooding; a score of 100 or more was reported to flag heavy bleeding with over 80% sensitivity "
             "and specificity. UNVERIFIED: known from search summaries only, paper not yet opened.",
             "https://pubmed.ncbi.nlm.nih.gov/2400752/"),
    "PBAC_ASIA": ("PBAC in Asian women, Hong Kong Med J 2021: reports clots and a period longer than 7 days as independent predictors of heavy "
                  "bleeding and discusses a higher cut-off. UNVERIFIED: search summary only.", "https://www.hkmj.org/abstracts/v27n6/399.htm"),
    "FLO1": ("Flo help centre, \"Logging your symptoms\": \"16 trackers with more than 50 symptoms and events to log\". Opened 2026-09-29. "
             "The full list is not published outside the app.", "https://help.flo.health/hc/en-us/articles/4406826542740-Logging-your-symptoms"),
    "FLO2": ("Flo help centre, \"How do I use the app?\": \"more than 80 symptoms and events to log\". Opened 2026-09-29. Note the two Flo pages "
             "give different counts.", "https://help.flo.health/hc/en-us/articles/360014347632-How-do-I-use-the-app"),
}

SEV = [(0, "None"), (1, "Mild: I noticed it, it did not bother me"), (2, "Moderate: it bothered me"),
       (3, "Severe: it affected my day (school, work, home)")]

FORM = [
    {"section": "Period", "questions": [
        {"id": "start_date", "status": "v1", "q": "When did this period start?", "type": "date", "field": "start_date",
         "why": "Cycle length is computed from two start dates. We never ask \"how long was your cycle\": people misremember it, dates do not.",
         "feeds": "cycle_length_days (derived), cycle_length_high / cycle_length_low signals"},
        {"id": "bleed_days", "status": "v2", "q": "How many days did you bleed?", "type": "number", "min": 1, "max": 15,
         "why": "Very long bleeding is a warning sign of heavy periods (reported as an independent predictor in PBAC_ASIA).",
         "feeds": "proposed: bleeding_days_high signal for anemia_pattern", "source": "PBAC_ASIA"},
        {"id": "flow", "status": "v1", "q": "How heavy was the flow on your heaviest day?", "type": "choice", "field": "flow",
         "options": [(0, "None: no bleeding"), (1, "Light: pad or tampon only lightly stained when changed"),
                     (2, "Medium: pad or tampon moderately soaked when changed"),
                     (3, "Heavy: pad or tampon fully soaked, or leaking through, or needing two at once")],
         "why": "Heavier flow than her own normal, together with tiredness, dizziness or pale skin, is the anemia-like pattern. Each level is described by what she sees, not a vague word.",
         "feeds": "flow_high signal (anemia_pattern)", "source": "PBAC"},
        {"id": "pbac", "status": "v2", "q": "Optional, for more accuracy: on your heaviest day, how many pads or tampons were lightly / moderately / fully soaked?",
         "type": "pbac", "why": "A counting chart turns \"heavy\" into a score. Scored on the phone only; the score, not the counts, is stored.",
         "feeds": "proposed: pbac_score (anemia_pattern)", "source": "PBAC"},
        {"id": "clots", "status": "v2", "q": "Did you pass clots bigger than a one-rupee coin, or have flooding (sudden gush that leaked through)?",
         "type": "choice", "options": [(0, "No"), (1, "Yes, once"), (2, "Yes, more than once")],
         "why": "Clots and flooding are part of the standard heavy-bleeding chart and reported predictors of heavy bleeding.",
         "feeds": "proposed: clots signal (anemia_pattern)", "source": "PBAC_ASIA"},
        {"id": "intermenstrual", "status": "v2", "q": "Any bleeding between periods or after sex?", "type": "choice",
         "options": [(0, "No"), (1, "Yes")],
         "why": "Safety question. A yes always shows \"consider consulting a doctor\", whatever the detector says.",
         "feeds": "proposed: safety prompt (never a pattern flag)"},
    ]},
    {"section": "Pain", "questions": [
        {"id": "pain", "status": "v1", "q": "How bad was your worst period pain this cycle?", "type": "scale", "min": 0, "max": 10, "field": "pain",
         "anchors": [("0", "No pain"), ("1 to 3", "Mild: noticeable, I could do my usual day"), ("4 to 6", "Moderate: I had to slow down or skip some things"),
                     ("7 to 9", "Severe: I could not do my usual activities"), ("10", "Extremely severe")],
         "why": "The 0 to 10 menstrual pain scale is validated with the end labels \"No pain\" and \"Extremely severe\"; a change of about 1 point is meaningful (NRS). The middle labels tie numbers to daily life so 6 means the same to everyone; those middle wordings are our design choice.",
         "feeds": "pain_high signal (context for all patterns)", "source": "NRS"},
        {"id": "pain_days", "status": "v2", "q": "On how many days did pain stop you from school, work or housework?", "type": "number", "min": 0, "max": 10,
         "why": "Function is what matters to a doctor: \"missed 3 days of college\" is clearer than a number.",
         "feeds": "proposed: pain_impact (shown in the doctor visit summary)"},
        {"id": "painkiller", "status": "v2", "q": "Did you take a painkiller for period pain?", "type": "choice", "options": [(0, "No"), (1, "Yes")],
         "why": "A pain score of 3 after a painkiller is not the same as 3 without one.", "feeds": "proposed: context for pain_high"},
    ]},
    {"section": "Symptoms this cycle", "note": "Each symptom uses the same four answers: " + "; ".join(t for _, t in SEV) + ".", "questions": [
        {"id": "acne", "status": "v1", "q": "Pimples or acne", "type": "sev", "field": "symptoms.acne", "why": "Androgen-type sign.", "feeds": "acne_high (pcos_pattern)"},
        {"id": "excess_hair", "status": "v1", "q": "New or thicker hair on face, chin, chest or stomach", "type": "sev", "field": "symptoms.excess_hair",
         "why": "Androgen-type sign, described by body place so it is not confused with normal hair.", "feeds": "excess_hair_high (pcos_pattern)"},
        {"id": "hair_loss", "status": "v1", "q": "Hair thinning or falling from the scalp", "type": "sev", "field": "symptoms.hair_loss",
         "why": "Seen in both androgen-type and thyroid-type changes.", "feeds": "hair_loss_high (pcos_pattern)"},
        {"id": "fatigue", "status": "v1", "q": "Tiredness that rest does not fix", "type": "sev", "field": "symptoms.fatigue",
         "why": "Shared by anemia-like and thyroid-like patterns; the other answers decide which.", "feeds": "fatigue_high (anemia_pattern, thyroid_pattern)"},
        {"id": "mood", "status": "v1", "q": "Low mood, irritability or anxiety", "type": "sev", "field": "symptoms.mood", "why": "Thyroid-type sign.", "feeds": "mood_high (thyroid_pattern)"},
        {"id": "weight_change", "status": "v1", "q": "Weight change you did not try for", "type": "sev", "field": "symptoms.weight_change",
         "why": "Thyroid-type sign.", "feeds": "weight_change_high (thyroid_pattern)"},
        {"id": "weight_dir", "status": "v2", "q": "If yes: gained or lost?", "type": "choice", "options": [(0, "Gained"), (1, "Lost")],
         "why": "Gain and loss point in different directions; today's contract cannot tell them apart.", "feeds": "proposed: weight_direction (thyroid_pattern)"},
        {"id": "dizziness", "status": "v1", "q": "Dizziness or feeling faint when standing", "type": "sev", "field": "symptoms.dizziness", "why": "Anemia-type sign.", "feeds": "dizziness_high (anemia_pattern)"},
        {"id": "pallor", "status": "v1", "q": "Pale skin, pale nails or pale inner eyelids", "type": "sev", "field": "symptoms.pallor",
         "why": "Anemia-type sign, described by where to look.", "feeds": "pallor_high (anemia_pattern)"},
    ]},
    {"section": "Anything that explains a change", "questions": [
        {"id": "context", "status": "v2", "q": "Was anything unusual this cycle? (tick all that apply)", "type": "multi",
         "options": [(0, "Travel"), (1, "Illness or fever"), (2, "Big stress (exams, family, work)"), (3, "Big change in food or exercise"),
                     (4, "Started or stopped a medicine")],
         "why": "On the simulator, our detector gave 39% of women with a one-off stress or travel cycle a pattern flag. Knowing the reason lets the app hold a flag and wait one more cycle instead of alarming her. Expected to cut false alarms; not yet measured.",
         "feeds": "proposed: context_benign, suppresses pattern flags for one cycle"},
        {"id": "hormonal", "status": "v2", "q": "Are you using hormonal contraception (pill, injection, implant, hormonal coil)?", "type": "choice",
         "options": [(0, "No"), (1, "Yes")],
         "why": "Hormonal contraception controls the bleeding pattern, so cycle-based screening does not apply. The app pauses pattern flags and says why.",
         "feeds": "proposed: screening_paused"},
        {"id": "pregnancy", "status": "v2", "q": "Could you be pregnant, or are you breastfeeding?", "type": "choice",
         "options": [(0, "No"), (1, "Yes"), (2, "Not sure")],
         "why": "A missed period may be pregnancy, not a pattern. Screening pauses and the app suggests a test or a doctor.",
         "feeds": "proposed: screening_paused"},
    ]},
    {"section": "Once, at setup (optional, stays on the phone)", "questions": [
        {"id": "known_dx", "status": "v2", "q": "Has a doctor already told you that you have PCOS, anemia or a thyroid condition?", "type": "multi",
         "options": [(0, "PCOS"), (1, "Anemia"), (2, "Thyroid"), (3, "None / not sure")],
         "why": "The app should not \"discover\" what she already knows; it switches to tracking and education for that condition.",
         "feeds": "proposed: suppress the matching pattern flag"},
        {"id": "age_band", "status": "v2", "q": "Your age group", "type": "choice", "options": [(0, "Under 18"), (1, "18 to 29"), (2, "30 to 39"), (3, "40 or over")],
         "why": "Cycles are naturally irregular in the first years after periods start and in the years before menopause.", "feeds": "proposed: detector sensitivity by age band"},
        {"id": "vitals", "status": "v2", "q": "Height and weight (optional)", "type": "number2",
         "why": "Adds the \"symptoms + vitals\" screening features (PCOS AUC 0.894 vs 0.891 symptoms only on real data: a small gain).",
         "feeds": "proposed: bmi for the symptom_plus_vitals screening model"},
    ]},
]

NOT_ASKED = [
    ("Sexual activity and sex drive", "Common in consumer trackers. Not needed for any of our screening patterns, and on a shared phone it is the most sensitive thing to store. Data minimisation: we do not ask."),
    ("Vaginal discharge", "Useful for infections and fertility, not for PCOS, anemia or thyroid patterns. Out of scope."),
    ("Ovulation tests, basal temperature, fertility window", "MyCycle is a screening aid, not a fertility or contraception app."),
    ("Daily mood diary, sleep hours, water intake", "Daily logging fatigues users. We ask once per cycle, which is what the detector uses."),
    ("Name, phone number, email", "No account. Nothing that identifies her is collected."),
]

QUESTIONS_SIR = [
    ("What exactly does pain 6 mean?", "It is her worst period pain this cycle on the validated 0 to 10 menstrual pain scale (0 = No pain, 10 = Extremely severe). At 4 to 6 the label reads \"I had to slow down or skip some things\", so two women mean the same thing. A change of about 1 point is considered meaningful (NRS)."),
    ("Is pain one number for the whole cycle?", "Yes: the worst day of this cycle. The validated scale also allows average and current pain; we use worst because it is easiest to remember once a month and it is what a doctor asks first."),
    ("How do you measure \"heavy\" flow without a lab?", "Each level is described by what she sees on the pad or tampon. An optional counting chart (the standard pictorial blood loss chart) turns pads and clots into a score on the phone."),
    ("Why 0 to 3 for symptoms and not 0 to 10?", "Four answers with plain-language labels are quicker and more reliable for low-literacy users than an 11-point scale. Each label says how the symptom affected her day."),
    ("Why do you ask for dates and not cycle length?", "People misremember cycle length. Two start dates give the exact number."),
    ("Why not ask everything Flo asks?", "Flo says it offers 50 to 80+ items (its help pages give both numbers). We ask only what feeds a screening signal or explains a change; the rest is either out of scope or too sensitive for a shared phone."),
    ("What stops a stressful month from raising a PCOS flag?", "Today, too little: on the simulator 39% of one-off stress or travel cycles got a pattern flag. The proposed context question lets the app wait a cycle instead. Not yet measured."),
    ("What happens if she is on the pill or pregnant?", "Screening pauses and the app says why; cycle patterns do not mean the same thing then."),
]


# ------------------------------------------------------------------------------------------------ markdown

def to_markdown() -> str:
    L = ["# MyCycle logging form: every question, answer, scale and reason", "",
         "Generated by `python demo/form_spec.py` (single source of truth; do not hand-edit). "
         "**v1** = in the frozen cycle-log contract today (CLAUDE.md 5.3) and used by the detector. "
         "**v2** = proposed; needs team agreement and a contract version bump.", "",
         "Design rules: one form per cycle (not daily), plain words, every scale point described by what she experiences, "
         "every question feeds a screening signal or explains a change, nothing that identifies her.", ""]
    for sec in FORM:
        L += [f"## {sec['section']}", ""]
        if sec.get("note"):
            L += [sec["note"], ""]
        L += ["| Status | Question | Answers | Why we ask | Feeds |", "|---|---|---|---|---|"]
        for q in sec["questions"]:
            if q["type"] == "sev":
                ans = "0 to 3 (see above)"
            elif q["type"] == "scale":
                ans = "; ".join(f"{v} = {t}" for v, t in q["anchors"])
            elif q["type"] in ("choice", "multi"):
                ans = "; ".join(t for _, t in q["options"]) + (" (tick all)" if q["type"] == "multi" else "")
            elif q["type"] == "pbac":
                ans = "counts per soak level, clots, flooding; scored on the phone"
            elif q["type"] == "number2":
                ans = "height (cm), weight (kg)"
            else:
                ans = {"date": "date picker", "number": f"number {q.get('min')} to {q.get('max')}"}[q["type"]]
            src = f" [{q['source']}]" if q.get("source") else ""
            L.append(f"| {q['status']} | {q['q']} | {ans} | {q['why']}{src} | {q['feeds']} |")
        L.append("")
    L += ["## What we deliberately do not ask", "", "| Item | Why not |", "|---|---|"] + [f"| {a} | {b} |" for a, b in NOT_ASKED] + [""]
    L += ["## Questions sir may ask about the form", ""]
    for q, a in QUESTIONS_SIR:
        L += [f"**{q}** {a}", ""]
    L += ["## Exact stored record (v1, contract 5.3)", "", "```json", json.dumps(EXAMPLE_V1, indent=2), "```", "",
          "Proposed v2 additions would add, for example: `bleeding_days`, `pbac_score`, `clots`, `intermenstrual`, `pain_impact_days`, "
          "`painkiller`, `weight_direction`, `context` (list), `screening_paused`. None of them leaves the phone.", "",
          "## Sources", ""]
    L += [f"- **{k}**: {t} <{u}>" for k, (t, u) in SOURCES.items()]
    return "\n".join(L) + "\n"


EXAMPLE_V1 = {"cycle_index": 6, "start_date": "2024-07-22", "cycle_length_days": 40, "flow": 2, "pain": 5,
              "symptoms": {"acne": 2, "excess_hair": 0, "hair_loss": 1, "fatigue": 2, "mood": 0, "weight_change": 1, "dizziness": 0, "pallor": 0}}


# ------------------------------------------------------------------------------------------------ html mock

def to_html() -> str:
    e = html.escape
    parts = []
    for sec in FORM:
        parts.append(f'<section><h2>{e(sec["section"])}</h2>')
        if sec.get("note"):
            parts.append(f'<p class="hint">{e(sec["note"])}</p>')
        for q in sec["questions"]:
            badge = f'<span class="st {q["status"]}">{"in use today" if q["status"] == "v1" else "proposed"}</span>'
            parts.append(f'<div class="q" data-id="{q["id"]}"><label>{e(q["q"])} {badge}</label>')
            t = q["type"]
            if t == "date":
                parts.append(f'<input type="date" name="{q["id"]}" value="2024-07-22"><input type="date" name="prev_start" value="2024-06-12" title="previous period start"><span class="hint">previous start (to compute cycle length)</span>')
            elif t == "number":
                parts.append(f'<input type="number" name="{q["id"]}" min="{q["min"]}" max="{q["max"]}" value="{q["min"]}">')
            elif t == "number2":
                parts.append('<input type="number" name="height" placeholder="height cm"> <input type="number" name="weight" placeholder="weight kg">')
            elif t == "scale":
                parts.append(f'<div class="scale"><input type="range" name="{q["id"]}" min="0" max="10" value="0" oninput="painLabel(this)"><b id="painval">0</b> <span id="painlab">No pain</span></div>')
                parts.append('<div class="anchors">' + "".join(f'<span>{v}: {e(tx)}</span>' for v, tx in q["anchors"]) + '</div>')
            elif t in ("choice", "sev"):
                opts = SEV if t == "sev" else q["options"]
                parts.append('<div class="opts">' + "".join(
                    f'<label class="opt"><input type="radio" name="{q["id"]}" value="{v}" {"checked" if i == 0 else ""}> {e(tx)}</label>' for i, (v, tx) in enumerate(opts)) + '</div>')
            elif t == "multi":
                parts.append('<div class="opts">' + "".join(f'<label class="opt"><input type="checkbox" name="{q["id"]}" value="{e(tx)}"> {e(tx)}</label>' for _, tx in q["options"]) + '</div>')
            elif t == "pbac":
                parts.append('<div class="pbac">Lightly soaked <input type="number" name="pb_l" min="0" value="0"> Moderately <input type="number" name="pb_m" min="0" value="0"> Fully <input type="number" name="pb_f" min="0" value="0"> <span class="hint">score shown below; UNVERIFIED weights (1, 5, 20 per item, as commonly quoted for the pictorial chart), clots/flooding from the next question</span></div>')
            parts.append(f'<p class="why"><b>Why:</b> {e(q["why"])} <b>Feeds:</b> {e(q["feeds"])}</p></div>')
        parts.append('</section>')
    body = "\n".join(parts)
    return HTML_FORM.replace("@@BODY@@", body)


HTML_FORM = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MyCycle Logging Form</title><style>
:root{--bg:#fbfaf6;--ink:#1c1c1c;--muted:#52525b;--accent:#0f766e;--line:#d6d3cb}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Segoe UI",Roboto,Arial,sans-serif;font-size:19px}
main{max-width:980px;margin:0 auto;padding:24px 16px 80px}h1{color:var(--accent);margin:8px 0}h2{margin:28px 0 8px;border-bottom:2px solid var(--accent);padding-bottom:4px}
.q{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:10px 0}.q>label{font-weight:700;display:block;margin-bottom:8px}
.opts{display:flex;flex-direction:column;gap:6px}.opt{font-weight:400;display:flex;gap:10px;align-items:flex-start;min-height:32px}
input[type=radio],input[type=checkbox]{width:22px;height:22px;margin-top:2px}input[type=number],input[type=date]{font-size:18px;padding:6px;border:1px solid var(--line);border-radius:8px;width:170px}
.scale{display:flex;align-items:center;gap:12px}.scale input{flex:1;height:30px}#painval{font-size:28px;color:var(--accent);width:36px;text-align:center}
.anchors{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:15px;color:var(--muted);margin-top:4px}
.why{font-size:15px;color:var(--muted);margin:10px 0 0}.hint{font-size:15px;color:var(--muted)}
.st{font-size:12px;font-weight:700;padding:2px 8px;border-radius:999px;margin-left:6px;vertical-align:middle}.st.v1{background:#dcfce7;color:#166534}.st.v2{background:#e0e7ff;color:#3730a3}
button{font-size:20px;padding:12px 22px;border:0;border-radius:10px;background:var(--accent);color:#fff;cursor:pointer;min-height:44px}
pre{background:#1f2937;color:#f9fafb;padding:14px;border-radius:10px;font-size:15px;white-space:pre-wrap}
.banner{background:#ecfdf5;border-left:5px solid var(--accent);padding:10px 14px;border-radius:6px;font-size:16px}
</style></head><body><main>
<h1>MyCycle: log this cycle</h1>
<p class="banner">Prototype of the logging form (design mock, not the app). Nothing here is sent anywhere: press the button to see the exact record the phone would store. Green = used by the detector today; blue = proposed addition. Simulated / preliminary, public and synthetic data, not real deployment data.</p>
<form id="f" onsubmit="return build()">
@@BODY@@
<p><button type="submit">Show the record this form stores</button></p></form>
<h2>Stored record (contract 5.3, v1 fields)</h2><pre id="out">press the button</pre>
<h2>Proposed v2 extras (still on the phone only)</h2><pre id="out2"></pre>
</main><script>
const LABELS=[[0,'No pain'],[1,'Mild: noticeable, I could do my usual day'],[4,'Moderate: I had to slow down or skip some things'],[7,'Severe: I could not do my usual activities'],[10,'Extremely severe']];
function painLabel(el){const v=+el.value;document.getElementById('painval').textContent=v;let t='';for(const [k,l] of LABELS){if(v>=k)t=l;}document.getElementById('painlab').textContent=t;}
function val(n){const f=document.getElementById('f');const el=f.querySelector(`[name="${n}"]:checked`)||f.querySelector(`[name="${n}"]`);return el?el.value:null;}
function multi(n){return [...document.querySelectorAll(`[name="${n}"]:checked`)].map(x=>x.value);}
function build(){
  const s=val('start_date'),p=val('prev_start');const len=Math.round((Date.parse(s)-Date.parse(p))/864e5);
  const sym={};['acne','excess_hair','hair_loss','fatigue','mood','weight_change','dizziness','pallor'].forEach(k=>sym[k]=+val(k));
  const rec={cycle_index:6,start_date:s,cycle_length_days:len,flow:+val('flow'),pain:+val('pain'),symptoms:sym};
  document.getElementById('out').textContent=JSON.stringify(rec,null,2);
  const clots=+val('clots');const pb=(+val('pb_l'))*1+(+val('pb_m'))*5+(+val('pb_f'))*20+(clots>0?(clots===1?1:5):0);
  const ctx=multi('context');const paused=val('hormonal')==='1'||val('pregnancy')!=='0';
  document.getElementById('out2').textContent=JSON.stringify({bleeding_days:+val('bleed_days'),pbac_score_unverified_weights:pb,clots:clots,
    intermenstrual:+val('intermenstrual'),pain_impact_days:+val('pain_days'),painkiller:+val('painkiller'),weight_direction:val('weight_dir')==='0'?'gained':'lost',
    context:ctx,screening_paused:paused,note:paused?'Screening paused: hormonal contraception, pregnancy or breastfeeding changes what cycle patterns mean.':(ctx.length?'A reason was given for this cycle: the app would hold any pattern flag and check again next cycle.':'')},null,2);
  return false;}
</script></body></html>"""


def main() -> None:
    (ROOT / "docs" / "LOGGING_FORM.md").write_text(to_markdown(), encoding="utf-8")
    (ROOT / "demo" / "logging_form.html").write_text(to_html(), encoding="utf-8")
    n = sum(len(s["questions"]) for s in FORM)
    v1 = sum(q["status"] == "v1" for s in FORM for q in s["questions"])
    print(f"wrote docs/LOGGING_FORM.md and demo/logging_form.html ({n} questions: {v1} in use today, {n - v1} proposed)")


if __name__ == "__main__":
    main()
