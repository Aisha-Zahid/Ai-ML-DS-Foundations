"""LangGraph state + nodes for AFL orchestrator."""

from __future__ import annotations

import re
from typing import Any, Literal, Optional, TypedDict

from .aliases import extract_two_teams, resolve_team_alias
from .fixtures import find_fixture, top_prediction_drivers
from .router import classify_intent, route_target
from .services import (
    dumps,
    predict_match,
    predict_top,
    retrieve_h2h,
    retrieve_player_game,
    retrieve_player_season,
    retrieve_recent,
    tool_ok,
)


# Consistent prediction framing (Day-5 hardening)
PREDICTION_DISCLAIMER = (
    "Predicted probability, not a certainty — treat this as a model tip from "
    "historical form features, not a guarantee."
)


class AFLState(TypedDict, total=False):
    user_query: str
    history: list
    intent: str
    route: str
    teams: list
    player: str
    match_date: str
    tool_name: str
    tool_result: dict
    tool_error: str
    needs_clarification: bool
    clarification_prompt: str
    final_response: str
    trace: list


def _trace(state: AFLState, msg: str) -> list:
    t = list(state.get("trace") or [])
    t.append(msg)
    return t


def router_node(state: AFLState) -> dict:
    q = state.get("user_query") or ""
    # Multi-turn: intent from the follow-up line; entities from the full text
    intent_q = q
    if "User follow-up:" in q:
        intent_q = q.split("User follow-up:")[-1].strip() or q
    intent = classify_intent(intent_q)
    # If follow-up is a thin tip ask, force prediction when prior named clubs+tip
    if (
        intent in {"ambiguous", "factual", "retrieval"}
        and "User follow-up:" in q
        and re.search(r"\b(who wins|tip|predict|winner|matchup)\b", intent_q, re.I)
        and re.search(r"\b(tip|predict|beat|vs)\b", q, re.I)
    ):
        intent = "prediction_match"
    route = route_target(intent)
    a, b = extract_two_teams(q)
    teams = [t for t in (a, b) if t]
    return {
        "intent": intent,
        "route": route,
        "teams": teams,
        "trace": _trace(state, f"[router] intent={intent} route={route} teams={teams}"),
    }


def refuse_node(state: AFLState) -> dict:
    resp = (
        "I'm built for AFL chat, stats lookups, and match/player predictions only. "
        "Ask about a club, a player, a record, or who might win a matchup."
    )
    return {
        "final_response": resp,
        "trace": _trace(state, "[refuse] off-topic"),
    }


def clarify_node(state: AFLState) -> dict:
    intent = state.get("intent")
    if intent and intent.startswith("prediction") and len(state.get("teams") or []) < 2:
        prompt = (
            "I need two AFL clubs to tip a match (full names or nicknames like Pies/Cats). "
            "Example: 'Will the Pies beat the Cats on 2024-03-15?'"
        )
    elif intent == "prediction_player" and not (state.get("teams") or []):
        prompt = "Which team and match date should I rank players for?"
    else:
        prompt = (
            "Could you clarify the AFL club/player and whether you want a fact lookup "
            "or a prediction?"
        )
    return {
        "needs_clarification": True,
        "clarification_prompt": prompt,
        "final_response": prompt,
        "trace": _trace(state, f"[clarify] {prompt}"),
    }


