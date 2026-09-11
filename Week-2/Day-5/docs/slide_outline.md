# Slide outline (5–7 min) — Web3Geeks Client Inquiry Desk

## 1. Hook / business goal (45s)
- Problem: inbound client questions about gear (price, stock, compare, quotes) are slow and inconsistent.
- Goal: one agent desk that answers from the catalog, logs tickets, and asks a human before sending quotes or escalating.

## 2. What we built (60s)
- End-to-end LangGraph pipeline behind FastAPI (`/inquire`, `/approve`).
- Data: products CSV + SQLite tickets.
- Demo one happy path (price/compare) in one sentence.

## 3. Architecture (60s)
- Show diagram: validate → classify → retrieve → draft → quality loop → human checkpoint → finalize.
- Point at HITL for `send_quote` / `escalate` only (not every chat).

## 4. Why LangGraph (45s)
- Need control, retries, and an approval interrupt — not a free-form multi-agent chat.
- CrewAI was useful for roles in Day 4; here control + approval mattered more than a manager crew.
- Raw loop is fine for demos; weaker for persistence + API resume.

## 5. Evaluation (90s)
- 6 criteria: success, facts, latency, cost, tone, safety.
- 8–10 cases including empty input, prompt injection, unknown product, tool timeout.
- Show results table highlight: success rate + mean score.
- Main failure: product name mismatch → next step = fuzzy match + suggestions.

## 6. Production readiness (60s)
- Logging: inputs, tools, latency, tokens, errors (JSONL + SQLite).
- Monitoring checklist: error rate, cost drift, latency, quality sampling, alert thresholds.

## 7. Limits & next steps (45s)
- Limits: small catalog, placeholder email send, MemorySaver (not durable across restarts yet).
- Next: durable checkpointer, fuzzy catalog search, stronger guardrails, human review UI, larger eval set.

## 8. Ask (20s)
- Approve pilot on real inquiry channel for 2 weeks with human approval on quotes.
