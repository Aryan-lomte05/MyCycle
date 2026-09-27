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
| C009 | Symptom-only screening reaches an AUC around 0.89 for PCOS on the kaggle_pcos dataset (best model: k-NN, 0.891, 95% CI 0.862-0.918) | slide 8, paper Results | measured | results/classifiers.json (rows where dataset=kaggle_pcos, feature_set=symptom_only), figure results/figures/classifier_comparison.png | supported | Aryan |
| C010 | Adding lab and ultrasound features raises the best AUC from about 0.89 (symptom-only) to about 0.96 (with labs, non-deployable reference); symptom-only screening keeps most but not all of that accuracy | slide 8, paper Results, Discussion/Limitations | measured | results/classifiers.json (feature_set=with_labs_reference vs symptom_only), results/figures/classifier_comparison.png | supported | Aryan |
| C011 | The top two symptom-only models (k-NN, random forest) are not significantly different (paired bootstrap p=0.82); on symptom+vitals, random forest beats logistic regression (p=0.047) | slide 9 (technique comparison), paper Methodology | measured | results/classifiers.json (`comparisons`), paired bootstrap, n_boot=2000 | supported | Aryan |
| C012 | The Tier 1 hybrid detector (z-score + CUSUM + rule layer) detects pcos_pattern in 99%, anemia_pattern in 92%, thyroid_pattern in 99% of simulated test users, tuned on validation only | slide 10, paper Results | measured | results/baseline_detection.json (detector=hybrid), tuned on results/sim val split, sim/DETECTORS.md | supported | Aryan |
| C013 | The fixed-threshold "what most apps do" baseline produces far more false alarms on benign shifts than the personal-baseline detectors (fixed_threshold reference row at spec threshold 2.0: 26.2 false alarms per 100 non-drift cycles on benign_shift, vs 9.6 for the tuned hybrid) | slide 10, paper Discussion | measured | results/baseline_detection.json (reference_rows vs rows, drift_type=benign_shift) | supported | Aryan |
