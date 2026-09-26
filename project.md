# Project: Privacy-Preserving Personal-Baseline Menstrual Health Screening

Course: 216U50P501 Community Engagement Project with Design Thinking
Faculty guide: Dr. Makarand G. Kulkarni
Team: Aryan Lomte, Liza Patel, Saanj Patil, Aditya Lokhande
SDGs: 3 (Good Health and Well-Being), 4 (Quality Education), 5 (Gender Equality)
Domain: Healthcare, data-based prediction (ML/AI)

## 1. Working title

Personalized Menstrual Health Anomaly Screening via Privacy-Preserving On-Device and Federated Learning, with Regional-Language Health Literacy Support

Paper title direction: "Federated Personal-Baseline Learning for Privacy-Preserving Menstrual Health Anomaly Screening"

Index terms: federated learning, differential privacy, menstrual health, anomaly detection, on-device machine learning, PCOS screening, health literacy

## 2. The problem in plain words

Menstrual disorders such as PCOS, iron-deficiency anemia and thyroid dysfunction are frequently found late, especially where lab tests and ultrasound are unaffordable or far away, where symptoms are dismissed as "just stress", and where people fear that intimate health data will leak. Four barriers stack on top of each other:

1. Clinical: labs (AMH, LH, FSH, TSH, hemoglobin) and ultrasound are costly and not always reachable.
2. Information: myths fill the gap and there is little reliable, local-language content.
3. Privacy: mainstream cycle apps centralize highly sensitive reproductive data on company servers.
4. Cultural: taboo and shame stop people discussing symptoms, even inside families.

## 3. The research gap

Published PCOS ML work mostly uses hospital datasets with lab and ultrasound features, trains one population-level classifier, and pools data centrally. Federated PCOS work exists (for example FLORA in our literature matrix), so "federated PCOS" alone is not our novelty.

Our contribution is a process contribution:

- **C1. Personal-baseline formulation.** "Abnormal" is defined relative to the user's own history (rolling statistics, changepoint detection, small sequence model), not a population cutoff. We measure detection rate, detection delay and false alarms against a fixed-threshold baseline on a documented simulator.
- **C2. Privacy-utility study for this data type.** We measure, under non-IID clients, how much accuracy federation costs and how much additional accuracy differential privacy costs, with a stated epsilon and delta.
- **C3. Symptom-only screening with honest limits.** We report how much performance is lost when lab and ultrasound features are removed, with confidence intervals, and we state the limit plainly.
- **C4. Systems and equity layer.** A working prototype with on-device inference, role-restricted family view, and regional-language audio myth-correction cards, informed by 10 community interviews.

What we do not claim: clinical validation, diagnosis, real-world deployment results, superiority over commercial apps on accuracy.

## 4. System overview

```
[Phone / PWA]
  Local log store (IndexedDB / SQLite)
  Tier 1: rolling z-score + CUSUM per feature      (works from cycle 1, gets stable by ~3)
  Tier 2: small GRU next-cycle predictor           (population-pretrained, locally fine-tuned)
  Rule layer: signals -> screening flag mapping
  UI: flag + non-alarming explanation + audio myth card
  Family view: phase + education only
        |
        |  periodically: DP-noised model update only
        v
[Federated server: Flower + FastAPI wrapper]
  FedAvg aggregation of clipped, noised updates
  PostgreSQL: aggregate metrics only
        |
        v
  Improved global model returned to devices
```

### 4.1 Tier 1 statistical baseline
For each user and each feature (cycle length, flow, pain, symptom composite), keep an exponentially weighted mean and standard deviation over that user's past cycles. Deviation score is a z-score. A one-sided CUSUM on the standardized series catches sustained drift. Flag when |z| exceeds the threshold or CUSUM exceeds its limit. Thresholds are tuned on the simulator's validation split, never the test split.

### 4.2 Tier 2 sequence model
GRU with 16 to 32 hidden units predicting the next cycle's feature vector from the previous cycles. Anomaly score is normalized prediction error. Pretrained on population simulator data, then personalized on-device by fine-tuning the last layer(s).

