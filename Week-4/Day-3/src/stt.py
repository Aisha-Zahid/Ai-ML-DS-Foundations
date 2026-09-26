"""Speech-to-text: mock (default) or Deepgram if key + live mode."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .config import DEEPGRAM_API_KEY, VOICE_MODE


def transcribe(audio_path: str | Path | None = None, *, text_override: str | None = None) -> dict[str, Any]:
    """
    Returns transcript + latency_ms.
    In mock/classroom mode, pass text_override (simulates STT output).
    """
    t0 = time.perf_counter()
    if text_override is not None:
        time.sleep(0.05)  # simulate STT partial finalize
        return {
            "text": text_override.strip(),
            "provider": "mock_stt",
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            "partials": _fake_partials(text_override.strip()),
        }

    if VOICE_MODE == "live" and DEEPGRAM_API_KEY and audio_path:
        return _deepgram_file(Path(audio_path), t0)

    # fallback: empty
    return {
        "text": "",
        "provider": "none",
        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        "partials": [],
        "error": "No transcript: provide text_override or DEEPGRAM_API_KEY + audio",
    }


def _fake_partials(text: str) -> list[str]:
    words = text.split()
    out = []
    buf = []
    for w in words:
        buf.append(w)
        if len(buf) % 3 == 0:
            out.append(" ".join(buf))
    if text and (not out or out[-1] != text):
        out.append(text)
    return out


def _deepgram_file(path: Path, t0: float) -> dict[str, Any]:
    try:
        import httpx
    except ImportError:
        return {
            "text": "",
            "provider": "deepgram",
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            "error": "httpx not installed",
        }
    if not path.exists():
        return {
            "text": "",
            "provider": "deepgram",
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            "error": f"missing audio {path}",
        }
    url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true"
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}
    with path.open("rb") as f:
        audio = f.read()
    with httpx.Client(timeout=60) as client:
        r = client.post(url, headers=headers, content=audio)
    latency = round((time.perf_counter() - t0) * 1000, 1)
    if r.status_code >= 400:
        return {
            "text": "",
            "provider": "deepgram",
            "latency_ms": latency,
            "error": r.text[:300],
        }
    data = r.json()
    text = (
        data.get("results", {})
        .get("channels", [{}])[0]
        .get("alternatives", [{}])[0]
        .get("transcript", "")
    )
    return {"text": text, "provider": "deepgram", "latency_ms": latency, "raw": data}
