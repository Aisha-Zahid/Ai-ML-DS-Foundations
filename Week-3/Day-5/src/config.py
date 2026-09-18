"""Week 3 Day 5 paths."""

from pathlib import Path
import os

DAY5 = Path(__file__).resolve().parents[1]
DAY4 = DAY5.parent / "Day-4"
DAY3 = DAY5.parent / "Day-3"
DAY2 = DAY5.parent / "Day-2"
DAY1 = DAY5.parent / "Day-1"

RESULTS = DAY5 / "results"
DOCS = DAY5 / "docs"
LOGS = DAY5 / "logs"

TOOL_TIMEOUT_SEC = float(os.getenv("TOOL_TIMEOUT_SEC", "90"))
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "30"))
