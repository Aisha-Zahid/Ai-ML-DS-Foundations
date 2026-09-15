"""
Match and top-player prediction helpers for Week 3 Day 2.

Examples
--------
>>> from predict import predict_match_winner, predict_top_player
>>> predict_match_winner("Geelong Cats", "Richmond Tigers", "2024-03-16")
>>> predict_top_player(team="Geelong Cats", match_date="2024-03-16", top_k=5)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / "models"
DAY1_MATCH = ROOT.parent / "Day-1" / "data" / "processed" / "match_features_v1.csv"
DAY1_PLAYER = ROOT.parent / "Day-1" / "data" / "processed" / "player_game_features_v1.csv"

# Optional Day-1 team normalizer (load by file path to avoid src/ name clash)
def normalize_team(name: object) -> str:
    try:
        import importlib.util

        path = ROOT.parent / "Day-1" / "src" / "load_data.py"
        spec = importlib.util.spec_from_file_location("day1_load_data", path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod.normalize_team(name)
    except Exception:  # noqa: BLE001
        return str(name).replace("\t", " ").strip()

class PredictionError(ValueError):
    """Raised for bad inputs or missing data."""


_CACHE: dict[str, Any] = {}


def _load_artifacts() -> tuple[Any, Any, dict]:
    if "match" not in _CACHE:
        match_path = MODELS / "match_winner.joblib"
        player_path = MODELS / "top_player.joblib"
        meta_path = MODELS / "model_meta.joblib"
        if not match_path.exists() or not player_path.exists():
            raise PredictionError(
                "Model files missing. Run `python train_models.py` in Week-3/Day-2 first."
            )
        _CACHE["match"] = joblib.load(match_path)
        _CACHE["player"] = joblib.load(player_path)
        _CACHE["meta"] = joblib.load(meta_path) if meta_path.exists() else {}
    return _CACHE["match"], _CACHE["player"], _CACHE["meta"]


def _load_match_table() -> pd.DataFrame:
    if "match_df" not in _CACHE:
        if not DAY1_MATCH.exists():
            raise PredictionError(f"Match feature table not found: {DAY1_MATCH}")
        _CACHE["match_df"] = pd.read_csv(DAY1_MATCH, parse_dates=["match_date"])
    return _CACHE["match_df"]


def _load_player_table() -> pd.DataFrame:
    if "player_df" not in _CACHE:
        if not DAY1_PLAYER.exists():
            raise PredictionError(
                f"Player feature table not found: {DAY1_PLAYER}. "
                "Run Day-1 `python build_features.py` first."
            )
        _CACHE["player_df"] = pd.read_csv(DAY1_PLAYER, parse_dates=["match_date"])
    return _CACHE["player_df"]


def _parse_date(date: str | pd.Timestamp) -> pd.Timestamp:
    try:
        return pd.Timestamp(date).normalize()
    except Exception as exc:  # noqa: BLE001
        raise PredictionError(f"Invalid date: {date!r}") from exc


def predict_match_winner(
    team_a: str,
    team_b: str,
    date: str,
    *,
    home_team: Optional[str] = None,
) -> dict[str, Any]:
    """
    Predict match winner using the saved pipeline.

    Parameters
    ----------
    team_a, team_b :
        Club names (normalized via Day-1 aliases when possible).
    date :
        Match date (YYYY-MM-DD). Used to look up the precomputed feature row.
    home_team :
        Optional explicit home team. If omitted, we look up the row where
        {team_a, team_b} match home/away on that date.

    Returns
    -------
    dict with winner, home_win_probability, home_team, away_team, match_id
    """
    model, _, meta = _load_artifacts()
    df = _load_match_table()
    a = normalize_team(team_a)
    b = normalize_team(team_b)
    dt = _parse_date(date)

    known = set(meta.get("known_teams") or [])
    for t in (a, b):
        if known and t not in known:
            raise PredictionError(
                f"Unknown team {t!r}. Example teams: {sorted(list(known))[:5]}..."
            )

    dmin = meta.get("match_date_min")
    dmax = meta.get("match_date_max")
    if dmin and dmax and not (pd.Timestamp(dmin) <= dt <= pd.Timestamp(dmax)):
        raise PredictionError(
            f"Date {dt.date()} outside data range {dmin} .. {dmax}."
        )

    day = df[df["match_date"].dt.normalize() == dt]
    if home_team:
        home = normalize_team(home_team)
        away = b if home == a else a if home == b else None
        if away is None:
            raise PredictionError("home_team must be team_a or team_b")
        rows = day[(day["home_team"] == home) & (day["away_team"] == away)]
    else:
        rows = day[
            ((day["home_team"] == a) & (day["away_team"] == b))
            | ((day["home_team"] == b) & (day["away_team"] == a))
        ]

    if rows.empty:
        raise PredictionError(
            f"No feature row for {a} vs {b} on {dt.date()}. "
            "Use a date/teams present in match_features_v1."
        )

    row = rows.iloc[0]
    num_cols = meta["match_num_cols"]
    cat_cols = meta["match_cat_cols"]
    X = row[num_cols + cat_cols].to_frame().T
    p_home = float(model.predict_proba(X)[0, 1])
    home = str(row["home_team"])
    away = str(row["away_team"])
    winner = home if p_home >= 0.5 else away
    return {
        "match_id": row["match_id"],
        "match_date": str(dt.date()),
        "home_team": home,
        "away_team": away,
        "winner": winner,
        "home_win_probability": round(p_home, 4),
        "away_win_probability": round(1.0 - p_home, 4),
    }


def predict_top_player(
    *,
    match_id: Optional[str] = None,
    team: Optional[str] = None,
    match_date: Optional[str] = None,
    opponent: Optional[str] = None,
    stat_type: str = "impact",
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Rank players for a match by predicted impact (default).

    Provide either ``match_id`` **or** (``team`` + ``match_date`` [+ optional opponent]).

    ``stat_type`` supports ``impact`` (composite score). Disposals/goals still
    use the same ranking until separate models exist.
    """
    if stat_type not in {"impact", "disposals", "goals"}:
        raise PredictionError("stat_type must be one of: impact, disposals, goals")

    _, model, meta = _load_artifacts()
    pdf = _load_player_table()

    if match_id:
        # player table has no match_id — resolve via match feature table
        mdf = _load_match_table()
        mrows = mdf[mdf["match_id"] == match_id]
        if mrows.empty:
            raise PredictionError(f"Unknown match_id: {match_id}")
        mr = mrows.iloc[0]
        team = str(mr["home_team"])
        opponent = str(mr["away_team"])
        match_date = str(pd.Timestamp(mr["match_date"]).date())
        # include both clubs' players
        dt = _parse_date(match_date)
        day = pdf[pdf["match_date"].dt.normalize() == dt]
        mask = ((day["team"] == team) & (day["opponent"] == opponent)) | (
            (day["team"] == opponent) & (day["opponent"] == team)
        )
        subset = day[mask].copy()
    else:
        if not team or not match_date:
            raise PredictionError("Provide match_id OR team + match_date")
        team_n = normalize_team(team)
        dt = _parse_date(match_date)
        day = pdf[pdf["match_date"].dt.normalize() == dt]
        subset = day[day["team"] == team_n].copy()
        if opponent:
            opp = normalize_team(opponent)
            subset = subset[subset["opponent"] == opp]
        if subset.empty:
            raise PredictionError(
                f"No player rows for team={team_n!r} on {dt.date()}"
            )

    if subset.empty:
        raise PredictionError("No players found for that match filter")

    num_cols = meta["player_num_cols"]
    cat_cols = meta["player_cat_cols"]
    X = subset[num_cols + cat_cols]
    pred = model.predict(X)
    w = float(meta.get("player_blend_model_weight", 0.3))
    form = subset["avg_impact_l5"].fillna(0.0).to_numpy()
    subset = subset.assign(pred_impact=w * pred + (1.0 - w) * form)

    # Optional: crude mapping if user asked disposals/goals — still rank by impact
    # but label the field clearly.
    ranked = subset.sort_values("pred_impact", ascending=False).head(int(top_k))
    players = [
        {
            "rank": i + 1,
            "player_id": str(r.player_id),
            "team": r.team,
            "pred_impact": round(float(r.pred_impact), 2),
            "actual_impact": (
                None if pd.isna(r.impact_score) else round(float(r.impact_score), 2)
            ),
        }
        for i, r in enumerate(ranked.itertuples())
    ]
    return {
        "stat_type": stat_type,
        "match_date": str(pd.Timestamp(subset["match_date"].iloc[0]).date()),
        "n_players_scored": int(len(subset)),
        "top_k": int(top_k),
        "note": (
            "Sorted by predicted impact (with form blend). "
            "disposals/goals use the same ranker for now."
            if stat_type != "impact"
            else "Sorted by predicted impact (with form blend)."
        ),
        "players": players,
    }


if __name__ == "__main__":
    import argparse
    import json

    p = argparse.ArgumentParser(description="AFL Day-2 predictors")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("match")
    m.add_argument("--home", required=True)
    m.add_argument("--away", required=True)
    m.add_argument("--date", required=True)

    t = sub.add_parser("player")
    t.add_argument("--team", required=True)
    t.add_argument("--date", required=True)
    t.add_argument("--opponent", default=None)
    t.add_argument("--top-k", type=int, default=5)

    args = p.parse_args()
    if args.cmd == "match":
        out = predict_match_winner(args.home, args.away, args.date, home_team=args.home)
    else:
        out = predict_top_player(
            team=args.team, match_date=args.date, opponent=args.opponent, top_k=args.top_k
        )
    print(json.dumps(out, indent=2))
