"""UrduLish conversational agent using Day-2 KB + memory + objections."""

from __future__ import annotations

import re
from typing import Any

from .day2_bridge import load_day2
from .memory import (
    CallMemory,
    remember_shortlist,
    resolve_references,
    update_memory_from_utterance,
)
from .objections import detect_objection, handle_objection
from .speech_behaviors import with_natural_prefix


def _fmt_prop_short(p: dict) -> str:
    return (
        f"{p.get('title')} ({p.get('price_display')}, {p.get('bedrooms')} bed, "
        f"{p.get('area')})"
    )


def generate_reply(user_text: str, mem: CallMemory) -> dict[str, Any]:
    """One conversational turn. Updates memory in place."""
    day2 = load_day2()
    mem = update_memory_from_utterance(mem, user_text)
    expanded = resolve_references(user_text, mem)
    used_tool = False
    sources: list[str] = []
    ack = True

    # Greeting / empty
    if not user_text.strip() or re.fullmatch(
        r"(hello|hi|salam|assalam.?o.?alaikum|haan|ji)\??",
        user_text.strip(),
        re.I,
    ):
        reply = (
            "Assalam-o-Alaikum sir! RealEstate Hub se baat ho rahi hai, main Ali. "
            "Aap buy karna chahte hain, rent, ya investment?"
        )
        out = with_natural_prefix(reply, acknowledge=False, user_text=user_text)
        mem.turns.append({"role": "user", "text": user_text})
        mem.turns.append({"role": "assistant", "text": out})
        return {
            "reply": out,
            "memory": mem.to_dict(),
            "used_tool": False,
            "sources": [],
            "intent": "greet",
        }

    # Objections first
    obj = detect_objection(user_text)
    if obj:
        mem.objections_seen.append(obj)
        handled = handle_objection(
            obj,
            user_text,
            rag_retrieve=lambda q: day2["retrieve"](q, top_k=2),
            memory_summary=mem.summary_urdulish(),
        )
        used_tool = bool(handled["sources"])
        sources = handled["sources"]
        # soft follow-up recommend if we have profile
        follow = ""
        if mem.budget_pkr or mem.city:
            recs = day2["recommend"](
                budget=mem.budget_text or mem.budget_pkr,
                city=mem.city,
                area=mem.area,
                bedrooms=mem.bedrooms,
                purpose="buy" if mem.purpose in {None, "invest", "buy"} else mem.purpose,
                amenities=mem.amenities or None,
                investment_goal=mem.investment_goal,
                top_n=2,
            )
            if recs:
                remember_shortlist(mem, recs)
                used_tool = True
                sources.extend([f"sql:{r['property_id']}" for r in recs])
                follow = " Alternative: " + "; ".join(_fmt_prop_short(r) for r in recs) + "."
        reply = with_natural_prefix(
            handled["reply"] + follow,
            used_tool=used_tool,
            acknowledge=True,
            user_text=user_text,
        )
        mem.turns.append({"role": "user", "text": user_text})
        mem.turns.append({"role": "assistant", "text": reply})
        return {
            "reply": reply,
            "memory": mem.to_dict(),
            "used_tool": used_tool,
            "sources": sources,
            "intent": f"objection:{obj}",
        }

    # Cheaper / options / area asks → recommend
    lower = expanded.lower()
    wants_options = any(
        w in lower
        for w in (
            "option",
            "recommend",
            "suggest",
            "kya hai",
            "dikhao",
            "sasti",
            "cheaper",
            "budget",
            "dha",
            "bahria",
            "clifton",
        )
    ) or (mem.budget_pkr and mem.city and len(user_text.split()) <= 8)

    if wants_options and (mem.city or mem.area or mem.budget_pkr or "memory:" in lower):
        purpose = mem.purpose or "buy"
        if purpose == "invest":
            purpose = "buy"
        recs = day2["recommend"](
            budget=mem.budget_text or mem.budget_pkr,
            city=mem.city,
            area=mem.area,
            bedrooms=mem.bedrooms,
            purpose=purpose if purpose in {"buy", "rent", "commercial"} else "buy",
            amenities=mem.amenities or None,
            investment_goal=mem.investment_goal,
            top_n=3,
        )
        # "us se sasti" — drop anything not cheaper than last highlighted property
        if any(w in lower for w in ("sasti", "cheaper", "us se kam")) and mem.last_shortlist:
            last_price = float(mem.last_shortlist[0].get("price_pkr") or 0)
            cheaper = [r for r in recs if float(r.get("price_pkr") or 0) < last_price]
            if cheaper:
                recs = cheaper[:2]
            elif mem.area and "dha" in mem.area.lower():
                # widen outside current area for cheaper comps
                recs = day2["recommend"](
                    budget=last_price * 0.9,
                    city=mem.city,
                    area=None,
                    bedrooms=mem.bedrooms,
                    purpose="buy",
                    top_n=2,
                )
                recs = [r for r in recs if float(r.get("price_pkr") or 0) < last_price][:2]
        used_tool = True
        if not recs:
            reply = (
                f"Hmm, {mem.summary_urdulish()} pe abhi tight match nahi mila. "
                "Budget thoda flex karain ya area widen karein?"
            )
        else:
            remember_shortlist(mem, recs)
            sources = [f"sql:{r['property_id']}" for r in recs]
            lines = [f"{i+1}) {_fmt_prop_short(r)}" for i, r in enumerate(recs)]
            reply = (
                f"Ji, aap ke liye yeh strong options hain: "
                + " ".join(lines)
                + " Weekend pe short visit arrange kar dein?"
            )
        out = with_natural_prefix(
            reply, used_tool=True, acknowledge=ack, user_text=user_text
        )
        mem.turns.append({"role": "user", "text": user_text})
        mem.turns.append({"role": "assistant", "text": out})
        return {
            "reply": out,
            "memory": mem.to_dict(),
            "used_tool": True,
            "sources": sources,
            "intent": "recommend",
            "shortlist": mem.last_shortlist,
        }

    # FAQ / factual via Day-2 answerer
    if any(
        w in lower
        for w in (
            "price",
            "kitne",
            "faq",
            "document",
            "maintenance",
            "payment",
            "school",
            "hospital",
            "available",
            "agent",
        )
    ):
        ans = day2["answer_question"](expanded)
        used_tool = True
        sources = ans.get("sources") or []
        # Compress into UrduLish spoken style
        raw = ans.get("answer") or ""
        spoken = raw.replace("Inventory matches:\n", "Inventory mein: ").replace("\n", " | ")
        spoken = spoken[:420]
        reply = with_natural_prefix(
            spoken, used_tool=True, acknowledge=True, user_text=user_text
        )
        mem.turns.append({"role": "user", "text": user_text})
        mem.turns.append({"role": "assistant", "text": reply})
        return {
            "reply": reply,
            "memory": mem.to_dict(),
            "used_tool": True,
            "sources": sources,
            "intent": "factual",
        }

    # Qualifying questions if profile incomplete
    if not mem.purpose:
        reply = "Theek hai — aap buy, rent, commercial, ya investment dekh rahe hain?"
    elif not mem.city:
        reply = "Kaun se city mein dekhna hai — Karachi, Lahore, ya Islamabad?"
    elif not mem.budget_text:
        reply = "Budget roughly kitna soch rahe hain? Jaise teen crore."
    elif not mem.area and mem.purpose == "buy":
        reply = f"Budget {mem.budget_text} note hai. Area / society prefer karenge — DHA, Bahria, ya koi aur?"
    else:
        reply = (
            f"Samajh gaya ({mem.summary_urdulish()}). "
            "Main options nikalta hoon — boliye 'options dikhao', ya koi specific society."
        )

    out = with_natural_prefix(reply, acknowledge=True, user_text=user_text)
    mem.turns.append({"role": "user", "text": user_text})
    mem.turns.append({"role": "assistant", "text": out})
    return {
        "reply": out,
        "memory": mem.to_dict(),
        "used_tool": False,
        "sources": [],
        "intent": "qualify",
    }
