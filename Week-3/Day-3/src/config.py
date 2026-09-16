"""Paths and constants for Week 3 Day 3."""

from pathlib import Path

DAY3 = Path(__file__).resolve().parents[1]
DAY1 = DAY3.parent / "Day-1"

MATCH_FEATURES = DAY1 / "data" / "processed" / "match_features_v1.csv"
PLAYER_FEATURES = DAY1 / "data" / "processed" / "player_game_features_v1.csv"
PLAYERS_INFO = DAY1 / "data" / "raw" / "afl_datasets" / "afl_players_info_raw.csv"
PLAYERS_SEASON = DAY1 / "data" / "raw" / "afl_datasets" / "afl_players_seasonal_stats_raw.csv"

FACT_CARDS = DAY3 / "data" / "afl_fact_cards.txt"
RESULTS = DAY3 / "results"
DOCS = DAY3 / "docs"
LOGS = DAY3 / "logs"
