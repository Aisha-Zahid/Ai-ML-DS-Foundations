# Week 4 Day 4 — Workflows, Scheduling & Business Automation

Book / reschedule / cancel site visits with Calendar + employee email + CRM logging. n8n workflow included; Python orchestrator runs the same path locally with retries.

## Setup

```powershell
cd Week-4/Day-4
pip install -r requirements.txt
copy .env.example .env
```

Default modes are **mock** (writes `outbox/calendar` + `outbox/email`, SQLite CRM). Flip to live Google/Resend via `.env` when ready.

## Run

```powershell
python scripts/demo_booking_flow.py
python scripts/test_retries.py
python app_cli.py slots
python app_cli.py book --name "Ayesha" --phone 03001234567 --when "Saturday 4pm" --property-id KR-DHA-8-001
python app_cli.py list
```

## Deliverables

| Task | Path |
|------|------|
| Google Calendar (mock/live) | `src/calendar_service.py` |
| Employee email | `src/email_service.py` |
| Book / reschedule / cancel | `src/appointments.py` |
| n8n workflow | `n8n/realestate_hub_workflow.json` |
| Workflow + retries | `src/workflow.py` |
| CRM logging | `src/crm.py` → `data/crm.sqlite` |

## Flow

Call → Intent → Property match → Appointment → Calendar event → Employee email → CRM (+ follow-up reminder)
