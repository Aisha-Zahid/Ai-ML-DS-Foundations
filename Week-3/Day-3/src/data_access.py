"""Load AFL tables and run exact structured lookups."""

from __future__ import annotations

import re
from functools import lru_cache

import pandas as pd

from .config import MATCH_FEATURES, PLAYER_FEATURES, PLAYERS_INFO, PLAYERS_SEASON

# Reuse Day-1 team aliases if available
try:
    import importlib.util
    from pathlib import Path

    _ld = Path(__file__).resolve().parents[2] / "Day-1" / "src" / "load_data.py"
    _spec = importlib.util.spec_from_file_location("day1_load", _ld)
    _mod = importlib.util.module_from_spec(_spec)
    assert _spec.loader is not None
    _spec.loader.exec_module(_mod)
    normalize_team = _mod.normalize_team
except Exception:  # noqa: BLE001

    def normalize_team(name: object) -> str:
        return str(name).replace("\t", " ").strip()


@lru_cache(maxsize=1)
def load_matches() -> pd.DataFrame:
    df = pd.read_csv(MATCH_FEATURES, parse_dates=["match_date"])
    df["home_team"] = df["home_team"].map(normalize_team)
    df["away_team"] = df["away_team"].map(normalize_team)
    return df


@lru_cache(maxsize=1)
def load_player_games() -> pd.DataFrame:
    df = pd.read_csv(PLAYER_FEATURES, parse_dates=["match_date"])
    df["team"] = df["team"].map(normalize_team)
    df["opponent"] = df["opponent"].map(normalize_team)
    df["player_id"] = df["player_id"].astype(str)
    return df


@lru_cache(maxsize=1)
def load_players_info() -> pd.DataFrame:
    df = pd.read_csv(PLAYERS_INFO, low_memory=False)
    df = df.rename(columns={"id": "player_id"})
    df["player_id"] = df["player_id"].astype(str)
    df = df.drop_duplicates(subset=["player_id"], keep="first")
    return df


@lru_cache(maxsize=1)
def load_player_seasons() -> pd.DataFrame:
    df = pd.read_csv(PLAYERS_SEASON, low_memory=False)
    df["player_id"] = df["player_id"].astype(str)
    df["team"] = df["team"].map(normalize_team)
    return df


def resolve_player_id(name_or_id: str) -> tuple[str | None, str | None]:
    """Return (player_id, display_name) or (None, None)."""
    q = str(name_or_id).strip()
    info = load_players_info()
    if q.isdigit() or re.fullmatch(r"\d+", q):
        row = info[info["player_id"] == q]
        if len(row):
            r = row.iloc[0]
            return str(r["player_id"]), str(r["player_name"])
        return None, None
    ql = q.lower()
    exact = info[info["player_name"].fillna("").str.lower() == ql]
    if len(exact):
        # Prefer the most recent player when names collide
        if "last_date" in exact.columns:
            exact = exact.sort_values("last_date", ascending=False)
        r = exact.iloc[0]
        return str(r["player_id"]), str(r["player_name"])
    mask = info["player_name"].fillna("").str.lower().str.contains(re.escape(ql), na=False)
    hits = info[mask]
    if hits.empty:
        return None, None
    if "last_date" in hits.columns:
        hits = hits.sort_values("last_date", ascending=False)
    r = hits.iloc[0]
    return str(r["player_id"]), str(r["player_name"])


def team_h2h_record(team_a: str, team_b: str, since_year: int | None = None) -> dict:
    a = normalize_team(team_a)
    b = normalize_team(team_b)
    m = load_matches()
    if since_year is not None:
        m = m[m["year"] >= int(since_year)]
    mask = ((m["home_team"] == a) & (m["away_team"] == b)) | (
        (m["home_team"] == b) & (m["away_team"] == a)
    )
    sub = m[mask]
    if sub.empty:
        return {"team_a": a, "team_b": b, "games": 0, "message": "No matches found in dataset."}

    a_wins = 0
    b_wins = 0
    draws = 0
    for _, r in sub.iterrows():
        if int(r["is_draw"]) == 1:
            draws += 1
            continue
        winner = r["home_team"] if int(r["home_win"]) == 1 else r["away_team"]
        if winner == a:
            a_wins += 1
        elif winner == b:
            b_wins += 1
    return {
        "team_a": a,
        "team_b": b,
        "games": int(len(sub)),
        "team_a_wins": int(a_wins),
        "team_b_wins": int(b_wins),
        "draws": int(draws),
        "year_min": int(sub["year"].min()),
        "year_max": int(sub["year"].max()),
        "source": "match_features_v1 (exact row counts)",
    }


