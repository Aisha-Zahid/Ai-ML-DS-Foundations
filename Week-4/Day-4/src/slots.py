"""Availability slots for site visits."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .config import COMPANY_TZ
from .crm import list_appointments


def _tz() -> ZoneInfo:
    try:
        return ZoneInfo(COMPANY_TZ)
    except Exception:
        return ZoneInfo("UTC")


def parse_slot(text: str, *, default_days_ahead: int = 1) -> datetime | None:
    """
    Parse simple UrduLish/English slot phrases into a timezone-aware datetime.
    Examples: 'Saturday 4pm', '2026-10-04 16:00', 'kal shaam 5 baje'
    """
    import re

    t = text.strip().lower()
    tz = _tz()
    now = datetime.now(tz)

    # ISO-ish
    m = re.search(r"(20\d{2}-\d{2}-\d{2})[ T](\d{1,2}):(\d{2})", t)
    if m:
        dt = datetime.fromisoformat(f"{m.group(1)}T{int(m.group(2)):02d}:{m.group(3)}:00")
        return dt.replace(tzinfo=tz)

    # hour
    hm = re.search(r"(\d{1,2})\s*(:(\d{2}))?\s*(am|pm|baje)?", t)
    hour = 16
    minute = 0
    if hm:
        hour = int(hm.group(1))
        if hm.group(3):
            minute = int(hm.group(3))
        ampm = (hm.group(4) or "").lower()
        if ampm == "pm" and hour < 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        if ampm == "baje" and hour < 8:
            hour += 12

    weekday_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
        "somwar": 0,
        "mangal": 1,
        "budh": 2,
        "jumeraat": 3,
        "juma": 4,
        "hafta": 5,
        "itwar": 6,
    }
    target = None
    for name, wd in weekday_map.items():
        if name in t:
            days = (wd - now.weekday()) % 7
            if days == 0 and (hour, minute) <= (now.hour, now.minute):
                days = 7
            target = now + timedelta(days=days)
            break
    if "kal" in t:
        target = now + timedelta(days=1)
    if target is None:
        target = now + timedelta(days=default_days_ahead)

    return target.replace(hour=hour, minute=minute, second=0, microsecond=0)


def offer_slots(n: int = 3, start_hour: int = 15) -> list[dict[str, Any]]:
    """Next n free-ish afternoon slots (skip already booked)."""
    tz = _tz()
    now = datetime.now(tz)
    booked = {
        a["starts_at"][:16]
        for a in list_appointments(status="booked")
        if a.get("starts_at")
    }
    out = []
    day = 1
    while len(out) < n and day < 14:
        dt = (now + timedelta(days=day)).replace(
            hour=start_hour + (len(out) % 3), minute=0, second=0, microsecond=0
        )
        if dt.weekday() == 6:  # skip Sunday lightly
            day += 1
            continue
        key = dt.isoformat()[:16]
        if key not in booked:
            out.append(
                {
                    "starts_at": dt.isoformat(),
                    "ends_at": (dt + timedelta(hours=1)).isoformat(),
                    "label": dt.strftime("%A %d %b %I:%M %p"),
                }
            )
        day += 1
    return out


def is_slot_free(starts_at: str, employee_id: str | None = None) -> bool:
    key = starts_at[:16]
    for a in list_appointments(status="booked"):
        if (a.get("starts_at") or "")[:16] == key:
            if employee_id and a.get("employee_id") != employee_id:
                continue
            return False
    return True
