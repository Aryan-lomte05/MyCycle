# Faculty Feedback Tracker

Source: handwritten notes from CEPDT Activity 5 Demo, 22/9/2026, 3:15 pm, Group No. 1. The ten points below are transcribed from that page. Slide numbers in the original notes refer to the OLD deck. The new deck order is in `requirements.md` section 4.

Rule: every row must be ticked by a second person (not the owner) before Monday. Tick means the fix exists in the deck or app and the check in the last column passed.

| # | What sir said (our reading) | Fix | Where | Owner | Check | Done |
|---|---|---|---|---|---|---|
| 1 | Name of app? | The app is named MyCycle. The name is on the title slide, in the footer of every slide, in the app header and in the README. | slide 1, footer, app | Saanj (deck), Liza (app) | `check_slides.py` requires "MyCycle" | [ ] |
| 2 | Slide 2: use the word "existing" | The gap slide says "existing systems" and "existing apps" and states what they do and what is missing. | slide 2 | Aditya | `check_slides.py` requires "existing" | [ ] |
| 3 | Slide 3: not readable | No dense slides. At most about 60 words of body text, tables of at most 6 data rows and 4 columns. The 12-paper literature matrix moves to an appendix and slide 2 shows only its conclusion. | all slides | Saanj | `check_slides.py` warns on density and dense tables | [ ] |
| 4 | Slide 3: figure caption should be given | Every figure, chart and table has a numbered caption below it ("Fig. N:" or "Table N:") saying what it shows, the dataset, n, the metric, and the simulated label where relevant. | all slides | everyone who supplies a figure | `check_slides.py` fails on a figure without a caption | [ ] |
| 5 | Explain federated learning | New slide 3, plain language, with a diagram: each phone trains on its own data, only a clipped and noised update leaves the phone, the server averages the updates, and the improved model goes back. Include the sensor analogy from `project.md` section 11. | slide 3 | Aditya writes, Aryan checks accuracy | rehearsal: a team member explains it in 30 seconds to someone outside the team | [ ] |
| 6 | Slide 4: which algorithm is used? Name it. If it is a hybrid, a hybrid of what? | New slide 6, "Algorithms used", naming every component: learning = FedAvg with differential privacy (clipping and Gaussian noise); personal-baseline detector = a hybrid of a statistical baseline (EWMA z-score and CUSUM), a GRU next-cycle predictor and a rule layer that maps signals to screening flags; personalization = last-layer fine-tuning. States exactly what is combined and why. Updated after the final results. | slide 6 | Aryan | `check_slides.py` requires "FedAvg"; second person checks names against `results/` | [ ] |
| 7 | Mention database category-wise | Our reading: list the data sources by category: clinical tabular (Kaggle PCOS), population survey (NHANES), real cycle-length data (calibration set), synthetic (simulator), qualitative (interviews). For each: what it is, size, what it is used for, and its limit. Also state that the backend database holds aggregate metrics only. If sir meant something else, add it. | slide 4 | Saanj | matches `data/DATA_REGISTER.md` | [ ] |
| 8 | Rewrite the formula (old slide 8) | New slide 7, "Formulas": typeset equations (equation editor or LaTeX rendered to an image, never plain typed text), every symbol defined on the slide, one idea per equation. Covers z-score, EWMA, CUSUM, clipping, Gaussian noise, FedAvg averaging and the epsilon-delta statement. The DP formula in the earlier project dump adds noise to the AVERAGED gradient, which looks wrong: the standard DP-SGD form adds noise to the SUM of clipped gradients before dividing by the batch size. Use the standard form and verify it against the original papers. | slide 7 | Aryan, verified by Saanj | both read the source paper and mark it VERIFIED in `docs/papers.csv` | [ ] |
| 9 | Slide fonts not readable | Minimum 18 pt for all text (14 pt for captions and sources), titles 32 pt or larger, high contrast, no text over images. | all slides | Saanj | `check_slides.py` fails on text under 18 pt | [ ] |
| 10 | Without FL, with FL, with FL and DP: make a table | Slide 11 carries one table: centralized (no FL), local only (no FL), FedAvg (FL), FedAvg with DP at several noise levels, with AUC, accuracy, epsilon and delta, rounds and the client split. Generated from `results/`, never typed by hand. | slide 11 | Aryan | `python sim/make_tables.py` writes `results/tables/fl_comparison.md` | [ ] |

## Words we could not read with certainty

Please confirm with someone who was in the room:
- Item 6: "Hybrid of ?" is read as "if it is a hybrid, of what?".
- Item 7: "Database categorywise" is read as datasets grouped by category. It could also mean the backend database tables by category. The plan covers both in one line.
- Item 10: the end of the line is read as "with FL and DP". If sir also wanted another column, add it to the table.

## One-sentence answers to rehearse (Sunday night)

1. What is the app called and why? 2. What do existing apps do and what is missing? 3. Why are slides now readable? 4. What does each figure show? 5. What is federated learning? 6. Which algorithm exactly, and what is hybrid about it? 7. Which data, by category? 8. What does each symbol in the formula mean? 9. (Font size, no question.) 10. What is the accuracy without FL, with FL, and with FL plus DP?
