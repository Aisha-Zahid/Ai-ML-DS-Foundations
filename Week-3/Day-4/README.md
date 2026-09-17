# Week 3 Day 4 — LangGraph AFL Orchestrator

Routes Day-3 retrieval and Day-2 predictions through an explicit LangGraph.

## Setup

```powershell
cd Week-3/Day-4
pip install -r requirements.txt
```

Needs Day-1 features, Day-2 `models/*.joblib`, Day-3 data access.

## Run

```powershell
python app.py -m "Will the Pies beat the Cats?" --trace
python app.py -m "What is Geelong Cats record vs Richmond Tigers?"
python evaluate_routing.py
jupyter notebook langgraph_orchestrator.ipynb
```

## Deliverables

| Item | Path |
|------|------|
| Graph app | `src/graph.py`, `app.py` |
| Design doc | `docs/graph_design.md` |
| Routing table | `results/routing_accuracy.csv` |
| Traces | `results/annotated_traces.json` |
| Report | `results/day4_report.md` |
