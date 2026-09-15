# Week 3 Day 2 — Prediction Models

Match-winner and top-player models on Day-1 features.

## Setup

```powershell
cd Week-3/Day-2
pip install -r requirements.txt
python train_models.py
jupyter notebook prediction_models.ipynb
```

Needs Day-1 processed tables:
- `../Day-1/data/processed/match_features_v1.csv`
- `../Day-1/data/processed/player_game_features_v1.csv`

## Deliverables

| Item | Path |
|------|------|
| Notebook | `prediction_models.ipynb` |
| Train script | `train_models.py` |
| Callable API | `predict.py` |
| Models | `models/match_winner.joblib`, `models/top_player.joblib` |
| Metrics | `results/metrics.json` |

## How to call

```python
from predict import predict_match_winner, predict_top_player

predict_match_winner(
    "Sydney Swans",
    "Melbourne Demons",
    "2024-03-07",
    home_team="Sydney Swans",
)
# -> {winner, home_win_probability, ...}

predict_top_player(
    team="Sydney Swans",
    match_date="2024-03-07",
    opponent="Melbourne Demons",
    top_k=5,
)
# -> ranked player list by predicted impact
```

CLI:

```powershell
python predict.py match --home "Sydney Swans" --away "Melbourne Demons" --date 2024-03-07
python predict.py player --team "Sydney Swans" --date 2024-03-07 --opponent "Melbourne Demons"
```

## Holdout snapshot (from `train_models.py`)

- Match **GBM**: ~65% acc, ROC AUC ~0.71, beats always-home and ladder baselines on AUC/Brier
- Player: regression + rank; blend improves top-5 hit rate vs raw model
