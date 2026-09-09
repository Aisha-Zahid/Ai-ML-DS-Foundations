# Week 2 Day 3 — LangGraph Stateful Agent

LangGraph workflow with:
- StateGraph + shared State schema
- Linear graph (plan → retrieve → generate → format)
- Conditional edges + self-correction loop (critique routes back to generate)
- Human-in-the-loop interrupt before final formatting
- Persistence + resuming using `MemorySaver`

## Setup

```powershell
cd Week-2/Day-3
pip install -r requirements.txt
```

Create a `.env` file with:

```
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-20b
```

## Run

```powershell
python langgraph_agent.py
jupyter notebook agent_langgraph.ipynb
```

## Files

- `langgraph_agent.py` — graph nodes, edges, state schema
- `agent_langgraph.ipynb` — Tasks 1–5 notebook
- `data/products.csv` — catalog used by the `retrieve` node
- `writeup.md` — write-up + comparison
- `graph_diagram.md` — Mermaid diagram
- `graph_diagram.png` — PNG flowchart
