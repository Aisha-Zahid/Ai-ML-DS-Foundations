# Knowledge base design (Day 2 Task 1)

## Purpose

RealEstate Hub never invents prices or availability. Facts live in two stores:

1. **Structured tables (SQL)** — inventory that must be exact  
2. **Semantic documents (RAG)** — brochures, FAQs, location write-ups  

## Datasets

| Dataset | Path | Fields / content |
|---------|------|------------------|
| Properties | `data/structured/properties.csv` | id, city, area, purpose, type, beds, size, price, status, amenities, schools, hospitals, developer, agent, payment plan, investment tag |
| Developers | `data/structured/developers.csv` | id, name, trust notes, cities |
| Agents | `data/structured/agents.csv` | id, name, phone, desk |
| Payment plans | `data/structured/payment_plans.csv` | id, name, summary |
| FAQs | `data/semantic/faqs.md` | token, transfer, visits, overseas, ROI, maintenance, docs |
| Payment detail | `data/semantic/payment_plans.md` | cash / Bahria 36 / rent |
| Locations | `data/semantic/locations.md` | DHA, Bahria, Clifton, Lahore, Islamabad notes |
| Brochures | `data/semantic/brochures/*.md` | marketing copy grounded to inventory |

Cities covered: **Karachi, Lahore, Islamabad**. Purposes: buy, rent, commercial. One `sold` row exists to test availability guardrails.

## Rebuild

```powershell
cd Week-4/Day-2
python scripts/seed_kb.py
python scripts/build_kb.py
```