def retrieve_node(state: AFLState) -> dict:
    q = state.get("user_query") or ""
    teams = list(state.get("teams") or [])
    trace = _trace(state, "[retrieve] start")

    # Unsupported prediction-flavoured stats asked as facts
    if re.search(
        r"\b(weather|injury length|brownlow odds|salary|transfer|trade value)\b",
        q,
        re.I,
    ):
        return {
            "tool_name": "",
            "tool_result": {},
            "tool_error": (
                "That request is out of scope — I only look up match/player table stats "
                "and tip match winners / top-impact players from the trained models."
            ),
            "trace": trace + ["[retrieve] unsupported"],
        }

    # H2H
    if re.search(r"record|head.?to.?head|h2h|vs", q, re.I) and len(teams) >= 2:
        year_m = re.search(r"since\s+(19|20)\d{2}", q, re.I)
        since = int(year_m.group(0).split()[-1]) if year_m else None
        result = retrieve_h2h(teams[0], teams[1], since_year=since)
        return {
            "tool_name": "get_team_h2h_record",
            "tool_result": result,
            "tool_error": "" if tool_ok(result) else result.get("message") or result.get("error") or "empty",
            "trace": trace + [f"[retrieve] h2h ok={tool_ok(result)}"],
        }

    # recent results
    if re.search(r"recent|last (few )?games|results", q, re.I) and teams:
        result = retrieve_recent(teams[0], n=5)
        return {
            "tool_name": "get_recent_team_results",
            "tool_result": result,
            "tool_error": "" if tool_ok(result) else "no recent games",
            "trace": trace + ["[retrieve] recent"],
        }

    # player season
    year_m = re.search(r"\b(19|20)\d{2}\b", q)
    # naive player: capitalized names / after 'did'
    player = state.get("player")
    if not player:
        # look for "Gary Ablett" style
        m = re.search(r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b", q)
        if m:
            player = m.group(1)
    if player and year_m:
        year = int(year_m.group(0))
        team = teams[0] if teams else None
        result = retrieve_player_season(player, year, team=team)
        ok = tool_ok(result)
        return {
            "player": player,
            "tool_name": "get_player_season_stats",
            "tool_result": result,
            "tool_error": "" if ok else str(result.get("error") or "lookup failed"),
            "trace": trace + [f"[retrieve] season player={player} ok={ok}"],
        }

    if player:
        result = retrieve_player_game(player)
        ok = tool_ok(result)
        return {
            "player": player,
            "tool_name": "get_player_game_stats",
            "tool_result": result,
            "tool_error": "" if ok else str(result.get("error") or "lookup failed"),
            "trace": trace + [f"[retrieve] game player={player} ok={ok}"],
        }

    if teams:
        result = retrieve_recent(teams[0], n=3)
        return {
            "tool_name": "get_recent_team_results",
            "tool_result": result,
            "tool_error": "" if tool_ok(result) else "no games",
            "trace": trace + ["[retrieve] fallback recent"],
        }

    return {
        "tool_name": "",
        "tool_result": {},
        "tool_error": "Could not resolve a team or player for lookup.",
        "needs_clarification": True,
        "trace": trace + ["[retrieve] unresolved"],
    }


def predict_match_node(state: AFLState) -> dict:
    teams = list(state.get("teams") or [])
    q = state.get("user_query") or ""
    if re.search(
        r"\b(weather|injury|brownlow|margin exactly|exact score|total points)\b",
        q,
        re.I,
    ):
        return {
            "tool_error": (
                "Out of scope: I only tip match winners (home/away probability) from "
                "the Day-2 model — not weather, injuries, exact scores, or Brownlow odds."
            ),
            "tool_result": {},
            "trace": _trace(state, "[predict_match] unsupported"),
        }
    if len(teams) < 2:
        return {
            "needs_clarification": True,
            "tool_error": "Need two teams for a match prediction.",
            "clarification_prompt": (
                "Tell me both clubs (e.g. Pies vs Cats) and ideally a date."
            ),
            "trace": _trace(state, "[predict_match] missing teams"),
        }

    date_m = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", q)
    as_of = date_m.group(1) if date_m else None
    fix = find_fixture(teams[0], teams[1], as_of=as_of, prefer_upcoming=True)
    if not fix:
        return {
            "tool_error": f"No fixture found for {teams[0]} vs {teams[1]} in the dataset.",
            "tool_result": {},
            "trace": _trace(state, "[predict_match] no fixture"),
        }

    try:
        out = predict_match(
            fix["home_team"],
            fix["away_team"],
            fix["match_date"],
            home_team=fix["home_team"],
        )
        drivers = top_prediction_drivers(fix["match_id"], k=3)
        out["drivers"] = drivers
        out["fixture"] = fix
        return {
            "match_date": fix["match_date"],
            "tool_name": "predict_match_winner",
            "tool_result": out,
            "tool_error": "",
            "trace": _trace(
                state,
                f"[predict_match] {fix['home_team']} vs {fix['away_team']} "
                f"{fix['match_date']} p_home={out.get('home_win_probability')}",
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "tool_error": str(exc),
            "tool_result": {},
            "trace": _trace(state, f"[predict_match] error {exc}"),
        }


def predict_player_node(state: AFLState) -> dict:
    teams = list(state.get("teams") or [])
    q = state.get("user_query") or ""
    if not teams:
        # try one team alias
        return {
            "needs_clarification": True,
            "tool_error": "Need a team (and preferably opponent/date) for top-player prediction.",
            "clarification_prompt": "Which team and match date should I rank?",
            "trace": _trace(state, "[predict_player] missing team"),
        }

    team = teams[0]
    opp = teams[1] if len(teams) > 1 else None
    date_m = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", q)
    as_of = date_m.group(1) if date_m else None
    if opp:
        fix = find_fixture(team, opp, as_of=as_of, prefer_upcoming=True)
    else:
        fix = None
    if fix:
        match_date = fix["match_date"]
        # use home side for ranking both clubs? rank the named team only
        if team not in (fix["home_team"], fix["away_team"]):
            team = fix["home_team"]
        opp = fix["away_team"] if team == fix["home_team"] else fix["home_team"]
    else:
        # fall back: need date
        if not as_of:
            return {
                "needs_clarification": True,
                "tool_error": "Need a match date for player ranking.",
                "clarification_prompt": f"What match date for {team}?",
                "trace": _trace(state, "[predict_player] need date"),
            }
        match_date = as_of

    try:
        out = predict_top(team=team, match_date=match_date, opponent=opp, top_k=5)
        return {
            "match_date": match_date,
            "tool_name": "predict_top_player",
            "tool_result": out,
            "tool_error": "",
            "trace": _trace(state, f"[predict_player] team={team} date={match_date}"),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "tool_error": str(exc),
            "tool_result": {},
            "trace": _trace(state, f"[predict_player] error {exc}"),
        }


def validate_node(state: AFLState) -> dict:
    err = state.get("tool_error") or ""
    result = state.get("tool_result") or {}
    if state.get("needs_clarification"):
        return {
            "trace": _trace(state, "[validate] needs clarification"),
        }
    if err or not tool_ok(result):
        # unsupported / failed
        msg = err or "Lookup/prediction returned nothing."
        if (
            "stat type" in msg.lower()
            or "don't model" in msg.lower()
            or "out of scope" in msg.lower()
        ):
            final = msg
        else:
            final = (
                f"I couldn't complete that AFL request: {msg} "
                "Please check the club/player names or give a date in the dataset range."
            )
        return {
            "final_response": final,
            "needs_clarification": "Could not resolve" in msg or "Need" in msg,
            "trace": _trace(state, f"[validate] fail: {msg}"),
        }
    return {"trace": _trace(state, "[validate] ok")}


def format_node(state: AFLState) -> dict:
    if state.get("final_response"):
        return {"trace": _trace(state, "[format] already set")}

    if state.get("needs_clarification") and state.get("clarification_prompt"):
        return {
            "final_response": state["clarification_prompt"],
            "trace": _trace(state, "[format] clarification"),
        }

    intent = state.get("intent") or ""
    tool = state.get("tool_name") or ""
    result = state.get("tool_result") or {}

    # Prefer tool_name so a mis-set intent cannot break formatting
    if tool == "predict_match_winner" or (
        intent.startswith("prediction_match") and result.get("winner")
    ):
        winner = result.get("winner")
        p_home = result.get("home_win_probability")
        home = result.get("home_team")
        away = result.get("away_team")
        drivers = result.get("drivers") or []
        fix = result.get("fixture") or {}
        if p_home is None:
            return {
                "final_response": "Prediction failed — no probability returned.",
                "trace": _trace(state, "[format] prediction missing prob"),
            }
        p_home = float(p_home)
        p_away = float(result.get("away_win_probability") or (1 - p_home))
        resp = (
            f"Prediction: {winner} is the more likely winner for "
            f"{home} vs {away} on {result.get('match_date')}. "
            f"Model home-win probability about {p_home:.1%} "
            f"(away about {p_away:.1%}). "
            f"Main pre-match signals: {'; '.join(drivers)}. "
            f"{PREDICTION_DISCLAIMER}"
        )
        if fix.get("round"):
            resp += f" Fixture round in data: {fix['round']}."
        return {"final_response": resp, "trace": _trace(state, "[format] prediction_match")}

    if tool == "predict_top_player" or (
        intent == "prediction_player" and result.get("players") is not None
    ):
        players = result.get("players") or []
        lines = [
            f"{p['rank']}. player_id={p['player_id']} (pred impact {p['pred_impact']})"
            for p in players[:5]
        ]
        resp = (
            f"Top-player ranking for {result.get('match_date')} "
            f"({result.get('n_players_scored', '?')} players scored).\n"
            + "\n".join(lines)
            + f"\n{PREDICTION_DISCLAIMER}"
        )
        return {"final_response": resp, "trace": _trace(state, "[format] prediction_player")}

    # retrieval formatting
    if tool == "get_team_h2h_record":
        resp = (
            f"Head-to-head (exact table): {result.get('team_a')} vs {result.get('team_b')} — "
            f"{result.get('games')} games, "
            f"{result.get('team_a')} wins {result.get('team_a_wins')}, "
            f"{result.get('team_b')} wins {result.get('team_b_wins')}, "
            f"draws {result.get('draws')} "
            f"({result.get('year_min')}–{result.get('year_max')})."
        )
        return {"final_response": resp, "trace": _trace(state, "[format] h2h")}

    if tool == "get_recent_team_results":
        games = result.get("games") or []
        bits = [
            f"{g['match_date']} vs {g['opponent']} {g['score_for']}-{g['score_against']}"
            for g in games
        ]
        resp = f"Recent results for {result.get('team')}: " + "; ".join(bits)
        return {"final_response": resp, "trace": _trace(state, "[format] recent")}

    if tool in {"get_player_season_stats", "get_player_game_stats"}:
        if result.get("player_name") or result.get("player_id"):
            bits = [
                f"{result.get('player_name') or result.get('player_id')}",
                f"year={result.get('year')}" if result.get("year") is not None else "",
                f"team={result.get('team')}" if result.get("team") else "",
                f"games={result.get('games_played')}" if result.get("games_played") is not None else "",
                f"disposals={result.get('disposals')}" if result.get("disposals") is not None else "",
                f"goals={result.get('goals')}" if result.get("goals") is not None else "",
                f"avg_disposals={result.get('avg_disposals')}" if result.get("avg_disposals") is not None else "",
            ]
            resp = "Player lookup (table): " + ", ".join(b for b in bits if b)
            return {"final_response": resp, "trace": _trace(state, "[format] player stats")}
        return {
            "final_response": f"Lookup result: {dumps(result)}",
            "trace": _trace(state, "[format] player stats"),
        }

    return {
        "final_response": (
            "I can look up AFL stats or tip a match/player if you name the clubs/date. "
            "Unsupported prediction types (e.g. weather, injury length) are out of scope."
        ),
        "trace": _trace(state, "[format] fallback unsupported"),
    }


def after_router(state: AFLState) -> Literal[
    "retrieve", "predict_match", "predict_player", "refuse", "clarify"
]:
    return state.get("route") or "clarify"  # type: ignore[return-value]


def after_validate(state: AFLState) -> Literal["format", "clarify"]:
    if state.get("needs_clarification") and not state.get("final_response"):
        return "clarify"
    if state.get("tool_error") and not state.get("final_response"):
        # format will explain failure
        return "format"
    return "format"
