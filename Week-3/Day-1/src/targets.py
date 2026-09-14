"""Prediction targets: match winner + top-player definitions."""

from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Match-level targets
# ---------------------------------------------------------------------------
# Framing choice:
#   primary = classification: home_win (1/0), with draws as 0 (rare ~0.8%)
#   secondary = regression: home_margin = home_score - away_score
# Classification is the main Day-2 contract for "who wins"; margin is useful
# for ranking / calibration checks.


def add_match_targets(matches: pd.DataFrame) -> pd.DataFrame:
    df = matches.copy()
    df["home_margin"] = df["home_score"] - df["away_score"]
    df["match_result"] = np.select(
        [
            df["home_result"].eq("W"),
            df["home_result"].eq("L"),
            df["home_result"].eq("D"),
        ],
        ["home_win", "away_win", "draw"],
        default="unknown",
    )
    # Binary for simpler classifiers (draws counted as non-home-win)
    df["home_win"] = (df["match_result"] == "home_win").astype(int)
    df["is_draw"] = (df["match_result"] == "draw").astype(int)
    return df


# ---------------------------------------------------------------------------
# Player-game top-player targets
# ---------------------------------------------------------------------------
# Version A — top disposal-getter in that match (among players with non-null disposals)
# Version B — top goal-kicker in that match
# Version C — composite impact score (fantasy-style), then top in match
#
# COMPOSITE IMPACT (Brownlow/fantasy-style proxy):
#   impact = 3*kicks + 2*handballs + 3*marks + 4*tackles
#          + 6*goals + 1*behinds + 1*hit_outs
# Missing component stats are treated as 0 for the formula (common in older seasons).
# When source fantasy_points exists, we also keep it as impact_official.


IMPACT_WEIGHTS = {
    "kicks": 3.0,
    "handballs": 2.0,
    "marks": 3.0,
    "tackles": 4.0,
    "goals": 6.0,
    "behinds": 1.0,
    "hit_outs": 1.0,
}


def compute_impact_score(df: pd.DataFrame) -> pd.Series:
    score = pd.Series(0.0, index=df.index)
    for col, w in IMPACT_WEIGHTS.items():
        if col in df.columns:
            score = score + w * df[col].fillna(0.0)
    return score


def add_player_targets(player_games: pd.DataFrame) -> pd.DataFrame:
    df = player_games.copy()
    df["impact_score"] = compute_impact_score(df)
    if "fantasy_points" in df.columns:
        df["impact_official"] = df["fantasy_points"].fillna(df["impact_score"])
    else:
        df["impact_official"] = df["impact_score"]

    # Match key for within-game rankings (team+opp+date is enough at player grain)
    df["game_key"] = (
        df["match_date"].astype(str)
        + "|"
        + df[["team", "opponent"]].min(axis=1)
        + "|"
        + df[["team", "opponent"]].max(axis=1)
    )

    def _is_top(series: pd.Series) -> pd.Series:
        mx = series.max()
        if pd.isna(mx):
            return pd.Series(False, index=series.index)
        return series.eq(mx) & series.notna()

    df["is_top_disposals"] = (
        df.groupby("game_key", sort=False)["disposals"].transform(_is_top).astype(int)
    )
    df["is_top_goals"] = (
        df.groupby("game_key", sort=False)["goals"].transform(_is_top).astype(int)
    )
    df["is_top_impact"] = (
        df.groupby("game_key", sort=False)["impact_score"].transform(_is_top).astype(int)
    )
    return df


TARGET_DICTIONARY = [
    {
        "target_name": "home_win",
        "definition": "1 if home team won the match, else 0 (draws = 0)",
        "formula": "1[home_result == 'W']",
        "level": "match",
        "task_type": "classification",
    },
    {
        "target_name": "match_result",
        "definition": "3-way label: home_win / away_win / draw",
        "formula": "map(home_result)",
        "level": "match",
        "task_type": "multiclass",
    },
    {
        "target_name": "home_margin",
        "definition": "Home score minus away score (points)",
        "formula": "home_score - away_score",
        "level": "match",
        "task_type": "regression",
    },
    {
        "target_name": "is_top_disposals",
        "definition": "Player recorded the equal-highest disposals in that match",
        "formula": "1[disposals == max(disposals | game_key)]",
        "level": "player-game",
        "task_type": "classification",
    },
    {
        "target_name": "is_top_goals",
        "definition": "Player recorded the equal-highest goals in that match",
        "formula": "1[goals == max(goals | game_key)]",
        "level": "player-game",
        "task_type": "classification",
    },
    {
        "target_name": "is_top_impact",
        "definition": "Player had equal-highest composite impact in that match",
        "formula": "impact = 3K+2H+3M+4T+6G+1B+1HO; 1[impact == max(impact|game)]",
        "level": "player-game",
        "task_type": "classification",
    },
    {
        "target_name": "impact_score",
        "definition": "Fantasy/Brownlow-style continuous player output",
        "formula": "3*kicks + 2*handballs + 3*marks + 4*tackles + 6*goals + 1*behinds + 1*hit_outs",
        "level": "player-game",
        "task_type": "regression",
    },
]
