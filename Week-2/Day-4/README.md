# Week 2 Day 4 — CrewAI Multi-Agent Crew

CrewAI crew for a budget product recommendation brief.

## Business task

Review catalog facts for Wireless Mouse vs Mechanical Keyboard, compare prices, and write a short stakeholder brief recommending the cheaper in-stock option.

## Agents

| Agent | Job | Tools |
|-------|-----|-------|
| Catalog Researcher | Pull product facts from CSV | `search_catalog`, `list_in_stock_by_category` |
| Pricing Analyst | Price gap + budget pick | `calculator` |
| Stakeholder Brief Writer | Final brief | none (writing only) |

## Setup

```powershell
cd Week-2/Day-4
pip install -r requirements.txt
```

`.env`:

```
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-20b
```

## Run

```powershell
python crewai_crew.py --mode sequential
python crewai_crew.py --mode hierarchical
python crewai_crew.py --mode both
jupyter notebook agent_crewai.ipynb
```

## Files

- `crewai_crew.py` — agents, tasks, sequential + hierarchical crews
- `agent_crewai.ipynb` — Tasks 1–5
- `data/products.csv` — catalog
- `writeup.md` — design notes + comparison
- `requirements.txt`
