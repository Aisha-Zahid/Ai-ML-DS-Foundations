"""Load and lightly clean AFL tables."""

from __future__ import annotations

import re

import pandas as pd

from .paths import PLAYERS_INFO, PLAYERS_ROUND, PLAYERS_SEASON, TEAM_MATCHES

TEAM_ALIASES = {
    "w. bulldogs": "Western Bulldogs",
    "western bulldogs": "Western Bulldogs",
    "footscray": "Western Bulldogs",
    "brisbane bears": "Brisbane Bears",
    "brisbane lions": "Brisbane Lions",
    "greater western sydney giants": "Greater Western Sydney Giants",
    "gws": "Greater Western Sydney Giants",
    "north melbourne kangaroos": "North Melbourne Kangaroos",
    "kangaroos": "North Melbourne Kangaroos",
    "adelaide crows": "Adelaide Crows",
    "carlton blues": "Carlton Blues",
    "collingwood magpies": "Collingwood Magpies",
    "essendon bombers": "Essendon Bombers",
    "fitzroy lions": "Fitzroy Lions",
    "fremantle dockers": "Fremantle Dockers",
    "geelong cats": "Geelong Cats",
    "gold coast suns": "Gold Coast Suns",
    "hawthorn hawks": "Hawthorn Hawks",
    "melbourne demons": "Melbourne Demons",
    "port adelaide power": "Port Adelaide Power",
    "richmond tigers": "Richmond Tigers",
    "st kilda saints": "St Kilda Saints",
    "sydney swans": "Sydney Swans",
    "west coast eagles": "West Coast Eagles",
}


def normalize_team(name: object) -> str:
    if pd.isna(name):
        return ""
    s = str(name).replace("\t", " ").strip()
    s = re.sub(r"\s+", " ", s)
    key = s.lower()
    return TEAM_ALIASES.get(key, s)


def _parse_dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def load_players_info() -> pd.DataFrame:
    df = pd.read_csv(PLAYERS_INFO, low_memory=False)
    df = df.rename(columns={"id": "player_id"})
    df["player_id"] = df["player_id"].astype(str)
    df["born_date"] = _parse_dates(df["born_date"])
    df["debut_date"] = _parse_dates(df["debut_date"])
    df["last_date"] = _parse_dates(df["last_date"])
    df = df.drop_duplicates(subset=["player_id"], keep="first")
    return df


def load_team_matches() -> pd.DataFrame:
    df = pd.read_csv(TEAM_MATCHES, low_memory=False)
    df = df.rename(columns={"id": "team_match_id", "team_name": "team"})
    df["team"] = df["team"].map(normalize_team)
    df["opponent"] = df["opponent"].map(normalize_team)
    df["match_date"] = _parse_dates(df["match_date"])
    df["home_away"] = df["home_away"].astype(str).str.strip().str.upper()
    df["result"] = df["result"].astype(str).str.strip().str.upper()
    df["round"] = df["round"].astype(str).str.strip()
    df["venue"] = df["venue"].astype(str).str.strip()
    return df


def load_player_games() -> pd.DataFrame:
    df = pd.read_csv(PLAYERS_ROUND, low_memory=False)
    df = df.rename(columns={"id": "player_game_id"})
    df["player_id"] = df["player_id"].astype(str)
    df["team"] = df["team"].map(normalize_team)
    df["opponent"] = df["opponent"].map(normalize_team)
    df["match_date"] = _parse_dates(df["match_date"])
    df["result"] = df["result"].astype(str).str.strip().str.upper()
    df["round"] = df["round"].astype(str).str.strip()
    for col in [
        "kicks",
        "handballs",
        "disposals",
        "marks",
        "tackles",
        "goals",
        "behinds",
        "hit_outs",
        "fantasy_points",
        "brownlow_votes",
        "margin",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    missing_disp = df["disposals"].isna() & df["kicks"].notna() & df["handballs"].notna()
    df.loc[missing_disp, "disposals"] = (
        df.loc[missing_disp, "kicks"] + df.loc[missing_disp, "handballs"]
    )
    df = df.drop_duplicates(subset=["player_game_id"], keep="first")
    return df


def load_player_seasons() -> pd.DataFrame:
    df = pd.read_csv(PLAYERS_SEASON, low_memory=False)
    df["player_id"] = df["player_id"].astype(str)
    df["team"] = df["team"].map(normalize_team)
    return df


def build_match_level(team_matches: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per match from the home team's perspective."""
    tm = team_matches if team_matches is not None else load_team_matches()
    home = tm[tm["home_away"] == "H"].copy()
    away = tm[tm["home_away"] == "A"].copy()

    home = home.rename(
        columns={
            "team": "home_team",
            "opponent": "away_team",
            "team_score": "home_score",
            "opponent_score": "away_score",
            "team_goals_kicked": "home_goals",
            "team_behinds": "home_behinds",
            "opponent_goals_kicked": "away_goals",
            "opponent_behinds": "away_behinds",
            "result": "home_result",
            "margin": "home_margin_raw",
            "team_match_id": "home_team_match_id",
        }
    )

    keys = ["match_date", "venue", "year", "round"]
    away_small = away[
        keys + ["team", "opponent", "team_score", "opponent_score", "result", "team_match_id"]
    ].rename(
        columns={
            "team": "away_team_check",
            "opponent": "home_team_check",
            "team_score": "away_score_check",
            "opponent_score": "home_score_check",
            "result": "away_result",
            "team_match_id": "away_team_match_id",
        }
    )

    m = home.merge(away_small, on=keys, how="left")
    m["away_score"] = m["away_score"].fillna(m.get("away_score_check"))
    m["match_id"] = (
        m["match_date"].dt.strftime("%Y%m%d")
        + "_"
        + m["home_team"].str.replace(" ", "", regex=False)
        + "_"
        + m["away_team"].str.replace(" ", "", regex=False)
    )
    m = m.drop_duplicates(subset=["match_id"], keep="first")
    m = m.sort_values(["match_date", "home_team"]).reset_index(drop=True)
    return m


def inventory_summary() -> dict:
    info = load_players_info()
    tm = load_team_matches()
    pg = load_player_games()
    ps = load_player_seasons()
    matches = build_match_level(tm)
    return {
        "players_info_rows": len(info),
        "players_unique": info["player_id"].nunique(),
        "team_match_rows": len(tm),
        "unique_matches": len(matches),
        "player_game_rows": len(pg),
        "player_season_rows": len(ps),
        "year_min": int(min(tm["year"].min(), pg["year"].min())),
        "year_max": int(max(tm["year"].max(), pg["year"].max())),
        "n_teams_matches": int(tm["team"].nunique()),
        "n_venues": int(tm["venue"].nunique()),
    }
