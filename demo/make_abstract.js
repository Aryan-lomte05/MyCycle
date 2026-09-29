// Writes demo/MyCycle_Product_Abstract.docx from demo/abstract_assets/abstract_data.json.
// Run through `python demo/make_abstract.py` (which produces the data first). Needs `npm install docx`.
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType,
  ImageRun, AlignmentType, LevelFormat, Footer, Header, PageNumber, PageBreak, BorderStyle,
} = require("docx");

const D = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const OUT = process.argv[3];
const K = D.k;
const W = 9026; // A4 content width in DXA with 1 inch margins
const TEAL = "0F766E", AMBER = "B45309";
const pct = (x) => (x === null || x === undefined ? "n/a" : `${Math.round(x * 100)}%`);
const f2 = (x) => x.toFixed(2), f3 = (x) => x.toFixed(3);

// ---------- helpers
function runs(text, base = {}) {
  // **bold** segments
  return text.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((s) =>
    s.startsWith("**") ? new TextRun({ text: s.slice(2, -2), bold: true, ...base }) : new TextRun({ text: s, ...base }));
}
const P = (text, opts = {}) => new Paragraph({ children: runs(text, opts.run || {}), spacing: { after: 120 }, ...opts.para });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)], spacing: { before: 280, after: 140 } });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)], spacing: { before: 220, after: 100 } });
const B = (t) => new Paragraph({ numbering: { reference: "bul", level: 0 }, children: runs(t), spacing: { after: 60 } });
const cap = (t) => new Paragraph({ children: [new TextRun({ text: t, italics: true, size: 18, color: "52525B" })], spacing: { after: 200 }, alignment: AlignmentType.CENTER });
const note = (t) => new Paragraph({
  children: runs(t, { size: 20 }), spacing: { before: 80, after: 160 },
  shading: { type: ShadingType.CLEAR, fill: "ECFDF5", color: "auto" },
  border: { left: { style: BorderStyle.SINGLE, size: 24, color: TEAL, space: 8 } },
});
const brk = () => new Paragraph({ children: [new PageBreak()] });

function img(key, maxW = 600) {
  const m = D.imgs[key];
  if (!m) return new Paragraph({ children: [new TextRun({ text: `[figure ${key} not available]`, italics: true })] });
  const w = Math.min(maxW, 600), h = Math.round((w * m.h) / m.w);
  return new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: "png", data: fs.readFileSync(m.path), transformation: { width: w, height: h } })] });
}

function tbl(headers, rows, widths, opts = {}) {
  const n = headers.length;
  widths = widths || Array(n).fill(Math.floor(W / n));
  const total = widths.reduce((a, b) => a + b, 0);
  const border = { style: BorderStyle.SINGLE, size: 4, color: "D6D3CB" };
  const borders = { top: border, bottom: border, left: border, right: border };
  const cell = (t, i, head, hl) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA }, borders,
    shading: head ? { type: ShadingType.CLEAR, fill: TEAL, color: "auto" } : hl ? { type: ShadingType.CLEAR, fill: "ECFDF5", color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text: String(t), bold: head || hl, color: head ? "FFFFFF" : undefined, size: opts.size || 18,
      font: opts.mono && !head ? "Consolas" : undefined })] })],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, i, true)) }),
      ...rows.map((r, ri) => new TableRow({ children: r.map((c, i) => cell(c, i, false, (opts.hl || []).includes(ri))) }))],
  });
}
const gap = () => new Paragraph({ children: [], spacing: { after: 60 } });

function code(text) {
  return text.split("\n").map((line, i, a) => new Paragraph({
    children: [new TextRun({ text: line || " ", font: "Consolas", size: 17 })],
    shading: { type: ShadingType.CLEAR, fill: "F3F4F6", color: "auto" },
    spacing: { after: i === a.length - 1 ? 160 : 0 },
    indent: { left: 200, right: 200 },
  }));
}

const VCOL = { WINS: "15803D", TIE: "475569", LOSES: AMBER, "TRADE-OFF": "7C3AED", MIXED: "0369A1", "NOT MEASURED": "78716C" };

// ---------- content
const C = [];
// Title
C.push(new Paragraph({ children: [new TextRun({ text: "MyCycle", bold: true, size: 64, color: TEAL })], spacing: { after: 60 } }));
C.push(new Paragraph({ children: [new TextRun({ text: "Product abstract: privacy-preserving, personal-baseline menstrual health screening", size: 30, bold: true })], spacing: { after: 120 } }));
C.push(P("216U50P501 Community Engagement Project with Design Thinking. Guide: Dr. Makarand G. Kulkarni. Team: Aryan Lomte, Liza Patel, Saanj Patil, Aditya Lokhande.", { run: { color: "52525B", size: 20 } }));
C.push(note(`Every number in this document is read from a results file produced by a script in the project repository (commit ${D.commit}). ${D.label}. MyCycle is a screening aid: it never gives a diagnosis and every flag suggests consulting a doctor.`));

