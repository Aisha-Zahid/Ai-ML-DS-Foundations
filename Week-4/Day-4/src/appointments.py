"""Appointment book / reschedule / cancel — calendar + email + CRM."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from . import calendar_service, crm, email_service
from .config import AGENT_EMAILS
from .slots import is_slot_free, parse_slot


def _agent_directory() -> dict[str, dict]:
    """Load Day-2 agents if present; else fall back to config emails only."""
    import csv
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "Day-2" / "data" / "structured" / "agents.csv"
    agents = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                agents[row["agent_id"]] = {
                    "name": row["name"],
                    "phone": row["phone"],
                    "desk": row["desk"],
                    "email": AGENT_EMAILS.get(row["agent_id"], f"{row['agent_id'].lower()}@realestatehub.local"),
                }
    for aid, email in AGENT_EMAILS.items():
        agents.setdefault(aid, {"name": aid, "phone": "", "desk": "", "email": email})
    return agents


def resolve_employee(property_row: dict | None, city: str | None = None) -> dict:
    agents = _agent_directory()
    if property_row and property_row.get("agent_id") in agents:
        aid = property_row["agent_id"]
        return {"employee_id": aid, **agents[aid]}
    # city fallback
    city_map = {
        "Karachi": "AGT-01",
        "Lahore": "AGT-05",
        "Islamabad": "AGT-07",
    }
    aid = city_map.get(city or "", "AGT-01")
    return {"employee_id": aid, **agents[aid]}


def book_appointment(
    *,
    client_name: str,
    client_phone: str,
    starts_at: str | datetime,
    property_id: str | None = None,
    property_title: str | None = None,
    property_row: dict | None = None,
    city: str | None = None,
    requirements: str = "",
    meeting_notes: str = "",
    duration_minutes: int = 60,
) -> dict[str, Any]:
    if isinstance(starts_at, datetime):
        start_dt = starts_at
        starts = starts_at.isoformat()
    else:
        starts = starts_at
        start_dt = datetime.fromisoformat(starts_at.replace("Z", "+00:00"))

    ends = (start_dt + timedelta(minutes=duration_minutes)).isoformat()
    employee = resolve_employee(property_row, city=city)
    if not is_slot_free(starts, employee_id=employee["employee_id"]):
        raise ValueError(f"Slot not available: {starts}")

    client_id = crm.upsert_client(name=client_name, phone=client_phone, city=city)
    title = property_title or (property_row or {}).get("title") or "General consultation"
    pid = property_id or (property_row or {}).get("property_id")

    summary = f"Site visit — {client_name} / {pid or 'consult'}"
    description = (
        f"Client: {client_name}\nPhone: {client_phone}\n"
        f"Employee: {employee['name']} ({employee['employee_id']})\n"
        f"Property: {title} ({pid})\n"
        f"Requirements: {requirements}\nNotes: {meeting_notes}"
    )
    event = calendar_service.create_event(
        summary=summary,
        description=description,
        starts_at=starts,
        ends_at=ends,
        attendee_email=employee["email"],
        metadata={
            "client_name": client_name,
            "client_phone": client_phone,
            "employee": employee["name"],
            "property_id": pid,
            "property_title": title,
            "meeting_notes": meeting_notes,
        },
    )

    subject, body = email_service.build_booking_email(
        action="BOOKED",
        client_name=client_name,
        client_phone=client_phone,
        property_title=title,
        property_id=pid or "n/a",
        starts_at=starts,
        requirements=requirements,
        meeting_notes=meeting_notes,
    )
    mail = email_service.send_employee_email(
        to_email=employee["email"],
        subject=subject,
        body=body,
        meta={"action": "book", "calendar_event_id": event["id"]},
    )

    apt_id = crm.insert_appointment(
        {
            "client_id": client_id,
            "client_name": client_name,
            "client_phone": client_phone,
            "employee_id": employee["employee_id"],
            "employee_name": employee["name"],
            "employee_email": employee["email"],
            "property_id": pid,
            "property_title": title,
            "starts_at": starts,
            "ends_at": ends,
            "status": "booked",
            "meeting_notes": meeting_notes,
            "calendar_event_id": event["id"],
            "last_email_id": mail["id"],
        }
    )
    crm.add_follow_up(
        client_id=client_id,
        appointment_id=apt_id,
        reason="Post-visit follow-up reminder",
        days=2,
    )
    return {
        "appointment_id": apt_id,
        "client_id": client_id,
        "calendar_event": event,
        "email": mail,
        "employee": employee,
        "starts_at": starts,
        "status": "booked",
    }


def reschedule_appointment(
    appointment_id: str,
    new_starts_at: str | datetime,
    *,
    duration_minutes: int = 60,
    note: str = "",
) -> dict[str, Any]:
    apt = crm.get_appointment(appointment_id)
    if not apt:
        raise KeyError(f"Unknown appointment {appointment_id}")
    if apt["status"] == "cancelled":
        raise ValueError("Cannot reschedule a cancelled appointment")

    if isinstance(new_starts_at, datetime):
        starts = new_starts_at.isoformat()
        start_dt = new_starts_at
    else:
        starts = new_starts_at
        start_dt = datetime.fromisoformat(new_starts_at.replace("Z", "+00:00"))
    ends = (start_dt + timedelta(minutes=duration_minutes)).isoformat()

    if not is_slot_free(starts, employee_id=apt["employee_id"]):
        # allow same appointment's old slot collision ignore by temporary cancel check
        # simple: if only conflict is itself, ok — list_appointments includes self
        conflicts = [
            a
            for a in crm.list_appointments(status="booked")
            if (a.get("starts_at") or "")[:16] == starts[:16]
            and a["appointment_id"] != appointment_id
            and a.get("employee_id") == apt["employee_id"]
        ]
        if conflicts:
            raise ValueError(f"Slot not available: {starts}")

    event = calendar_service.update_event(
        apt["calendar_event_id"],
        starts_at=starts,
        ends_at=ends,
        description=(apt.get("meeting_notes") or "") + (f"\nReschedule note: {note}" if note else ""),
    )
    subject, body = email_service.build_booking_email(
        action="RESCHEDULED",
        client_name=apt["client_name"],
        client_phone=apt["client_phone"],
        property_title=apt.get("property_title") or "",
        property_id=apt.get("property_id") or "n/a",
        starts_at=starts,
        requirements="",
        meeting_notes=note or apt.get("meeting_notes") or "",
    )
    mail = email_service.send_employee_email(
        to_email=apt["employee_email"],
        subject=subject,
        body=body,
        meta={"action": "reschedule", "appointment_id": appointment_id},
    )
    crm.update_appointment(
        appointment_id,
        starts_at=starts,
        ends_at=ends,
        status="booked",
        last_email_id=mail["id"],
        meeting_notes=(apt.get("meeting_notes") or "") + (f" | reschedule: {note}" if note else ""),
    )
    return {
        "appointment_id": appointment_id,
        "calendar_event": event,
        "email": mail,
        "starts_at": starts,
        "status": "booked",
    }


def cancel_appointment(appointment_id: str, *, reason: str = "") -> dict[str, Any]:
    apt = crm.get_appointment(appointment_id)
    if not apt:
        raise KeyError(f"Unknown appointment {appointment_id}")
    event = calendar_service.cancel_event(apt["calendar_event_id"])
    subject, body = email_service.build_booking_email(
        action="CANCELLED",
        client_name=apt["client_name"],
        client_phone=apt["client_phone"],
        property_title=apt.get("property_title") or "",
        property_id=apt.get("property_id") or "n/a",
        starts_at=apt.get("starts_at") or "",
        requirements="",
        meeting_notes=reason or apt.get("meeting_notes") or "",
    )
    mail = email_service.send_employee_email(
        to_email=apt["employee_email"],
        subject=subject,
        body=body,
        meta={"action": "cancel", "appointment_id": appointment_id},
    )
    crm.update_appointment(
        appointment_id,
        status="cancelled",
        last_email_id=mail["id"],
        meeting_notes=(apt.get("meeting_notes") or "") + (f" | cancel: {reason}" if reason else ""),
    )
    return {
        "appointment_id": appointment_id,
        "calendar_event": event,
        "email": mail,
        "status": "cancelled",
    }


def book_from_phrase(
    *,
    client_name: str,
    client_phone: str,
    when_text: str,
    property_row: dict | None = None,
    requirements: str = "",
) -> dict[str, Any]:
    dt = parse_slot(when_text)
    if not dt:
        raise ValueError("Could not parse visit time")
    return book_appointment(
        client_name=client_name,
        client_phone=client_phone,
        starts_at=dt,
        property_row=property_row,
        property_id=(property_row or {}).get("property_id"),
        property_title=(property_row or {}).get("title"),
        city=(property_row or {}).get("city"),
        requirements=requirements,
        meeting_notes=f"Requested slot phrase: {when_text}",
    )
