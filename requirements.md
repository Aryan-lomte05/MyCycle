# Requirements and Deliverables

Read `CLAUDE.md` and `project.md` first. This file lists what must exist, who owns it, and how we know it is done.

## 1. Deliverables overview

| # | Deliverable | Owner | Priority | Path |
|---|---|---|---|---|
| D1 | Statistics and evidence PPT | Saanj assembles, all contribute slides | P0 | `docs/slides/` |
| D2 | Working prototype (PWA) | Liza builds, Aryan supplies models | P0 | `app/` |
| D3 | Prototype demo video with narration | Liza records, Aditya edits, all narrate | P0 | `docs/video/` |
| D4 | Datasets register | Saanj | P0 | `data/DATA_REGISTER.md` |
| D5 | Technique comparison document | Aryan writes, Saanj gathers evidence | P0 | `docs/TECHNIQUE_COMPARISON.md` |
| D6 | Results, figures, reproducible pipeline | Aryan | P0 | `results/`, `sim/` |
| D7 | Claims-evidence table | Saanj maintains, all feed | P0 | `docs/CLAIMS_EVIDENCE.md` |
| D8 | Research paper (IEEE format) | Aryan integrates, all write sections | P1 | `docs/paper/` |
| D9 | Education content in en, hi, mr | Aditya | P0 | `content/` |
| D10 | Backend API | Aditya (family routes: Liza) | P1 | `server/` |
| D11 | On-device feasibility numbers | Saanj | P1 | `results/ondevice.json` |
| D12 | Interview synthesis | Aditya | P0 | `docs/INTERVIEWS.md` |
| D13 | README with one-command reproduction | Aryan | P0 | `README.md` |

## 2. Functional requirements for the prototype (D2)

The prototype is what Monday is judged on. It must run in a browser on a laptop and be installable as a PWA on a phone. It must work offline after first load.

**FR1 Onboarding.** Language choice (en, hi, mr), privacy explanation in one screen ("Your cycle logs stay on your phone. You choose what to share."), role choice (self or companion), no account, no email, no phone number.

**FR2 Logging.** Log a cycle: start date, length, flow (0-3), pain (0-10), eight symptoms (0-3). Icon plus text labels. Editable. Stored only in IndexedDB.

**FR3 Personal baseline view.** Chart of the user's cycle length over time with the personal band (mean plus or minus 2 SD) and the current cycle marked. Explanation text in plain language. This is the hero visual of the video and poster: the band, the marker, and the line "Built around your own normal".

**FR4 Screening flag.** After each new cycle, the on-device detector runs and shows one of the five flag types with a calm explanation, the contributing signals in plain words, and "consider consulting a doctor". Never diagnostic wording. Simulated badge visible in demo mode.

**FR5 Audio myth card.** Each flag opens a card with an icon-led explanation and an audio player in the selected language, with transcript.

**FR6 Privacy panel.** A screen showing what is stored (local only), what would be shared (DP-noised model update only, off by default), and a delete-all button. A "federated round" demo button that shows the size of the update and the noise added, without sending raw data. Extended by FR13.

**FR7 Family view.** Invite code flow between two browser profiles. Companion sees phase and education only, per the visibility matrix in `liza.md`. User can revoke.

**FR8 Reminders.** Upcoming period estimate and hydration/iron-rich-food style education nudges from server rules, shown in-app (no push in P0).

**FR9 Demo mode.** Four demo personas loaded from `/exports/demo_users/`: regular, pcos_pattern, anemia_pattern, thyroid_pattern. Adding the next cycle for a persona visibly triggers the correct flag. This is the core of the video.

**FR10 Results page.** A "Evidence" screen reading `results/summary.json` and showing the key charts (model comparison, privacy-utility curve, detection delay) with the simulated label.

### Public-facing features (added 26 Sep 2026)

These are the features a non-technical audience can see and understand. Priorities: P0 must exist Monday, P1 should, P2 only if everything else is green. Each one needs a row in `docs/CLAIMS_EVIDENCE.md` for anything it claims.

