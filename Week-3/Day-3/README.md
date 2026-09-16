# Week 3 Day 3 — Domain-Scoped AFL Chat Agent

LangChain agent that stays on AFL, looks up real tables for stats, and refuses off-topic asks.

## Setup

```powershell
cd Week-3/Day-3
pip install -r requirements.txt
```

`.env` (Groq):

```
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-20b
```

Needs Day-1 processed CSVs under `../Day-1/data/processed/`.

## Run

```powershell
python chat.py -m "What is Geelong Cats record vs Richmond Tigers?"
python chat.py
python evaluate_guardrails.py
jupyter notebook afl_chat_agent.ipynb
```

## Files

| Path | Role |
|------|------|
| `src/agent.py` | LangChain tool-calling agent + memory |
| `src/tools.py` | Structured + fact-card tools |
| `src/prompts.py` | Scope + refusal examples |
| `docs/retrieval_design.md` | Lookup vs text search |
| `results/guardrail_eval.md` | Eval report |

## How to call

```python
from src.agent import chat, reset_session

reset_session("demo")
print(chat("Show recent Sydney Swans results", session_id="demo")["answer"])
print(chat("What about the game before that?", session_id="demo")["answer"])
```
