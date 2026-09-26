"""Week 4 Day 4 paths and toggles."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

DAY4 = Path(__file__).resolve().parents[1]
DAY3 = DAY4.parent / "Day-3"
DAY2 = DAY4.parent / "Day-2"

load_dotenv(DAY4 / ".env")

DATA = DAY4 / "data"
RESULTS = DAY4 / "results"
OUTBOX = DAY4 / "outbox"
EMAIL_OUTBOX = OUTBOX / "email"
CAL_OUTBOX = OUTBOX / "calendar"
N8N = DAY4 / "n8n"
DOCS = DAY4 / "docs"

CRM_DB = DATA / "crm.sqlite"

# mock | live
CALENDAR_MODE = os.getenv("CALENDAR_MODE", "mock")
EMAIL_MODE = os.getenv("EMAIL_MODE", "mock")

GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "bookings@realestatehub.local")
COMPANY_TZ = os.getenv("COMPANY_TZ", "Asia/Karachi")

# Retry policy for workflow steps
MAX_RETRIES = int(os.getenv("WORKFLOW_MAX_RETRIES", "3"))
RETRY_BACKOFF_SEC = float(os.getenv("WORKFLOW_RETRY_BACKOFF_SEC", "0.4"))

# Agent emails (desk routing)
AGENT_EMAILS = {
    "AGT-01": "sara.ahmed@realestatehub.local",
    "AGT-02": "bilal.khan@realestatehub.local",
    "AGT-03": "hina.malik@realestatehub.local",
    "AGT-04": "omar.sheikh@realestatehub.local",
    "AGT-05": "ayesha.raza@realestatehub.local",
    "AGT-06": "usman.ali@realestatehub.local",
    "AGT-07": "fatima.noor@realestatehub.local",
}
