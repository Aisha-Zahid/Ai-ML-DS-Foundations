"""Business workflow with retries: Call → Intent → Match → Appointment → Calendar → Email → CRM."""

from __future__ import annotations

import time
import traceback
import uuid
from typing import Any, Callable

from . import appointments, crm
from .config import MAX_RETRIES, RETRY_BACKOFF_SEC


class StepError(RuntimeError):
    pass


def _retry(name: str, fn: Callable[[], Any], steps: list[dict]) -> Any:
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = fn()
            steps.append(
                {
                    "step": name,
                    "attempt": attempt,
                    "status": "ok",
                    "result_preview": str(result)[:240],
                }
            )
            return result
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            steps.append(
                {
                    "step": name,
                    "attempt": attempt,
                    "status": "retry" if attempt < MAX_RETRIES else "failed",
                    "error": str(exc),
                }
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SEC * attempt)
    raise StepError(f"{name} failed after {MAX_RETRIES} attempts: {last_exc}")


def run_booking_workflow(
    *,
    transcript: list[dict],
    intent: str,
    client_name: str,
    client_phone: str,
    city: str | None,
    preferences: dict,
    property_row: dict | None,
    when_text: str,
    requirements: str = "",
    fail_calendar_times: int = 0,
) -> dict[str, Any]:
    """
    Mirrors the n8n graph in Python for local demos/tests.
    `fail_calendar_times` forces N artificial calendar failures to exercise retries.
    """
    run_id = f"WF-{uuid.uuid4().hex[:8].upper()}"
    steps: list[dict] = []
    crm.init_db()
    crm.log_workflow_run(run_id=run_id, status="running", steps=steps)

    try:
        # 1) Call logged
        client_id = _retry(
            "upsert_client",
            lambda: crm.upsert_client(name=client_name, phone=client_phone, city=city),
            steps,
        )
        call_id = _retry(
            "log_call",
            lambda: crm.log_call(
                client_id=client_id, transcript=transcript, intent=intent
            ),
            steps,
        )

        # 2) Intent already provided by voice agent — record
        steps.append({"step": "intent", "attempt": 1, "status": "ok", "result_preview": intent})

        # 3) Property match (passed in / validated)
        if not property_row or property_row.get("status") == "sold":
            raise StepError("No available property match")
        steps.append(
            {
                "step": "property_match",
                "attempt": 1,
                "status": "ok",
                "result_preview": property_row.get("property_id"),
            }
        )

        # 4–6) Appointment creates calendar + email internally; inject retry by wrapping
        state = {"fails_left": fail_calendar_times}

        def _book():
            if state["fails_left"] > 0:
                state["fails_left"] -= 1
                raise RuntimeError("Simulated calendar outage")
            return appointments.book_from_phrase(
                client_name=client_name,
                client_phone=client_phone,
                when_text=when_text,
                property_row=property_row,
                requirements=requirements
                or preferences.get("budget_text")
                or preferences.get("area")
                or "",
            )

        booking = _retry("appointment_calendar_email", _book, steps)

        # 7) CRM preferences + follow-up already partly done in book; save prefs explicitly
        pref_id = _retry(
            "crm_preferences",
            lambda: crm.save_preferences(
                client_id,
                {
                    **preferences,
                    "shortlist": [property_row.get("property_id")],
                },
            ),
            steps,
        )

        result = {
            "run_id": run_id,
            "status": "success",
            "client_id": client_id,
            "call_id": call_id,
            "pref_id": pref_id,
            "booking": booking,
            "steps": steps,
        }
        crm.log_workflow_run(run_id=run_id, status="success", steps=steps)
        return result
    except Exception as exc:  # noqa: BLE001
        crm.log_workflow_run(
            run_id=run_id,
            status="failed",
            steps=steps,
            error=f"{exc}\n{traceback.format_exc()[-500:]}",
        )
        return {"run_id": run_id, "status": "failed", "error": str(exc), "steps": steps}
