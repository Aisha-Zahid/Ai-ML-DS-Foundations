"""Baselines for match winner and top player."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .metrics import classification_report_dict, regression_report_dict, topk_hit_rate


def match_baseline_always_home(holdout: pd.DataFrame) -> dict:
    y = holdout["home_win"].astype(int)
    pred = np.ones(len(y), dtype=int)
    prob = np.full(len(y), y.mean() if len(y) else 0.5)  # use train prior if passed later
    # Use empirical home win rate on holdout labels only for reporting shape;
    # caller should pass train_home_rate for honest probs.
    return classification_report_dict(y, pred, prob)


def match_baseline_always_home_with_prior(holdout: pd.DataFrame, train_home_rate: float) -> dict:
    y = holdout["home_win"].astype(int)
    pred = np.ones(len(y), dtype=int)
    prob = np.full(len(y), float(train_home_rate))
    return classification_report_dict(y, pred, prob)


def match_baseline_higher_ladder(holdout: pd.DataFrame) -> dict:
    """Predict home win if home ladder_pct_pre >= away ladder_pct_pre."""
    y = holdout["home_win"].astype(int)
    home_better = holdout["home_ladder_pct_pre"].fillna(0.5) >= holdout[
        "away_ladder_pct_pre"
    ].fillna(0.5)
    pred = home_better.astype(int).to_numpy()
    # crude probability: 0.55 if home favoured else 0.45
    prob = np.where(pred == 1, 0.55, 0.45)
    return classification_report_dict(y, pred, prob)


def add_player_game_key(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    a = out["team"].astype(str)
    b = out["opponent"].astype(str)
    out["game_key"] = (
        out["match_date"].astype(str)
        + "|"
        + np.minimum(a, b)
        + "|"
        + np.maximum(a, b)
    )
    return out


def player_baseline_prev_leader(
    train: pd.DataFrame, holdout: pd.DataFrame, *, k: int = 5
) -> dict:
    """
    Baseline: rank players in a holdout match by their previous-game impact
    (avg_impact_l3 as proxy / last known form). If missing, use career-ish avg_impact_l5.
    """
    h = add_player_game_key(holdout)
    score = h["avg_impact_l3"].fillna(h["avg_impact_l5"]).fillna(0.0)
    h = h.assign(baseline_pred=score)
    reg = regression_report_dict(h["impact_score"].fillna(0), h["baseline_pred"])
    topk = topk_hit_rate(
        h, game_col="game_key", pred_col="baseline_pred", actual_col="impact_score", k=k
    )
    # also: "season average leader" style using avg_impact_l5 only
    h2 = h.assign(baseline_pred2=h["avg_impact_l5"].fillna(0.0))
    topk_season = topk_hit_rate(
        h2, game_col="game_key", pred_col="baseline_pred2", actual_col="impact_score", k=k
    )
    return {
        **{f"reg_{kk}": vv for kk, vv in reg.items()},
        f"topk{k}_prev_form": topk,
        f"topk{k}_seasonish_avg": topk_season,
        "n_holdout_rows": int(len(h)),
        "n_holdout_games": int(h["game_key"].nunique()),
    }