### 4.3 Flag mapping
A layered rule plus score approach maps contributing signals to pattern flags. The rules are drafted from published clinical criteria and refined with gynecologist input from the interviews. Flags are always screening language.

- irregularity: cycle length or variability outside personal baseline
- pcos_pattern: sustained long or skipped cycles plus androgen-related symptoms (acne, excess hair, hair loss)
- anemia_pattern: heavy flow plus fatigue, dizziness, pallor
- thyroid_pattern: cycle change in either direction plus fatigue, weight change, mood symptoms

### 4.4 Federated learning with DP
Flower simulation with 8 to 10 non-IID clients. Each client trains locally, clips per-example gradients to L2 norm C, adds Gaussian noise with multiplier sigma, and returns the update. The server runs FedAvg weighted by client sample count. Epsilon is computed with an accountant at fixed delta (1e-5). Four conditions are compared: centralized, centralized personalized, FedAvg without DP, FedAvg with DP at several sigma values.

### 4.5 Literacy layer
Icon-forward cards with audio in English, Hindi and Marathi. Each flag links to a card that corrects a specific myth (for example "irregular periods are only stress") without shaming. Content is reviewed by the gynecologist interviewees where possible.

### 4.6 Family and partner sharing
Roles: self, partner, parent, sibling. Sharing is opt-in by the user and revocable. Companions see cycle phase, general support tips and education. They never see raw logs or flags unless the user explicitly shares a flag (P2 feature).

### 4.7 Public-facing features

Beyond the research core, the prototype carries features a non-technical audience can see: the personal-baseline hero chart (FR3), voice logging in Hindi and Marathi with an on-device Whisper model (FR11, per-language accuracy gate), disguise mode for shared phones (FR12), a live "0 bytes sent" privacy proof with an airplane-mode demo (FR13), a family circle with a daily Today card (FR15), a doctor visit card generated on the device (FR14), local food nudges (FR16) and a year-in-cycles summary (FR17, P2). Requirements are in `requirements.md`. The threat model behind FR12 and FR13 covers the household as well as the server, because for many users the privacy risk is someone who can pick up the phone.

## 5. Datasets (details in `data/DATA_REGISTER.md`)

| ID | Purpose | Notes |
|---|---|---|
| kaggle_pcos | PCOS symptom-only classifier and federated experiment | 541 rows, hospital-derived, labels come from clinical assessment. Lab and ultrasound columns are removed to prevent leakage. Verify column list and licence on download. |
| nhanes | Anemia and thyroid screening from questionnaire and basic features, lab-defined labels | US survey. Variable names change across cycles. Must handle survey design and sample weights. Verify files used. |
| cycle_calibration | Real cycle-length variability used to calibrate simulator parameters | Candidate: Marquette / Fehring menstrual cycle data. Verify existence, size and licence before use. |
| simulator | Personal-baseline detection experiments | Fully synthetic, generated by `sim/`. Clearly labeled synthetic. |
| interviews | Qualitative evidence for motivation, content design and flag wording | Not used for model training. Anonymized. |

Important honesty point: the Kaggle PCOS set has one row per woman, so it cannot test a per-user baseline over time. The simulator exists for that reason. The simulator's drift patterns encode our assumptions from clinical literature, so simulator results show that the detector works under those assumptions, not that it works on real patients. The paper says so.

## 6. Evaluation plan

