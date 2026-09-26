# Liza: Prototype, UX and Design Lead

You own `/app` (the working prototype) and `server/routes/family.py`. Monday is judged mostly on what people see, so your work is the face of the project. You do not need to build any ML: Aryan gives you a detector and a model file with a usage example, and fixed data formats so you can build the whole app against placeholders from tonight.

Read first: `CLAUDE.md` (rules and contracts), `requirements.md` section 2 (functional requirements FR1 to FR10).

## Ground rules for your code

- Next.js (App Router), TypeScript strict, Tailwind, Dexie (IndexedDB), PWA with service worker.
- Never invent flag text. Use `message_key` and load text from `/content/{lang}/messages.json` (Aditya).
- Never send log data over the network. Only the content and metrics endpoints are called, and only for content, never with user data.
- Never write the word "diagnosis" in UI copy. Screening flag, pattern, "consider consulting a doctor".
- Show the "Simulated demo data" badge whenever demo personas or results are on screen.
- Accessibility per `CLAUDE.md` section 6.

## Work packages

### L0 (P0, tonight, 90 min): Project setup and design tokens
- `npx create-next-app` with TypeScript, Tailwind, App Router. Add PWA manifest and service worker (next-pwa or a simple custom worker).
- Design system file `app/styles/tokens.ts`: calm palette (no alarming red for flags, use warm amber for "worth a look", teal or soft green for normal), type scale, spacing, radius, elevation. Contrast checked at AA.
- Base components: Button, Card, IconLabel, Badge (including the SIMULATED badge), Chart wrapper, AudioPlayer, LanguageSwitcher, BottomNav.
- i18n set up for `en`, `hi`, `mr` with strings loaded from `/content`.
- Load `results/summary.json` (placeholder version from Aryan) and `/exports/demo_users/*.json`.

Acceptance: app runs, switches language, shows a card and a badge, installable as PWA.

### L1 (P0, tonight and Sunday morning): Screens
Build in this order so something is always demoable.

1. **Onboarding (FR1):** language, one-screen privacy promise ("Your logs stay on this phone"), role choice, no signup.
2. **Home:** current phase, next expected period with an honest uncertainty range, latest flag card if any.
3. **Log cycle (FR2):** start date, length, flow with four icon buttons, pain slider 0-10, eight symptom chips with four severity steps each. Big tap targets. Save to IndexedDB. Edit and delete past cycles.
4. **Baseline chart (FR3):** line chart of cycle length with the personal band (mean plus or minus 2 SD), current cycle highlighted, one plain-language sentence under it. Use a light charting library (Recharts or uPlot).
5. **Flag screen (FR4):** shows flag type, calm explanation from content, contributing signals in plain words, "consider consulting a doctor", button to open the audio myth card, button "Share this with someone I trust" (P2).
6. **Myth card (FR5):** icon-led card, audio player, transcript toggle, language follows the app language.
7. **Privacy panel (FR6):** three blocks: stored on this phone, never leaves the phone, optional model update sharing (off by default). "Run demo federated round" button that shows update size in KB, clipping and noise settings, and a note "no logs were sent". Delete-all button with confirmation.
8. **Family view (FR7):** see below.
9. **Reminders (FR8):** list from server rules or local fallback.
10. **Evidence screen (FR10):** charts from `summary.json`: model comparison, privacy-utility, detection delay, each with the simulated label and n.
11. **Demo mode (FR9):** picker for four personas. "Add next cycle" button that appends the next cycle from the persona file and runs the detector. Must reliably produce the intended flag on the intended cycle. Include a "reset persona" button. This is the centerpiece of the video, so test it 20 times.

### L2 (P0, Sunday late morning): Wire the detector
- Aryan delivers `exports/detector.ts`, `exports/gru_v1.onnx`, `exports/README.md` by Sunday 12:00. Until then use a stub implementing the same interface that returns the example outputs from `exports/examples/`.
- Tier 1 detector runs in plain TypeScript (guaranteed path). The GRU runs through onnxruntime-web in a web worker so the UI never freezes. If the GRU fails to load, the app falls back to Tier 1 and shows "using basic baseline" in a small note. Do not spend more than 90 minutes on the GRU integration. Tier 1 alone is enough for Monday.
- Measure inference time per cycle in the browser and expose it in the privacy or evidence panel.

