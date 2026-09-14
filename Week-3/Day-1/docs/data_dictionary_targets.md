# Data dictionary & prediction targets — Week 3 Day 1

## Source tables

| File | Grain | Row means | Join keys |
|------|-------|-----------|-----------|
| `afl_players_info_raw.csv` | player | one bio row per player | `player_id` |
| `afl_players_round_by_round_stats_raw...csv` | player-game | one row per player in a match | `player_id`, `team`, `opponent`, `match_date` |
| `afl_players_seasonal_stats_raw.csv` | player-season | season totals/averages (finals flag) | `player_id`, `year`, `team` |
| `team_matches_home_away_raw...csv` | team-game | each match appears twice (H and A) | `team`, `opponent`, `match_date`, `venue` |

Match-level modeling uses a derived table: **one row per match** (home perspective) with `match_id`.

## Coverage notes

- Years roughly **1983–2025** (player and team tables).
- Team renames / structure: Brisbane Bears → Lions; Footscray / W. Bulldogs → Western Bulldogs; Fitzroy exits; Gold Coast & GWS join later.
- Source team names had leading tabs/spaces; loaders strip and alias them.
- Player `score` column is empty; use `fantasy_points` / our `impact_score`.
- Older seasons have many null advanced stats (clearances, Brownlow, etc.).

## Match winner framing

Primary target: **`home_win`** (binary classification). Draws are rare and coded as 0.
Secondary: **`home_margin`** (regression) for strength of win.
Also keep **`match_result`** ∈ {home_win, away_win, draw} for multiclass if needed.

Why classification first: stakeholders ask “who wins?”; margin is a useful extra signal for Day 2.

## Top player definitions

All at **player-game** level within a match (`game_key`).

1. **Top disposal-getter** — `is_top_disposals = 1` if player ties for max `disposals` in that game.
2. **Top goal-kicker** — `is_top_goals = 1` if player ties for max `goals` in that game.
3. **Composite impact** —

```
impact_score = 3*kicks + 2*handballs + 3*marks + 4*tackles
             + 6*goals + 1*behinds + 1*hit_outs
```

`is_top_impact = 1` if player ties for max `impact_score` in that game. Missing inputs treated as 0.

## Target contract (Day 2)

| target_name | definition | formula | level | task |
|-------------|------------|---------|-------|------|
| `home_win` | 1 if home team won the match, else 0 (draws = 0) | `1[home_result == 'W']` | match | classification |
| `match_result` | 3-way label: home_win / away_win / draw | `map(home_result)` | match | multiclass |
| `home_margin` | Home score minus away score (points) | `home_score - away_score` | match | regression |
| `is_top_disposals` | Player recorded the equal-highest disposals in that match | `1[disposals == max(disposals | game_key)]` | player-game | classification |
| `is_top_goals` | Player recorded the equal-highest goals in that match | `1[goals == max(goals | game_key)]` | player-game | classification |
| `is_top_impact` | Player had equal-highest composite impact in that match | `impact = 3K+2H+3M+4T+6G+1B+1HO; 1[impact == max(impact|game)]` | player-game | classification |
| `impact_score` | Fantasy/Brownlow-style continuous player output | `3*kicks + 2*handballs + 3*marks + 4*tackles + 6*goals + 1*behinds + 1*hit_outs` | player-game | regression |

## Train / hold-out

Default: train `year < 2024`, holdout `year >= 2024` via `src.splits.time_based_split`.

## Accuracy ceiling

AFL match outcomes are noisy: injuries, weather, travel, umpiring, and in-game variance mean even strong models rarely clear ~60–70% accuracy on home/away winner over a long span. Margin MAE of several goals is normal. Near-perfect accuracy on a holdout season would be a red flag for leakage (e.g. using same-game stats, post-match ladder, or a shuffled split).