1. **Classifier comparison** (kaggle_pcos, nhanes): LR, RF, XGBoost, SVM, MLP, plus stated exclusions of other families. Stratified 5-fold CV repeated with 5 seeds, patient-level splits, bootstrap confidence intervals. Metrics: AUC, sensitivity at 90 percent specificity, specificity at 90 percent sensitivity, Brier score, calibration curve.
2. **Feature ablation:** symptom-only vs symptom plus basic vitals vs with-labs (upper reference only, not deployable).
3. **Personal baseline detection** (simulator): fixed threshold, z-score, CUSUM, GRU. Metrics: detection rate, median detection delay in cycles, false alarms per 100 cycles, per drift type, including benign one-off shifts.
4. **Federated study:** centralized vs FedAvg vs FedAvg+DP, IID vs non-IID, several sigma values, epsilon reported. Curves of metric vs round and metric vs epsilon.
5. **On-device feasibility:** model size, latency p50 and p95, memory, and Python-vs-device output parity.
6. **Technique comparison:** for every method choice, a documented comparison (see `requirements.md` section 5).
7. **Qualitative:** interview themes and their mapping to design decisions.

## 7. Positioning against existing apps

Presented as a feature and method comparison using cited public sources, never as an accuracy claim. Dimensions: baseline type (personal vs population), where raw data lives, whether labs are required, family role model, regional-language audio, open source, monetization model. The honest differentiators are personal baselines, on-device raw data, no ads, no monetization and open methodology. Established apps have far larger user bases and content teams and we say so.

## 8. Ethics and compliance

- Interview consent script and anonymization documented in `docs/INTERVIEWS.md`.
- Ask the faculty guide today how the institution handles ethics approval for interview-based work and record the answer. Many venues require an ethics statement.
- The app is a screening aid, not a medical device claim. Future work section discusses India's DPDP Act 2023 and medical device software regulation. Do not state legal conclusions, only that review is needed.
- No real user health data is collected in this phase.

## 9. Timeline (Saturday 26 Sep 2026 to Monday 28 Sep 2026)

| When | Milestone |
|---|---|
| Sat 21:00 | Contracts frozen, repo scaffolded, datasets downloaded, demo users v0 exported |
| Sat night | Simulator and Tier 1 done, classifier pipeline running |
| Sun 10:00 | First full `results/summary.json`, figures v0, prototype screens wired to mock results |
| Sun 15:00 | GRU, federated and DP results, technique comparison drafted, prototype uses real exports |
| Sun 19:00 | Slides complete, prototype frozen, screen recording |
| Sun 22:00 | Narration recorded, video edited, claims-evidence table complete, rehearsal with hard questions |
| Mon | Present |

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Symptom-only accuracy is modest | Report honestly with CIs, show ablation vs labs, frame as screening |
| Simulator seen as circular | State assumptions, cite the criteria they come from, validate marginals against the real cycle dataset |
| Small PCOS set overfits | Patient-level CV, repeated seeds, no tuning on test folds, report spread |
| DP hurts accuracy too much | Show the whole curve, choose an operating point openly |
| Time | P0, P1, P2 tagging, cut P2 first |
| Browser inference problems | Tier 1 in plain TypeScript is the guaranteed fallback, GRU is a bonus |
| Unverified citations | Citation rule in CLAUDE.md, `UNVERIFIED` status |
| On-device Whisper is too slow or too inaccurate, especially for Marathi | Time-box 2 hours, smallest workable model, per-language accuracy threshold, disable failing languages, icon logging is the guaranteed path |
| Disguise mode mistaken for strong security | The UI and paper state it is a discretion feature, not protection against a determined person with device access |
| Too many features, none finished | P0, P1, P2 tags. Voice logging and year-in-cycles are cut first |

## 11. Explaining the method to non-machine-learning reviewers

The faculty guide's background is in infrared and radio wave technology, so the method is best explained as signal processing:

- A cycle history is a signal. The personal baseline is the expected level of that signal for one person, and the band around it is the normal noise.
- Detecting a change is change detection on a sensor stream: a z-score against the baseline, and CUSUM to catch a slow drift, the same family of methods used to spot a shift in a measured signal.
- The privacy noise is added on purpose: before an update leaves the phone, we clip its size and add random noise so the original signal cannot be reconstructed, while the average over many phones still carries the useful pattern.
- The simulator plays the role of a test signal generator: we inject known drifts and measure how quickly and how reliably the detector finds them.
