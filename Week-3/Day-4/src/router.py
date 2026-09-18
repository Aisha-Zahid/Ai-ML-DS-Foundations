"""Intent routing: heuristic first (stable), optional LLM refine."""

from __future__ import annotations

import re
from typing import Literal

Intent = Literal[
    "prediction_match",
    "prediction_player",
    "retrieval",
    "factual",
    "off_topic",
    "ambiguous",
]

PREDICTION_MATCH_PAT = re.compile(
    r"\b(who will win|will .+ beat|winner|tip|predict|prediction|odds|chance|"
    r"beat the|beat |defeat|favourite|favorite|match.?up)\b",
    re.I,
)
PREDICTION_PLAYER_PAT = re.compile(
    r"\b(top[- ]?scor\w*|top[- ]?player|most disposals|who will (kick|get|have)|"
    r"predict .+ (goals|disposals|impact)|leading goalkicker|fantasy)\b",
    re.I,
)
RETRIEVAL_PAT = re.compile(
    r"\b(how many|stats?|disposals|goals|record\b.{0,12}\bvs\b|head[- ]?to[- ]?head|h2h|"
    r"season (stats|totals)|last round|recent results|what were|"
    r"average|played in)\b",
    re.I,
)
OFFTOPIC_PAT = re.compile(
    r"\b(soccer|fifa|nba|nfl|nrl|cricket|netflix|crypto|python hello|"
    r"weather|pizza|translate|ignore previous|pretend you|"
    r"travel agent|bitcoin|super bowl|premier league)\b",
    re.I,
)
INJECTION_PAT = re.compile(
    r"(ignore (all )?(previous|prior|above) (instructions|rules|prompts)|"
    r"disregard (your|the) (system|instructions)|"
    r"you are now |jailbreak|developer mode|"
    r"override (your|the) (scope|rules|guardrails)|"
    r"act as (a |an )?(unrestricted|general|dan)|"
    r"do not (stay|remain) (in |an )?afl)",
    re.I,
)
AFL_HINT = re.compile(
    r"\b(afl|footy|geelong|collingwood|pies|cats|swans|tigers|bulldogs|"
    r"disposal|mark|behind|brownlow|premiership)\b",
    re.I,
)


def classify_intent(query: str) -> Intent:
    q = (query or "").strip()
    if not q:
        return "ambiguous"

    # Prompt-injection / scope override attempts → refuse
    if INJECTION_PAT.search(q):
        return "off_topic"

    # Vague tipping asks need clarification, not a hard refuse
    if re.fullmatch(r"(who wins\??|who will win\??|predict( the)? winner\??)", q, re.I):
        if "predict" in q.lower() and "winner" in q.lower():
            return "prediction_match"
        return "ambiguous"

    # Cross-sport / jailbreak style even if AFL is mentioned
    if re.search(
        r"\b(soccer|fifa|nba|nfl|nrl|cricket|crypto|netflix|python|super bowl)\b",
        q,
        re.I,
    ):
        if re.search(
            r"\b(compare|vs|versus|better|fitness|ignore previous|pretend|won)\b",
            q,
            re.I,
        ) or not re.search(r"\b(disposals|goals|record|round|fixture)\b", q, re.I):
            return "off_topic"

    if OFFTOPIC_PAT.search(q) and not AFL_HINT.search(q):
        return "off_topic"

    # Exact stats / H2H before tip patterns (e.g. "Cats record vs Tigers")
    if RETRIEVAL_PAT.search(q):
        return "retrieval"
    if PREDICTION_PLAYER_PAT.search(q) and not re.search(
        r"\b(how many|record|stats?|average|season)\b", q, re.I
    ):
        return "prediction_player"
    if PREDICTION_MATCH_PAT.search(q) or re.search(
        r"\b(will|tip|predict).{0,40}\b(pies|cats|swans|tigers|beat)\b", q, re.I
    ) or re.search(
        r"\b(pies|cats|swans|tigers)\b.{0,30}\b(beat|defeat)\b", q, re.I
    ):
        return "prediction_match"
    if AFL_HINT.search(q) or re.search(r"\b(team|player|match|round|club)\b", q, re.I):
        return "factual"
    if OFFTOPIC_PAT.search(q):
        return "off_topic"
    # Short non-AFL chit-chat
    if len(q.split()) <= 3 and not AFL_HINT.search(q):
        return "off_topic"
    return "ambiguous"


def route_target(intent: Intent) -> str:
    return {
        "prediction_match": "predict_match",
        "prediction_player": "predict_player",
        "retrieval": "retrieve",
        "factual": "retrieve",  # factual AFL Qs still prefer tools when possible
        "off_topic": "refuse",
        "ambiguous": "clarify",
    }[intent]
