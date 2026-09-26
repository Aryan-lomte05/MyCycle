# Context Handoff (read this after CLAUDE.md)

Written Saturday 26 Sep 2026, 19:10 IST, at the end of the planning session. Purpose: any Claude Code or Antigravity session opened in this repo should know everything decided so far without asking. If this file conflicts with `CLAUDE.md`, `CLAUDE.md` wins.

## 1. Situation in five lines

- Course project (216U50P501 Community Engagement Project with Design Thinking, guide Dr. Makarand G. Kulkarni), four students: Aryan Lomte, Liza Patel, Saanj Patil, Aditya Lokhande.
- Goal: an international-conference-style research paper AND a working prototype, domain Healthcare (data-based prediction), SDGs 3, 4, 5.
- Presentation is Monday 28 Sep 2026. Plan: a screen-recorded video of the working prototype with narration over it, plus a statistics and evidence PPT.
- The team has one working day (Saturday evening to Sunday night) using Claude Code and Antigravity.
- The system is a screening aid. It never diagnoses.

## 2. What sir wants (the acceptance criteria that matter)

1. He must approve every claim. So every claim needs evidence (`docs/CLAIMS_EVIDENCE.md`).
2. He wants to see all datasets, listed properly (`data/DATA_REGISTER.md`, including datasets considered and rejected).
3. He wants many models trained and compared, under one fair protocol, with confidence intervals.
4. For every technique chosen he asks: why this one, when the world has many others? He wants a detailed comparison backed by evidence (`docs/TECHNIQUE_COMPARISON.md`, decisions T1 to T12).
5. Order of work: the PPT with proper statistical understanding first, then the prototype. Monday shows the prototype (recorded video) and the statistics.
6. Long-term aspiration from the team: publish the paper, help women worldwide, no monetary motive, community benefit only.

## 3. What the earlier documents claimed that we cannot claim

The two source documents (`docs/source/`) contain statements that are not supported. They are excluded from everything we present unless evidence is produced today.

| Earlier statement | Problem | What we do instead |
|---|---|---|
| "10000x better than Flo", "rules the world" | Unmeasurable, invites the question "measured how?" | Cited feature and method comparison, with an honest row for what Flo does better. Rule 10 in CLAUDE.md. |
| "3.9% accuracy delta federated vs centralized" | No experiment had been run | Report the real delta from our own federated runs, with CIs. |
| "ASHA workers verified high comprehension" | No such testing done | Mark as planned, not yet done. |
| "Increased consultation rate after alerts" | No deployment exists | Remove, or list as future work. |
| "Zero-leak, mathematically private" | DP gives a bounded epsilon, not zero leakage | Say: raw logs never leave the device; shared updates are clipped and noised at a stated epsilon and delta. |
| "Scales to millions", "zero cloud cost" | Unsupported; an aggregation server still exists | Remove or soften. |
| "Validated against known disease patterns" | Kaggle PCOS is one row per woman; cannot validate a per-user baseline over time | Use the synthetic simulator for baseline detection and say so openly. |
| "96% PCOS accuracy" (literature) | That result used 44 features including hormone labs and ultrasound | Our symptom-only accuracy will be lower. Report it honestly with CIs and show the with-labs reference. |
| DP noise formula in the dump: noise N(0, sigma^2 C^2 I) added to the averaged gradient | Looks wrong: the standard DP-SGD form adds it to the sum of clipped gradients, then divides by batch size | Use the standard form, verified against the source paper. |
| Survey percentages from n=5 online and n=5 offline | Tiny qualitative sample | Report counts ("4 of 10"), not percentages with statistical weight. |

## 4. Decisions made, with reasons

