"""Objection handling playbook — grounded with Day-2 KB where possible."""

from __future__ import annotations

import re
from typing import Any, Callable


ObjectionHandler = Callable[[str, dict], str]


def detect_objection(text: str) -> str | None:
    t = text.lower()
    rules = [
        ("price", r"mehnga|expensive|zyada (hai|ho)|budget se|price high|costly|afford"),
        ("trust", r"trust|scam|fraud|yaqeen|reliable|pakka"),
        ("location", r"door|far|location|commute|traffic|area theek"),
        ("investment", r"roi|return|profit|investment risk|double"),
        ("builder", r"builder|developer|bahria trust|dha transfer"),
        ("maintenance", r"maintenance|mehnat|charges|society fee"),
    ]
    for name, pat in rules:
        if re.search(pat, t, re.I):
            return name
    return None


def handle_objection(
    kind: str,
    user_text: str,
    *,
    rag_retrieve: Callable[[str], list[dict]] | None = None,
    memory_summary: str = "",
) -> dict[str, Any]:
    """Return UrduLish reply + sources."""
    sources: list[str] = []
    ctx = ""
    if rag_retrieve:
        qmap = {
            "price": "payment plan cash Bahria installment",
            "trust": "developer DHA Bahria trust notes documents",
            "location": "locations DHA Bahria commute schools hospitals",
            "investment": "ROI guarantee investment returns FAQ",
            "builder": "developer Bahria DHA trust transfer",
            "maintenance": "maintenance society charges FAQ",
        }
        hits = rag_retrieve(qmap.get(kind, user_text))
        if hits:
            ctx = hits[0]["text"][:400]
            sources.append(f"rag:{hits[0].get('source')}")

    replies = {
        "price": (
            "Ji rate thoda premium feel ho sakta hai — "
            "payment plan aur comparable options dekh lete hain, phir decide karna. "
            f"Aap ka context: {memory_summary or 'budget confirm karein'}."
        ),
        "trust": (
            "Sahi sawal hai. Main sirf verified file se bolta hoon — "
            "andaza nahi. Docs / society process clear karwa dunga, aur visit pe khud dekh lena."
        ),
        "location": (
            "Commute important hai. Bataiye office ya daily route kidhar hai, "
            "us hisaab se nearer societies filter karun?"
        ),
        "investment": (
            "ROI guarantee nahi de sakta — RealEstate Hub returns promise nahi karta. "
            "Jo published payment plan / location facts hain woh clear bataunga."
        ),
        "builder": (
            "Builder / society process confirm karke batata hoon. "
            "DHA transfers aur Bahria allotment status file se verify hota hai."
        ),
        "maintenance": (
            "Maintenance usually society charge karti hai — exact monthly figure confirm karke batata hoon, guess nahi."
        ),
    }
    base = replies.get(kind, "Ji, aap ki concern samajh gaya — detail confirm karke batata hoon.")
    if ctx:
        base += f" File note: {ctx[:220]}"
    return {"reply": base, "objection": kind, "sources": sources}
