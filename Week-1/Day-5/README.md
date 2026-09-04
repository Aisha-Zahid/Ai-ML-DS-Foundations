# Adult Income Prediction — Week 1 Final Project

Predict whether someone earns more than 50K USD using the UCI Adult census dataset.

## Project objective

Predict who earns above 50K so outreach can focus on higher-income contacts. Main metric: **F1**.

## Dataset

| Item | Detail |
|------|--------|
| Source | UCI Adult / OpenML `adult` version 2 |
| Rows | 48,842 |
| Target | `income` — 0 = <=50K, 1 = >50K (~24% positive) |
| Split | 80/20 stratified hold-out, `random_state=42` (fixed from Day 1) |

## Feature engineering

Row-level features only (no target encoding): `age_bucket`, `hours_bin`, `has_capital_gain`, `log_capital_gain`, `is_higher_edu`, `edu_x_hours`, `has_capital_loss`, `is_full_time`.

`fnlwgt` was dropped (census sampling weight). Code: `feature_engineering.py`.

## Preprocessing

- Numeric: median impute → `StandardScaler`
- Categorical: constant `"Missing"` → `OneHotEncoder(handle_unknown="ignore")`
- All steps inside sklearn `Pipeline` / `ColumnTransformer` (no leakage)

## Models tested (Week 1)

| Stage | Models |
|-------|--------|
| Day 1 | Majority baseline, education-num rule |
| Day 2 | Logistic Regression, Decision Tree |
| Day 3 | LR, Random Forest, HistGradientBoosting (+ engineered features, CV) |
| Day 4 | Tuned LR / RF / HGB + calibration + threshold |

## Hyperparameter tuning

- Metric: F1, StratifiedKFold (3-fold in search to keep runtime reasonable)
- LR: GridSearch (`penalty`, `C`, `class_weight`)
- RF / HGB: RandomizedSearch

### Best HGB parameters

```
learning_rate=0.15, max_iter=100, max_depth=None,
l2_regularization=0.5, min_samples_leaf=10, random_state=42
```

## Selected final model

- **HistGradientBoosting** + isotonic **CalibratedClassifierCV**
- **Classification threshold: 0.33** (validation F1; favors recall vs 0.50)
- Artifact: `final_model.joblib`

## Final hold-out test performance

| Metric | Value |
|--------|-------|
| Accuracy | 0.8571 |
| Precision | 0.6707 |
| Recall | 0.7917 |
| **F1** | **0.7262** |
| ROC AUC | 0.9299 |
| PR AUC | 0.8343 |
| Brier | 0.0867 |

Confusion matrix: TN=6522, FP=909, FN=487, TP=1851

## Important features (permutation importance)

1. marital-status  
2. capital-gain  
3. age  
4. education-num  
5. capital-loss / occupation / workclass / hours-per-week  

## Known limitations

- Observational census data; associations are not causal
- Threshold and calibration assume similar class balance in production
- Search used 3-fold CV (speed); subgroup fairness not fully audited
- Marital status / sex / race can raise fairness concerns if used for decisions

## How to reproduce training

```bash
cd Week-1/Day-5
pip install -r requirements.txt
jupyter notebook final_validation.ipynb
```

Earlier days: Day-1 → Day-2 → Day-3 → Day-4 notebooks (`RANDOM_STATE = 42`).

## How to run inference

```bash
python inference_example.py
```

Or in Python:

```python
import joblib
import pandas as pd

artifact = joblib.load("final_model.joblib")
model = artifact["model"]
thr = artifact["threshold"]

# new_data: DataFrame with the same raw Adult columns as training
proba = model.predict_proba(new_data)[:, 1]
pred = (proba >= thr).astype(int)
```

Do **not** re-apply preprocessing manually — it is inside the pipeline.

## Environment

See notebook cell output and `requirements.txt`. Typical versions: Python 3.13, scikit-learn >= 1.3, pandas >= 2.0, numpy >= 1.24.

## Files in this folder

- `final_model.joblib` — calibrated pipeline + threshold
- `final_validation.ipynb` — Day 5 notebook
- `feature_engineering.py` — shared transforms
- `inference_example.py` — inference demo
- `README.md` — this file
- `final_report.md` / `final_report.pdf` — project write-up
- `requirements.txt`
