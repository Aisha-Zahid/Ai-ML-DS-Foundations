# CRM logging (Task 5)

SQLite `data/crm.sqlite` tables:

| Table | Stores |
|-------|--------|
| `clients` | name, phone, city |
| `call_logs` | transcript JSON, intent |
| `preferences` | budget/area/beds/shortlist |
| `appointments` | booking history + calendar/email ids |
| `follow_ups` | open reminders (default +2 days post visit) |
| `workflow_runs` | step traces for ops |

Query via `python app_cli.py list` or open the SQLite file.
