# Executive report — Web3Geeks Client Inquiry Desk

**Week 2 Day 5 Capstone**  
**Author:** internship submission  
**Stack:** LangGraph + Groq + FastAPI + SQLite

---

## 1. Business goal

Web3Geeks (and similar freelance / small-shop setups) get repeated client messages about product price, stock, comparisons, formal quotes, and complaints. Manual replies are slow and easy to get wrong on numbers.

This project is a **Client Inquiry Desk** agent that:

- Sorts the message (price / stock / compare / quote / escalate)
- Looks up a local catalog (`products.csv`)
- Drafts a short reply from those facts
- Logs every ticket to SQLite
- **Waits for human approval** before sending a quote or escalating

Goal: fewer wrong prices, faster first replies, and a human check on important actions.

---

## 2. Architecture (short)

API (`POST /inquire`) → LangGraph nodes:

`validate_input` → `classify_intent` → `retrieve_catalog` → `draft_reply` → `quality_check` (loop) → `human_checkpoint` (if quote/escalate) → `apply_action` → `finalize`

Failures go to `fail_gracefully` with a clear message.

| Layer | Choice |
|-------|--------|
| Orchestration | LangGraph state machine + MemorySaver threads |
| Model | Groq (`GROQ_MODEL`, default `openai/gpt-oss-20b`) |
| Tools / data | Catalog CSV search, calculator, SQLite `tickets.db` |
| API | FastAPI `/inquire` + `/approve` |
| Observability | JSONL logs (`logs/agent.jsonl`) + ticket rows |

See `docs/architecture.md` for the diagram.

---

## 3. Framework choice

**LangGraph**, not CrewAI.

The desk needs validation, routing, a quality retry loop, and a pause before quote/escalate. LangGraph fits that shape and reuses the Day 3 HITL idea behind an API. CrewAI was good in Day 4 for role handoffs, but hierarchical runs were slower/costlier on similar catalog work without clearly better answers. A raw Day-1 ReAct loop is fine for learning, but weaker for saved approval state and resume. Catalog tools and critique ideas still come from Days 1–4.

---

## 4. Evaluation results

Criteria (0/1 each): **task success**, **factual accuracy**, **latency**, **cost**, **tone/quality**, **safety**.

Suite: **10 cases** (includes empty input, prompt-injection / SQL-ish text, unknown product, simulated catalog timeout).

Scores: `results/evaluation_results.md` (and CSV). Latest run:

- **10/10** expected statuses matched (task success **100%**)
- **Mean score 6.0 / 6**
- Happy-path latency about **1.5–2.5s**; cost per run under **$0.05**
- Edge cases returned `failed` / `refused` as expected (short input, injection text, unknown product, tool timeout)

### Most common failure pattern

**Catalog name mismatch** — clients name products that are not exact CSV titles (or invent items). The agent fails closed, but the message is blunt.

### What to change next

Add fuzzy / alias matching and return top-3 catalog suggestions when lookup misses, instead of only a hard error.

---

## 5. Known limitations

- Catalog is a small static CSV (not a live inventory API).
- Quote “send” and escalate are placeholders (logged only, not real email/ITSM yet).
- Checkpointer is in-memory (`MemorySaver`) — process restart drops open approval threads.
- Classification is mostly keyword-based with optional model backup; odd phrasing can mis-route.
- Quality scoring is simple (grounding + length), not a full judge panel.

---

## 6. Recommended next steps

1. **Durable state** — Sqlite/Postgres checkpointer for HITL resume across deploys.
2. **Guardrails** — tighter input filters, PII scrubbing in logs, allow-list tools only.
3. **Retrieval** — fuzzy match + embeddings over catalog; sync from real stock DB.
4. **Human oversight UI** — simple queue for `/approve` with draft diff.
5. **Larger eval** — grow to 30+ cases; weekly check on model changes; follow `docs/monitoring_checklist.md`.
6. **Pilot** — 2-week shadow mode on real inquiries, human approval required on all quotes.

---

## Appendix — how to run

```powershell
cd Week-2/Day-5
pip install -r requirements.txt
# set GROQ_API_KEY in .env
python agent_system.py --message "What is the price of the Wireless Mouse?" --auto-approve
python evaluate.py
uvicorn api:app --port 8000
```
