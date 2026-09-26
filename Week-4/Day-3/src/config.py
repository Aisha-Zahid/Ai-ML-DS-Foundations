"""Week 4 Day 3 paths."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

DAY3 = Path(__file__).resolve().parents[1]
DAY2 = DAY3.parent / "Day-2"
DAY1 = DAY3.parent / "Day-1"

load_dotenv(DAY3 / ".env")

RESULTS = DAY3 / "results"
RECORDINGS = DAY3 / "recordings"
AUDIO_OUT = DAY3 / "audio_out"
DOCS = DAY3 / "docs"

SYSTEM_PROMPT = DAY1 / "prompts" / "realestate_voice_agent_system.txt"

# Latency budget (ms) — voice agent target under 2s end-to-end when warm
BUDGET_STT_MS = 500
BUDGET_LLM_MS = 800
BUDGET_TTS_FIRST_MS = 400
BUDGET_TOTAL_MS = 2000

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
FISH_API_KEY = os.getenv("FISH_API_KEY", "")
FISH_REFERENCE_ID = os.getenv("FISH_REFERENCE_ID", "")
VOICE_MODE = os.getenv("VOICE_MODE", "mock")  # mock | live
