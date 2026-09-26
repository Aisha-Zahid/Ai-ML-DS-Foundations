"""Employee email notifications (mock outbox or Resend)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import EMAIL_FROM, EMAIL_MODE, EMAIL_OUTBOX, RESEND_API_KEY


def send_employee_email(
    *,
    to_email: str,
    subject: str,
    body: str,
    meta: dict | None = None,
) -> dict[str, Any]:
    if EMAIL_MODE == "live" and RESEND_API_KEY:
        return _resend_send(to_email=to_email, subject=subject, body=body, meta=meta)

    EMAIL_OUTBOX.mkdir(parents=True, exist_ok=True)
    email_id = f"mail-{uuid.uuid4().hex[:10]}"
    payload = {
        "id": email_id,
        "from": EMAIL_FROM,
        "to": to_email,
        "subject": subject,
        "body": body,
        "meta": meta or {},
        "provider": "mock",
        "sent_at": datetime.utcnow().isoformat() + "Z",
    }
    (EMAIL_OUTBOX / f"{email_id}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return payload


def build_booking_email(
    *,
    action: str,
    client_name: str,
    client_phone: str,
    property_title: str,
    property_id: str,
    starts_at: str,
    requirements: str,
    meeting_notes: str,
) -> tuple[str, str]:
    subject = f"[RealEstate Hub] Site visit {action}: {client_name} — {property_id}"
    body = f"""Assalam-o-Alaikum,

A site visit was {action}.

Client: {client_name}
Phone: {client_phone}
Property: {property_title} ({property_id})
Meeting time: {starts_at}
Requirements: {requirements}
Notes: {meeting_notes}

Please confirm and prepare the file.

— RealEstate Hub Booking Bot
"""
    return subject, body


def _resend_send(**kwargs) -> dict[str, Any]:
    import httpx

    r = httpx.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from": EMAIL_FROM,
            "to": [kwargs["to_email"]],
            "subject": kwargs["subject"],
            "text": kwargs["body"],
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return {
        "id": data.get("id", f"resend-{uuid.uuid4().hex[:8]}"),
        "to": kwargs["to_email"],
        "subject": kwargs["subject"],
        "provider": "resend",
        "meta": kwargs.get("meta") or {},
    }
