"""Structured JSONL logging for monitoring."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import LOGS


def log_event(event: dict[str, Any], path: Path | None = None) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    out = path or (LOGS / "assistant.jsonl")
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


class Timer:
    def __init__(self) -> None:
        self.t0 = time.perf_counter()

    def ms(self) -> float:
        return round((time.perf_counter() - self.t0) * 1000, 1)
