"""Week 3 Day 2 paths and feature contracts."""

from __future__ import annotations

from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1]
DAY1 = DAY2.parent / "Day-1"

MATCH_FEATURES = DAY1 / "data" / "processed" / "match_features_v1.csv"
PLAYER_FEATURES = DAY1 / "data" / "processed" / "player_game_features_v1.csv"

MODELS_DIR = DAY2 / "models"
RESULTS_DIR = DAY2 / "results"
DOCS_DIR = DAY2 / "docs"

MATCH_MODEL_PATH = MODELS_DIR / "match_winner.joblib"
PLAYER_MODEL_PATH = MODELS_DIR / "top_player.joblib"
META_PATH = MODELS_DIR / "model_meta.joblib"

# Post-match / target leakage — never use as inputs
MATCH_LEAK_COLS = {
    "home_score",
    "away_score",
    "home_margin",
    "match_result",
    "is_draw",
    "home_win",
}

MATCH_ID_COLS = {"match_id", "match_date", "year", "round"}

MATCH_CAT_COLS = ["home_team", "away_team", "venue", "home_state", "away_state"]

MATCH_NUM_COLS = [
    "home_rest_days",
    "home_win_streak_pre",
    "home_win_rate_l3",
    "home_avg_pf_l3",
    "home_avg_pa_l3",
    "home_avg_margin_l3",
    "home_games_l3",
    "home_win_rate_l5",
    "home_avg_pf_l5",
    "home_avg_pa_l5",
    "home_avg_margin_l5",
    "home_games_l5",
    "home_win_rate_l8",
    "home_avg_pf_l8",
    "home_avg_pa_l8",
    "home_avg_margin_l8",
    "home_games_l8",
    "home_ladder_points_pre",
    "home_season_games_pre",
    "home_ladder_pct_pre",
    "away_rest_days",
    "away_win_streak_pre",
    "away_win_rate_l3",
    "away_avg_pf_l3",
    "away_avg_pa_l3",
    "away_avg_margin_l3",
    "away_games_l3",
    "away_win_rate_l5",
    "away_avg_pf_l5",
    "away_avg_pa_l5",
    "away_avg_margin_l5",
    "away_games_l5",
    "away_win_rate_l8",
    "away_avg_pf_l8",
    "away_avg_pa_l8",
    "away_avg_margin_l8",
    "away_games_l8",
    "away_ladder_points_pre",
    "away_season_games_pre",
    "away_ladder_pct_pre",
    "h2h_home_win_rate",
    "h2h_games",
    "rest_days_diff",
    "ladder_pct_diff",
    "form_margin_diff_l5",
    "is_interstate",
    "venue_code",
    "crowd",
]

PLAYER_NUM_COLS = [
    "avg_disposals_l3",
    "avg_disposals_l5",
    "avg_goals_l3",
    "avg_goals_l5",
    "avg_impact_l3",
    "avg_impact_l5",
    "avg_fantasy_l3",
    "avg_fantasy_l5",
    "games_played_pre",
    "player_rest_days",
    "career_game_count",
]

PLAYER_CAT_COLS = ["team"]

HOLDOUT_YEAR = 2024
