# Adult Income Prediction — Tuning & Final Pipeline (Day 4)

Continuation of Day 1–3: hyperparameter search, diagnostics, calibration, and a saved final pipeline.

## Setup

```bash
pip install -r requirements.txt
jupyter notebook model_tuning.ipynb
```

## Files

- `model_tuning.ipynb` — Day 4 notebook
- `report.md` / `report.pdf` — tuning write-up
- `final_income_pipeline.joblib` — calibrated pipeline + threshold
- `requirements.txt` — dependencies

## Day 1–3 connection

Same Adult dataset and Day 1 hold-out split (`random_state=42`). Tuning uses training data only; the hold-out test set is used once at the end.