**FR11 Voice logging (P1, on-device Whisper).** Mic button on the log screen. The user says a short phrase in English, Hindi or Marathi, for example "period started today, pain is high". Speech is transcribed by a Whisper model running inside the browser (transformers.js or a WebAssembly build of whisper.cpp), so audio never leaves the device. A rule-based parser (keyword and number dictionary from `content/{lang}/voice_phrases.json`, no language model) turns the transcript into log fields, and the user confirms on a review screen before anything is saved. Icon logging always remains available.

Model handling: choose the smallest model that works (start with tiny, try base) by testing 10 recorded phrases per language and counting how many are parsed into the correct fields. A language ships only if the team's threshold is met (default 80 percent of test phrases parsed correctly); otherwise that language is disabled and the app says so. Model files are self-hosted in `app/public/models/` (gitignored, fetched once by a documented script), never loaded from a third-party site at run time, cached by the service worker so voice works offline, and fetched through `netClient` as a `content` request. Audio is processed in memory and never stored. The 0 bytes counter must stay at 0 for user data while voice is used. Accuracy is expected to be weaker for Marathi than for Hindi or English, and the results (pass rate per language) go into the claims table, not into marketing copy.

**FR12 Disguise mode (P1).** Optional. When on, the app opens as a working calculator. A PIN (4 to 6 digits, stored only as a salted PBKDF2 hash in local storage) opens the real app. A quick-hide button returns to the calculator in one tap. The name shown in app switchers stays neutral and no notification contains health text. Honest limit: this is a discretion feature against casual snooping, not protection against a determined person with full access to the device, and the UI says so.

**FR13 Privacy proof (P0, extends FR6).** A live panel showing "Your data sent to our servers: 0 bytes" and a request log. All network access goes through `app/lib/netClient.ts`, which counts requests and bytes, tags each one as content fetch or model update, and throws if a payload contains any field from the cycle log contract. Content fetches (cards, messages, reminder rules, model files) are listed separately and carry no user data. If family sharing is switched on, the phase that is shared appears as its own labeled line, for example "Shared with your circle: phase only", so the counter never hides anything. The federated round demo appears as a labeled model update with its real size in KB. Video scene: turn on airplane mode, keep logging, show the counter unchanged. The counter is measured, never hard-coded, and a vitest fails the build if any `fetch`, `XMLHttpRequest`, `sendBeacon` or `WebSocket` call exists outside `netClient.ts`.

**FR14 Doctor visit card (P1).** One tap creates a one-page summary generated on the device: personal baseline (mean and range of cycle length), recent cycles chart, flags with dates in screening wording, symptom summary, and the footer "Screening summary from a self-tracking app, not a medical record. Please consult a doctor." The user chooses what to include before it is generated. Output uses the browser print-to-PDF (no extra library) plus an optional QR code carrying a compact JSON summary under about 500 bytes. Nothing is uploaded.

**FR15 Family circle (P0 for the Today card, P1 for learning cards; extends FR7).** The companion home shows a Today card driven only by the cycle phase, with a short supportive tip such as "Today may be a low-energy day. Offer rest, a warm drink, or take over one chore." It never shows any log data. Learning cards for partner, parent, brother or son and teacher come from cards 8 to 10 in `aditya.md`. Wording is neutral about gender roles and reviewed by the gynecologist interviewees where possible.

**FR16 Local food nudges (P1).** Reminder and card content that suggests regional, iron-rich and comfort foods by language (for example jaggery, ragi, leafy greens), linked to card 4 and the reminder rules. Each suggestion has a recorded source in `content/SOURCES.md`. Nudges are education, not treatment.

**FR17 Year in cycles (P2).** Local summary cards (average cycle length, most regular month, symptom trends) that the user can save as an image. Never uploaded, and no share button to third-party apps.

## 3. Non-functional requirements

- Loads under 3 seconds on a mid-range laptop, detector inference under 100 ms per cycle in the browser.
- Works offline (service worker).
- Accessibility per `CLAUDE.md` section 6.
- No network request contains log data. Verify in browser network tab and include a screenshot in the evidence folder.
- Reproducibility: fresh clone, `make all`, produces every figure and table in the slides and paper.

