# Claims-Evidence Table

Owner: Saanj. No entry, no claim. Status must be `supported` before Monday, otherwise the claim is rewritten or removed.

| claim id | exact claim text | where it appears | type (measured / cited / interview / design decision) | evidence pointer | status | owner |
|---|---|---|---|---|---|---|
| C001 | Raw cycle and symptom logs are stored only on the device | app privacy panel, slide 14 | design decision | docs/evidence/network_privacy.png (pending) | needs work | Liza |
| C002 | Screening flags are non-diagnostic and always advise consulting a doctor | app, content/messages.json | design decision | content/en/messages.json (pending), scripts/lint_language.py | needs work | Aditya |
| C003 | Works without internet after first load | app, video scene 6 | measured | acceptance test 9 (pending) | needs work | Liza |
| C004 | The app sent 0 bytes of user data | privacy panel, poster | measured | netClient counter and vitest, acceptance test 10 (pending) | needs work | Liza |
| C005 | Disguise mode hides the app from casual viewing | app, poster | design decision | acceptance test 11 (pending) | needs work | Liza |
| C006 | The doctor visit card is generated on the device and nothing is uploaded | app, poster | design decision | acceptance test 12 (pending) | needs work | Liza |
| C007 | Voice logging runs on the device and audio is not stored | app, video scene 4 | measured | acceptance test 14 and network check (pending) | needs work | Liza |
| C008 | Your cycle logs stay on your phone. You choose what to share. | app onboarding, privacy panel, poster, slides | design decision plus measured | netClient counter and vitest, acceptance test 10 (pending); family sharing sends phase only (FR15) | needs work | Liza |
