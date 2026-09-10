# Week 2 Day 4 Write-up — CrewAI

## Task design

Business goal: recommend Wireless Mouse vs Mechanical Keyboard for a budget client and write a short stakeholder brief.

| Agent | Role | Goal | Why separate |
|-------|------|------|--------------|
| Catalog Researcher | Find catalog facts | Accurate prices / stock | Stays grounded in CSV |
| Pricing Analyst | Compare numbers | Clear cheaper option | Owns calculator math |
| Brief Writer | Stakeholder writing | Clean brief | No tools; uses prior outputs only |

I used separate agents because research, math, and writing need different tools. For a tiny one-shot lookup, one agent would be enough.

## Tool assignment

- Researcher gets catalog tools only.
- Analyst gets calculator only.
- Writer gets no tools so it cannot re-query or invent new numbers.

## Task output format

Researcher output was free-form at first, so the analyst sometimes missed prices. I added a `CATALOG_FACTS` JSON block in `expected_output` (and `PRICE_ANALYSIS` for the analyst) so the next step gets clear numbers.

## Sequential vs hierarchical

| | Sequential | Hierarchical |
|--|------------|--------------|
| Pros | Simple order, fewer moving parts | Manager can re-check / re-assign |
| Cons | Weak if an early output is messy | More tokens / latency |
| Use when | Steps are clear and linear | Quality control / delegation matters |

## Cost and complexity

Sequential run was about 5s and ~11k tokens (score 3/3). Hierarchical also scored 3/3 but took ~68s and more tokens because the manager re-delegated work. Day 3 LangGraph is cheaper for the same catalog compare on a single path. For this brief, sequential CrewAI is enough — roles are clearer, but hierarchical cost is high for little extra quality.