## 4. Statistics deliverable (D1): slide requirements

The deck is a statistical and evidence walkthrough. Every slide title states a finding or a decision, not a topic. Every chart states n, metric, CI method and the simulated label where relevant.

Order (17 slides, updated after faculty feedback, see `docs/SIR_FEEDBACK.md`):

1. Title with the name MyCycle, then the problem and four barriers (with interview evidence, anonymized quotes)
2. Existing systems and the gap, then our four contributions (the slide uses the word "existing")
3. Federated learning explained in plain language (diagram: train on the phone, send only a protected update, average, send the better model back)
4. Data used, grouped by category (clinical tabular, population survey, real cycle data, synthetic, qualitative), with the leakage-removal table
5. Preprocessing and split protocol (patient-level, seeds, CV design)
6. Algorithms used, every one named, and what the hybrid combines
7. Formulas, typeset, with every symbol defined
8. Classifier comparison with confidence intervals, symptom-only vs with-labs reference
9. Technique comparison summary: for each decision, what we chose, alternatives considered, evidence (one slide per major decision, matrix format)
10. Personal baseline detection results vs fixed threshold, by drift type, including false alarm rate
11. Without federated learning, with federated learning, and with federated learning plus differential privacy: one table generated from `results/`, plus the training curves
12. Privacy-utility curve with epsilon and delta stated
13. On-device feasibility table
14. Prototype architecture and screenshots
15. Feature and method comparison with existing apps (cited sources only)
16. Limitations, ethics, and future work (clinical validation, DPDP Act review, real deployment)
17. Claims-evidence summary slide

Owners: slides 1-3 and 15-16 Aditya (slide 3 text is checked for accuracy by Aryan). Slides 4-5, 13 and 17 Saanj. Slides 6-7 Aryan writes the content and Saanj places it. Slides 8-12 Aryan supplies figures, tables and one-paragraph speaker notes, Saanj places them. Slide 14 Liza. Saanj does final consistency and formatting and runs `python scripts/check_slides.py` on the exported deck.

## 5. Technique comparison requirement (D5)

Sir will ask why each technique was chosen over the alternatives. `docs/TECHNIQUE_COMPARISON.md` answers that for every decision, with evidence, in a fixed format.

### 5.1 Decisions that must be covered

| ID | Decision | Candidates that must appear |
|---|---|---|
| T1 | Symptom-only PCOS/anemia/thyroid classifier | Logistic regression, random forest, gradient boosting (XGBoost, LightGBM), SVM, MLP, naive Bayes, k-NN, TabNet or FT-Transformer (discuss only), deep image models on ultrasound (excluded) |
| T2 | Personal anomaly detector | Fixed population threshold, rolling z-score, EWMA control chart, CUSUM, Bayesian online changepoint, Isolation Forest, One-Class SVM, autoencoder, GRU/LSTM predictor, transformer (discuss only) |
| T3 | Sequence model for Tier 2 | GRU, LSTM, 1D CNN, small transformer, ARIMA or exponential smoothing |
| T4 | Learning setting | Centralized, federated, split learning, purely local, gossip or peer-to-peer |
| T5 | Federated algorithm | FedAvg, FedProx, SCAFFOLD, FedAdam, personalized variants (FedPer, Ditto) |
| T6 | Privacy mechanism | None, DP-SGD (clipped Gaussian), local DP, secure aggregation, homomorphic encryption, k-anonymity style aggregation |
| T7 | FL framework | Flower, TensorFlow Federated, PySyft, FedML, NVFlare |
| T8 | On-device runtime | TFLite, ONNX Runtime (mobile and web), PyTorch Mobile or ExecuTorch, Core ML, TF.js |
| T9 | Personalization method | Last-layer fine-tuning, full fine-tuning, per-user statistical baseline only, meta-learning (MAML), multi-task heads |
| T10 | Class imbalance and missing data | None, class weights, SMOTE, undersampling; mean, median, iterative, kNN imputation |
| T11 | App platform | PWA, React Native, Flutter, native |
| T12 | Data source choices | Each dataset in the register versus alternatives found and rejected, with reason |