C.push(H1("Abstract"));
C.push(P(`PCOS, iron-deficiency anemia and thyroid problems are often noticed late, because lab tests and ultrasound cost money or are far away, myths fill the information gap, and people are wary of apps that store intimate data on company servers. **MyCycle** screens for patterns that look like these conditions using only what a woman can log herself (cycle length, flow, pain and eight symptoms), comparing each new cycle with **her own history** rather than a population average. Raw logs never leave the phone. A Tier 1 detector (an adaptive z-score and CUSUM with a rule layer) caught ${pct(K.hyb[0])} of simulated PCOS-like, ${pct(K.hyb[1])} of anemia-like and ${pct(K.hyb[2])} of thyroid-like changes on held-out test users, at ${f2(K.hyb_fa)} false alarms per 100 normal cycles. On real hospital data (n=${K.n_pcos}), symptom-only PCOS screening reached AUC ${f3(K.s1)} (95% CI ${f3(K.s1_lo)} to ${f3(K.s1_hi)}) against ${f3(K.s3)} when lab and ultrasound values are allowed. On India's NFHS-5 survey (${K.n_nfhs.toLocaleString("en-IN")} women), symptoms predicted self-reported thyroid disease reasonably (AUC ${f3(K.th)}) but anemia only weakly (AUC ${f3(K.an)}), so the anemia flag recommends a blood test. Federated learning, which keeps data on each phone, recovered AUC ${f3(K.avg)} against ${f3(K.cen)} for pooling all data and ${f3(K.loc)} for phones learning alone; adding differential privacy gave a stated privacy budget (for example epsilon ${f2(K.dp1.epsilon)} at noise 1.0) at a measured accuracy cost. A GRU neural network was tested and found weaker than the simple statistics, and is reported as such.`));

C.push(H1("1. The product in plain words"));
C.push(H2("The problem"));
[["Clinical access", "hormone tests, blood counts and ultrasound cost money and are often far away"],
 ["Information", "myths fill the gap, for example \"irregular periods are just stress\""],
 ["Privacy", "most existing cycle apps keep raw data on company servers"],
 ["Culture", "shame and taboo stop people discussing symptoms, even at home"]].forEach(([a, b]) => C.push(B(`**${a}:** ${b}.`)));
C.push(H2("What MyCycle does"));
C.push(B("**Learns her own normal.** After a few logged cycles it knows her usual cycle length, flow and symptoms, and how much they usually vary."));
C.push(B("**Raises a screening flag** when her own pattern changes in a way that looks like PCOS, anemia or thyroid trouble, or an irregular cycle. The flag names what changed and always says: consider consulting a doctor."));
C.push(B("**Keeps logs on the phone.** Optionally, phones improve a shared model by sending only a clipped, noise-added model update (federated learning with differential privacy)."));
C.push(B("**Backend** serves flag wording, education cards and reminder rules, and accepts only anonymous counts. It refuses anything that looks like a cycle log."));
C.push(H2("What it is not"));
C.push(P("It is not a diagnostic tool, it has not been clinically validated on real patients, and the phone app screens are still being built. What is built and measured today is the engine: detector, screening models, private learning and backend."));

