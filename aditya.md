# Aditya: Community Research, Content, Backend and Video Lead

You own `/content`, `/server` (the FastAPI app that serves content, reminders and aggregate metrics), `docs/INTERVIEWS.md`, and the final video edit. Your work is the human side of the project: the interviews, the wording of every message, the education cards, and how the story is told on Monday. All tasks below have exact inputs, outputs and checks.

Read first: `CLAUDE.md`, `requirements.md` (sections 2, 7, 8).

## Ground rules

- Wording rule: screening flag, risk pattern, "consider consulting a doctor". Never "diagnosis" as something the app does.
- Tone: calm, non-alarming, no shame, no blame, no medical jargon. Reading level: a school-age reader can understand.
- Every health statement on a card needs a source (WHO, NHS, ACOG, ICMR, a verified paper) recorded in `content/SOURCES.md`, and where possible a gynecologist interviewee has reviewed it.
- Hindi and Marathi text must be checked by a fluent speaker before it ships. Do not rely on machine translation alone.
- Interview data: anonymized codes only (P01 to P10), no names, no identifying details in the repo.

## Work packages

### AD0 (P0, tonight, 60 min): Server scaffold
- FastAPI app in `/server` with Pydantic models, CORS for the local app, `/v1/health`, and stub endpoints from `CLAUDE.md` 5.4 returning static JSON so Liza can call them tonight.
- Structure: `server/main.py`, `server/routes/content.py`, `server/routes/reminders.py`, `server/routes/metrics.py`, mount `routes/family.py` from Liza later.
- Export `docs/openapi.json` with `make openapi`. Tests with pytest and httpx.
- PostgreSQL: one table `aggregate_metrics(id, metric_name, value, bucket_date)` created by a migration script. Aggregate counts only. For local development SQLite is acceptable, record which one is used.

Acceptance: `uvicorn server.main:app` runs, `/v1/health` returns 200, OpenAPI file committed, tests pass.

### AD1 (P0, tonight and Sunday morning): Message skeleton
- `content/en/messages.json` with one entry per `message_key` the detector emits. Ask Aryan for the key list by Sat 21:30. Expected keys: `flag.none.v1`, `flag.irregularity.v1`, `flag.pcos_pattern.v1`, `flag.anemia_pattern.v1`, `flag.thyroid_pattern.v1`, plus `confidence.low|medium|high` and signal names (`cycle_length_high`, `cycle_length_low`, `flow_high`, `fatigue_high`, `acne_high`, and so on).
- Each flag message has: title, one-sentence summary, what this pattern means in plain words, what you can do next, "consider consulting a doctor" line, and the myth card id it links to.
- Draft in English first and give it to Liza by Sat 23:00. Then translate to `hi` and `mr`.
- Example tone for a pcos_pattern message: "Your cycles have been longer than usual for a few months, and you noted some other changes. This is a pattern that is sometimes seen with hormone conditions like PCOS. It does not mean you have it. A doctor can check with simple tests. Consider consulting a doctor."

Acceptance: all keys present in en, hi, mr, every flag message contains the doctor-consult line, `lint_language.py` passes.

### AD2 (P0, Sunday, 4 hours): Education cards (`content/{lang}/cards.json`)
Cards to write (10 to 12 in total, each with title, body of 60 to 90 words, one icon name, audio file reference, source ids):

1. What is a normal cycle (range and variation between people)
2. Irregular periods are not only stress (myth correction, hormones in simple words)
3. PCOS: what it is, common signs, it is common and manageable
4. Anemia and heavy periods: signs, iron-rich foods, when to see a doctor
5. Thyroid and periods: signs, a simple blood test exists
6. Period pain: when it is common and when to get checked
7. Myths: "period blood is impure", "cannot cook or enter kitchen", "do not talk about it" (each corrected kindly)
8. For partners: how to support without prying
9. For parents: how to talk with daughters
10. For brothers and sons: what periods are and how to help
11. Your privacy: why your logs stay on your phone
12. When to see a doctor: red flags (very heavy bleeding, severe pain, no period for 3 months and not pregnant)

Process:
- Draft from verified public sources. Record in `content/SOURCES.md`: card id, statement, source, URL, date accessed.
- Ask the gynecologist interviewees (if reachable) to review the health statements. Record who reviewed and what they changed, by code (G01, G02).
- Reading level check: short sentences, no jargon.
- Translate to Hindi and Marathi, then have a fluent speaker review. Record reviewer initials.

