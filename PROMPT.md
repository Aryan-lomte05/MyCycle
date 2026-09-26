# Starting prompts for each tool

Use these in Claude Code or Antigravity. Open the repo folder first, then paste the matching prompt as the first message. If the tool supports a project rules file, point it at `CLAUDE.md`; the prompts below already name the files to read.

## 0. One-time setup (Aryan, then everyone)

Aryan, in the project folder:

```
cd "E:\Personal or College Projects\MyCycle"
pip install -r requirements-dev.txt
python scripts/check.py
git init
git add .
git commit -m "scaffold: docs, contracts, checks"
```

Then create a PRIVATE GitHub repository, add it as `origin`, and push:

```
git branch -M main
git remote add origin <your private repo url>
git push -u origin main
```

Liza, Saanj and Aditya clone that repo, run `pip install -r requirements-dev.txt` and `python scripts/check.py`, and then paste their prompt. Everyone works mostly in their own folders (see `CLAUDE.md` section 3), so merge conflicts should be rare. Pull often. Never commit raw data, interview names, audio or secrets.

## 1. Aryan (main session)

```
You are working on MyCycle, our course project: a privacy-preserving, personal-baseline menstrual health screening system (research paper plus working prototype). We present on Monday 28 Sep 2026 and our faculty guide questions every claim, so honesty and correctness matter more than speed.

Read these files completely, in this order, before doing anything:
1. CLAUDE.md
2. docs/CONTEXT.md
3. docs/SIR_FEEDBACK.md
4. project.md
5. requirements.md
6. aryan.md

Then reply in under 12 lines with: the non-negotiable rules as you understand them, the current state of the repo, and the order you will work in. Do not write code until I confirm.

Setup: run pip install -r requirements-dev.txt and python scripts/check.py. It must be green before you start.

Working rules:
- Work only in sim/, exports/, results/ and docs/ unless I say otherwise. Never change a contract in CLAUDE.md section 5 without asking me.
- Never invent, hard-code or estimate a metric. Every number comes from a script that writes into results/. Fixed seeds. Log the seed and git commit.
- Everything simulated carries the label: "Simulated / preliminary, public and synthetic data, not real deployment data".
- Never write "diagnosis" as something the system does. Use screening flag, risk pattern, "consider consulting a doctor".
- No em dashes anywhere: code, comments, docs, commit messages.
- Do not fabricate citations. If you cannot verify a clinical source or a paper, mark it "assumption" or UNVERIFIED and tell me.
- Differential privacy: use the standard DP-SGD form (noise on the sum of clipped gradients, then divide by the batch size). See aryan.md A5.
- Tests first. Run python scripts/check.py after every package. Never report a package done if it is red.
- Commit small, format "area: what changed". Add two lines to docs/CHANGELOG.md per package.
- If something is unclear, write it in docs/OPEN_QUESTIONS.md, take the most conservative reading, and tell me.

Work order: A1 simulator (sim/simulator.py, tests for each drift type, sim/ASSUMPTIONS.md). Then A2 detectors. Then replace the crude demo personas in exports/demo_users with simulator-derived ones that provably trigger the intended flags, and update the manifest. Then A3 classifiers once Saanj supplies the Kaggle column list. Slide content packages A12 to A14 come after the results exist.

After each package, report in at most 5 lines: what exists, what the tests show, what is still an assumption, and what you need from me.
```

## 2. Liza