C.push(H1("2. How it works"));
C.push(img("architecture"));
C.push(cap("Figure 1: System architecture. Everything that touches personal data happens on the phone; only an optional, protected model update can leave."));
C.push(P("**Tier 1 (used for flags):** an adaptive z-score measures how unusual this cycle is for her; CUSUM adds up small excesses so a slow drift is caught; a rule layer turns the signals that changed into one named flag. **Tier 2 (evaluated):** a small GRU neural network that predicts her next cycle; it was measured and is currently weaker than Tier 1, so it does not raise flags."));
C.push(img("federated"));
C.push(cap("Figure 2: Federated learning in four steps. Raw data stays on each phone; only a clipped, noised update travels."));
C.push(tbl(["Job", "Algorithm used", "Why"], [
  ["Notice a change in her pattern", "Hybrid: adaptive z-score (EWMA) + CUSUM + rule layer", "Sudden jumps + slow creeps + a named pattern"],
  ["Predict next cycle", "GRU (ONNX export)", "Measured; weaker than Tier 1 today"],
  ["Screen from symptoms", "Random forest (8 models compared)", "Near-top everywhere, significant in 2 comparisons"],
  ["Learn across phones", "FedAvg with differential privacy", "Raw logs stay on the phone, stated epsilon"],
], [2400, 3500, 3126]));
C.push(gap());
C.push(H2("Formulas, with every symbol explained"));
[["m(t) = m(t-1) + a (x(t) - m(t-1))", "her running average; x = this cycle's value, a = 0.3"],
 ["z(t) = (x(t) - m(t-1)) / s(t-1)", "how unusual this cycle is for her; s = her usual spread"],
 ["S(t) = max(0, S(t-1) + z(t) - k), flag when S(t) > h", "CUSUM; k = 0.5, h tuned on validation data"],
 ["g_i clipped = g_i x min(1, C / ||g_i||)", "no single person's update can exceed size C"],
 ["g_noisy = (1/B) (sum of clipped g_i + N(0, sigma^2 C^2 I))", "noise on the SUM of clipped updates, then divide by batch size B"],
 ["w_new = sum over phones k of (n_k / n) w_k", "FedAvg: average of phone models weighted by data size"],
 ["P[M(D) in S] <= e^epsilon P[M(D') in S] + delta", "(epsilon, delta) privacy: one person changes any outcome's chance by at most e^epsilon"],
].forEach(([f, d]) => { C.push(new Paragraph({ children: [new TextRun({ text: f, font: "Cambria Math", size: 22 })], spacing: { after: 0 } })); C.push(P(d, { run: { size: 18, color: "52525B" } })); });

C.push(H1("3. Exact input and output"));
C.push(P(`**Input:** one logged cycle (contract 5.3). This is cycle ${D.first_flag_cycle} of Person B, exactly as stored on the phone:`));
code(D.example_in).forEach((p) => C.push(p));
C.push(P("**Output:** what the real Tier 1 detector returned for that cycle (contract 5.2):"));
code(D.example_out).forEach((p) => C.push(p));
C.push(P("**What the user sees:** the app looks up the message key in the backend's wording (it never invents flag text):"));
C.push(note(`**${D.example_msg.title || ""}.** ${D.example_msg.summary || ""} ${D.example_msg.meaning || ""} **${D.example_msg.doctor_consult || ""}**`));
C.push(H2("Backend calls (real server, throwaway database)"));
C.push(tbl(["Call", "Purpose", "Status", "What it proves"], D.backend, [2500, 2400, 900, 3226]));
C.push(gap());
C.push(P("Status 200/201 means accepted; 422 means refused. The refused request tried to send a cycle length along with an anonymous count. The server's reply:"));
code(D.rej_detail).forEach((p) => C.push(p));

C.push(brk());
C.push(H1("4. Worked example: four people, cycle by cycle"));
C.push(img("personas"));
C.push(cap(`Figure 3: The real Tier 1 detector on four simulated people. Shaded band = her own normal (mean plus or minus 2 SD of early cycles). ${D.label}.`));
C.push(tbl(["Person", "Change starts", "First flag", "Matches expected?"], D.summaries, [3200, 1700, 2700, 1426]));
C.push(gap());
C.push(H2("Person B, every cycle"));
C.push(P("Narrative: her first cycles sit inside her own band, so nothing is flagged. Then her cycles lengthen and androgen-type symptoms (acne, hair changes) appear. The detector flags a PCOS-like pattern as soon as a cycle-length signal and a matching symptom signal coincide, and names both."));
C.push(tbl(["Cycle", "Days", "Flow", "Pain", "Symptoms logged", "Detector output", "What changed"], D.walk,
  [650, 650, 850, 700, 2500, 1800, 1876], { size: 16 }));

C.push(H1("5. Data"));
C.push(tbl(["Category", "Dataset", "Size", "Used for"], [
  ["Clinical, tabular (real)", "Kaggle PCOS, 10 Kerala hospitals", `${K.n_pcos} women`, "Symptom-only PCOS model"],
  ["Population survey (real)", "NFHS-5, India", `${K.n_nfhs.toLocaleString("en-IN")} non-pregnant women`, "Anemia (real haemoglobin) and thyroid"],
  ["Real cycle lengths", "FedCycleData", `${K.n_val_w} women, ${K.n_val_c.toLocaleString("en-IN")} cycles`, "Checking the simulator"],
  ["Synthetic", "MyCycle simulator, labeled synthetic", `${K.sim_users.toLocaleString("en-IN")} users, ${K.sim_cycles.toLocaleString("en-IN")} cycles`, "Change detection with known truth"],
  ["Qualitative", "Community interviews", "10 people", "Design only, never training"],
], [2100, 2600, 2100, 2226]));
C.push(gap());
C.push(P("**No cheating:** every hormone lab, ultrasound and haemoglobin column was removed from the symptom-only models; cleaning is learned inside each training fold; thresholds are tuned on validation data and the code refuses to tune on the test set."));
C.push(H2("Is the simulator realistic?"));
C.push(tbl(["Measure", "Real women", "Simulator"], D.val_rows, [4200, 2400, 2426]));
C.push(gap());
C.push(P("The average and the share of unusual cycles match closely; real cycles vary slightly more. This checks normal cycles only; disease-like drifts are stated assumptions."));

