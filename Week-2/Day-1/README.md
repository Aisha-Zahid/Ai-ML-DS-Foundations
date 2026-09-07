# Week 2 Day 1 — Agent Foundations

Minimal **raw Python** ReAct agent using the **Groq** API (no LangChain / LangGraph / CrewAI).

## Setup

```bash
cd Week-2/Day-1
pip install -r requirements.txt
```

Put the API key in a local `.env`:

```
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-20b
```

Or PowerShell for the current session:

```powershell
$env:GROQ_API_KEY = "gsk_..."
```

## Run

```bash
# Multi-step agent (weather in 2 cities + calculator) — Task 3
python agent.py

# Custom prompt
python agent.py --prompt "Read sample_notes.txt and summarize it."

# Task 2: single tool round-trip demo
python agent.py --single-tool-demo

# Task 5: deliberate failure prompts
python agent.py --demo-failures

# Notebook walkthrough (concepts + same code)
jupyter notebook agent_foundations.ipynb
```

## Files

| File | Purpose |
|------|---------|
| `agent.py` | Tools, schemas, ReAct loop, logging, failure demos |
| `agent_foundations.ipynb` | Tasks 1–5 with explanations + runnable cells |
| `sample_notes.txt` | Demo file for `read_file` |
| `writeup.md` | 1-page write-up (ReAct, schemas, failures) |
| `requirements.txt` | Dependencies |
| `.env` | Local API key (do not commit) |

## Tools

1. **calculator** — safe arithmetic expressions  
2. **get_weather** — stub weather for a few cities  
3. **read_file** — read text files inside this folder only  

## Safety notes

- Never commit API keys (`.env` is gitignored).
- `max_iterations` stops infinite tool loops.
- Tool errors are returned as JSON strings so the model can recover or admit failure.
