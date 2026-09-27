| Feature set | Model | Median impute AUC | KNN impute AUC | Abs diff |
|---|---|---|---|---|
| S1 symptom only | logistic_regression | 0.8827 | 0.8823 | 0.0004 |
| S1 symptom only | random_forest | 0.8886 | 0.8875 | 0.0010 |
| S2 symptom + vitals | logistic_regression | 0.8771 | 0.8770 | 0.0001 |
| S2 symptom + vitals | random_forest | 0.8932 | 0.8934 | 0.0002 |
| S3 with labs (reference, non-deployable) | logistic_regression | 0.9416 | 0.9417 | 0.0001 |
| S3 with labs (reference, non-deployable) | random_forest | 0.9570 | 0.9568 | 0.0001 |

Table: kaggle_pcos, n=541, 5-fold CV x 3 seeds. Only 2 of 541 rows have any missing value (data/DATA_REGISTER.md), so this table shows the choice barely matters on this dataset, not a general result. Simulated / preliminary, public and synthetic data, not real deployment data