C.push(brk());
C.push(H1("6. Results"));
C.push(H2("6.1 Personal-baseline detection (simulated test users)"));
C.push(tbl(["Detector", "PCOS-like", "Anemia-like", "Thyroid-like", "False alarms / 100", "Healthy ever flagged"], D.det_rows,
  [2800, 1000, 1100, 1100, 1500, 1526], { hl: [5], size: 17 }));
C.push(gap());
C.push(P(`Reading: every tuned statistical detector catches nearly all PCOS-like changes. The fixed 21 to 35 day range (what most apps do) is a strong baseline here and raises fewer false alarms per cycle (${f2(K.fix_fa)} vs ${f2(K.hyb_fa)}); the hybrid is better on thyroid-like changes and flags fewer healthy people. The EWMA chart is a credible alternative. Neural networks were clearly weaker.`));
C.push(H2("6.2 Symptom-only PCOS screening (real data)"));
C.push(img("clf"));
C.push(cap(`Figure 4: AUC with 95% bootstrap CI, 8 models x 3 feature sets, kaggle_pcos n=${K.n_pcos}, 5-fold CV x 5 seeds. ${D.label}.`));
C.push(tbl(["Inputs", "Best model", "AUC (95% CI)", "Sens @90% spec", "Spec @90% sens", "Brier"], D.pcos_rows, [2600, 1400, 2000, 1000, 1000, 1026], { hl: [0], size: 17 }));
C.push(gap());
C.push(tbl(["Model (symptoms only)", "AUC", "95% CI", "Sens @90% spec"], D.model_rows, [3000, 1500, 2700, 1826], { size: 17 }));
C.push(gap());
C.push(img("calib", 380));
C.push(cap("Figure 5: Calibration, symptom-only features: predicted risk vs observed PCOS rate."));
C.push(H2("6.3 Anemia and thyroid on NFHS-5 (real survey)"));
C.push(tbl(["Condition", "Features", "Best model", "AUC (95% CI)"], D.nfhs_rows, [3000, 2000, 1700, 2326], { size: 17 }));
C.push(gap());
C.push(P("Anemia from symptoms alone is close to a coin toss (a real negative result): it needs a blood count, which is what the anemia flag recommends. Thyroid is usefully predicted. Models were trained on a 6,000-row stratified sample to fit the compute budget."));
C.push(H2("6.4 Without FL, with FL, with FL plus differential privacy"));
C.push(tbl(["Setting", "Data per phone", "Noise", "Epsilon (delta 1e-5)", "AUC", "Accuracy"], D.fed_rows, [3100, 1200, 800, 1500, 1100, 1326], { size: 17 }));
C.push(gap());
C.push(P(`${D.fed_protocol}. Epsilon computed with the Opacus accountant (our first formula understated it up to 4 times and was replaced).`));
C.push(img("pu", 460));
C.push(cap("Figure 6: Privacy vs usefulness. Smaller epsilon = stronger privacy."));
C.push(img("fc", 520));
C.push(cap("Figure 7: AUC per federated round for each setting."));
C.push(H2("6.5 Neural network and personalization"));
C.push(P(`The GRU caught ${pct(K.gru[0])}, ${pct(K.gru[1])} and ${pct(K.gru[2])} of PCOS-, anemia- and thyroid-like changes, against ${pct(K.hyb[0])}, ${pct(K.hyb[1])} and ${pct(K.hyb[2])} for Tier 1. Fine-tuning it per user:`));
C.push(tbl(["Measure", "Before fine-tuning", "After fine-tuning"], D.pers_rows, [4000, 2500, 2526]));
C.push(gap());
C.push(P("More changes caught, but far more false alarms, so fine-tuning is not used."));

