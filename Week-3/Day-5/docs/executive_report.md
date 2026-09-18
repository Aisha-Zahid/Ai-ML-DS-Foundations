# Executive report — AFL Chat & Prediction Assistant

**Audience:** stakeholders / client property owners  
**Length:** ~2 pages  
**Product:** Domain-locked AFL assistant (chat + retrieval + probabilistic tips)

## 1. Product goal

Ship a demo-ready AFL assistant that answers factual club/player questions from tables, tips match winners and top-impact players with explicit probabilities, and refuses off-topic or jailbreak prompts — suitable for a Web3Geeks-style showcase or client embed behind an API/UI.

## 2. Architecture

```
User → FastAPI / Streamlit → Day-5 hardened wrapper
         → abuse / rate checks → timed LangGraph (Day-4)
              router → retrieve | predict_match | predict_player | refuse | clarify
                   → validate → format (disclaimer on all tips)
         → JSONL monitoring log
```

- **Retrieval** reuses Day-3 table tools (H2H, recent form, player season).
- **Prediction** calls Day-2 `predict_match_winner` / `predict_top_player` after nickname + fixture resolve.
- **LangGraph routing** is explicit so tips always go through the prediction node (probabilities + drivers + “predicted probability, not a certainty”), instead of a free-form agent inventing odds.

## 3. Evaluation results

From the Day-5 capstone suite (`results/capstone_eval.md`) and Day-2 holdout metrics:

- **Combined suite:** **28 cases**, overall **~96–100%** pass after multi-turn hardening; categories cover factual Q&A, prediction framing/sanity, guardrails (4/4 prompt-injection holds), and multi-turn coherence.
- **Weakest category:** conversational coherence (entity carry-over on short follow-ups) — mitigated by classifying follow-up intent separately and seeding prior user turns only.
- **Match model context:** Day-2 GBM holdout accuracy **65.0%**, ROC AUC **0.71**, vs higher-ladder naive baseline **63.9%** / **0.63** AUC (+1.2pp accuracy, +0.07 AUC). Always-home baseline **56.2%**.

## 4. Known limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Data recency | Tips use historical feature dump, not live odds | Weekly feature refresh after each round |
| Accuracy ceiling | ~65% holdout; close games stay near 50% | Always show probabilities + disclaimer |
| Guardrail edge cases | Novel jailbreaks / blended AFL+off-topic | Expand injection patterns; refuse-first |
| Cold-start latency | First tip loads joblib + large CSVs | Cache models at API startup; timeouts |
| Player tips | Rank by impact composite, not named fantasy | Label clearly; optional name join later |

## 5. Recommended next steps

1. Preload Day-2 artifacts in FastAPI lifespan to cut p95 latency.
2. Join player display names into top-player responses.
3. Persist tips + actuals for live drift dashboards.
4. Add auth + per-IP rate limits before public internet exposure.
5. Optional: light LLM rewrite *after* tools, still forbidden from changing refuse/tip math.

## Bottom line

The system is **demo-ready**: factual lookups, probabilistic tips with consistent disclaimers, injection refusals, API + Streamlit UI, and an ops checklist for round-by-round refresh. Treat tips as decision support, not guarantees.
