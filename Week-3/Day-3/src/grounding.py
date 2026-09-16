"""Grounding helpers: numbers in the reply should appear in tool output."""

from __future__ import annotations

import re
from typing import Any


def extract_numbers(text: str) -> list[str]:
    # Keep ints/floats as strings for substring checks
    return re.findall(r"\d+(?:\.\d+)?", text or "")


def grounding_check(answer: str, tool_log: list[dict[str, Any]]) -> dict:
    """
    For answers that look stat-heavy, check that numeric tokens appear in tool results.
    Heuristic: if no tools were called and answer has many digits, flag weak grounding.
    """
    nums = extract_numbers(answer)
    # Ignore years that often appear in prose without tools if tools empty — still flag
    tool_blob = " ".join(str(t.get("result", "")) for t in tool_log)
    missing = []
    for n in nums:
        if n in {"1", "2", "3", "4", "5"}:  # tiny ordinals / counts often narrative
            continue
        if n not in tool_blob:
            missing.append(n)
    return {
        "tool_calls": len(tool_log),
        "numbers_in_answer": nums,
        "numbers_missing_from_tools": missing,
        "grounded_ok": len(missing) == 0 or len(tool_log) > 0 and len(missing) <= 1,
        "tool_log": tool_log,
    }
