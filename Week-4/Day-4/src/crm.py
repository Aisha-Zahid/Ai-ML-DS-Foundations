"""CRM SQLite: calls, preferences, appointments, follow-ups."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import CRM_DB, DATA


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or CRM_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | None = None) -> Path:
    path = db_path or CRM_DB
    DATA.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS clients (
              client_id TEXT PRIMARY KEY,
              name TEXT,
              phone TEXT,
              city TEXT,
              created_at TEXT,
              updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS call_logs (
              call_id TEXT PRIMARY KEY,
              client_id TEXT,
              started_at TEXT,
              ended_at TEXT,
              transcript_json TEXT,
              intent TEXT,
              notes TEXT
            );

            CREATE TABLE IF NOT EXISTS preferences (
              pref_id TEXT PRIMARY KEY,
              client_id TEXT,
              purpose TEXT,
              city TEXT,
              area TEXT,
              budget_text TEXT,
              budget_pkr REAL,
              bedrooms INTEGER,
              amenities_json TEXT,
              shortlist_json TEXT,
              updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS appointments (
              appointment_id TEXT PRIMARY KEY,
              client_id TEXT,
              client_name TEXT,
              client_phone TEXT,
              employee_id TEXT,
              employee_name TEXT,
              employee_email TEXT,
              property_id TEXT,
              property_title TEXT,
              starts_at TEXT,
              ends_at TEXT,
              status TEXT,
              meeting_notes TEXT,
              calendar_event_id TEXT,
              last_email_id TEXT,
              created_at TEXT,
              updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS follow_ups (
              follow_up_id TEXT PRIMARY KEY,
              client_id TEXT,
              appointment_id TEXT,
              due_at TEXT,
              reason TEXT,
              status TEXT,
              created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS workflow_runs (
              run_id TEXT PRIMARY KEY,
              started_at TEXT,
              finished_at TEXT,
              status TEXT,
              steps_json TEXT,
              error TEXT
            );
            """
        )
        conn.commit()
    finally:
        conn.close()
    return path


def upsert_client(*, name: str | None, phone: str | None, city: str | None = None) -> str:
    conn = connect()
    try:
        row = None
        if phone:
            row = conn.execute(
                "SELECT client_id FROM clients WHERE phone = ?", (phone,)
            ).fetchone()
        if row:
            cid = row["client_id"]
            conn.execute(
                """
                UPDATE clients SET name=COALESCE(?, name), city=COALESCE(?, city), updated_at=?
                WHERE client_id=?
                """,
                (name, city, _now(), cid),
            )
        else:
            cid = f"CLI-{uuid.uuid4().hex[:8].upper()}"
            conn.execute(
                """
                INSERT INTO clients(client_id, name, phone, city, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (cid, name, phone, city, _now(), _now()),
            )
        conn.commit()
        return cid
    finally:
        conn.close()


def log_call(
    *,
    client_id: str,
    transcript: list[dict],
    intent: str | None = None,
    notes: str | None = None,
) -> str:
    call_id = f"CALL-{uuid.uuid4().hex[:8].upper()}"
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO call_logs(call_id, client_id, started_at, ended_at, transcript_json, intent, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                call_id,
                client_id,
                _now(),
                _now(),
                json.dumps(transcript, ensure_ascii=False),
                intent,
                notes,
            ),
        )
        conn.commit()
        return call_id
    finally:
        conn.close()


def save_preferences(client_id: str, prefs: dict[str, Any]) -> str:
    pref_id = f"PREF-{uuid.uuid4().hex[:8].upper()}"
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO preferences(
              pref_id, client_id, purpose, city, area, budget_text, budget_pkr,
              bedrooms, amenities_json, shortlist_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pref_id,
                client_id,
                prefs.get("purpose"),
                prefs.get("city"),
                prefs.get("area"),
                prefs.get("budget_text"),
                prefs.get("budget_pkr"),
                prefs.get("bedrooms"),
                json.dumps(prefs.get("amenities") or [], ensure_ascii=False),
                json.dumps(prefs.get("shortlist") or [], ensure_ascii=False),
                _now(),
            ),
        )
        conn.commit()
        return pref_id
    finally:
        conn.close()


def insert_appointment(row: dict[str, Any]) -> str:
    aid = row.get("appointment_id") or f"APT-{uuid.uuid4().hex[:8].upper()}"
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO appointments(
              appointment_id, client_id, client_name, client_phone, employee_id,
              employee_name, employee_email, property_id, property_title,
              starts_at, ends_at, status, meeting_notes, calendar_event_id,
              last_email_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                aid,
                row.get("client_id"),
                row.get("client_name"),
                row.get("client_phone"),
                row.get("employee_id"),
                row.get("employee_name"),
                row.get("employee_email"),
                row.get("property_id"),
                row.get("property_title"),
                row.get("starts_at"),
                row.get("ends_at"),
                row.get("status", "booked"),
                row.get("meeting_notes"),
                row.get("calendar_event_id"),
                row.get("last_email_id"),
                _now(),
                _now(),
            ),
        )
        conn.commit()
        return aid
    finally:
        conn.close()


def update_appointment(appointment_id: str, **fields: Any) -> None:
    if not fields:
        return
    fields["updated_at"] = _now()
    cols = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [appointment_id]
    conn = connect()
    try:
        conn.execute(f"UPDATE appointments SET {cols} WHERE appointment_id=?", vals)
        conn.commit()
    finally:
        conn.close()


def get_appointment(appointment_id: str) -> dict | None:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM appointments WHERE appointment_id=?", (appointment_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_appointments(status: str | None = None) -> list[dict]:
    conn = connect()
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM appointments WHERE status=? ORDER BY starts_at",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM appointments ORDER BY starts_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_follow_up(
    *,
    client_id: str,
    appointment_id: str | None,
    reason: str,
    days: int = 2,
) -> str:
    fid = f"FU-{uuid.uuid4().hex[:8].upper()}"
    due = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO follow_ups(follow_up_id, client_id, appointment_id, due_at, reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'open', ?)
            """,
            (fid, client_id, appointment_id, due, reason, _now()),
        )
        conn.commit()
        return fid
    finally:
        conn.close()


def log_workflow_run(
    *,
    status: str,
    steps: list[dict],
    error: str | None = None,
    run_id: str | None = None,
) -> str:
    rid = run_id or f"WF-{uuid.uuid4().hex[:8].upper()}"
    conn = connect()
    try:
        existing = conn.execute(
            "SELECT run_id FROM workflow_runs WHERE run_id=?", (rid,)
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE workflow_runs SET finished_at=?, status=?, steps_json=?, error=?
                WHERE run_id=?
                """,
                (_now(), status, json.dumps(steps, ensure_ascii=False), error, rid),
            )
        else:
            conn.execute(
                """
                INSERT INTO workflow_runs(run_id, started_at, finished_at, status, steps_json, error)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    rid,
                    _now(),
                    _now(),
                    status,
                    json.dumps(steps, ensure_ascii=False),
                    error,
                ),
            )
        conn.commit()
        return rid
    finally:
        conn.close()
