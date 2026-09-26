"""Property recommendation engine on structured filters + light ranking."""

from __future__ import annotations

from typing import Any

from .structured import get_property, search_properties

# amenity aliases clients might say
AMENITY_ALIASES = {
    "gym": "gym",
    "pool": "pool",
    "swimming": "pool",
    "security": "security",
    "generator": "generator",
    "parking": "parking",
    "lawn": "lawn",
    "sea view": "sea_view",
    "seaview": "sea_view",
    "furnished": "furnished",
}


def parse_crore_to_pkr(text: str | float | int | None) -> float | None:
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    t = str(text).lower().replace(",", "").strip()
    if "crore" in t or "cr" in t:
        num = "".join(ch if ch.isdigit() or ch == "." else " " for ch in t).split()
        if not num:
            return None
        return float(num[0]) * 10_000_000
    if "lakh" in t:
        num = "".join(ch if ch.isdigit() or ch == "." else " " for ch in t).split()
        if not num:
            return None
        return float(num[0]) * 100_000
    digits = "".join(ch if ch.isdigit() or ch == "." else "" for ch in t)
    return float(digits) if digits else None


def recommend(
    *,
    budget: str | float | int | None = None,
    city: str | None = None,
    area: str | None = None,
    bedrooms: int | None = None,
    purpose: str = "buy",
    amenities: list[str] | None = None,
    investment_goal: str | None = None,
    property_type: str | None = None,
    top_n: int = 3,
) -> list[dict[str, Any]]:
    """
    Recommend available properties.
    Budget is max price (buy/commercial) or max monthly rent when purpose=rent.
    """
    max_price = parse_crore_to_pkr(budget)
    # soft budget band: allow 10% over for near-misses then filter score
    query_max = max_price * 1.1 if max_price else None

    rows = search_properties(
        city=city,
        area=area,
        purpose=purpose,
        bedrooms=bedrooms,
        max_price=query_max,
        property_type=property_type,
        available_only=True,
        limit=50,
    )

    wanted = []
    if amenities:
        for a in amenities:
            key = AMENITY_ALIASES.get(a.lower().strip(), a.lower().strip().replace(" ", "_"))
            wanted.append(key)

    scored: list[tuple[float, dict]] = []
    for r in rows:
        score = 0.0
        reasons: list[str] = []
        price = float(r["price_pkr"])
        if max_price:
            if price <= max_price:
                score += 3.0
                reasons.append("within budget")
            elif price <= max_price * 1.1:
                score += 1.0
                reasons.append("slightly over budget")
            else:
                continue
        if city and r["city"].lower() == city.lower():
            score += 2.0
            reasons.append("city match")
        if area and area.lower() in str(r["area"]).lower():
            score += 2.5
            reasons.append("area match")
        if bedrooms is not None and int(r["bedrooms"]) == int(bedrooms):
            score += 1.5
            reasons.append(f"{bedrooms} beds")
        am = str(r.get("amenities") or "")
        for w in wanted:
            if w in am:
                score += 1.0
                reasons.append(f"has {w}")
        if investment_goal:
            tag = str(r.get("investment_tag") or "")
            g = investment_goal.lower()
            if g in tag or (g in {"growth", "apartment"} and "apartment" in tag):
                score += 1.2
                reasons.append("investment tag fit")
            if g in {"plot", "long term", "long-term"} and "plot" in tag:
                score += 1.2
                reasons.append("plot / long-term fit")
            if g in {"yield", "commercial"} and "commercial" in tag:
                score += 1.2
                reasons.append("commercial yield fit")
        enriched = dict(r)
        enriched["score"] = round(score, 2)
        enriched["reasons"] = reasons
        # attach agent for booking later
        full = get_property(r["property_id"])
        if full:
            enriched["agent_name"] = full.get("agent_name")
            enriched["agent_phone"] = full.get("agent_phone")
            enriched["developer_name"] = full.get("developer_name")
            enriched["payment_plan_name"] = full.get("payment_plan_name")
        scored.append((score, enriched))

    scored.sort(key=lambda x: (-x[0], x[1]["price_pkr"]))
    return [item for _, item in scored[:top_n]]