### L3 (P0): Family view and visibility matrix
Roles and what each may see (companion never sees raw logs):

| Item | Self | Partner | Parent | Sibling |
|---|---|---|---|---|
| Raw cycle and symptom logs | yes | no | no | no |
| Screening flags | yes | no (unless user shares a specific flag, P2) | no (same) | no |
| Current cycle phase | yes | yes | yes | yes |
| Expected period window (coarse, 3-day window) | yes | yes | yes | no |
| Education cards and "how to support" tips | yes | yes | yes | yes |
| Revoke access | yes | n/a | n/a | n/a |

- Invite flow: user generates a short code with role and expiry, companion enters it in another browser profile. For the prototype the family record lives in the FastAPI route `server/routes/family.py` and stores only role, coarse phase, expiry and a random id. No names, no logs.
- Companion screen has a clear "You can see phase and tips only" banner.
- Test: the companion view's network responses must not contain any field from the cycle-log contract. Add a vitest that asserts this.

### L4 (P1): Backend routes for family sharing
- FastAPI router with `/v1/family/invite`, `/v1/family/accept`, `/v1/family/view`, `/v1/family/revoke`. In-memory or SQLite storage is fine for the prototype. Pydantic models, OpenAPI exported to `docs/openapi.json` (share the file with Aditya, who owns the server app that mounts your router).
- Unit tests for expiry, revoke and role restrictions.

### L5 (P0, Sunday afternoon): Prototype polish and freeze
- Empty states, error states, loading states, offline behavior tested with the browser's offline mode.
- Lighthouse run: PWA, accessibility, performance. Save the report to `docs/evidence/lighthouse.html`.
- Screenshot of the browser network tab during logging and detection showing no log data leaves the device: `docs/evidence/network_privacy.png`.
- Feature freeze Sunday 19:00.

### L6 (P0, Sunday 19:00 to 21:00): Screen recording for the video
- Record at 1080p, cursor visible, clean browser profile, demo mode on, simulated badge visible.
- Follow the storyboard in `requirements.md` section 8. Record each scene as a separate clip so single scenes can be redone.
- Hand raw clips to Aditya for editing. Narration is recorded separately over the clips.