1. **Merge the two scopes** (ASHA and low-literacy audio cards, plus partner and family role view) into one product.
2. **Novelty is the process, not "another PCOS classifier"**: (C1) personal-baseline anomaly formulation, (C2) privacy-utility study for cycle data under non-IID clients, (C3) symptom-only screening with honest limits, (C4) systems and equity layer informed by 10 interviews. Federated PCOS papers already exist (FLORA), so federation alone is not novel.
3. **Synthetic cycle simulator** for personal-baseline experiments, calibrated to real cycle statistics, with drift injection for PCOS-like, anemia-like, thyroid-like, plus benign shifts as the false-alarm test. All simulator assumptions cite clinical sources or are marked "assumption".
4. **Datasets**: Kaggle PCOS (symptom-only, labs and ultrasound columns dropped to prevent leakage), NHANES (anemia and thyroid from questionnaire features, lab-defined labels; cut to P1 if slow), a real cycle-length dataset for calibrating the simulator (Marquette/Fehring candidate, must verify), simulator output, interviews (qualitative only).
5. **Tech stack**: Python, PyTorch or Keras (one only), scikit-learn, XGBoost, Flower, own clipped-Gaussian DP validated against an accountant; Next.js PWA with Dexie (IndexedDB); Tier 1 detector in plain TypeScript (guaranteed path), GRU via onnxruntime-web (bonus); TFLite for on-device feasibility numbers; FastAPI and PostgreSQL (aggregate-only).
6. **Screening language everywhere**: "screening flag" or "risk pattern", always "consider consulting a doctor". Enforced by `scripts/lint_language.py`.
7. **Frozen contracts** (CLAUDE.md section 5): results JSON, screening output object, cycle log object, server API. Additive enum changes were already made (fedprox, fedper, ewma, isolation_forest, lstm, cnn1d).
8. **Priority tags**: P0 must exist Monday, P1 should, P2 only if green. Cut P2 first.
9. **Publication reality**: aim at workshop or AI4SG or student tracks, not main-track AAAI or NeurIPS. Venue deadlines were not checked (unknown); search each venue for the 2026-27 cycle and pick one that leaves 4 to 8 weeks after Monday. An ethics or consent statement is required because of the interviews; ask the faculty guide how the institution handles ethics approval.

## 5. Ownership (details in each person's file)

| Person | Owns |
|---|---|
| Aryan | `/sim`, `/exports`, `/results`, technique comparison, README, paper integration. Runs the scientific critical path and the integration. |
| Liza | `/app` (Next.js PWA prototype), `server/routes/family.py`, demo personas in the UI, screen recording |
| Saanj | `/data`, `/ondevice`, dataset register, `docs/papers.csv`, claims table, slide deck assembly, QA and acceptance runs |
| Aditya | `/content`, `/server`, interview synthesis (`docs/INTERVIEWS.md`), education cards and audio, video edit and narration |

## 6. Current state of the repo (as of this handoff)

Done: folder layout, all seven planning docs, results schema and a PLACEHOLDER `results/summary.json`, cycle-log and screening-output schemas, four hand-shaped demo personas plus manifest, one example screening output per flag, `scripts/lint_language.py`, `scripts/validate_contracts.py`, `scripts/check.py` (cross-platform runner), 4 passing contract tests, stub docs (claims table, open questions, changelog, papers.csv header).

Not done: everything else. No simulator, no detectors, no classifiers, no GRU, no federated runs, no app, no server, no content, no datasets downloaded, no slides, no paper text. Every number in `results/summary.json` is a placeholder.

