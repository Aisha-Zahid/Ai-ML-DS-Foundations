# Retrieval design — Week 3 Day 3

## Split

| Kind | Used for | Why |
|------|----------|-----|
| **Structured lookup** (pandas on Day-1 tables) | H2H records, season totals, player-game disposals/goals, recent scores | Sports numbers must be exact. Fuzzy/vector search can invent or blend stats. |
| **Fact-card search** (keyword over short blurbs) | Club/player background text generated from the same tables | We do not have match-report news. Cards give light context only; tools still own the numbers. |

## Tools

1. `get_team_h2h_record`
2. `get_player_season_stats`
3. `get_player_game_stats`
4. `get_recent_team_results`
5. `search_afl_fact_cards` (optional semantic-style retrieval)

## Grounding

`chat()` logs every tool JSON payload. After the model answers, `grounding_check` lists digits in the reply that never appear in tool output. Stat questions should show `tool_calls >= 1` and few/no missing numbers.
