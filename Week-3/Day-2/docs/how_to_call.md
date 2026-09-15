# How to call Day-2 models

## Match winner

```python
from predict import predict_match_winner

out = predict_match_winner(
    team_a="Geelong Cats",
    team_b="Collingwood Magpies",
    date="2024-05-01",
    home_team="Geelong Cats",  # optional but clearer
)
print(out["winner"], out["home_win_probability"])
```

Errors (unknown team, bad date, missing feature row) raise `PredictionError` with a clear message.

## Top player

```python
from predict import predict_top_player

out = predict_top_player(
    team="Geelong Cats",
    match_date="2024-05-01",
    opponent="Collingwood Magpies",
    stat_type="impact",
    top_k=5,
)
for p in out["players"]:
    print(p["rank"], p["player_id"], p["pred_impact"])
```

Or by `match_id` from the match feature table:

```python
predict_top_player(match_id="20240307_SydneySwans_MelbourneDemons", top_k=5)
```

## Retrain

```powershell
python train_models.py
```
