# Week 2 Day 2 — LangChain Agent

Rebuild Day 1’s agent with **LangChain**: tools, AgentExecutor, memory, structured output. Uses **Groq** (same free key pattern as Day 1). Brief asks for `create_tool_calling_agent` + `AgentExecutor` — those live in `langchain-classic` under LangChain 1.x (same APIs).

## Setup

```powershell
cd Week-2/Day-2
pip install -r requirements.txt
```

Put the key in `.env` (or reuse Day-1 `.env` — the code falls back):

```
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-20b
```

## Run

```powershell
python langchain_agent.py
jupyter notebook agent_langchain.ipynb
```

## Files

| File | Purpose |
|------|---------|
| `langchain_agent.py` | Tools, LCEL chain, AgentExecutor, memory helpers |
| `agent_langchain.ipynb` | Tasks 1–5 with traces |
| `data/products.csv` | Catalog for `lookup_product` |
| `writeup.md` | Raw-Python vs LangChain + annotated trace |
| `requirements.txt` | Dependencies |

## Tools

1. `calculator` — arithmetic (from Day 1)
2. `get_weather` — stub weather (from Day 1)
3. `lookup_product` — reads `data/products.csv`
4. `flaky_divide` — intentional failures for error handling