Acceptance: 12 cards in three languages, sources for every statement, reviewer log.

### AD3 (P0, Sunday, 2 hours): Audio
- Generate audio for each card and message in en, hi, mr. Preferred: a text-to-speech service with good Hindi and Marathi voices, checked by listening to each file. Alternative: record human voice.
- Files at `content/audio/{lang}/{card_id}.mp3`, under 300 KB each, normalized volume, no background noise.
- Note in `content/AUDIO_NOTES.md` how each file was produced (tool, voice, date) and the licence terms of the tool. State in the paper that voices are synthetic if TTS is used.
- Give Liza the audio by Sunday 12:00, even if only English is ready. Add the rest as they finish.

Acceptance: every card has audio in all three languages, or a documented gap listed in `docs/OPEN_QUESTIONS.md`.

### AD4 (P0, tonight and Sunday morning): Interview synthesis (`docs/INTERVIEWS.md`)
- Inputs: your 10 interviews (5 online, 5 offline; community, teacher, gynecologist).
- Step 1: anonymize. Codes P01 to P10 (community P01 to P05, teacher T01 to T02, gynecologist G01 to G03, adjust to your actual split). Remove names, places and identifying details.
- Step 2: codebook. Read all interviews and list codes such as `barrier_cost`, `barrier_taboo`, `privacy_fear`, `myth_belief`, `tracks_cycle`, `wants_alerts`, `wants_family_role`, `flag_wording_concern`, `symptom_useful`, `symptom_noise`.
- Step 3: a table with rows = codes, columns = interviewees, cells = short evidence (paraphrase or a quote under 25 words, only if consent covers quoting).
- Step 4: themes, each linked to a design decision (for example, "privacy_fear" links to on-device storage; "wants_family_role" links to the companion view). Liza and Aryan use this table in the prototype and paper.
- Step 5: counts stated honestly ("4 of 10 said ..."), with the small sample size named as a limitation. Do not report percentages as if this were a survey with statistical power.
- Step 6: consent and ethics: record how consent was obtained, what was told to participants, what happens to notes, and what the faculty guide said about ethics approval.
- Correct any earlier document claim that is not supported by the actual interview data (for example survey percentages, or claims about ASHA worker testing). Only report what was actually done. If ASHA workers were not tested with the cards, say "planned, not yet done".

Acceptance: table complete, every design decision linked to at least one interview code or a stated "design choice, not from interviews", consent section complete, quotes checked against consent.

### AD5 (P0, Sunday): Reminders and aggregate metrics
- `/v1/reminders/rules`: simple JSON rules the app applies locally, for example "expected period in 3 days" tips, hydration and iron-rich food nudges (linked to cards), "log your cycle" prompts. The rules are evaluated on the device, the server only serves rule definitions.
- `/v1/metrics/aggregate`: accepts only `{metric_name, value}` pairs from an allow-list (for example `federated_round_completed`, `app_opened_count`) with no user identifiers, validates and stores counts. Rejects any body with extra fields. Test that a payload containing log fields is rejected with 422.

### AD6 (P0, Sunday 21:00 to Monday morning): Video edit and narration
- Inputs: Liza's clips (Sun 21:00), script pieces from each person.
- Write the narration script from the storyboard in `requirements.md` section 8, with Aryan supplying the technical wording for scenes 3 to 6 and 8. Keep sentences short. Every claim spoken must exist in the claims table.
- Record narration in a quiet room, one scene at a time, with a decent microphone. Record 2 takes per scene.
- Edit: trim clips, add narration, add on-screen captions for key numbers, add English subtitles, show the simulated label wherever results appear. 3 to 5 minutes. Export 1080p MP4 and keep the project file.
- Do a full watch-through with the team and fix mistakes before Monday.

