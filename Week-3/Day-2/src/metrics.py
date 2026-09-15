"""Evaluation helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    roc_auc_score,
)


def classification_report_dict(y_true, y_pred, y_prob) -> dict:
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    y_prob = np.asarray(y_prob, dtype=float)
    out = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "brier": float(brier_score_loss(y_true, y_prob)),
    }
    # ROC needs both classes present
    if len(np.unique(y_true)) > 1:
        out["roc_auc"] = float(roc_auc_score(y_true, y_prob))
    else:
        out["roc_auc"] = float("nan")
    return out


def regression_report_dict(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
    }


def topk_hit_rate(
    df: pd.DataFrame,
    *,
    game_col: str,
    pred_col: str,
    actual_col: str,
    k: int = 5,
) -> float:
    """
    Fraction of games where the actual top scorer (max actual_col)
    appears in the top-k predicted players (by pred_col).
    """
    hits = 0
    n = 0
    for _, g in df.groupby(game_col, sort=False):
        if g[actual_col].isna().all() or g[pred_col].isna().all():
            continue
        actual_top = g.loc[g[actual_col].idxmax(), "player_id"]
        topk = set(g.nlargest(k, pred_col)["player_id"].astype(str))
        hits += int(str(actual_top) in topk)
        n += 1
    return float(hits / n) if n else float("nan")
