"""Rate / abuse handling for the AFL assistant."""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from .config import RATE_LIMIT_PER_MIN

INJECTION_PAT = re.compile(
    r"(ignore (all )?(previous|prior|above) (instructions|rules|prompts)|"
    r"disregard (your|the) (system|instructions)|"
    r"you are now |jailbreak|developer mode|"
    r"override (your|the) (scope|rules|guardrails)|"
    r"act as (a |an )?(unrestricted|general|dan)|"
    r"do not (stay|remain) (in |an )?afl|"
    r"reveal (your|the) (system )?prompt)",
    re.I,
)

REFUSAL = (
    "I'm built for AFL chat, stats lookups, and match/player predictions only. "
    "I won't follow instructions that try to override that scope."
)


@dataclass
class AbuseDecision:
    blocked: bool
    reason: str = ""
    response: str = ""


class AbuseGuard:
    """In-memory rate limit + injection / repeated off-topic probing."""

    def __init__(self, per_minute: int = RATE_LIMIT_PER_MIN) -> None:
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._offtopic_streak: dict[str, int] = defaultdict(int)

    def check(self, key: str, message: str, *, is_offtopic_route: bool = False, count_hit: bool = True) -> AbuseDecision:
        now = time.time()
        q = self._hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if count_hit:
            if len(q) >= self.per_minute:
                return AbuseDecision(
                    True,
                    "rate_limit",
                    f"Too many requests ({self.per_minute}/min). Please wait a moment.",
                )
            q.append(now)
        elif len(q) >= self.per_minute:
            return AbuseDecision(
                True,
                "rate_limit",
                f"Too many requests ({self.per_minute}/min). Please wait a moment.",
            )

        if INJECTION_PAT.search(message or ""):
            self._offtopic_streak[key] += 1
            return AbuseDecision(True, "prompt_injection", REFUSAL)

        if is_offtopic_route:
            self._offtopic_streak[key] += 1
            if self._offtopic_streak[key] >= 4:
                return AbuseDecision(
                    True,
                    "offtopic_probe",
                    REFUSAL
                    + " Repeated off-topic requests are blocked for this conversation — "
                    "ask an AFL stats or tipping question to continue.",
                )
        else:
            self._offtopic_streak[key] = 0

        return AbuseDecision(False)
