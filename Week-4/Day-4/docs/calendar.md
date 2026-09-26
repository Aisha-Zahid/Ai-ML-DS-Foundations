# Calendar integration (Task 1)

Creates events with:

- Client name & phone  
- Employee (assigned agent)  
- Property id/title  
- Date/time  
- Meeting notes  

**Mock mode** (default): JSON under `outbox/calendar/`.  
**Live mode**: set `CALENDAR_MODE=live` + `GOOGLE_CREDENTIALS_JSON` (service account) + share calendar with that account.
