# Acceptance Log

Owner: Saanj
Date: 2026-09-27

Status values are `PASS`, `FAIL`, or `BLOCKED`. A blocked item requires an owner or artifact outside the Saanj-owned evidence and data folders.

| Check | Status | Evidence or blocker | Owner |
|---|---|---|---|
| Fresh-clone reproduction and result regeneration | BLOCKED | `results/summary.json` remains placeholder-based and the full `make all` pipeline is not available in this Windows workspace | Aryan |
| Cross-platform repository checks | PASS | `python scripts/check.py`: language lint OK, contracts OK, 76 tests passed, 16 skipped | Saanj |
| Liza prototype branch build and focused tests | PASS | On `origin/liza-frontend` at `9aaa921`, `npm test` passed 3 privacy tests and `npm run build` completed successfully | Liza / Saanj |
| Liza prototype integration into team main | BLOCKED | The prototype is present on `origin/liza-frontend`, but `origin/main` currently contains the backend cleanup history and does not contain the `app/` tree | Liza / all contributors |
| Dataset register and checksums | PASS | `data/DATA_REGISTER.md` and `data/checksums.txt`; raw data remains outside the repository | Saanj |
| Kaggle PCOS source registration | PASS | Source URL, licence note, file checksums, feature disposition, missingness and limitations recorded | Saanj |
| NHANES integration or current-run cut decision | PASS | `data/DATA_REGISTER.md` now records the 2026-09-28 decision to cut NHANES from the current run and explains the limitation | Aryan / Saanj |
| Cycle calibration dataset | BLOCKED | No usable public dataset and licence were verified | Saanj |
| Verified citation library target | PASS | 25 unique `VERIFIED` entries exist in `docs/papers.csv`; CSV structure and language lint pass | Saanj |
| Final author-list verification for abbreviated citations | BLOCKED | arXiv and scholarly metadata lookups were rate-limited or unavailable during the 2026-09-28 check; P018 and P025 remain marked with abbreviated-author notes and must be checked manually before paper submission | Saanj |
| Claims table coverage | FAIL | C009-C018 are supported; C001-C008 still require app acceptance evidence | All owners |
| ONNX benchmark | PASS | `results/ondevice.json`: measured size, p50, p95, memory and PyTorch parity | Saanj |
| TFLite conversion and second device | BLOCKED | One `onnx2tf` attempt and one dependency-repaired retry were made; conversion stopped on missing `tf_keras`, then incompatible protobuf runtime. No TFLite or Android metric was fabricated | Saanj |
| Offline logging and detection test | BLOCKED | Prototype is not present in `app/` | Liza |
| Network payload rejection test | BLOCKED | `app/lib/netClient.ts` and vitest test are not present | Liza |
| Disguise mode test | BLOCKED | Prototype implementation is not present | Liza |
| Doctor visit card test | BLOCKED | Prototype implementation is not present | Liza |
| Voice logging test | BLOCKED | Liza's branch contains a review-and-confirm voice screen, but its handler is explicitly simulated and no Whisper model or per-language accuracy test is present | Liza / Aditya |
| Saanj evidence-slide export and slide standards | PASS | `docs/slides/saanj_evidence_slides.pptx` contains four generated evidence slides and passes `check_slides.py` with zero errors | Saanj |
| Final 17-slide deck and faculty review | BLOCKED | The four-slide Saanj contribution exists, but final deck content from all contributors and second-person review are still missing | Saanj / all contributors |
| Paper citation resolution | BLOCKED | `docs/paper/` contains only `.gitkeep`; no paper text exists to inspect | Aryan |
| Faculty feedback sign-off | BLOCKED | No final deck or second-person review record exists | All contributors |

## Dependency summary

Saanj can complete the dataset register, evidence citations, claims bookkeeping, benchmark documentation, and QA recording independently. Completion of the prototype acceptance checks depends on Liza's app and tests. Completion of the final deck depends on Aryan's final result summary and figures plus content from Liza and Aditya. Completion of paper citation resolution depends on Aryan's paper text.
