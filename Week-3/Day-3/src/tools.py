"""LangChain tools: structured AFL lookups + optional fact-card search."""

from __future__ import annotations

import json
import re
from typing import Optional

from langchain_core.tools import tool

from . import data_access as da
from .fact_cards import load_fact_documents

# Last tool payloads for grounding checks
_LAST_TOOL_LOG: list[dict] = []


def clear_tool_log() -> None:
    _LAST_TOOL_LOG.clear()


def get_tool_log() -> list[dict]:
    return list(_LAST_TOOL_LOG)


def _log(name: str, args: dict, result: dict | str) -> str:
    payload = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
    _LAST_TOOL_LOG.append({"tool": name, "args": args, "result": payload})
    return payload


@tool
def get_team_h2h_record(team_a: str, team_b: str, since_year: int = 0) -> str:
    """Exact head-to-head record between two AFL clubs from the match table.
    Use for 'record vs', 'how many times has X beaten Y'. Optional since_year filters seasons
    (0 means all years in the dataset)."""
    sy = None if not since_year else int(since_year)
    out = da.team_h2h_record(team_a, team_b, since_year=sy)
    return _log("get_team_h2h_record", {"team_a": team_a, "team_b": team_b, "since_year": since_year}, out)


@tool
def get_player_season_stats(player: str, year: int, team: str = "") -> str:
    """Exact season totals/averages for an AFL player in a given year from seasonal stats.
    Player can be name or player_id. Leave team empty unless you need a specific club year."""
    out = da.player_season_stats(player, year, team=team or None)
    return _log(
        "get_player_season_stats",
        {"player": player, "year": year, "team": team},
        out,
    )


@tool
def get_player_game_stats(
    player: str,
    match_date: str = "",
    year: int = 0,
    round_name: str = "",
) -> str:
    """Exact player-game stats (disposals, goals, impact) for one match.
    Prefer match_date as YYYY-MM-DD. Or pass year and round_name (e.g. year=2024, round_name='1')."""
    out = da.player_game_stats(
        player,
        match_date=match_date or None,
        year=year or None,
        round_name=round_name or None,
    )
    return _log(
        "get_player_game_stats",
        {
            "player": player,
            "match_date": match_date,
            "year": year,
            "round_name": round_name,
        },
        out,
    )


@tool
def get_recent_team_results(team: str, n: int = 5) -> str:
    """Exact recent AFL match results for a club (scores and opponents) from the match table."""
    out = da.recent_team_results(team, n=n)
    return _log("get_recent_team_results", {"team": team, "n": n}, out)


def _keyword_search(query: str, docs: list[str], k: int = 3) -> list[str]:
    tokens = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2]
    scored = []
    for d in docs:
        dl = d.lower()
        score = sum(1 for t in tokens if t in dl)
        if score:
            scored.append((score, d))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:k]]


@tool
def search_afl_fact_cards(query: str) -> str:
    """Semantic/keyword search over short AFL club/player fact cards derived from the dataset.
    Use for background blurbs only — NOT for exact match stats (use the other tools for numbers)."""
    docs = load_fact_documents()
    # Prefer simple embeddings-free search for reliability; still a retrieval tool
    hits = _keyword_search(query, docs, k=3)
    if not hits:
        out = {"hits": [], "message": "No fact cards matched."}
    else:
        out = {"hits": hits, "note": "Fact cards are summaries; verify numbers with structured tools."}
    return _log("search_afl_fact_cards", {"query": query}, out)


def get_all_tools():
    return [
        get_team_h2h_record,
        get_player_season_stats,
        get_player_game_stats,
        get_recent_team_results,
        search_afl_fact_cards,
    ]
