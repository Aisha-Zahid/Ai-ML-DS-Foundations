"""Shared paths for Week 3 Day 1."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw" / "afl_datasets"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DOCS_DIR = BASE_DIR / "docs"

# Raw file names (as shipped in the Drive zip)
PLAYERS_INFO = RAW_DIR / "afl_players_info_raw.csv"
PLAYERS_ROUND = (
    RAW_DIR
    / "afl_players_round_by_round_stats_raw - afl_players_round_by_round_stats_raw.csv.csv"
)
PLAYERS_SEASON = RAW_DIR / "afl_players_seasonal_stats_raw.csv"
TEAM_MATCHES = (
    RAW_DIR / "team_matches_home_away_raw - team_matches_home_away_raw.csv.csv"
)

FEATURE_MATCH_CSV = PROCESSED_DIR / "match_features_v1.csv"
FEATURE_MATCH_PARQUET = PROCESSED_DIR / "match_features_v1.parquet"
FEATURE_PLAYER_CSV = PROCESSED_DIR / "player_game_features_v1.csv"
FEATURE_DICT = DOCS_DIR / "feature_dictionary.md"
DATA_DICT = DOCS_DIR / "data_dictionary_targets.md"
