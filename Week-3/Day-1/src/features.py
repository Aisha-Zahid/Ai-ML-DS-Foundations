"""Leakage-safe feature engineering for match and player-game tables."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .targets import add_match_targets, add_player_targets


def _team_game_log(matches: pd.DataFrame) -> pd.DataFrame:
    """Expand match table to one row per team per game (for rolling form)."""
    home = matches[
        [
            "match_id",
            "match_date",
            "year",
            "round",
            "venue",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
            "home_win",
            "is_draw",
            "home_margin",
        ]
    ].copy()
    home["team"] = home["home_team"]
    home["opponent"] = home["away_team"]
    home["is_home"] = 1
    home["points_for"] = home["home_score"]
    home["points_against"] = home["away_score"]
    home["won"] = home["home_win"]
    home["drawn"] = home["is_draw"]
    home["margin"] = home["home_margin"]

    away = matches[
        [
            "match_id",
            "match_date",
            "year",
            "round",
            "venue",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
            "home_win",
            "is_draw",
            "home_margin",
        ]
    ].copy()
    away["team"] = away["away_team"]
    away["opponent"] = away["home_team"]
    away["is_home"] = 0
    away["points_for"] = away["away_score"]
    away["points_against"] = away["home_score"]
    away["won"] = (1 - away["home_win"]) * (1 - away["is_draw"])
    away["drawn"] = away["is_draw"]
    away["margin"] = -away["home_margin"]

    cols = [
        "match_id",
        "match_date",
        "year",
        "round",
        "venue",
        "team",
        "opponent",
        "is_home",
        "points_for",
        "points_against",
        "won",
        "drawn",
        "margin",
    ]
    log = pd.concat([home[cols], away[cols]], ignore_index=True)
    log = log.sort_values(["team", "match_date", "match_id"]).reset_index(drop=True)
    return log


def _rolling_team_features(log: pd.DataFrame, windows: tuple[int, ...] = (3, 5, 8)) -> pd.DataFrame:
    """Rolling stats using only prior games (shift 1)."""
    parts = []
    for team, g in log.groupby("team", sort=False):
        g = g.sort_values("match_date").copy()
        g["prev_match_date"] = g["match_date"].shift(1)
        g["rest_days"] = (g["match_date"] - g["prev_match_date"]).dt.days
        # win streak ending before this game
        prev_won = g["won"].shift(1)
        streak = []
        cur = 0
        for w in prev_won.fillna(0):
            if w == 1:
                cur += 1
            else:
                cur = 0
            streak.append(cur)
        g["win_streak_pre"] = streak

        for n in windows:
            # shift so current game is excluded
            g[f"win_rate_l{n}"] = g["won"].shift(1).rolling(n, min_periods=1).mean()
            g[f"avg_pf_l{n}"] = g["points_for"].shift(1).rolling(n, min_periods=1).mean()
            g[f"avg_pa_l{n}"] = g["points_against"].shift(1).rolling(n, min_periods=1).mean()
            g[f"avg_margin_l{n}"] = g["margin"].shift(1).rolling(n, min_periods=1).mean()
            g[f"games_l{n}"] = g["won"].shift(1).rolling(n, min_periods=1).count()
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def _season_ladder_points(log: pd.DataFrame) -> pd.DataFrame:
    """Premiership points before each game (W=4, D=2) within season — no leakage."""
    parts = []
    for (team, year), g in log.groupby(["team", "year"], sort=False):
        g = g.sort_values("match_date").copy()
        pts = (g["won"] * 4 + g["drawn"] * 2).shift(1).fillna(0)
        g["ladder_points_pre"] = pts.cumsum()
        g["season_games_pre"] = np.arange(len(g))
        g["ladder_pct_pre"] = np.where(
            g["season_games_pre"] > 0,
            g["ladder_points_pre"] / (g["season_games_pre"] * 4.0),
            0.5,
        )
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


TEAM_STATE = {
    "Adelaide Crows": "SA",
    "Port Adelaide Power": "SA",
    "West Coast Eagles": "WA",
    "Fremantle Dockers": "WA",
    "Brisbane Lions": "QLD",
    "Brisbane Bears": "QLD",
    "Gold Coast Suns": "QLD",
    "Sydney Swans": "NSW",
    "Greater Western Sydney Giants": "NSW",
    "Carlton Blues": "VIC",
    "Collingwood Magpies": "VIC",
    "Essendon Bombers": "VIC",
    "Fitzroy Lions": "VIC",
    "Geelong Cats": "VIC",
    "Hawthorn Hawks": "VIC",
    "Melbourne Demons": "VIC",
    "North Melbourne Kangaroos": "VIC",
    "Richmond Tigers": "VIC",
    "St Kilda Saints": "VIC",
    "Western Bulldogs": "VIC",
}


def _h2h_features(matches: pd.DataFrame, lookback: int = 10) -> pd.DataFrame:
    """Prior head-to-head win rate for the current home team (meetings before this date)."""
    df = matches.sort_values("match_date").copy()
    history: dict[tuple[str, str], list[tuple[str, int]]] = {}
    rates = []
    counts = []
    for _, row in df.iterrows():
        home, away = row["home_team"], row["away_team"]
        key = tuple(sorted([home, away]))
        past = history.get(key, [])[-lookback:]
        if not past:
            rates.append(0.5)
            counts.append(0)
        else:
            # past entries: (winner_team or 'draw',)
            wins = sum(1 for w in past if w == home)
            decided = sum(1 for w in past if w != "draw")
            rates.append(wins / decided if decided else 0.5)
            counts.append(len(past))
        if int(row["is_draw"]) == 1:
            winner = "draw"
        else:
            winner = home if int(row["home_win"]) == 1 else away
        history.setdefault(key, []).append(winner)
    df["h2h_home_win_rate"] = rates
    df["h2h_games"] = counts
    return df


def build_match_feature_table(matches: pd.DataFrame) -> pd.DataFrame:
    """Versioned match feature matrix (pre-match info only)."""
    m = add_match_targets(matches)
    log = _team_game_log(m)
    log = _rolling_team_features(log)
    log = _season_ladder_points(log)

    home_feats = log[log["is_home"] == 1].copy()
    away_feats = log[log["is_home"] == 0].copy()

    keep_roll = [
        c
        for c in home_feats.columns
        if c.startswith(("win_rate_l", "avg_pf_l", "avg_pa_l", "avg_margin_l", "games_l"))
        or c
        in {
            "rest_days",
            "win_streak_pre",
            "ladder_points_pre",
            "ladder_pct_pre",
            "season_games_pre",
            "match_id",
            "team",
        }
    ]
    home_feats = home_feats[keep_roll].rename(
        columns={c: f"home_{c}" if c not in {"match_id", "team"} else c for c in keep_roll}
    )
    home_feats = home_feats.rename(columns={"team": "home_team"})

    away_feats = away_feats[keep_roll].rename(
        columns={c: f"away_{c}" if c not in {"match_id", "team"} else c for c in keep_roll}
    )
    away_feats = away_feats.rename(columns={"team": "away_team"})

    base_cols = [
        "match_id",
        "match_date",
        "year",
        "round",
        "venue",
        "home_team",
        "away_team",
        "home_score",
        "away_score",
        "home_win",
        "match_result",
        "home_margin",
        "is_draw",
        "crowd",
    ]
    base_cols = [c for c in base_cols if c in m.columns]
    out = m[base_cols].merge(home_feats, on=["match_id", "home_team"], how="left")
    out = out.merge(away_feats, on=["match_id", "away_team"], how="left")
    out = _h2h_features(out)

    out["rest_days_diff"] = out["home_rest_days"] - out["away_rest_days"]
    out["ladder_pct_diff"] = out["home_ladder_pct_pre"] - out["away_ladder_pct_pre"]
    out["form_margin_diff_l5"] = out["home_avg_margin_l5"] - out["away_avg_margin_l5"]
    out["home_state"] = out["home_team"].map(TEAM_STATE).fillna("UNK")
    out["away_state"] = out["away_team"].map(TEAM_STATE).fillna("UNK")
    out["is_interstate"] = (out["home_state"] != out["away_state"]).astype(int)
    out["venue_code"] = out["venue"].astype("category").cat.codes

    return out.sort_values("match_date").reset_index(drop=True)


def build_player_feature_table(player_games: pd.DataFrame) -> pd.DataFrame:
    """Player-game features with prior form only (shift within player)."""
    df = add_player_targets(player_games)
    df = df.sort_values(["player_id", "match_date", "player_game_id"]).reset_index(drop=True)

    g = df.groupby("player_id", sort=False)
    for n in (3, 5):
        df[f"avg_disposals_l{n}"] = (
            g["disposals"].shift(1).rolling(n, min_periods=1).mean().reset_index(level=0, drop=True)
        )
        df[f"avg_goals_l{n}"] = (
            g["goals"].shift(1).rolling(n, min_periods=1).mean().reset_index(level=0, drop=True)
        )
        df[f"avg_impact_l{n}"] = (
            g["impact_score"].shift(1).rolling(n, min_periods=1).mean().reset_index(level=0, drop=True)
        )
        df[f"avg_fantasy_l{n}"] = (
            g["impact_official"].shift(1).rolling(n, min_periods=1).mean().reset_index(level=0, drop=True)
        )

    df["games_played_pre"] = g.cumcount()
    df["prev_match_date"] = g["match_date"].shift(1)
    df["player_rest_days"] = (df["match_date"] - df["prev_match_date"]).dt.days

    keep = [
        "player_game_id",
        "player_id",
        "team",
        "opponent",
        "year",
        "round",
        "match_date",
        "result",
        "disposals",
        "goals",
        "impact_score",
        "impact_official",
        "is_top_disposals",
        "is_top_goals",
        "is_top_impact",
        "avg_disposals_l3",
        "avg_disposals_l5",
        "avg_goals_l3",
        "avg_goals_l5",
        "avg_impact_l3",
        "avg_impact_l5",
        "avg_fantasy_l3",
        "avg_fantasy_l5",
        "games_played_pre",
        "player_rest_days",
        "career_game_count",
    ]
    keep = [c for c in keep if c in df.columns]
    return df[keep].sort_values(["match_date", "player_id"]).reset_index(drop=True)


FEATURE_DICTIONARY = [
    ("home_win_rate_l5", "Home team win rate over previous 5 games", "last 5 prior", "team log won"),
    ("away_win_rate_l5", "Away team win rate over previous 5 games", "last 5 prior", "team log won"),
    ("home_avg_margin_l5", "Home avg margin last 5 prior games", "last 5 prior", "margin"),
    ("away_avg_margin_l5", "Away avg margin last 5 prior games", "last 5 prior", "margin"),
    ("home_avg_pf_l5", "Home avg points-for last 5", "last 5 prior", "points_for"),
    ("away_avg_pf_l5", "Away avg points-for last 5", "last 5 prior", "points_for"),
    ("home_rest_days", "Days since home team's previous match", "prior gap", "match_date"),
    ("away_rest_days", "Days since away team's previous match", "prior gap", "match_date"),
    ("rest_days_diff", "home_rest_days - away_rest_days", "derived", "rest_days"),
    ("home_win_streak_pre", "Consecutive wins before this match (home)", "streak prior", "won"),
    ("away_win_streak_pre", "Consecutive wins before this match (away)", "streak prior", "won"),
    ("home_ladder_pct_pre", "Home season points ratio before match", "season-to-date prior", "W/D"),
    ("away_ladder_pct_pre", "Away season points ratio before match", "season-to-date prior", "W/D"),
    ("ladder_pct_diff", "home_ladder_pct_pre - away_ladder_pct_pre", "derived", "ladder_pct"),
    ("h2h_home_win_rate", "Historical home-team win rate in prior H2H", "last 10 meetings", "results"),
    ("h2h_games", "Number of prior H2H games used", "<=10", "matches"),
    ("venue_code", "Categorical code for venue", "match", "venue"),
    ("form_margin_diff_l5", "home_avg_margin_l5 - away_avg_margin_l5", "derived", "margins"),
    ("is_interstate", "1 if home/away teams mapped to different states", "match", "team state map"),
    ("avg_disposals_l5", "Player avg disposals last 5 prior games", "last 5 prior", "disposals"),
    ("avg_goals_l5", "Player avg goals last 5 prior games", "last 5 prior", "goals"),
    ("avg_impact_l5", "Player avg impact last 5 prior games", "last 5 prior", "impact_score"),
    ("player_rest_days", "Days since player's previous game", "prior gap", "match_date"),
]
