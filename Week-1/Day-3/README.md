# Adult Income Prediction — Feature Engineering & CV (Day 3)

Continuation of Day 1–2: engineered features, leakage-safe pipelines, and cross-validated model comparison.

## Setup

```bash
pip install -r requirements.txt
jupyter notebook feature_engineering_cv.ipynb
```

## Files

- `feature_engineering_cv.ipynb` — Day 3 analysis notebook
- `report.md` / `report.pdf` — 2-page write-up
- `requirements.txt` — dependencies

## Day 1–2 connection

Same Adult dataset, cleaning, and 80/20 stratified hold-out split (`random_state=42`). Cross-validation is run on the training set only; the hold-out test set is not used for model selection.
