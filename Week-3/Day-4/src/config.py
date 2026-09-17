"""Week 3 Day 4 paths."""

from pathlib import Path

DAY4 = Path(__file__).resolve().parents[1]
DAY3 = DAY4.parent / "Day-3"
DAY2 = DAY4.parent / "Day-2"
DAY1 = DAY4.parent / "Day-1"

RESULTS = DAY4 / "results"
DOCS = DAY4 / "docs"
LOGS = DAY4 / "logs"

MATCH_FEATURES = DAY1 / "data" / "processed" / "match_features_v1.csv"
MATCH_IMPORTANCE = DAY2 / "results" / "match_feature_importance.csv"
