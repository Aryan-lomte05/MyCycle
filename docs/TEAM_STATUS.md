# Team assignments and current status

Generated 2026-09-29 by Aryan's Claude Code session, from the four task files (`aryan.md`, `liza.md`,
`saanj.md`, `aditya.md`) checked against what is actually committed in the repo right now. All
original deadlines in the task files were written relative to Sat 26 to Mon 28 Sep 2026; today is
2026-09-29, so every "tonight" / "Sunday" / "Monday" deadline below has already passed. This file
says what exists, not what should have happened by when.

Each person owns a folder per `CLAUDE.md` section 3: Aryan = `/sim`, `/exports`, `/results`; Liza =
`/app`, `server/routes/family.py`; Saanj = `/data`, `/ondevice`; Aditya = `/content`, `/server`.

---

## Aryan: ML architecture, experiments, integration

| Package | What it is | Status |
|---|---|---|
| A0 | Scaffold, frozen contracts | Done |
| A1 | Synthetic simulator | Done, tests pass, validated against real data (FedCycleData) |
| A2 | Detectors (z-score, CUSUM, EWMA, fixed-threshold, isolation forest, hybrid) | Done, tuned and measured |
| A3 | PCOS classifier comparison (kaggle_pcos, real data) | Done, 8 models, real AUCs |
| A3 ext | NFHS-5 anemia + thyroid classifiers (real data, added beyond the original plan) | Done. Anemia AUC 0.62 (near chance, honest negative result), thyroid AUC 0.77 |
| A4 | GRU sequence model, ONNX export, personalization | Done. Honest result: GRU underperforms Tier 1 |
| A5 | Federated learning + differential privacy | Done. Found and fixed a real DP-accounting bug (epsilon was understated up to 4x) by validating against Opacus, as the task required |
| A6 | Technique comparison doc (`docs/TECHNIQUE_COMPARISON.md`) | **Not started** |
| A7 | Results merge into frozen `results/summary.json` | **Not started** (`summary.json` is still the placeholder) |
| A8 | Speaker notes for slides 6-12 | Not started |
| A9 | Paper integration (Abstract, Intro, Related Work, Methodology, Conclusion) | Not started |
| A12-A14 | Algorithms slide, formulas slide, FL comparison table content | Table script exists (`sim/make_tables.py`), slide content not written |

**What's real right now:** `results/classifiers.json`, `results/baseline_detection.json`,
`results/sequence_models.json`, `results/federated.json`, `results/sim_validation.json`,
`results/thresholds.json`, plus figures. 130+ tests passing. `docs/CLAIMS_EVIDENCE.md` has 17 rows,
all measured and supported. `data/DATA_REGISTER.md` has full entries for kaggle_pcos, nfhs5,
cycle_calibration (I did this instead of Saanj since nobody had started it; flagged in
`docs/OPEN_QUESTIONS.md` for Saanj to review).

