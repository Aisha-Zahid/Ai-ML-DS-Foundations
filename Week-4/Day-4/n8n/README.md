# n8n workflow — RealEstate Hub

Import `realestate_hub_workflow.json` into n8n (Workflows → Import).

## Flow

1. **Webhook** receives voice-agent payload  
2. **Intent normalize**  
3. **Property available?** gate  
4. **HTTP Book** → FastAPI/internal book (calendar + email + CRM) with **3 retries**  
5. Respond success/failure  

## Local equivalent

Without running n8n, use the Python orchestrator (same steps + retries):

```powershell
python scripts/demo_booking_flow.py
python scripts/test_retries.py
```

## Payload example

```json
{
  "intent": "buy",
  "client_name": "Ayesha",
  "client_phone": "03001234567",
  "city": "Karachi",
  "when_text": "Saturday 4pm",
  "property": {"property_id": "KR-DHA-8-001", "status": "available", "title": "...", "agent_id": "AGT-02"},
  "preferences": {"budget_text": "3 crore", "area": "DHA"},
  "transcript": [{"role": "user", "text": "..."}]
}
```