### AD7 (P0): Slides you author
Slides 1, 2, 3, 15 and 16 in the deck plan (`requirements.md` section 4). Follow the slide standards in section 12 (18 pt minimum, numbered captions, no dense slides) and the faculty feedback in `docs/SIR_FEEDBACK.md`.
- Slide 1: title with the name MyCycle, then the problem and four barriers with anonymized interview evidence.
- Slide 2: "existing systems" and "existing apps", what they do and what is missing, then the four contributions (from `project.md` section 3). Use the word "existing". Show only the conclusion of the literature matrix and move the 12-paper table to an appendix.
- Slide 3: federated learning explained in plain language for a reader who is not a machine learning specialist. One diagram in four steps: each phone trains on its own data, only a protected update leaves the phone, the server averages the updates, the improved model goes back. Include the sensor analogy from `project.md` section 11. Aryan checks the accuracy of the text. Test it: explain it in 30 seconds to someone outside the team.
- Slide 15: feature and method comparison with existing apps. Use only Saanj's VERIFIED sources from privacy policies and product pages. Dimensions: baseline type, where raw data lives, labs needed, family roles, regional audio, open source, monetization. Never write "better than". Put an honest row for what existing apps do better (user base, clinical partnerships, content depth).
- Slide 16: limitations, ethics, future work (clinical validation cohort, DPDP Act 2023 review, medical device regulation review, ASHA-led pilot, wearables).
Give the slide text and speaker notes to Saanj by Sunday 17:00.

### AD8 (P1): Paper sections
- **Community Study and Content Design:** interview method, themes, design decisions, content review process.
- **Discussion, Limitations and Ethics:** what the results mean and do not mean, simulated data, symptom-only limits, small interview sample, TTS voices, no clinical validation, privacy limits (DP gives a bounded epsilon, not zero leakage), regulatory review needed.
- **Results (prose draft):** Aryan supplies the numbers and figures, you write the paragraphs, Aryan checks every number.

### AD9 (P2)
- Add a second gynecologist review round, community usability test with 3 to 5 people if time allows (record as pilot, not results).

## Public-facing feature packages (added 26 Sep 2026)

Requirements are FR11 to FR17 in `requirements.md`. Copy follows `requirements.md` section 11.

### AD10 (P1): Local food nudges (FR16)
- Write regional, iron-rich and comfort food nudges in en, hi, mr (for example jaggery, ragi, leafy greens), linked to card 4 and the reminder rules. Record a source for every suggestion in `content/SOURCES.md` and get gynecologist review where possible. Education, not treatment: no dosages, no promises.
- Output: `content/{lang}/food_nudges.json`.

### AD11 (P0): Family circle Today tips (FR15)
- For each cycle phase (menstrual, follicular, ovulation, luteal) write 3 short supportive tips for a partner, parent or sibling, in en, hi, mr. Neutral about gender roles, calm, no health data, no medical claims. Example: "Today may be a low-energy day. Offer rest, a warm drink, or take over one chore."
- Output: `content/{lang}/today_tips.json`. Give the English version to Liza by Sat 23:00.

### AD12 (P1): Voice phrase dictionaries (FR11)
- Build `content/{lang}/voice_phrases.json`: how people say "period started", flow words (light, normal, heavy), pain words and numbers, and the eight symptom words, in en, hi, mr, including common spoken variants. Have a fluent speaker review Hindi and Marathi and record initials.
- The parser is rule-based and reads this file, so keep entries plain and unambiguous.

### AD13 (P0): Public-facing copy pack
- Write the poster taglines, one-line feature descriptions and video captions. Check every line against `requirements.md` section 11 and add a row to `docs/CLAIMS_EVIDENCE.md` for anything factual. Safe example: "Built around your own normal." Not allowed: "world's best", "100% private", "detects PCOS".
- Give the pack to Saanj by Sun 17:00 for the slides.

## Interfaces you owe and receive

| From or to | What | By |
|---|---|---|
| From Aryan | List of message keys and signal names | Sat 21:30 |
| To Liza | Server scaffold with static stubs | Sat 22:00 |
| To Liza | English `messages.json` | Sat 23:00 |
| To Aryan | Interview themes for the paper's motivation and flag rules feedback from gynecologists | Sun 10:00 |
| To Liza | Cards and audio (en first) | Sun 12:00 |
| To Liza | `today_tips.json` (en first), then `food_nudges.json` and `voice_phrases.json` | Sat 23:00 / Sun 12:00 |
| From Liza | `family.py` and OpenAPI | Sun 14:00 |
| To Saanj | Slide 1, 2, 3, 15, 16 text and notes | Sun 17:00 |
| From Liza | Raw screen clips | Sun 21:00 |
| To all | Edited video v1 | Mon 07:00 |

## Hard questions to prepare for

1. How were participants chosen and what are the limits of 10 interviews? (small qualitative sample, not statistical)
2. What did the gynecologists say about flag wording and symptom selection? (G codes)
3. How do you know the Hindi and Marathi content is correct? (reviewer log)
4. What in the design came directly from the interviews? (theme to decision table)
5. How does the app avoid alarming or misleading a user? (message design, doctor-consult line, screening language)
