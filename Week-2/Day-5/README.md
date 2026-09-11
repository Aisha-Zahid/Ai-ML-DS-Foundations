# Week 2 Day 5 — Capstone: Client Inquiry Desk

Agent for Web3Geeks-style client questions (price, stock, compare, quote, escalate).

## Files

| File | Role |
|------|------|
| `agent_system.py` | LangGraph pipeline + tools + SQLite tickets |
| `api.py` | FastAPI `/inquire` + `/approve` |
| `evaluate.py` | 10-case eval → `results/` |
| `data/products.csv` | Catalog |
| `docs/architecture.md` | Design + diagram |
| `docs/monitoring_checklist.md` | Prod monitoring |
| `docs/executive_report.md` / `.pdf` | 2-page report |
| `docs/slide_outline.md` | 5–7 min stakeholder outline |

## Setup

```powershell
cd Week-2/Day-5
pip install -r requirements.txt
```

`.env`:

```
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-20b
```

## Run agent (CLI)

```powershell
python agent_system.py --message "What is the price of the Wireless Mouse?" --auto-approve
```

## Evaluation

```powershell
python evaluate.py
```

Writes `results/evaluation_results.csv` and `results/evaluation_results.md`.

## API

```powershell
uvicorn api:app --port 8000
```

```powershell
curl -X POST http://127.0.0.1:8000/inquire -H "Content-Type: application/json" -d "{\"message\":\"Compare Wireless Mouse vs Mechanical Keyboard\",\"auto_approve\":true}"
```

For quote/escalate without `auto_approve`, call `/approve` with the returned `thread_id`.

## PDF report

```powershell
python build_report_pdf.py
```

## Framework choice (short)

LangGraph for control, quality loop, and human approval. CrewAI was better for role demos in Day 4; here interrupt + API resume mattered more than a manager crew.
