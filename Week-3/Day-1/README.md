# Week 3 Day 1 — AFL Data Foundations

EDA, target definitions, leakage-safe features, and a shared time-based split for the AFL week.

## Setup

```powershell
cd Week-3/Day-1
pip install -r requirements.txt
```

Dataset (Google Drive zip) should sit under `data/raw/` (already extracted to `data/raw/afl_datasets/` if you used the course link).

Rebuild features + dictionaries:

```powershell
python build_features.py
```

Open the notebook:

```powershell
jupyter notebook afl_data_foundations.ipynb
```

## Deliverables

| Item | Path |
|------|------|
| Notebook | `afl_data_foundations.ipynb` |
| Data dictionary + targets | `docs/data_dictionary_targets.md` |
| Feature dictionary | `docs/feature_dictionary.md` |
| Match features v1 | `data/processed/match_features_v1.csv` (+ parquet) |
| Player-game features v1 | `data/processed/player_game_features_v1.csv` (build locally; large file) |
| Shared split helper | `src/splits.py` |

## Targets (short)

- Match: `home_win` (classification), `home_margin` (regression)
- Player: `is_top_disposals`, `is_top_goals`, `is_top_impact` with  
  `impact = 3*kicks + 2*handballs + 3*marks + 4*tackles + 6*goals + 1*behinds + 1*hit_outs`

## Split

Train: `year < 2024`  
Holdout: `year >= 2024`  
Function: `src.splits.time_based_split`