### 5.2 Required format per decision

```
## T#: Decision title
Context: one paragraph.
Criteria (weights sum to 1): e.g. accuracy on our data 0.3, works without labs 0.2, on-device size 0.15, privacy compatibility 0.15, interpretability 0.1, maturity and licence 0.1
Candidates table: candidate | how evaluated (ran / cited / excluded) | key numbers or facts | evidence link | verdict
Chosen: X
Why X: 3 to 5 sentences referencing the table.
Why not the others: one line each, with the disqualifying criterion.
Evidence: experiment id in results/ or verified citation id in papers.csv
Confidence and caveat: where this choice could be wrong.
```

### 5.3 Evidence rules

- "Ran" means we trained and evaluated it under the shared protocol in `results/`. Target: run at least 6 candidates for T1, 5 for T2, 3 for T3, 3 for T5 (FedAvg, FedProx, one personalized), DP at 5 sigma values.
- "Cited" means a specific finding from a source that a team member opened and read, recorded in `docs/papers.csv` with a page or section reference.
- "Excluded" means removed by a stated hard constraint (needs labs, needs image hardware, cannot run on device, licence, immaturity) with a source for the constraint.
- Nobody claims to have compared "100 techniques". We compare the candidates that matter, run the ones we can under one protocol, and justify exclusion of the rest explicitly.
- A weight table without a sensitivity check is weak. Include a one-line check: does the winner change if weights shift by 20 percent.

## 6. Dataset register requirement (D4)

`data/DATA_REGISTER.md` has one section per dataset with these fields: id, name, source URL, access date, licence and terms, file names and SHA-256 checksums, rows, columns kept, columns dropped and why, label definition, missing data summary, known biases and limitations, preprocessing steps in order, script that produces the processed file, what it is used for, which results depend on it. It also lists datasets considered and rejected, with reasons. No dataset is used before it has a complete entry.

## 7. Paper requirement (D8)

IEEE conference format, two columns, 10 pt Times, numbered figures and tables, at least 20 verified references. Sections and writers:

| Section | Writer |
|---|---|
| Abstract (last), Introduction, Related Work | Aryan |
| Datasets and Preprocessing | Saanj |
| Methodology: System and UX | Liza |
| Methodology: Personal-baseline model, Federated and DP protocol | Aryan |
| Methodology: On-device implementation | Saanj |
| Community Study (interviews) and Content design | Aditya |
| Results | Aryan (numbers), Aditya (prose draft) |
| Discussion, Limitations, Ethics | Aditya, reviewed by Aryan |
| Conclusion and Future Work | Aryan |

Every results paragraph states "simulated / preliminary, public and synthetic data, not real deployment data". Aryan runs the final consistency pass.

## 8. Video requirement (D3)

3 to 5 minutes. Screen recording of the prototype, narration recorded separately.

Storyboard (about 4 min 50 s): (1) problem in 20 s, (2) onboarding and privacy promise in 25 s, (3) your own normal: regular persona and the baseline band in 30 s, (4) voice logging in 25 s (skip if FR11 is cut), (5) pcos_pattern persona triggers the flag and audio card, with quick cuts to anemia and thyroid, in 50 s, (6) airplane mode on, logging continues, the 0 bytes counter, federated round demo in 30 s, (7) disguise mode in 20 s, (8) family circle Today card in 25 s, (9) doctor visit card in 20 s, (10) evidence screen with key charts in 25 s, (11) limitations and next steps in 20 s.

## 9. Acceptance test (run Sunday 19:00)

