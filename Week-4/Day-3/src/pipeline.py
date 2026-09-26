"""Speech → reason → voice pipeline with latency tracking."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .agent import generate_reply
from .config import BUDGET_TOTAL_MS, RESULTS
from .memory import CallMemory
from .speech_behaviors import BargeInController, simulate_thinking_pause
from .stt import transcribe
from .tts import synthesize


class VoicePipeline:
    def __init__(self) -> None:
        self.memory = CallMemory()
        self.barge = BargeInController()
        self.latency_log: list[dict] = []
        # Warm Day-2 SQLite + TF-IDF so first spoken turn stays near budget
        from .day2_bridge import load_day2

        load_day2()

    def interrupt(self) -> None:
        self.barge.interrupt()

    def reset_call(self) -> None:
        self.memory = CallMemory()
        self.barge.reset()

    def turn(
        self,
        *,
        user_text: str | None = None,
        audio_path: str | Path | None = None,
        speak: bool = True,
    ) -> dict[str, Any]:
        """
        Full turn: STT (or text) → agent → TTS.
        Target: total_ms under ~2000 when warm (mock path).
        """
        self.barge.reset()
        t0 = time.perf_counter()

        stt = transcribe(audio_path, text_override=user_text)
        text = (stt.get("text") or "").strip()
        t_stt = stt.get("latency_ms", 0)

        t_reason0 = time.perf_counter()
        # tiny natural pause before answering (human-like)
        simulate_thinking_pause(80)
        agent_out = generate_reply(text, self.memory)
        t_reason = round((time.perf_counter() - t_reason0) * 1000, 1)

        tts_meta: dict[str, Any] = {}
        if speak:
            tts_meta = synthesize(agent_out["reply"], barge=self.barge)

        total = round((time.perf_counter() - t0) * 1000, 1)
        row = {
            "user": text,
            "reply": agent_out["reply"],
            "intent": agent_out.get("intent"),
            "stt_ms": t_stt,
            "reason_ms": t_reason,
            "tts_ttfa_ms": tts_meta.get("ttfa_ms"),
            "tts_ms": tts_meta.get("latency_ms"),
            "total_ms": total,
            "under_2s": total <= BUDGET_TOTAL_MS,
            "interrupted": tts_meta.get("interrupted", False),
            "sources": agent_out.get("sources"),
            "memory": agent_out.get("memory"),
            "stt_provider": stt.get("provider"),
            "tts_provider": tts_meta.get("provider"),
        }
        self.latency_log.append(row)
        return row

    def save_latency_log(self, path: Path | None = None) -> Path:
        import json

        RESULTS.mkdir(parents=True, exist_ok=True)
        out = path or (RESULTS / "latency_log.json")
        out.write_text(json.dumps(self.latency_log, indent=2, ensure_ascii=False), encoding="utf-8")
        return out
