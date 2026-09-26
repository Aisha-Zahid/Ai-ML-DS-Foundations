"""Call memory: budget, city, area, shortlist, and reference resolution."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CallMemory:
    name: str | None = None
    phone: str | None = None
    purpose: str | None = None  # buy / rent / commercial / invest
    city: str | None = None
    area: str | None = None
    budget_text: str | None = None
    budget_pkr: float | None = None
    bedrooms: int | None = None
    amenities: list[str] = field(default_factory=list)
    investment_goal: str | None = None
    last_shortlist: list[dict] = field(default_factory=list)
    last_property_id: str | None = None
    objections_seen: list[str] = field(default_factory=list)
    turns: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def summary_urdulish(self) -> str:
        bits = []
        if self.budget_text:
            bits.append(f"budget {self.budget_text}")
        if self.city:
            bits.append(self.city)
        if self.area:
            bits.append(self.area)
        if self.bedrooms:
            bits.append(f"{self.bedrooms} bed")
        if self.purpose:
            bits.append(self.purpose)
        return ", ".join(bits) if bits else "abhi details incomplete"


def parse_budget_pkr(text: str) -> tuple[str | None, float | None]:
    t = text.lower().replace(",", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*crore", t)
    if m:
        return f"{m.group(1)} crore", float(m.group(1)) * 10_000_000
    m = re.search(r"(\d+(?:\.\d+)?)\s*lakh", t)
    if m:
        return f"{m.group(1)} lakh", float(m.group(1)) * 100_000
    return None, None


def update_memory_from_utterance(mem: CallMemory, text: str) -> CallMemory:
    q = text.lower()
    bt, bp = parse_budget_pkr(text)
    if bt:
        mem.budget_text = bt
        mem.budget_pkr = bp

    for c in ("karachi", "lahore", "islamabad"):
        if c in q:
            mem.city = c.title()

    area_map = [
        ("dha phase 6", "DHA Phase 6"),
        ("dha phase 8", "DHA Phase 8"),
        ("dha phase 5", "DHA Phase 5"),
        ("bahria enclave", "Bahria Enclave"),
        ("bahria town", "Bahria Town"),
        ("bahria", "Bahria Town"),
        ("clifton", "Clifton"),
        ("gulshan", "Gulshan-e-Iqbal"),
        ("johar", "Johar Town"),
        ("g-11", "G-11"),
        ("f-7", "F-7"),
        ("dha", "DHA"),
    ]
    for key, val in area_map:
        if key in q:
            mem.area = val
            break

    bed = re.search(r"(\d+)\s*bed", q)
    if bed:
        mem.bedrooms = int(bed.group(1))

    if any(w in q for w in ("rent", "kiraya")):
        mem.purpose = "rent"
    elif any(w in q for w in ("commercial", "shop", "office", "showroom")):
        mem.purpose = "commercial"
    elif any(w in q for w in ("invest", "investment", "plot")):
        mem.purpose = "invest" if "invest" in q else mem.purpose or "buy"
        if "plot" in q:
            mem.investment_goal = "plot"
    elif any(w in q for w in ("buy", "kharid", "purchase")):
        mem.purpose = "buy"

    for a in ("gym", "pool", "security", "generator", "parking", "lawn", "furnished"):
        if a in q and a not in mem.amenities:
            mem.amenities.append(a)

    phone = re.search(r"(\+?92[\d\-]{10,}|\b03\d{9}\b)", text.replace(" ", ""))
    if phone:
        mem.phone = phone.group(1)

    name_m = re.search(r"\b(?:my name is|main|mera naam)\s+([A-Z][a-z]+)", text, re.I)
    if name_m:
        mem.name = name_m.group(1)

    return mem


def resolve_references(text: str, mem: CallMemory) -> str:
    """Expand 'us se sasti', 'wahi area', etc. using memory for downstream tools."""
    q = text
    lower = text.lower()
    hints = []
    if any(p in lower for p in ("us se sasti", "us se kam", "cheaper", "sasti")):
        if mem.budget_pkr:
            # ask for cheaper than last shortlist top price if available
            if mem.last_shortlist:
                top = mem.last_shortlist[0]
                hints.append(f"cheaper than {top.get('price_display')} in {mem.area or mem.city or ''}")
                # tighten budget to just under last option
                try:
                    mem.budget_pkr = float(top["price_pkr"]) * 0.95
                    mem.budget_text = f"under {top.get('price_display')}"
                except Exception:
                    pass
            else:
                hints.append("cheaper options")
    if any(p in lower for p in ("wahi area", "usi area", "same area", "udhar")):
        if mem.area:
            hints.append(mem.area)
    if any(p in lower for p in ("wahi city", "yahan", "yahan pe")) and mem.city:
        hints.append(mem.city)
    if "options" in lower or "kya options" in lower or "kya hai" in lower:
        if mem.city:
            hints.append(mem.city)
        if mem.area:
            hints.append(mem.area)
        if mem.budget_text:
            hints.append(f"budget {mem.budget_text}")
    if hints:
        q = f"{text} [memory: {', '.join(hints)}]"
    return q


def remember_shortlist(mem: CallMemory, props: list[dict]) -> None:
    mem.last_shortlist = props[:5]
    if props:
        mem.last_property_id = props[0].get("property_id")
