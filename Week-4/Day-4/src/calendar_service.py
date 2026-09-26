"""Google Calendar integration (mock file store or live Google API)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import CAL_OUTBOX, CALENDAR_MODE, GOOGLE_CALENDAR_ID, GOOGLE_CREDENTIALS_JSON


def _mock_store() -> Path:
    CAL_OUTBOX.mkdir(parents=True, exist_ok=True)
    return CAL_OUTBOX / "events.json"


def _load_mock() -> dict[str, Any]:
    path = _mock_store()
    if not path.exists():
        return {"events": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_mock(data: dict[str, Any]) -> None:
    _mock_store().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def create_event(
    *,
    summary: str,
    description: str,
    starts_at: str,
    ends_at: str,
    attendee_email: str | None = None,
    metadata: dict | None = None,
) -> dict[str, Any]:
    """
    Create calendar event.
    Fields covered: client/employee/property/notes via description + metadata.
    """
    if CALENDAR_MODE == "live" and GOOGLE_CREDENTIALS_JSON:
        return _google_create(
            summary=summary,
            description=description,
            starts_at=starts_at,
            ends_at=ends_at,
            attendee_email=attendee_email,
        )

    event_id = f"gcal-mock-{uuid.uuid4().hex[:10]}"
    data = _load_mock()
    event = {
        "id": event_id,
        "summary": summary,
        "description": description,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "attendee_email": attendee_email,
        "status": "confirmed",
        "metadata": metadata or {},
        "provider": "mock",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    data["events"][event_id] = event
    _save_mock(data)
    # also drop a readable artifact
    (CAL_OUTBOX / f"{event_id}.json").write_text(
        json.dumps(event, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return event


def update_event(
    event_id: str,
    *,
    starts_at: str | None = None,
    ends_at: str | None = None,
    summary: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    if CALENDAR_MODE == "live" and GOOGLE_CREDENTIALS_JSON:
        return _google_patch(
            event_id,
            starts_at=starts_at,
            ends_at=ends_at,
            summary=summary,
            description=description,
        )
    data = _load_mock()
    ev = data["events"].get(event_id)
    if not ev:
        raise KeyError(f"Unknown calendar event: {event_id}")
    if starts_at:
        ev["starts_at"] = starts_at
    if ends_at:
        ev["ends_at"] = ends_at
    if summary:
        ev["summary"] = summary
    if description:
        ev["description"] = description
    ev["updated_at"] = datetime.utcnow().isoformat() + "Z"
    data["events"][event_id] = ev
    _save_mock(data)
    (CAL_OUTBOX / f"{event_id}.json").write_text(
        json.dumps(ev, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return ev


def cancel_event(event_id: str) -> dict[str, Any]:
    if CALENDAR_MODE == "live" and GOOGLE_CREDENTIALS_JSON:
        return _google_delete(event_id)
    data = _load_mock()
    ev = data["events"].get(event_id)
    if not ev:
        raise KeyError(f"Unknown calendar event: {event_id}")
    ev["status"] = "cancelled"
    ev["cancelled_at"] = datetime.utcnow().isoformat() + "Z"
    data["events"][event_id] = ev
    _save_mock(data)
    (CAL_OUTBOX / f"{event_id}.json").write_text(
        json.dumps(ev, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return ev


def _google_create(**kwargs) -> dict[str, Any]:
    """Optional live path — requires google-api-python-client + credentials file."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "Live calendar needs google-api-python-client and google-auth"
        ) from exc

    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_JSON,
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    body = {
        "summary": kwargs["summary"],
        "description": kwargs["description"],
        "start": {"dateTime": kwargs["starts_at"]},
        "end": {"dateTime": kwargs["ends_at"]},
    }
    if kwargs.get("attendee_email"):
        body["attendees"] = [{"email": kwargs["attendee_email"]}]
    created = (
        service.events()
        .insert(calendarId=GOOGLE_CALENDAR_ID, body=body, sendUpdates="all")
        .execute()
    )
    return {
        "id": created["id"],
        "summary": created.get("summary"),
        "starts_at": kwargs["starts_at"],
        "ends_at": kwargs["ends_at"],
        "status": created.get("status", "confirmed"),
        "provider": "google",
        "htmlLink": created.get("htmlLink"),
    }


def _google_patch(event_id: str, **kwargs) -> dict[str, Any]:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_JSON,
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    body: dict[str, Any] = {}
    if kwargs.get("summary"):
        body["summary"] = kwargs["summary"]
    if kwargs.get("description"):
        body["description"] = kwargs["description"]
    if kwargs.get("starts_at"):
        body["start"] = {"dateTime": kwargs["starts_at"]}
    if kwargs.get("ends_at"):
        body["end"] = {"dateTime": kwargs["ends_at"]}
    updated = (
        service.events()
        .patch(
            calendarId=GOOGLE_CALENDAR_ID,
            eventId=event_id,
            body=body,
            sendUpdates="all",
        )
        .execute()
    )
    return {"id": updated["id"], "status": updated.get("status"), "provider": "google"}


def _google_delete(event_id: str) -> dict[str, Any]:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_JSON,
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    service.events().delete(
        calendarId=GOOGLE_CALENDAR_ID, eventId=event_id, sendUpdates="all"
    ).execute()
    return {"id": event_id, "status": "cancelled", "provider": "google"}
