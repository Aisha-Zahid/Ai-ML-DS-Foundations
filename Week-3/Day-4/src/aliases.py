"""Team nicknames / aliases → dataset team keys."""

from __future__ import annotations

import re

# Map common nicknames to Day-1 canonical names
NICKNAMES = {
    "pies": "Collingwood Magpies",
    "magpies": "Collingwood Magpies",
    "collingwood": "Collingwood Magpies",
    "cats": "Geelong Cats",
    "geelong": "Geelong Cats",
    "tigers": "Richmond Tigers",
    "richmond": "Richmond Tigers",
    "swans": "Sydney Swans",
    "sydney": "Sydney Swans",
    "bombers": "Essendon Bombers",
    "essendon": "Essendon Bombers",
    "blues": "Carlton Blues",
    "carlton": "Carlton Blues",
    "demons": "Melbourne Demons",
    "melbourne": "Melbourne Demons",
    "hawks": "Hawthorn Hawks",
    "hawthorn": "Hawthorn Hawks",
    "eagles": "West Coast Eagles",
    "west coast": "West Coast Eagles",
    "dockers": "Fremantle Dockers",
    "fremantle": "Fremantle Dockers",
    "crows": "Adelaide Crows",
    "adelaide": "Adelaide Crows",
    "power": "Port Adelaide Power",
    "port": "Port Adelaide Power",
    "port adelaide": "Port Adelaide Power",
    "saints": "St Kilda Saints",
    "st kilda": "St Kilda Saints",
    "bulldogs": "Western Bulldogs",
    "dogs": "Western Bulldogs",
    "western bulldogs": "Western Bulldogs",
    "lions": "Brisbane Lions",
    "brisbane": "Brisbane Lions",
    "suns": "Gold Coast Suns",
    "gold coast": "Gold Coast Suns",
    "giants": "Greater Western Sydney Giants",
    "gws": "Greater Western Sydney Giants",
    "kangaroos": "North Melbourne Kangaroos",
    "roos": "North Melbourne Kangaroos",
    "north melbourne": "North Melbourne Kangaroos",
    "north": "North Melbourne Kangaroos",
}


def normalize_team_query(text: str) -> str:
    try:
        import importlib.util
        from pathlib import Path

        path = Path(__file__).resolve().parents[2] / "Day-1" / "src" / "load_data.py"
        spec = importlib.util.spec_from_file_location("day1_load", path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod.normalize_team(text)
    except Exception:  # noqa: BLE001
        return str(text).replace("\t", " ").strip()


def resolve_team_alias(token: str) -> str | None:
    t = token.strip().lower()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    if t in NICKNAMES:
        return NICKNAMES[t]
    # try full normalize
    cand = normalize_team_query(token)
    if cand and cand.lower() != t:
        return cand
    # partial nickname contains
    for k, v in NICKNAMES.items():
        if k in t or t in k:
            return v
    return None


def extract_two_teams(query: str) -> tuple[str | None, str | None]:
    """Best-effort extract two clubs from a free-text query."""
    q = query.lower()
    found: list[str] = []
    # longer keys first
    keys = sorted(NICKNAMES.keys(), key=len, reverse=True)
    used_spans: list[tuple[int, int]] = []
    for k in keys:
        for m in re.finditer(rf"\b{re.escape(k)}\b", q):
            span = m.span()
            if any(not (span[1] <= a or span[0] >= b) for a, b in used_spans):
                continue
            team = NICKNAMES[k]
            if team not in found:
                found.append(team)
                used_spans.append(span)
            if len(found) >= 2:
                return found[0], found[1]
    # vs pattern with full names
    m = re.search(r"(.+?)\s+vs\.?\s+(.+)", query, flags=re.I)
    if m and len(found) < 2:
        a = resolve_team_alias(m.group(1).strip()) or normalize_team_query(m.group(1))
        b = resolve_team_alias(m.group(2).strip()) or normalize_team_query(m.group(2))
        return a or None, b or None
    if len(found) == 1:
        return found[0], None
    if len(found) >= 2:
        return found[0], found[1]
    return None, None
