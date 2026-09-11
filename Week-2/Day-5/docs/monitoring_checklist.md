# Monitoring checklist (production)

One-page checklist for the Web3Geeks Client Inquiry Desk.

## What to track

| Signal | Why | Where |
|--------|-----|--------|
| Error rate (`status=failed` / 5xx) | Catch breakage fast | `logs/agent.jsonl`, API logs, tickets.db |
| Refusal rate | Safety / prompt-injection pressure | agent logs (`status=refused`) |
| Latency p50 / p95 | UX and Groq slowdowns | `latency_ms` field |
| Cost per run + daily spend | Budget drift | `estimated_cost_usd`, token fields |
| Tool failure rate | Catalog / SQLite / calculator issues | `tool_calls` + error events |
| Approval queue depth | HITL bottleneck | `needs_approval` tickets |
| Output quality sample | Tone / factual drift | weekly human review of 20 replies |

## Alert thresholds (starting point)

- Error rate > 5% over 15 minutes → page on-call
- p95 latency > 20s for 10 minutes → warn
- Estimated daily cost > 2× 7-day baseline → warn
- Refusal rate > 10% (possible attack or bad UX) → investigate
- Catalog tool errors > 2% → check CSV/DB path
- Approval wait > 30 minutes median → staffing issue

## Re-evaluation cadence

| Cadence | Action |
|---------|--------|
| Daily | Skim error + cost dashboard; clear stuck approvals |
| Weekly | Re-run `evaluate.py` (8–10 fixed cases); spot-check 20 live replies |
| Monthly | Refresh criteria, add new edge cases, review HITL rules |
| On model change | Full eval suite before promoting new `GROQ_MODEL` |

## Log fields to keep

`request_id`, `client_name`, `intent`, `status`, `latency_ms`, `tokens_in`, `tokens_out`, `estimated_cost_usd`, `tool_calls`, `error`, `proposed_action`, `human_approved`.
