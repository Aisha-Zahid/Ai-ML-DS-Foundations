# Week 4 Day 2 — Summary

## Done

1. **Knowledge base** — 16 properties (Karachi/Lahore/Islamabad), developers, agents, payment plans, FAQs, locations, brochures.  
2. **RAG pipeline** — load → chunk (400/800/1200) → TF-IDF index → retrieve → grounded answer.  
3. **Structured vs semantic** — SQL for price/availability/size/agents; vectors for FAQ/brochure (`docs/structured_vs_semantic.md`).  
4. **Recommendation engine** — budget, city, area, beds, purpose, amenities, investment tags.  
5. **Evals** — chunk hit rates; **20/20** hallucination suite (grounding 100%, hallucination 0%).

## Key results

| Eval | Result |
|------|--------|
| Chunk probes | 100% hit rate on small/medium/large |
| Hallucination suite | 20/20 pass |
| Grounding rate | 100% |
| Hallucination rate | 0% |

## Next (Day 3)

Wire this KB into the streaming voice loop (STT → LLM+tools → Fish TTS) with UrduLish fillers and memory.
