# Day 4 routing & traces

## Routing accuracy

**20/20 = 100%** on held-out style phrases.

See `routing_accuracy.csv` for the full table.

## Annotated traces

Representative runs are in `annotated_traces.json` (retrieval, named tip, off-topic, multi-turn).

1. **retrieval** — router → retrieve (H2H tool) → validate → format with exact counts  
2. **predict_match_named** — router → predict_match → fixture resolve → probability + drivers disclaimer  
3. **off_topic** — router → refuse → format (no tools)
4. **multiturn_followup** — history supplies clubs; follow-up tips with the same prediction path

### Why LangGraph vs one LangChain agent

A single free-form agent can skip disclaimers, invent tips, or call the wrong tool.
Explicit routes force prediction through a node that always attaches probabilities and
fallback/clarify paths when teams or dates are missing — safer for tipping-style asks.

## E2E

`e2e_conversations.csv` has 12 runs covering retrieval, match/player prediction,
refusal, and clarification.