```
I am Liza. I own the MyCycle prototype in app/ (Next.js PWA, TypeScript strict, Tailwind, Dexie) and server/routes/family.py.

Read completely, in this order: CLAUDE.md, docs/CONTEXT.md, docs/SIR_FEEDBACK.md, requirements.md (section 2 FR1 to FR17, section 11 copy rules, section 12 slide standards), liza.md. Then reply in under 10 lines with what you will build first and which files you will touch. Do not write code until I confirm.

Rules:
- Work only in app/ and server/routes/family.py.
- Build against results/summary.json (a placeholder), exports/demo_users/*.json, exports/examples/*.json and the contracts in CLAUDE.md section 5.
- Create app/lib/netClient.ts FIRST. Every network call goes through it (CLAUDE.md rule 12). It counts requests and bytes and refuses any payload containing cycle-log fields. The "0 bytes sent" counter must be measured, never hard-coded.
- Never invent flag text: use message_key and load text from content/{lang}/messages.json (use the English example until Aditya delivers).
- Never write "diagnosis" in UI copy. The only approved privacy sentence is "Your cycle logs stay on your phone. You choose what to share."
- Show a "Simulated demo data" badge wherever demo personas or results appear.
- Voice logging uses Whisper running in the browser on the device, time-boxed to 2 hours, and it is built last (liza.md L14). Icon logging is the guaranteed path.
- No em dashes anywhere.
- Run lint, tsc and vitest before saying a screen is done.

Build order: L0 setup and design tokens, L9 netClient and privacy proof, then the screens in the order listed in liza.md (onboarding, log, baseline chart, flag screen, demo mode first) so something is always demoable. The baseline chart is the hero visual. Then the family circle, disguise mode and doctor visit card.
```

## 3. Saanj

```
I am Saanj. I own data, on-device feasibility, the datasets register, the citation library, the claims-evidence table and the final slide deck for MyCycle.

Read completely, in this order: CLAUDE.md, docs/CONTEXT.md, docs/SIR_FEEDBACK.md, requirements.md (sections 4, 5, 6, 10, 12), saanj.md. Then reply in under 10 lines with what you will do first. Do not start until I confirm.

Rules:
- Work only in data/, ondevice/, docs/papers.csv, docs/CLAIMS_EVIDENCE.md, docs/ACCEPTANCE_LOG.md and docs/slides/.
- Nothing goes into the register or the citations file unless we opened the source and read the relevant part. Unread items are UNVERIFIED and must not be cited.
- Record URLs, access dates, licences and SHA-256 checksums. Never commit raw data.
- Never invent numbers: copy them from results/ files.
- The deck follows the 17-slide plan in requirements.md section 4 and the slide standards in section 12. Export it as .pptx into docs/slides/ and run python scripts/check_slides.py. Our faculty guide's feedback is tracked in docs/SIR_FEEDBACK.md and each row needs a second person to tick it.
- No em dashes anywhere.

Start with S0: download and register kaggle_pcos, send Aryan the exact column list, then group all data sources by category for slide 4. Then S1 (papers library).
```

## 4. Aditya

```
I am Aditya. I own content, the FastAPI server, the interview synthesis, the public-facing copy and the video edit for MyCycle.

Read completely, in this order: CLAUDE.md, docs/CONTEXT.md, docs/SIR_FEEDBACK.md, requirements.md (sections 2, 7, 8, 11, 12), aditya.md. Then reply in under 10 lines with what you will do first. Do not start until I confirm.

Rules:
- Work only in content/, server/ (except routes/family.py, which Liza owns), docs/INTERVIEWS.md and your slides.
- Wording: screening flag, risk pattern, "consider consulting a doctor". Never "diagnosis" as something the app does. The only approved privacy sentence is "Your cycle logs stay on your phone. You choose what to share."
- Every health statement needs a recorded source in content/SOURCES.md. Hindi and Marathi text must be reviewed by a fluent speaker.
- Interview material is anonymized (codes only) before it is committed, and quotes are used only if consent covers them. Report only what was actually done. Anything not done is written as "planned, not yet done".
- Public copy follows requirements.md section 11. Slides follow section 12 and docs/SIR_FEEDBACK.md.
- No em dashes anywhere.

Start with AD0 (server scaffold with static stubs), AD1 (English messages.json), AD11 (Today tips, English first, to Liza by Saturday 23:00), then AD4 (interview synthesis).
```

## 5. Any session: recovery prompt (when a session loses context)

```
Re-read CLAUDE.md, docs/CONTEXT.md, docs/SIR_FEEDBACK.md and my task file. Run python scripts/check.py, look at git status and docs/CHANGELOG.md, and tell me in 8 lines where we are and what the next step is. Do not change any files until I confirm.
```
