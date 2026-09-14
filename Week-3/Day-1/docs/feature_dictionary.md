# Feature dictionary v1

All rolling / ladder / H2H features use **only games strictly before** the row's `match_date` (shift-1).

| name | description | window | source |
|------|-------------|--------|--------|
| `home_win_rate_l5` | Home team win rate over previous 5 games | last 5 prior | team log won |
| `away_win_rate_l5` | Away team win rate over previous 5 games | last 5 prior | team log won |
| `home_avg_margin_l5` | Home avg margin last 5 prior games | last 5 prior | margin |
| `away_avg_margin_l5` | Away avg margin last 5 prior games | last 5 prior | margin |
| `home_avg_pf_l5` | Home avg points-for last 5 | last 5 prior | points_for |
| `away_avg_pf_l5` | Away avg points-for last 5 | last 5 prior | points_for |
| `home_rest_days` | Days since home team's previous match | prior gap | match_date |
| `away_rest_days` | Days since away team's previous match | prior gap | match_date |
| `rest_days_diff` | home_rest_days - away_rest_days | derived | rest_days |
| `home_win_streak_pre` | Consecutive wins before this match (home) | streak prior | won |
| `away_win_streak_pre` | Consecutive wins before this match (away) | streak prior | won |
| `home_ladder_pct_pre` | Home season points ratio before match | season-to-date prior | W/D |
| `away_ladder_pct_pre` | Away season points ratio before match | season-to-date prior | W/D |
| `ladder_pct_diff` | home_ladder_pct_pre - away_ladder_pct_pre | derived | ladder_pct |
| `h2h_home_win_rate` | Historical home-team win rate in prior H2H | last 10 meetings | results |
| `h2h_games` | Number of prior H2H games used | <=10 | matches |
| `venue_code` | Categorical code for venue | match | venue |
| `form_margin_diff_l5` | home_avg_margin_l5 - away_avg_margin_l5 | derived | margins |
| `is_interstate` | 1 if home/away teams mapped to different states | match | team state map |
| `avg_disposals_l5` | Player avg disposals last 5 prior games | last 5 prior | disposals |
| `avg_goals_l5` | Player avg goals last 5 prior games | last 5 prior | goals |
| `avg_impact_l5` | Player avg impact last 5 prior games | last 5 prior | impact_score |
| `player_rest_days` | Days since player's previous game | prior gap | match_date |

Files: `data/processed/match_features_v1.csv` (+ parquet), `player_game_features_v1.csv`.
