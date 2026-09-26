# Structured vs semantic retrieval (Day 2 Task 3)

## Split

| Need | Store | Why |
|------|-------|-----|
| Prices | SQL `properties.price_pkr` / `price_display` | Exact numbers; no embedding drift |
| Availability / status | SQL `status` | sold vs available must be binary-correct |
| Plot / unit sizes | SQL `size_value` + `size_unit` | Filters and comparisons |
| Agent names / phones | SQL `agents` | Contact routing for booking |
| Brochures & lifestyle copy | Vector RAG | Fuzzy “batao DHA Phase 6 kaisa hai” |
| FAQs (token, docs, ROI policy) | Vector RAG | Paraphrase-friendly |
| Payment plan narratives | Vector RAG (+ id join to SQL) | Long text; SQL holds the plan id only |

## Justification

Voice clients ask messy questions. Embeddings help for “maintenance ka scene kya hai?” but must **not** invent “2.7 crore” when SQL says 3.2. Hybrid rule:

1. If the question needs a number, status, size, or person → **SQL first**.  
2. If it needs explanation, policy, or brochure tone → **RAG**.  
3. Recommendations combine SQL filters + ranking (`src/recommend.py`), then optional RAG for pitch lines later (Day 3+).

## Code map

- SQL: `src/structured.py`, `src/db.py`  
- RAG: `src/rag.py`, `src/chunking.py`  
- Hybrid answers: `src/answer.py`
