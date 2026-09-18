# Monitoring & maintenance checklist

One-page ops plan for the AFL assistant in production-like demos (Web3Geeks / client).

## What to track

| Signal | Source | Why |
|--------|--------|-----|
| Response latency (p50 / p95) | `logs/assistant.jsonl` → `latency_ms` | Catch slow Day-2 model loads / cold starts |
| Tool error rate | `tool_error` non-null / total | Broken fixtures, missing feature rows |
| Off-topic leak rate | intent≠off_topic on injection/off-topic prompts (eval pack) | Scope failures |
| Prompt-injection block rate | `blocked_reason=prompt_injection` | Abuse pressure |
| Prediction coverage | tip requests with empty `prediction` | Fixture resolve gaps |
| Prediction accuracy drift | after each round: tip vs actual home_win | Model freshness |

## Alert thresholds (demo / soft prod)

- **p95 latency > 20s** for 10+ requests in 15 min → investigate model cache / CSV I/O
- **Tool error rate > 10%** over 50 requests → page on-call / disable tip route temporarily
- **Off-topic leak > 0** on the injection eval pack → hotfix router / refuse node before demo
- **Accuracy drift:** rolling 4-round tip accuracy **> 5pp below** holdout GBM (~65%) → schedule retrain

## Cadence

| Cadence | Action |
|---------|--------|
| Daily | Skim JSONL for spikes; smoke `/health` + one tip + one H2H |
| Weekly | Re-run `evaluate_capstone.py` + injection trio; archive pass rates |
| After each AFL round | Ingest results → refresh features → compare tipped probs vs outcomes |
| Monthly / mid-season | Full retrain of match + player models if drift alert fires |

## Weekly refresh / retrain loop

1. **Ingest** new match + player rows into the raw Day-1 tables.
2. **Rebuild features:** `Week-3/Day-1/python build_features.py` → `match_features_v1` / player features.
3. **Score drift:** compare last round’s stored tips (`prediction.home_win_probability`) to actual `home_win`.
4. **Retrain when:** (a) drift alert, or (b) ≥1 new completed round and it has been ≥7 days since last train — run `Week-3/Day-2/python train_models.py`.
5. **Redeploy:** restart API so joblib artifacts reload; smoke tip + retrieval; bump model version in logs.

## Ownership notes

- Keep `.env` secrets out of git; rotate Groq keys if leaked.
- Cap rate limit (`RATE_LIMIT_PER_MIN`) per `conversation_id` to blunt probing.
- Prefer rule-based router for scope; only use LLM if it cannot override refuse paths.