1. Fresh clone, `make all` succeeds and regenerates `results/summary.json` and all figures.
2. `make check` green (tests, language lint, contract validation).
3. Each demo persona produces the intended flag in the app.
4. Network tab shows no request containing log data.
5. Every number on every slide has a row in `docs/CLAIMS_EVIDENCE.md`.
6. Every citation in the paper and slides is `VERIFIED` in `docs/papers.csv`.
7. Grep for "diagnos" in `app/`, `content/`, `docs/slides/`, `docs/paper/` returns only allowed contexts (describing clinicians, or negations such as "not a diagnosis").
8. Rehearsal: each member answers three hard questions from another member and the answers are checked against the claims table.
9. Airplane-mode test: with the network off, logging, detection, flags and cards still work and the privacy counter is unchanged.
10. netClient test: a payload containing any cycle-log field is rejected, and grep finds no network call outside `app/lib/netClient.ts`.
11. Disguise mode: opens as a calculator, the correct PIN opens the app, a wrong PIN does not, quick-hide works, and the honest-limit note is visible.
12. Doctor visit card fits one printed page, contains the screening footer, and includes only the fields the user selected.
13. Public-facing copy check: every line on the poster, slides and video captions passes section 11.
14. Voice logging: with the network off, a spoken phrase in each shipped language fills the log form correctly and needs confirmation before saving; no audio is stored; the pass rate per language is recorded in `docs/ACCEPTANCE_LOG.md`.
15. Slide standards: `python scripts/check_slides.py` passes on the exported final deck (fonts, captions, required words).
16. Faculty feedback: every row of `docs/SIR_FEEDBACK.md` is ticked by a second person.

## 10. Rule for the claims-evidence table (D7)

Columns: claim id, exact claim text, where it appears (slide or section), type (measured, cited, interview, design decision), evidence pointer (results key, papers.csv id, interview code), status (supported, needs work, remove), owner. Any claim with status other than "supported" is removed or rewritten before Monday.

## 11. Public-facing copy rules (poster, slides, video captions, app store style text)

The audience includes people who are not machine learning specialists, so copy must be short and must also survive a hard question.

| Use | Never use |
|---|---|
| "Built around your own normal" | "world's best", "best in the world", "rules the world" |
| "Your cycle logs stay on your phone. You choose what to share." | "Everything stays on your phone", "100% private", "zero leaks", "unhackable" |
| "A screening flag, with a suggestion to consult a doctor" | "detects PCOS", "diagnoses", "AI doctor", "clinically proven" |
| "Works without internet or an account" | "better than" or "beats" any named app |
| "For the whole family" | Any accuracy number that is not in `results/` |

Rules:
- The privacy sentence is exactly "Your cycle logs stay on your phone. You choose what to share." It is accurate because logs never leave the device, while the family circle shares only the cycle phase and only when the user turns it on, and the federated demo sends only a clipped, noised model update. Do not shorten it to "everything stays on your phone".
- A comparison with another app needs a verified public source in `docs/papers.csv`. Without one, describe what this app does and stop.
- Every claim on a poster or slide has a row in `docs/CLAIMS_EVIDENCE.md`.
- Everything simulated carries the standard simulated label.

## 12. Slide standards (from faculty feedback)

These come straight from the demo feedback in `docs/SIR_FEEDBACK.md` and are checked by `scripts/check_slides.py`.

- **Fonts:** 18 pt minimum for all text including table cells and chart labels. Captions and source lines 14 pt minimum. Titles 32 pt or larger. Footers and slide numbers are exempt at 12 pt.
- **Density:** about 60 words of body text at most per slide (excluding tables and captions). Tables have at most 6 data rows and 4 columns; split or move the rest to an appendix. The literature matrix is an appendix.
- **Captions:** every figure, chart and table has a numbered caption below it in the form "Fig. N: ..." or "Table N: ...", stating what it shows, the dataset, n, the metric and CI method, and the simulated label where relevant. Decorative images are named with the prefix "decor" and are exempt.
- **Equations:** typeset with the equation editor or rendered from LaTeX at high resolution. Never typed as plain text. Every symbol is defined on the same slide. One idea per equation.
- **Wording:** the gap slide says "existing systems" and "existing apps". The title slide and every footer carry the name MyCycle. Algorithms are always named ("FedAvg with differential privacy"), never "our model". If a method is a hybrid, the slide says what it is a hybrid of.
- **Contrast:** dark text on a light background or the reverse. No light grey on white and no text over images.
- **Export:** the deck must be exported as `.pptx` into `docs/slides/` so the automatic check can run. If it is built in another tool, export first, then check.
