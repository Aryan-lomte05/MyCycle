# CLAUDE.md

Read this file first, every session, before writing any code. It applies to every team member and every Claude Code session in this repo. If a task file (aryan.md, liza.md, saanj.md, aditya.md) conflicts with this file, this file wins.

## 1. What this repo is

MyCycle: a privacy-preserving menstrual health screening system: a research paper plus a working prototype for the course 216U50P501 Community Engagement Project with Design Thinking (guide: Dr. Makarand G. Kulkarni). Full description in `project.md`. Deliverables and acceptance criteria in `requirements.md`.

One-line pitch: per-user baseline anomaly screening for PCOS, anemia and thyroid patterns from symptoms only (no labs), trained with on-device personalization and federated learning with differential privacy, delivered with role-aware family sharing and regional-language audio education.

## 2. Non-negotiable rules (violations block merge)

1. **Never write the word "diagnosis", "diagnose", or "diagnostic" as something the system does.** The system produces a "screening flag" or "risk pattern" and always says "consider consulting a doctor". Describing what doctors do is allowed. Enforced by `scripts/lint_language.py`.
2. **Label all simulated results as simulated.** Every figure, table, slide, JSON and UI screen that derives from synthetic or public-dataset experiments must carry the label "Simulated / preliminary, public and synthetic data, not real deployment data". The results JSON has `meta.simulated = true`. The UI shows a visible badge.
3. **Raw cycle or symptom logs never leave the device in the federated design.** Only DP-noised model updates are transmitted. No server endpoint may accept raw per-user logs. No analytics SDKs. No third-party trackers.
4. **Family and partner views never show raw symptom logs.** They show cycle phase and education content only, as defined in the visibility matrix in `liza.md`.
5. **No unsupported claim.** Every numeric or comparative claim in the paper, slides, UI copy or README must have an entry in `docs/CLAIMS_EVIDENCE.md` pointing to a results file, a verified citation or an interview code. No entry, no claim.
6. **No fabricated citations.** A reference enters `docs/papers.csv` only after someone opened the source and read the relevant part. Unread items are marked `UNVERIFIED` and may not be cited in the paper or slides.
7. **No fabricated results.** Never hard-code a metric. Numbers come from `results/` files produced by scripts. Fixed seeds, reproducible with one command.
8. **No real personal data in the repo.** Interview material is anonymized (codes like P01) before it is committed. Raw notes, audio and names stay off the repo.
9. **Never use em dashes in any written output** (docs, UI copy, paper text, commit messages). Use commas, colons or hyphens.
10. **Never claim the system is "better than", "beats", or "outperforms" any named product** unless a measured experiment in this repo shows it on a stated metric. Comparisons with commercial apps are feature and method comparisons with cited public sources.
11. **Public-facing copy follows `requirements.md` section 11.** No "world's best", "100% private", "detects PCOS", "clinically proven", and no comparison with another app without a verified source. Enforced in user-facing folders by `scripts/lint_language.py`.
12. **All network access in the app goes through `app/lib/netClient.ts`.** It counts requests and bytes and refuses any payload containing cycle-log fields. No other file may call `fetch`, `XMLHttpRequest`, `sendBeacon` or `WebSocket`.
13. **Slides follow `requirements.md` section 12** (18 pt minimum, numbered captions on every figure and table, typeset formulas, named algorithms) and must pass `python scripts/check_slides.py` before they are shown. The faculty feedback list is in `docs/SIR_FEEDBACK.md`.

## 3. Repo layout and owners

```
/sim            Aryan     synthetic simulator, datasets loaders, all model training, federated + DP
/exports        Aryan     model files handed to others (ONNX, TFLite, TS detector). Versioned.
/results        Aryan     generated results and figures (contract in section 5). Never hand-edited.
/ondevice       Saanj     TFLite conversion checks, latency/size/memory benchmarks
/data           Saanj     download scripts, checksums, DATA_REGISTER. Raw data is gitignored.
/app            Liza      Next.js PWA prototype
/server         Aditya    FastAPI: content, reminders, aggregate metrics (Liza owns routes/family.py)
/content        Aditya    education cards and UI strings in en, hi, mr (JSON)
/docs           shared    paper, slides, CLAIMS_EVIDENCE.md, TECHNIQUE_COMPARISON.md, papers.csv, INTERVIEWS.md
/scripts        shared    lint_language.py, make targets
```

Do not edit files inside another person's folder. Open an issue or message the owner. Exception: fixing a typo in a shared doc.

## 4. Tech stack (fixed, do not swap without a written decision in TECHNIQUE_COMPARISON.md)

| Layer | Choice |
|---|---|
| ML training | Python 3.11, PyTorch or Keras (Aryan decides, one only), scikit-learn, XGBoost |
| Federated | Flower (flwr) simulation |
| Differential privacy | Own clipped-Gaussian implementation validated against Opacus or TensorFlow Privacy accountant for epsilon |
| Prototype inference (in browser) | TypeScript port of Tier 1 detector + GRU via onnxruntime-web |
| Mobile feasibility numbers | TFLite (Saanj) |
| Frontend | Next.js (App Router) PWA, TypeScript, Tailwind, IndexedDB via Dexie for local logs |
| Backend | FastAPI, PostgreSQL (aggregate-only tables) |
| Tests | pytest (Python), vitest (TS) |
| Repro | `make all` runs data check, simulator, training, figures, lint |

## 5. Interface contracts (the reason nobody's code breaks)

These three contracts are frozen at 21:00 Saturday. Changes require all four people to agree and a version bump.

