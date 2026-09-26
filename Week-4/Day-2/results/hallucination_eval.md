# Hallucination / grounding evaluation (20 questions)

| Metric | Value |
|--------|-------|
| Cases | 20 |
| Pass rate | 100% |
| Grounding rate | 100% |
| Retrieval accuracy | 100% |
| Hallucination rate | 0% |

Definitions:
- **Grounded**: answer tied to SQL/RAG sources (or honest abstain).
- **Retrieval accuracy**: required anchors found + sources present (or correct abstain).
- **Hallucination**: forbidden invented content or unsourced confident facts.

See `hallucination_eval.csv` for per-question detail.
