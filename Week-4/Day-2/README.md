# Week 4 Day 2 — Knowledge Base, RAG & Property Intelligence

Grounded property intelligence for the RealEstate Hub voice agent: SQL inventory + TF-IDF RAG + recommendations + hallucination eval.

## Setup

```powershell
cd Week-4/Day-2
pip install -r requirements.txt
python scripts/seed_kb.py
python scripts/build_kb.py
python scripts/evaluate_chunks.py
python scripts/evaluate_hallucination.py
jupyter notebook knowledge_base.ipynb
```

## Deliverables

| Task | Path |
|------|------|
| KB design | `docs/knowledge_base_design.md` |
| Structured data | `data/structured/*.csv` |
| Semantic docs | `data/semantic/**` |
| RAG pipeline | `src/chunking.py`, `src/rag.py`, `src/answer.py` |
| Structured retrieval | `src/structured.py`, `src/db.py` |
| Why SQL vs vector | `docs/structured_vs_semantic.md` |
| Recommendations | `src/recommend.py` |
| Chunk eval | `results/chunk_eval.md` |
| Hallucination eval (20 Q) | `results/hallucination_eval.md` |

## Quick API (Python)

```python
from src.recommend import recommend
from src.answer import answer_question
from src.structured import search_properties

recommend(budget="3 crore", city="Karachi", purpose="buy", bedrooms=3)
answer_question("Do you guarantee ROI on Bahria plots?")
search_properties(city="Lahore", purpose="buy", available_only=True)
```

## Notes

- Embeddings use **TF-IDF + cosine** locally (no paid API). Swap for Chroma/OpenAI embeddings in production without changing SQL layer.
- Default chunk variant: `medium_800` (see chunk eval for comparison).