### 5.1 Results file: `results/summary.json` (schema version 1)

```json
{
  "meta": {
    "schema_version": 1,
    "run_id": "string",
    "git_commit": "string",
    "seed": 42,
    "generated_at": "ISO-8601",
    "simulated": true,
    "label": "Simulated / preliminary, public and synthetic data, not real deployment data"
  },
  "datasets": [
    {"id": "kaggle_pcos", "n_rows": 0, "n_features_used": 0, "label_definition": "string"}
  ],
  "classifiers": [
    {"dataset": "kaggle_pcos", "model": "xgboost", "feature_set": "symptom_only",
     "auc_mean": 0.0, "auc_ci_low": 0.0, "auc_ci_high": 0.0,
     "sens_at_90spec": 0.0, "spec_at_90sens": 0.0, "brier": 0.0, "n_folds": 5}
  ],
  "federated": [
    {"mode": "centralized|local_only|fedavg|fedavg_dp|fedprox|fedper", "noise_multiplier": 0.0, "clip_norm": 1.0,
     "epsilon": null, "delta": 1e-5, "auc": 0.0, "accuracy": 0.0, "rounds": 0, "non_iid": true}
  ],
  "baseline_detection": [
    {"detector": "fixed_threshold|zscore|ewma|cusum|isolation_forest|gru|lstm|cnn1d", "drift_type": "pcos|anemia|thyroid|benign_shift",
     "detection_rate": 0.0, "median_delay_cycles": 0.0, "false_alarms_per_100_cycles": 0.0}
  ],
  "ondevice": {
    "model_size_kb": 0.0, "inference_latency_ms_p50": 0.0, "inference_latency_ms_p95": 0.0,
    "peak_memory_mb": 0.0, "device": "string", "parity_max_abs_diff": 0.0
  }
}
```

Owners of sections: `classifiers`, `federated`, `baseline_detection`, `datasets` = Aryan. `ondevice` = Saanj (written to `results/ondevice.json`, merged by `make results`).

### 5.2 Screening output object (produced by the detector, consumed by the app)

```json
{
  "cycle_index": 12,
  "flag": "none | irregularity | pcos_pattern | anemia_pattern | thyroid_pattern",
  "score": 0.0,
  "confidence": "low | medium | high",
  "contributing_signals": ["cycle_length_high", "acne_high"],
  "message_key": "flag.pcos_pattern.v1",
  "detector": "zscore | cusum | gru",
  "simulated": true
}
```

`message_key` maps to text in `/content/{en,hi,mr}/messages.json` (Aditya). The app never invents flag text. Every message must contain the phrase equivalent to "consider consulting a doctor".

### 5.3 Cycle log object (stored locally in the app, fed to the detector)

```json
{
  "cycle_index": 12,
  "start_date": "YYYY-MM-DD",
  "cycle_length_days": 29,
  "flow": 1,
  "pain": 4,
  "symptoms": {
    "acne": 0, "excess_hair": 0, "hair_loss": 0, "fatigue": 1, "mood": 0,
    "weight_change": 0, "dizziness": 0, "pallor": 0
  }
}
```

Ranges: `flow` 0-3 (none, light, medium, heavy). `pain` 0-10. Each symptom 0-3 (none, mild, moderate, severe). Demo users live in `/exports/demo_users/*.json` as arrays of this object.

### 5.4 Server API (Aditya, versioned under /v1)

- `GET /v1/health`
- `GET /v1/content/cards?lang=en|hi|mr&topic=pcos|anemia|thyroid|myths|general`
- `GET /v1/content/messages?lang=...`
- `GET /v1/reminders/rules`
- `POST /v1/metrics/aggregate` (accepts only counts, no user identifiers, no log content)
- Family sharing (Liza): `POST /v1/family/invite`, `POST /v1/family/accept`, `GET /v1/family/view?role=...` returns phase and education only.

OpenAPI JSON is exported to `/docs/openapi.json` and is the source of truth.

## 6. Coding standards

- Small commits, one purpose each. Message format: `area: what changed` (example: `sim: add cusum detector`).
- Every function that touches a metric has a test. Every port between languages (Python to TypeScript) has a parity test on the same fixtures (max absolute difference under 1e-4).
- Set all seeds. Log the seed and git commit into every results file.
- No global state, no secrets in the repo, `.env.example` only.
- Type hints in Python, `strict` in TypeScript.
- Accessibility in the app: WCAG AA contrast, tap targets 44px minimum, every icon has a text label, audio cards have a transcript.
- Run `make check` before every push. A red `make check` is never pushed.

## 7. Definition of done for any task

1. Output file exists at the path named in the task.
2. Acceptance criteria in the task file are ticked.
3. `make check` passes.
4. Any claim it supports has an entry in `docs/CLAIMS_EVIDENCE.md`.
5. The owner has written two lines in `docs/CHANGELOG.md`: what changed, how to rerun.

## 8. If you are a Claude Code session working for a team member

- Read this file, `docs/CONTEXT.md`, `project.md`, `requirements.md`, then the person's task file.
- Work only in that person's folder unless told otherwise.
- Ask the person before changing any contract in section 5.
- When a requirement is unclear, write the question into `docs/OPEN_QUESTIONS.md` and continue with the most conservative reading.
- Never mark a task done if a test is failing or an output is a placeholder. Say what is missing.
- Prefer boring, well-known libraries over clever ones. This must run on Monday.

## 9. Priorities when time is short

P0 = must exist for Monday. P1 = should exist. P2 = only if everything else is green. Each task file tags its items. Cut P2 first, then P1. Never cut anything in section 2.
