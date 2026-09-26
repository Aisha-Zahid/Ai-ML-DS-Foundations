"""Natural UrduLish speech behaviors: fillers, acks, barge-in, pauses."""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field

FILLERS = [
    "Hmm…",
    "Acha…",
    "Ek second sir…",
    "Ji, thoda wait karein…",
    "Haan…",
]

ACKS = [
    "Ji bilkul.",
    "Samajh gaya.",
    "Theek hai.",
    "Okay ji.",
    "Haan sir, bilkul valid point hai.",
]

THINKING = [
    "Ek second, inventory check karta hoon…",
    "Hmm, options dekh raha hoon…",
    "Ji, abhi filter karta hoon…",
]

SOFT_LAUGH = [
    "Haha, theek hai.",
    "Heh, samajh gaya.",
]


@dataclass
class BargeInController:
    """If caller interrupts, cancel pending TTS playback."""

    cancelled: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def interrupt(self) -> None:
        with self._lock:
            self.cancelled = True

    def reset(self) -> None:
        with self._lock:
            self.cancelled = False

    def is_cancelled(self) -> bool:
        with self._lock:
            return self.cancelled


def pick_ack() -> str:
    return random.choice(ACKS)


def pick_filler() -> str:
    return random.choice(FILLERS)


def pick_thinking() -> str:
    return random.choice(THINKING)


def maybe_soft_laugh(user_text: str) -> str | None:
    t = user_text.lower()
    if any(w in t for w in ("joke", "hasna", "funny", "haha")):
        return random.choice(SOFT_LAUGH)
    return None


def with_natural_prefix(
    reply: str,
    *,
    used_tool: bool = False,
    acknowledge: bool = False,
    user_text: str = "",
) -> str:
    """Prepend light human glue — at most one prefix style."""
    reply = reply.strip()
    laugh = maybe_soft_laugh(user_text)
    if laugh:
        return f"{laugh} {reply}"
    if used_tool:
        return f"{pick_thinking()} {reply}"
    if acknowledge:
        return f"{pick_ack()} {reply}"
    return reply


def simulate_thinking_pause(ms: int = 180) -> None:
    time.sleep(ms / 1000.0)


def stream_text_chunks(text: str, chunk_chars: int = 42):
    """Yield reply in chunks (simulates TTS streaming tokens)."""
    text = text.strip()
    i = 0
    while i < len(text):
        # prefer break on space
        j = min(i + chunk_chars, len(text))
        if j < len(text):
            sp = text.rfind(" ", i, j)
            if sp > i:
                j = sp + 1
        yield text[i:j]
        i = j