C.push(brk());
C.push(H1("7. Why this, not that: every choice compared honestly"));
C.push(P("WINS = measurably better. TIE = numbers close, chosen for a stated reason. LOSES = tested, lost, not relied on. TRADE-OFF = worse on accuracy, chosen on purpose. MIXED = better on some measures, worse on others. NOT MEASURED = reasoned choice only."));
C.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: [3800, 3526, 1700],
  rows: [new TableRow({ tableHeader: true, children: ["Decision", "We use", "Verdict"].map((h, i) => new TableCell({
    width: { size: [3800, 3526, 1700][i], type: WidthType.DXA }, shading: { type: ShadingType.CLEAR, fill: TEAL, color: "auto" },
    margins: { top: 60, bottom: 60, left: 100, right: 100 }, children: [new Paragraph({ children: [new TextRun({ text: h, bold: true, color: "FFFFFF", size: 18 })] })] })) }),
  ...D.comparisons.map((c) => new TableRow({ children: [c.decision, c.chosen, c.verdict].map((t, i) => new TableCell({
    width: { size: [3800, 3526, 1700][i], type: WidthType.DXA }, margins: { top: 50, bottom: 50, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text: t, size: 18, bold: i === 2, color: i === 2 ? VCOL[t] : undefined })] })] })) }))],
}));
D.comparisons.forEach((c) => {
  C.push(H2(c.decision));
  C.push(new Paragraph({ children: [new TextRun({ text: `${c.verdict}  `, bold: true, color: VCOL[c.verdict] }), new TextRun({ text: "We use: " }), new TextRun({ text: c.chosen, bold: true })], spacing: { after: 100 } }));
  C.push(tbl(c.headers, c.rows, null, { size: 17 }));
  C.push(gap());
  C.push(P(`**In plain words:** ${c.plain}`));
  C.push(P(`**Where we could be wrong:** ${c.caveat}`, { run: { color: "52525B" } }));
});

C.push(brk());
C.push(H1("8. Privacy proof"));
C.push(img("privacy"));
C.push(cap("Figure 8: Live demo slide: the page's own network request count, and the backend refusing a cycle length."));
C.push(P("The demo is a single file that makes zero network requests, measured live by the browser. The backend accepts only allow-listed anonymous counts and returns 422 for anything carrying cycle-log fields. The phone app is designed so that all traffic passes through one counter that refuses such payloads."));

C.push(H1("9. What we claim, and what we do not"));
C.push(H2("We claim"));
[`Symptom-only PCOS screening at AUC ${f3(K.s1)} on real data, with confidence intervals`,
 "A personal-baseline detector tested on a labeled synthetic benchmark whose normal cycles match real data",
 `Federated learning keeps raw data on the phone and recovers most pooled accuracy (${f3(K.avg)} vs ${f3(K.cen)})`,
 "A measured privacy vs accuracy curve with a stated epsilon"].forEach((t) => C.push(B(t)));
C.push(H2("We do not claim"));
["Diagnosis, or clinical validation on real patients", "Real deployment results", "That the neural network beats simple statistics",
 "That we are more accurate than any named app", `Millions of real rows: real data is ${K.n_pcos} + ${K.n_nfhs.toLocaleString("en-IN")} women; the simulator is labeled synthetic`].forEach((t) => C.push(B(t)));
C.push(H2("Limitations and next steps"));
[["Detection tested on simulated people", "a consented clinical validation study"], ["Anemia from symptoms is weak", "keep recommending a blood count"],
 ["Simulator's clinical thresholds are stated assumptions", "verify against Rotterdam, WHO and FIGO sources"],
 ["Phone speed and memory not yet measured", "on-device benchmark (in progress)"], ["Privacy law review not done", "review under India's DPDP Act 2023"]]
  .forEach(([a, b]) => C.push(B(`**${a}:** next step, ${b}.`)));
C.push(H1("10. Reproduce"));
code("python demo/run_demo.py --run-tests      # the smart-board demo\npython demo/make_abstract.py             # this document\npython scripts/check.py                  # tests, language rules, contracts").forEach((p) => C.push(p));

// ---------- document
const doc = new Document({
  creator: "MyCycle team", title: "MyCycle Product Abstract",
  styles: {
    default: { document: { run: { font: "Calibri", size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 32, bold: true, color: TEAL }, paragraph: { outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 25, bold: true, color: "1C1C1C" }, paragraph: { outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "MyCycle product abstract", size: 16, color: "52525B" })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text: `${D.label}  |  page `, size: 15, color: "52525B" }), new TextRun({ children: [PageNumber.CURRENT], size: 15, color: "52525B" })] })] }) },
    children: C,
  }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log(`wrote ${OUT} (${Math.round(buf.length / 1024)} KB)`); });
