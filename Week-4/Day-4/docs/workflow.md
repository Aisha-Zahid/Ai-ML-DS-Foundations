# Workflow automation (Task 4)

## n8n

Import `n8n/realestate_hub_workflow.json`.

## Python twin

`src/workflow.py` → `run_booking_workflow`:

1. upsert client  
2. log call transcript  
3. intent  
4. property match gate  
5. appointment (calendar + email) with retries  
6. CRM preferences  

Failures retry up to `WORKFLOW_MAX_RETRIES` with backoff. See `scripts/test_retries.py`.