Environment facts: the project lives at `E:\Personal or College Projects\` on a Windows laptop. The project name is MyCycle (decided 26 Sep 2026, 19:10 IST); the folder on disk may still be called `Ritu` and should be renamed to `MyCycle`. Use the name for display text only, never in identifiers that would break if it changes. `make` is probably not installed on Windows; use `python scripts/check.py`. The `Makefile` could not be written by the remote tooling because it is a protected file, so copy it in manually if wanted (the Windows-safe runner is `scripts/check.py`).

The demo personas are crude placeholders. Nothing yet verifies that a detector fires on them.

## 7. Next actions in order (Aryan's critical path)

1. Simulator (`sim/simulator.py`, package A1) with tests per drift type and `sim/ASSUMPTIONS.md`.
2. Detectors (`sim/detectors.py`, A2): fixed threshold, rolling z-score, EWMA, CUSUM, Isolation Forest, rule layer. Thresholds tuned on validation split only.
3. Replace the crude demo personas with simulator-derived ones that provably trigger the intended flags; update `exports/demo_users/manifest.json`.
4. Classifier comparison (A3) once Saanj supplies the Kaggle column list.
5. GRU plus ONNX export plus TypeScript port of Tier 1 with parity tests (A4).
6. Federated and DP experiments (A5), figures and results merge (A7), technique comparison (A6).

## 8. Things that must be verified before they are stated (from memory, not checked)

- That the Marquette/Fehring menstrual cycle dataset exists, its size (roughly 159 women and 1,600 cycles was from memory), and its licence.
- NHANES cycles, file names, variable names and weights.
- The Kaggle PCOS dataset's exact columns, licence and provenance (541 rows, Kerala hospitals, from memory and from the team's literature matrix).
- Every reference in the team's 12-paper literature matrix: open each and confirm the listed finding before citing (`docs/papers.csv`, status VERIFIED only after reading).
- Clinical thresholds used in the simulator (Rotterdam criteria, WHO hemoglobin cut-offs, thyroid and cycle links, FIGO abnormal uterine bleeding).
- Conference deadlines and formats.

## 9. Working preferences of the user (apply to all output)

- Never use em dashes in any written output.
- Direct, opinionated prose over hedged balance. Say plainly when a claim will not survive scrutiny.
- Keep factual specifics (names, quotes, attributions) exactly as supplied.
- Casual, Hinglish-friendly for internal team messages; formal and structured for deliverables.

## 10. Do not

- Invent, hard-code or estimate any metric. Numbers come from scripts that write into `results/`.
- Present simulated or public-dataset results as real deployment results.
- Cite a paper that nobody opened.
- Change a frozen contract without all four people agreeing and a version bump.
- Claim superiority over any named app without a measured experiment.
- Commit raw data, interview names, audio or secrets.

## 11. Source documents

Verbatim originals are in `docs/source/`:

- `activity_docs_master_breakdown.txt`: a synthesis of the course activity documents (empathy research, literature matrix of 12 papers, SCAMPER, design canvases, roadmap).
- `project_dump_for_transfer.txt`: the earlier full project dump (architecture, algorithms, FedAvg and DP specification, interview plan, evaluation plan, paper structure, venues).

They contain unsupported claims (section 3 above). Use them for background only.

## 12. Public-facing feature set (added 26 Sep 2026, about 19:20 IST)

Why: the faculty guide's background is infrared and radio wave technology, not machine learning, and the public audience wants features they can see. So the research core is now paired with visible features. Requirements are FR11 to FR17 in `requirements.md`, copy rules in its section 11, and the method is explained to non-specialists in `project.md` section 11 (signal processing language).

Features: personal-baseline hero chart (FR3), voice logging in Hindi and Marathi (FR11, gated), disguise mode (FR12), live "0 bytes sent" privacy proof with airplane-mode demo (FR13), doctor visit card (FR14), family circle Today card (FR15), local food nudges (FR16), year in cycles (FR17, P2).

Important honesty points decided here:
- Voice logging decision (26 Sep 2026, 19:27 IST): use Whisper running on the device, not a browser or cloud speech service, so audio never leaves the phone. Model files are self-hosted and cached. Each language ships only if it passes an accuracy threshold on recorded test phrases. Marathi is expected to be the weakest.
- Disguise mode is a discretion feature, not strong security, and the app says so.
- The "0 bytes" counter must be measured by `app/lib/netClient.ts`, never hard-coded.
- Comparisons with other apps need a verified public source; otherwise describe only what this app does.

Language: all team communication and documentation is in English.

Privacy wording decision (26 Sep 2026, 19:27 IST): the only approved public sentence is "Your cycle logs stay on your phone. You choose what to share." Do not write "everything stays on your phone", because the family circle sends the cycle phase to a server when the user turns sharing on, and the federated demo sends a noised model update.

## 13. Faculty feedback from the last demo (added 26 Sep 2026, about 19:30 IST)

Sir's handwritten feedback from CEPDT Activity 5 Demo (22/9/2026) is transcribed and tracked in `docs/SIR_FEEDBACK.md`. In short: name the app (MyCycle), use the word "existing" on slide 2, make slides readable (18 pt minimum, no dense tables), caption every figure, explain federated learning, name the algorithm and say what the hybrid is, show data category-wise, rewrite the formulas, and add a table of without FL, with FL and with FL plus DP. The deck plan is now 17 slides (`requirements.md` section 4) with standards in section 12, enforced by `scripts/check_slides.py`.

Formula issue found while reading the feedback: the project dump adds the DP noise to the AVERAGED gradient. The standard DP-SGD form adds noise to the SUM of the clipped gradients before dividing by the batch size. Use the standard form and verify it against the original papers (`aryan.md` A5 and A13).