### L7 (P1): Paper section
- Write "Methodology: System and UX": architecture diagram, screen figures (export from the app at 2x), design decisions and their link to interview findings (use interview codes from Aditya's `docs/INTERVIEWS.md`), visibility matrix as a table, accessibility choices.
- Also write the slide 14 content (prototype architecture and screenshots) for Saanj to place. Fonts on slides are 18 pt minimum and every screenshot has a numbered caption (`requirements.md` section 12).

### L8 (P2)
- Push notification reminders, share-a-flag with companion, dark mode.

## Public-facing feature packages (added 26 Sep 2026)

Full requirements are FR11 to FR17 in `requirements.md`. Copy on every screen follows `requirements.md` section 11.

### L9 (P0, start first, Sunday morning): netClient and privacy proof (FR13)
- Create `app/lib/netClient.ts` BEFORE any other network code, so nothing is retrofitted. Every request goes through it. It counts requests and bytes, tags each as `content` or `model_update`, and throws if a payload contains any field from the cycle-log contract.
- Privacy panel shows "Your data sent to our servers: 0 bytes" from the real counter (never hard-coded), plus a request log with content fetches listed separately.
- "Run demo federated round" appears as a labeled model update with the real size in KB (Aryan supplies a representative sample).
- vitest: fails if `fetch`, `XMLHttpRequest`, `sendBeacon` or `WebSocket` appear outside `netClient.ts`; fails if a payload with cycle-log fields is accepted.
- Offline test for the video: airplane mode on, log and get a flag, counter unchanged.

Acceptance: acceptance tests 9 and 10 in `requirements.md` pass.

### L10 (P0): Family circle Today card (FR15)
- Companion home shows a Today card chosen from the cycle phase only, text from Aditya's `content/{lang}/today_tips.json`. No log data ever reaches the companion screen (this extends the vitest in L3).
- Learning cards for partner, parent, brother or son and teacher from cards 8 to 10.

### L11 (P1): Disguise mode (FR12)
- Working calculator skin. PIN (4 to 6 digits) stored only as a salted PBKDF2 hash via WebCrypto. Quick-hide button on every screen. Neutral app name in the PWA manifest while disguise is on. No health text in any notification.
- Settings screen states the honest limit: a discretion feature against casual snooping, not protection against a determined person with full device access.

Acceptance: acceptance test 11 passes.

### L12 (P1): Doctor visit card (FR14)
- Screen where the user ticks what to include, then a one-page print layout (print stylesheet, browser print-to-PDF). Contents: baseline mean and range, recent cycles chart, flags with dates in screening wording, symptom summary, footer "Screening summary from a self-tracking app, not a medical record. Please consult a doctor."
- Optional QR with a compact JSON summary under about 500 bytes. Nothing is uploaded.

Acceptance: acceptance test 12 passes.

### L13 (P1): Food nudges hook (FR16)
- Show Aditya's food nudges in reminders and on the anemia card. Content only, no logic beyond language and topic.

### L14 (P1, time-box 2 hours, check in at Sunday 14:00): On-device voice logging with Whisper (FR11)
- Load a Whisper model in a web worker with transformers.js (or a WebAssembly build of whisper.cpp), so the UI never freezes. Start with the tiny model and try base only if accuracy is poor. Use a language hint for en, hi and mr.
- Put the model files in `app/public/models/` (gitignored). Write `app/README.md` with the exact command to fetch them. Never load models from a third-party site at run time, and register the files with the service worker so voice works offline.
- Parser: rule-based, reads Aditya's `voice_phrases.json`, outputs a proposed cycle-log object. A review screen shows the transcript and the parsed fields, and nothing is saved until the user confirms.
- Test with 10 recorded phrases per language (the team records them). Count phrases parsed into the correct fields. A language ships only if it reaches the threshold in FR11 (default 80 percent); otherwise disable that language and say so in the UI. Record the pass rates in `docs/ACCEPTANCE_LOG.md`.
- All model file requests go through `netClient` as `content`. The 0 bytes counter must not move while voice runs. No audio is stored.
- If Whisper is not working by the 2 hour mark, cut the voice button, keep icon logging, and tell Aryan so the claims table and video storyboard stay accurate.

### L15 (P2): Year in cycles (FR17)
- Local summary cards the user can save as an image. No upload, no share button.

## Interfaces you owe and receive

| From or to | What | By |
|---|---|---|
| From Aryan | Frozen contracts, placeholder `summary.json`, demo users v0, flag examples | Sat 21:30 |
| From Aditya | `messages.json` and card content skeleton for all flag keys (en first) | Sat 23:00 |
| From Aditya | Audio files or a TTS pipeline note (see aditya.md) | Sun 12:00 |
| From Aryan | `detector.ts`, `gru_v1.onnx`, README | Sun 12:00 |
| To Aditya | `family.py` router and OpenAPI | Sun 14:00 |
| To Saanj | Slide 14 content and screenshots | Sun 17:00 |
| To Aditya | Raw screen recordings | Sun 21:00 |

## If you get stuck

- Stub and move on. Never block the demo on one unfinished piece.
- Ask in the group with a screenshot and the console error. Aryan answers model and contract questions, Aditya answers content and API questions, Saanj answers data and slide questions.
- Priority order if time runs out: onboarding, log, baseline chart, flag screen with demo personas, privacy panel with the live network counter (L9), family circle Today card, disguise mode, doctor visit card, evidence screen, reminders, food nudges hook, voice logging, year in cycles.

## Hard questions to prepare for

1. Why is the companion view designed this way? (interview evidence, privacy by default)
2. What exactly stays on the device? (walk through the network screenshot)
3. Why a PWA and not React Native or Flutter? (T11 in the technique comparison, offline, one codebase, no store approval delay)
4. How was the flag wording chosen? (gynecologist input, screening language)
5. Who is the primary user and how does the design serve low digital literacy? (icon plus text, audio, regional language)