def player_season_stats(player: str, year: int, team: str | None = None) -> dict:
    pid, pname = resolve_player_id(player)
    if not pid:
        return {"error": f"Player not found: {player}"}
    ps = load_player_seasons()
    sub = ps[(ps["player_id"] == pid) & (ps["year"] == int(year))]
    if team:
        sub = sub[sub["team"] == normalize_team(team)]
    if sub.empty:
        return {
            "error": f"No season row for {pname} ({pid}) in {year}",
            "player_id": pid,
            "player_name": pname,
        }
    # Prefer non-finals aggregate if both exist
    home = sub[sub["is_finals"] == False]  # noqa: E712
    row = home.iloc[0] if len(home) else sub.iloc[0]
    return {
        "player_id": pid,
        "player_name": pname,
        "year": int(year),
        "team": str(row["team"]),
        "is_finals": bool(row["is_finals"]),
        "games_played": int(row["games_played"]),
        "disposals": float(row["disposals"]) if pd.notna(row["disposals"]) else None,
        "goals": float(row["goals"]) if pd.notna(row["goals"]) else None,
        "kicks": float(row["kicks"]) if pd.notna(row["kicks"]) else None,
        "handballs": float(row["handballs"]) if pd.notna(row["handballs"]) else None,
        "avg_disposals": float(row["avg_disposals"]) if pd.notna(row["avg_disposals"]) else None,
        "avg_goals": float(row["avg_goals"]) if pd.notna(row["avg_goals"]) else None,
        "avg_fantasy_points": (
            float(row["avg_fantasy_points"]) if pd.notna(row["avg_fantasy_points"]) else None
        ),
        "source": "afl_players_seasonal_stats_raw (exact)",
    }


def player_game_stats(
    player: str,
    match_date: str | None = None,
    year: int | None = None,
    round_name: str | None = None,
) -> dict:
    pid, pname = resolve_player_id(player)
    if not pid:
        return {"error": f"Player not found: {player}"}
    pg = load_player_games()
    sub = pg[pg["player_id"] == pid]
    if match_date:
        dt = pd.Timestamp(match_date).normalize()
        sub = sub[sub["match_date"].dt.normalize() == dt]
    if year is not None:
        sub = sub[sub["year"] == int(year)]
    if round_name is not None:
        sub = sub[sub["round"].astype(str) == str(round_name)]
    if sub.empty:
        return {
            "error": f"No player-game rows for {pname} with those filters",
            "player_id": pid,
            "player_name": pname,
        }
    # Most recent matching game if many
    r = sub.sort_values("match_date").iloc[-1]
    return {
        "player_id": pid,
        "player_name": pname,
        "match_date": str(pd.Timestamp(r["match_date"]).date()),
        "year": int(r["year"]),
        "round": str(r["round"]),
        "team": str(r["team"]),
        "opponent": str(r["opponent"]),
        "disposals": float(r["disposals"]) if pd.notna(r["disposals"]) else None,
        "goals": float(r["goals"]) if pd.notna(r["goals"]) else None,
        "impact_score": float(r["impact_score"]) if pd.notna(r["impact_score"]) else None,
        "result": str(r["result"]),
        "source": "player_game_features_v1 (exact)",
    }


def recent_team_results(team: str, n: int = 5) -> dict:
    t = normalize_team(team)
    m = load_matches()
    home = m[m["home_team"] == t].copy()
    home["opponent"] = home["away_team"]
    home["score_for"] = home["home_score"]
    home["score_against"] = home["away_score"]
    home["won"] = home["home_win"]

    away = m[m["away_team"] == t].copy()
    away["opponent"] = away["home_team"]
    away["score_for"] = away["away_score"]
    away["score_against"] = away["home_score"]
    away["won"] = (1 - away["home_win"]) * (1 - away["is_draw"])

    cols = ["match_date", "year", "round", "opponent", "score_for", "score_against", "won", "venue"]
    log = pd.concat([home[cols], away[cols]], ignore_index=True).sort_values("match_date")
    tail = log.tail(int(n))
    if tail.empty:
        return {"team": t, "games": [], "message": "No games found"}
    games = []
    for _, r in tail.iterrows():
        games.append(
            {
                "match_date": str(pd.Timestamp(r["match_date"]).date()),
                "round": str(r["round"]),
                "opponent": str(r["opponent"]),
                "score_for": int(r["score_for"]),
                "score_against": int(r["score_against"]),
                "won": bool(r["won"]),
                "venue": str(r["venue"]),
            }
        )
    return {"team": t, "n": len(games), "games": games, "source": "match_features_v1 (exact)"}
