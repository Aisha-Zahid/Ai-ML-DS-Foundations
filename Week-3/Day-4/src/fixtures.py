"""Resolve fixtures / dates for prediction requests."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from .aliases import normalize_team_query
from .config import MATCH_FEATURES

_MATCH_CACHE: pd.DataFrame | None = None


def _load_matches() -> pd.DataFrame:
    global _MATCH_CACHE
    if _MATCH_CACHE is not None:
        return _MATCH_CACHE
    df = pd.read_csv(MATCH_FEATURES, parse_dates=["match_date"])
    df["home_team"] = df["home_team"].map(normalize_team_query)
    df["away_team"] = df["away_team"].map(normalize_team_query)
    _MATCH_CACHE = df
    return df


def find_fixture(
    team_a: str,
    team_b: str,
    *,
    as_of: str | None = None,
    prefer_upcoming: bool = True,
) -> dict | None:
    """
    Find a match row for two teams.
    'this week' / upcoming: nearest match on/after as_of (default = max date - 14d
    if asking upcoming in a historical dump, else today).
    Falls back to most recent prior meeting if none ahead.
    """
    m = _load_matches()
    a = normalize_team_query(team_a)
    b = normalize_team_query(team_b)
    mask = ((m["home_team"] == a) & (m["away_team"] == b)) | (
        (m["home_team"] == b) & (m["away_team"] == a)
    )
    sub = m[mask].sort_values("match_date")
    if sub.empty:
        return None

    if as_of:
        ref = pd.Timestamp(as_of).normalize()
        exact = sub[sub["match_date"] == ref]
        if not exact.empty:
            row = exact.iloc[0]
            return {
                "match_id": row["match_id"],
                "match_date": str(pd.Timestamp(row["match_date"]).date()),
                "home_team": row["home_team"],
                "away_team": row["away_team"],
                "year": int(row["year"]),
                "round": str(row["round"]),
            }
    else:
        # Historical dump: treat "this week" as near the end of available data
        ref = (sub["match_date"].max() - timedelta(days=10)).normalize()

    future = sub[sub["match_date"] >= ref]
    if prefer_upcoming and not future.empty:
        row = future.iloc[0]
    else:
        past = sub[sub["match_date"] <= ref]
        row = past.iloc[-1] if not past.empty else sub.iloc[-1]

    return {
        "match_id": row["match_id"],
        "match_date": str(pd.Timestamp(row["match_date"]).date()),
        "home_team": row["home_team"],
        "away_team": row["away_team"],
        "year": int(row["year"]),
        "round": str(row["round"]),
    }


def top_prediction_drivers(match_id: str, k: int = 3) -> list[str]:
    """Short plain-language drivers from feature row + importance file."""
    m = _load_matches()
    row = m[m["match_id"] == match_id]
    if row.empty:
        return ["form and ladder features from the pre-match table"]
    r = row.iloc[0]
    bits = []
    if pd.notna(r.get("form_margin_diff_l5")):
        bits.append(f"form margin diff (L5) = {float(r['form_margin_diff_l5']):.1f}")
    if pd.notna(r.get("ladder_pct_diff")):
        bits.append(f"ladder % diff = {float(r['ladder_pct_diff']):.2f}")
    if pd.notna(r.get("h2h_home_win_rate")):
        bits.append(f"prior H2H home win rate = {float(r['h2h_home_win_rate']):.2f}")
    if pd.notna(r.get("is_interstate")):
        bits.append("interstate matchup" if int(r["is_interstate"]) == 1 else "same-state matchup")
    return bits[:k] or ["pre-match form and ladder features"]
