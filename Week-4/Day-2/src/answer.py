"""Grounded answer generation: structured + RAG, no free invention."""

from __future__ import annotations

import re
from typing import Any

from .rag import retrieve
from .recommend import recommend
from .structured import get_property, search_properties


def _format_property(p: dict) -> str:
    return (
        f"{p.get('property_id')}: {p.get('title')} | {p.get('city')} / {p.get('area')} | "
        f"{p.get('bedrooms')} bed | {p.get('size_value')} {p.get('size_unit')} | "
        f"{p.get('price_display')} | status={p.get('status')}"
    )


def _detect_city(q_lower: str) -> str | None:
    for c in ("karachi", "lahore", "islamabad"):
        if c in q_lower:
            return c.title()
    return None


def _detect_area(q_lower: str) -> str | None:
    mapping = [
        ("dha phase 6", "DHA Phase 6"),
        ("dha phase 8", "DHA Phase 8"),
        ("dha phase 5", "DHA Phase 5"),
        ("dha phase 2", "DHA Phase 2"),
        ("bahria enclave", "Bahria Enclave"),
        ("bahria town", "Bahria Town"),
        ("bahria", "Bahria"),
        ("clifton", "Clifton"),
        ("gulshan", "Gulshan"),
        ("johar town", "Johar Town"),
        ("johar", "Johar"),
        ("shahrah-e-faisal", "Shahrah-e-Faisal"),
        ("g-11", "G-11"),
        ("f-7", "F-7"),
    ]
    for key, val in mapping:
        if key in q_lower:
            return val
    return None


def answer_question(question: str) -> dict[str, Any]:
    """
    Hybrid answerer for Day-2 eval (no LLM required).
    Uses SQL for numeric/inventory facts and RAG for FAQ/brochure prose.
    """
    q = (question or "").strip()
    q_lower = q.lower()

    if any(
        w in q_lower
        for w in (
            "secret",
            "internal commission",
            "commission percentage",
            "reveal prompt",
            "system prompt",
        )
    ):
        return {
            "answer": (
                "I don't have that in the RealEstate Hub knowledge base "
                "(no internal commission or secret data on this line). "
                "I can connect you to a human agent instead of guessing."
            ),
            "sources": [],
            "route": "abstain",
            "grounded": True,
        }

    m_id = re.search(r"\b([A-Za-z]{2,3}-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+)\b", q)
    if m_id:
        row = get_property(m_id.group(1).upper())
        if not row:
            for cand in search_properties(available_only=False, limit=100):
                if cand["property_id"].lower() == m_id.group(1).lower():
                    row = get_property(cand["property_id"])
                    break
        if row:
            sources = [f"sql:properties:{row['property_id']}"]
            if "available" in q_lower or "availability" in q_lower:
                ans = (
                    f"{row['property_id']} ({row['title']}) status is **{row['status']}**. "
                    f"Listed price: {row.get('price_display')}."
                )
            else:
                ans = (
                    f"From inventory: {_format_property(row)}. "
                    f"Agent: {row.get('agent_name')} ({row.get('agent_id')}, "
                    f"{row.get('agent_phone')}). "
                    f"Developer: {row.get('developer_name')}."
                )
            return {
                "answer": ans,
                "sources": sources,
                "route": "structured",
                "grounded": True,
            }

    wants_inventory = any(
        w in q_lower
        for w in (
            "price",
            "kitne",
            "cost",
            "rate",
            "crore",
            "available",
            "availability",
            "rent",
            "monthly",
            "size",
            "marla",
            "sq yd",
            "sq ft",
            "kanal",
            "shop",
            "office",
            "how much",
        )
    )
    if wants_inventory:
        city = _detect_city(q_lower)
        area = _detect_area(q_lower)
        if "rent" in q_lower:
            purpose = "rent"
        elif any(w in q_lower for w in ("commercial", "office", "shop", "showroom")):
            purpose = "commercial"
        else:
            purpose = "buy"
        rows = search_properties(
            city=city, area=area, purpose=purpose, available_only=True, limit=5
        )
        if not rows and area:
            rows = search_properties(city=city, area=area, available_only=True, limit=5)
        if rows:
            sources = [f"sql:properties:{r['property_id']}" for r in rows]
            lines = [_format_property(r) for r in rows]
            return {
                "answer": "Inventory matches:\n" + "\n".join(lines),
                "sources": sources,
                "route": "structured",
                "grounded": True,
            }

    if any(w in q_lower for w in ("recommend", "suggest", "options", "budget", "suitable")):
        city = _detect_city(q_lower)
        if "rent" in q_lower:
            purpose = "rent"
        elif "shop" in q_lower or "commercial" in q_lower:
            purpose = "commercial"
        else:
            purpose = "buy"
        budget = None
        bm = re.search(r"(\d+(?:\.\d+)?)\s*crore", q_lower)
        if bm:
            budget = f"{bm.group(1)} crore"
        beds = None
        bed_m = re.search(r"(\d+)\s*bed", q_lower)
        if bed_m:
            beds = int(bed_m.group(1))
        area = _detect_area(q_lower)
        inv = None
        if "plot" in q_lower:
            inv = "plot"
        elif "apartment" in q_lower or "flat" in q_lower:
            inv = "apartment"
        recs = recommend(
            budget=budget,
            city=city,
            area=area,
            bedrooms=beds,
            purpose=purpose,
            investment_goal="plot"
            if "plot" in q_lower
            else ("growth" if "invest" in q_lower else None),
            property_type=None if purpose == "commercial" else inv,
            top_n=3,
        )
        if recs:
            sources = [f"sql:properties:{r['property_id']}" for r in recs]
            lines = [
                f"{_format_property(r)} | score={r['score']} | reasons={', '.join(r['reasons'])}"
                for r in recs
            ]
            return {
                "answer": "Recommendations (from available inventory only):\n"
                + "\n".join(lines),
                "sources": sources,
                "route": "recommend+structured",
                "grounded": True,
            }

    if "agent" in q_lower:
        from .db import fetch_all

        agents = fetch_all("SELECT * FROM agents")
        for a in agents:
            if a["name"].split()[0].lower() in q_lower or a["agent_id"].lower() in q_lower:
                return {
                    "answer": (
                        f"Agent {a['name']} ({a['agent_id']}) — desk: {a['desk']}, "
                        f"phone: {a['phone']}."
                    ),
                    "sources": [f"sql:agents:{a['agent_id']}"],
                    "route": "structured",
                    "grounded": True,
                }

    hits = retrieve(q, top_k=4)
    if hits:
        sources = [f"rag:{h['source']}#{h['chunk_id']}" for h in hits]
        context = "\n---\n".join(h["text"] for h in hits)
        ans = "Based on company documents (not invented):\n" + context[:1800]
        if ("guarantee" in q_lower and "return" in q_lower) or "roi guarantee" in q_lower:
            ans = "RealEstate Hub does not guarantee investment returns. " + ans
        return {
            "answer": ans,
            "sources": sources,
            "route": "rag",
            "grounded": True,
            "retrieval_scores": [h["score"] for h in hits],
        }

    return {
        "answer": (
            "I don't have that in the RealEstate Hub knowledge base. "
            "I can connect you to a human agent instead of guessing."
        ),
        "sources": [],
        "route": "abstain",
        "grounded": True,
    }
