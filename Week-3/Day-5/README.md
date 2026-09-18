# Week 3 Day 5 — Capstone AFL Assistant

Full product wrap: hardened LangGraph pipeline, evaluation pack, FastAPI + Streamlit, monitoring docs, and stakeholder materials.

## Setup

```powershell
cd Week-3/Day-5
pip install -r requirements.txt
pip install -r ..\Day-4\requirements.txt
copy ..\Day-4\.env .env   # or fill .env.example
```

Needs Day-1 features, Day-2 `models/*.joblib`, and Day-4 graph code.

## Run API

```powershell
python api.py
# or: uvicorn api:app --host 0.0.0.0 --port 8000
```

```powershell
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"Will the Pies beat the Cats?\",\"conversation_id\":\"demo1\"}"
```

## Run UI

```powershell
streamlit run ui_streamlit.py
```

## Evaluate

```powershell
python evaluate_capstone.py
python benchmark_compare.py
python make_pdf.py
```

## Deliverables

| Item | Path |
|------|------|
| Hardened assistant | `src/assistant.py`, `src/abuse.py` |
| FastAPI | `api.py` |
| Streamlit UI | `ui_streamlit.py` |
| Eval (25+ cases) | `results/capstone_eval.md` / `.csv` |
| Benchmark vs ladder | `results/benchmark_compare.md` |
| Monitoring checklist | `docs/monitoring_checklist.md` |
| Executive report | `docs/executive_report.md` + `.pdf` |
| Demo script | `docs/demo_script.md` |

## Hardening notes

- Tool/graph **timeouts** (`TOOL_TIMEOUT_SEC`)
- Consistent tip disclaimer: *Predicted probability, not a certainty*
- Rate limit + injection / repeated off-topic probing (`src/abuse.py`)
- Structured JSONL logs: query, intent, tools, latency, token estimate → `logs/assistant.jsonl`
