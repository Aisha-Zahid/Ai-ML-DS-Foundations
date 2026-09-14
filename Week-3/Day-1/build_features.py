"""Build processed feature tables + markdown dictionaries."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.features import (  # noqa: E402
    FEATURE_DICTIONARY,
    build_match_feature_table,
    build_player_feature_table,
)
from src.load_data import (  # noqa: E402
    build_match_level,
    inventory_summary,
    load_player_games,
    load_team_matches,
)
from src.paths import (  # noqa: E402
    DATA_DICT,
    FEATURE_DICT,
    FEATURE_MATCH_CSV,
    FEATURE_MATCH_PARQUET,
    FEATURE_PLAYER_CSV,
    PROCESSED_DIR,
)
from src.splits import CEILING_NOTE, DEFAULT_HOLDOUT_YEAR, describe_split  # noqa: E402
from src.targets import TARGET_DICTIONARY  # noqa: E402


def write_data_dictionary() -> None:
    lines = [
        "# Data dictionary & prediction targets — Week 3 Day 1",
        "",
        "## Source tables",
        "",
        "| File | Grain | Row means | Join keys |",
        "|------|-------|-----------|-----------|",
        "| `afl_players_info_raw.csv` | player | one bio row per player | `player_id` |",
        "| `afl_players_round_by_round_stats_raw...csv` | player-game | one row per player in a match | `player_id`, `team`, `opponent`, `match_date` |",
        "| `afl_players_seasonal_stats_raw.csv` | player-season | season totals/averages (finals flag) | `player_id`, `year`, `team` |",
        "| `team_matches_home_away_raw...csv` | team-game | each match appears twice (H and A) | `team`, `opponent`, `match_date`, `venue` |",
        "",
        "Match-level modeling uses a derived table: **one row per match** (home perspective) with `match_id`.",
        "",
        "## Coverage notes",
        "",
        "- Years roughly **1983–2025** (player and team tables).",
        "- Team renames / structure: Brisbane Bears → Lions; Footscray / W. Bulldogs → Western Bulldogs; Fitzroy exits; Gold Coast & GWS join later.",
        "- Source team names had leading tabs/spaces; loaders strip and alias them.",
        "- Player `score` column is empty; use `fantasy_points` / our `impact_score`.",
        "- Older seasons have many null advanced stats (clearances, Brownlow, etc.).",
        "",
        "## Match winner framing",
        "",
        "Primary target: **`home_win`** (binary classification). Draws are rare and coded as 0.",
        "Secondary: **`home_margin`** (regression) for strength of win.",
        "Also keep **`match_result`** ∈ {home_win, away_win, draw} for multiclass if needed.",
        "",
        "Why classification first: stakeholders ask “who wins?”; margin is a useful extra signal for Day 2.",
        "",
        "## Top player definitions",
        "",
        "All at **player-game** level within a match (`game_key`).",
        "",
        "1. **Top disposal-getter** — `is_top_disposals = 1` if player ties for max `disposals` in that game.",
        "2. **Top goal-kicker** — `is_top_goals = 1` if player ties for max `goals` in that game.",
        "3. **Composite impact** —",
        "",
        "```",
        "impact_score = 3*kicks + 2*handballs + 3*marks + 4*tackles",
        "             + 6*goals + 1*behinds + 1*hit_outs",
        "```",
        "",
        "`is_top_impact = 1` if player ties for max `impact_score` in that game. Missing inputs treated as 0.",
        "",
        "## Target contract (Day 2)",
        "",
        "| target_name | definition | formula | level | task |",
        "|-------------|------------|---------|-------|------|",
    ]
    for t in TARGET_DICTIONARY:
        lines.append(
            f"| `{t['target_name']}` | {t['definition']} | `{t['formula']}` | {t['level']} | {t['task_type']} |"
        )

    lines += [
        "",
        "## Train / hold-out",
        "",
        f"Default: train `year < {DEFAULT_HOLDOUT_YEAR}`, holdout `year >= {DEFAULT_HOLDOUT_YEAR}` via `src.splits.time_based_split`.",
        "",
        "## Accuracy ceiling",
        "",
        CEILING_NOTE,
        "",
    ]
    DATA_DICT.parent.mkdir(parents=True, exist_ok=True)
    DATA_DICT.write_text("\n".join(lines), encoding="utf-8")
    print("Wrote", DATA_DICT)


def write_feature_dictionary() -> None:
    lines = [
        "# Feature dictionary v1",
        "",
        "All rolling / ladder / H2H features use **only games strictly before** the row's `match_date` (shift-1).",
        "",
        "| name | description | window | source |",
        "|------|-------------|--------|--------|",
    ]
    for name, desc, window, source in FEATURE_DICTIONARY:
        lines.append(f"| `{name}` | {desc} | {window} | {source} |")
    lines += [
        "",
        "Files: `data/processed/match_features_v1.csv` (+ parquet), `player_game_features_v1.csv`.",
        "",
    ]
    FEATURE_DICT.write_text("\n".join(lines), encoding="utf-8")
    print("Wrote", FEATURE_DICT)


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    print("Inventory:", inventory_summary())

    matches = build_match_level(load_team_matches())
    match_feat = build_match_feature_table(matches)
    match_feat.to_csv(FEATURE_MATCH_CSV, index=False)
    try:
        match_feat.to_parquet(FEATURE_MATCH_PARQUET, index=False)
        print("Wrote", FEATURE_MATCH_PARQUET)
    except Exception as exc:  # noqa: BLE001
        print("parquet skipped:", exc)
    print("Wrote", FEATURE_MATCH_CSV, match_feat.shape)
    print("split:", describe_split(match_feat))

    # Player table can be large — write CSV (optionally sample years for parquet speed)
    pg = load_player_games()
    # Keep modern era for player modeling volume control still includes history needed for rolling
    player_feat = build_player_feature_table(pg)
    # Full CSV may be big; write full and a recent slice
    player_feat.to_csv(FEATURE_PLAYER_CSV, index=False)
    print("Wrote", FEATURE_PLAYER_CSV, player_feat.shape)
    print("player split:", describe_split(player_feat))

    write_data_dictionary()
    write_feature_dictionary()


if __name__ == "__main__":
    main()
