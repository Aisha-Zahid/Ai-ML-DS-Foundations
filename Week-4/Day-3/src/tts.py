"""Text-to-speech: mock streaming (default) or Fish Audio if configured."""

from __future__ import annotations

import time
import wave
from pathlib import Path
from typing import Any, Iterator

from .config import AUDIO_OUT, FISH_API_KEY, FISH_REFERENCE_ID, VOICE_MODE
from .speech_behaviors import BargeInController, stream_text_chunks


def synthesize(
    text: str,
    *,
    out_path: Path | None = None,
    barge: BargeInController | None = None,
) -> dict[str, Any]:
    """
    Stream TTS. Mock mode writes a short silent wav + yields text chunks with timings.
    Live mode calls Fish Audio API when FISH_API_KEY is set.
    """
    AUDIO_OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    first_ms = None
    chunks_meta = []

    if VOICE_MODE == "live" and FISH_API_KEY:
        return _fish_tts(text, out_path=out_path, barge=barge, t0=t0)

    # mock streaming
    path = out_path or (AUDIO_OUT / "last_utterance.wav")
    for i, chunk in enumerate(stream_text_chunks(text)):
        if barge and barge.is_cancelled():
            return {
                "provider": "mock_tts",
                "interrupted": True,
                "path": str(path),
                "ttfa_ms": first_ms,
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                "chunks": chunks_meta,
            }
        now = round((time.perf_counter() - t0) * 1000, 1)
        if first_ms is None:
            first_ms = now
        chunks_meta.append({"i": i, "text": chunk, "t_ms": now})
        time.sleep(0.02)  # simulate audio chunk pacing

    _write_silent_wav(path, duration_s=max(0.4, len(text) / 40.0))
    return {
        "provider": "mock_tts",
        "interrupted": False,
        "path": str(path),
        "ttfa_ms": first_ms,
        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        "chunks": chunks_meta,
        "text": text,
    }


def _write_silent_wav(path: Path, duration_s: float = 1.0, rate: int = 16000) -> None:
    n = int(rate * duration_s)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * n)


def _fish_tts(
    text: str,
    *,
    out_path: Path | None,
    barge: BargeInController | None,
    t0: float,
) -> dict[str, Any]:
    try:
        import httpx
    except ImportError:
        return {
            "provider": "fish",
            "error": "httpx not installed",
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    path = out_path or (AUDIO_OUT / "fish_last.mp3")
    headers = {
        "Authorization": f"Bearer {FISH_API_KEY}",
        "Content-Type": "application/json",
        "model": "s2.1-pro",
    }
    body: dict[str, Any] = {"text": text}
    if FISH_REFERENCE_ID:
        body["reference_id"] = FISH_REFERENCE_ID
    first_ms = None
    with httpx.Client(timeout=60) as client:
        with client.stream(
            "POST", "https://api.fish.audio/v1/tts", headers=headers, json=body
        ) as r:
            if r.status_code >= 400:
                return {
                    "provider": "fish",
                    "error": r.read().decode("utf-8", errors="replace")[:300],
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                }
            chunks = []
            with path.open("wb") as f:
                for chunk in r.iter_bytes():
                    if barge and barge.is_cancelled():
                        return {
                            "provider": "fish",
                            "interrupted": True,
                            "path": str(path),
                            "ttfa_ms": first_ms,
                            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                        }
                    if first_ms is None:
                        first_ms = round((time.perf_counter() - t0) * 1000, 1)
                    f.write(chunk)
                    chunks.append(len(chunk))
    return {
        "provider": "fish",
        "interrupted": False,
        "path": str(path),
        "ttfa_ms": first_ms,
        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        "n_chunks": len(chunks),
        "text": text,
    }