**Biggest gap:** A6 (technique comparison) and A7 (results merge) are the two P0 items most likely
to be asked about directly ("why this technique over the alternatives", "where's the final results
file") and neither exists yet.

---

## Liza: Prototype, UX (`/app`)

| Package | What it is | Status |
|---|---|---|
| L0 | Project setup, design tokens | **Not started** |
| L1 | All 11 screens (onboarding, log, baseline chart, flag, myth card, privacy panel, family, reminders, evidence, demo mode) | **Not started** |
| L2 | Wire the detector (Tier 1 TS port + GRU ONNX) | **Not started** (my exports are ready: `exports/gru_v1.onnx`, `exports/gru_v1.scaler.json`, `exports/README.md`, `exports/demo_users/`) |
| L3 | Family view and visibility matrix | Not started (I have the visibility matrix from her own task file, nothing built) |
| L9 | `netClient.ts` and 0-bytes privacy proof | Not started |
| L10-L15 | Today card, disguise mode, doctor visit card, food nudges hook, voice logging, year in cycles | Not started |

**Reality check:** `app/` contains only a placeholder file. Nothing from Liza's task file is built.
This is the single biggest gap in the whole project: Monday's video and demo both depend entirely
on this folder, and it does not exist yet.

**What she can start from right now:** four verified demo personas that provably trigger their
flags (`exports/demo_users/`), a Tier 2 model ready to load (`exports/gru_v1.onnx` +
`.scaler.json`), both schemas (`exports/cycle_log.schema.json`, `exports/screening_output.schema.json`),
and a written usage guide (`exports/README.md`). Aditya has a live FastAPI backend she can call
(`server/main.py`, health check, content/metrics/reminders routes, `docs/openapi.json`).

---

## Saanj: Data register, on-device, evidence, slides (`/data`, `/ondevice`)

| Package | What it is | Status |
|---|---|---|
| S0 | Download and register datasets | **Done, but by Aryan, not Saanj** (kaggle_pcos, nfhs5, cycle_calibration all in `data/DATA_REGISTER.md` with checksums; I did this ahead of the team joining, flagged for Saanj's review in `docs/OPEN_QUESTIONS.md`) |
| S1 | Papers library (`docs/papers.csv`), target 25 VERIFIED | **Empty, header row only.** Nothing verified. This blocks every clinical threshold in `sim/ASSUMPTIONS.md` and every citation in the technique comparison and paper |
| S2 | On-device feasibility (TFLite conversion, latency, memory) | **Not started.** `ondevice/` is empty, `results/ondevice.json` does not exist |
| S3 | Claims-evidence table | **Done, but by Aryan** (17 rows, all mine; Saanj was supposed to own and chase this) |
| S4 | Slide deck | **Not started.** `docs/slides/` is empty |
| S5 | QA / acceptance test runner, `docs/ACCEPTANCE_LOG.md` | Not started |

**Biggest gap:** `docs/papers.csv` being empty is the most structurally damaging gap in the whole
project. It blocks: marking any clinical threshold VERIFIED (Rotterdam criteria, WHO anemia cutoff,
FIGO AUB guidance), the technique comparison's "cited" evidence column, and every reference in the
paper. Nothing else can close this except someone actually reading the sources.

---

## Aditya: Content, backend, interviews, video (`/content`, `/server`)

| Package | What it is | Status |
|---|---|---|
| AD0 | FastAPI server scaffold | **Done.** `server/main.py`, `db.py`, routes for content/metrics/reminders, `docs/openapi.json`, `tests/test_server.py` exist and are committed (merged via PR #1) |
| AD1 | Message skeleton (`content/{lang}/messages.json`) | **Not started.** `content/` is empty except a placeholder |
| AD2 | Education cards (10-12 cards x 3 languages) | Not started |
| AD3 | Audio | Not started |
| AD4 | Interview synthesis (`docs/INTERVIEWS.md`) | **Not started.** File does not exist |
| AD5 | Reminders + aggregate metrics endpoints | Partially covered by AD0's route scaffold; whether the actual rule logic and allow-list validation exist needs Aditya to confirm, not visible from outside `server/routes/` as committed |
| AD6 | Video edit and narration | Not started (nothing to edit yet, Liza's clips do not exist) |
| AD7 | Slides 1, 2, 3, 15, 16 | Not started |
| AD10-AD13 | Food nudges, today tips, voice phrases, public copy pack | Not started |

**What's real right now:** the backend scaffold (AD0) is genuinely done and is the second most
complete package in the project after Aryan's ML core. Some earlier commits from Saanj's side
("add evidence and on-device deliverables", "record citation verification blocker") were pushed
and then reverted in git history; what that means for actual current state is unclear from the
repo alone, worth asking Saanj directly.

---

## The honest overall picture

Two folders are essentially complete with real, tested, honestly-reported work: `/sim` (mine) and
the backend half of `/server` (Aditya's AD0). Three entire packages that gate everything else are
empty: `/app` (nothing can be demoed or recorded without it), `docs/papers.csv` (nothing can be
cited), `docs/slides/` (nothing can be presented). `/content`, `/ondevice`, `docs/INTERVIEWS.md`,
`docs/TECHNIQUE_COMPARISON.md` and the A7 results merge are also all untouched.

If time is short, the task files themselves already say what to cut, in order: A11/A8 (mine), L8/L15
(Liza's, P2), S7 (Saanj's, P2), AD9 (Aditya's, P2), then P1 items. What cannot be cut per every task
file's own ground rules: the simulator and Tier 1 detector (done), the PCOS classifier comparison
(done), the app's onboarding/log/baseline chart/flag screens with demo mode (not started), the
privacy proof (not started), and at least the header of the claims table (started, needs Saanj's
ownership going forward).
