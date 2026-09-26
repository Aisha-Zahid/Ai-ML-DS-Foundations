"""Prove workflow retries on simulated calendar outage."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import crm  # noqa: E402
from src.workflow import run_booking_workflow  # noqa: E402


def main() -> None:
    crm.init_db()
    prop = {
        "property_id": "KR-BAH-001",
        "title": "Bahria Town Karachi — Precinct 10 apartment",
        "city": "Karachi",
        "status": "available",
        "agent_id": "AGT-03",
    }
    # Fail twice, succeed on 3rd attempt (MAX_RETRIES=3)
    wf = run_booking_workflow(
        transcript=[{"role": "user", "text": "Book Bahria visit kal 5 baje"}],
        intent="buy",
        client_name="Hina Test",
        client_phone="03007654321",
        city="Karachi",
        preferences={"budget_text": "2.5 crore", "area": "Bahria"},
        property_row=prop,
        when_text="kal 5 baje",
        fail_calendar_times=2,
    )
    print(json.dumps({"status": wf["status"], "steps": wf["steps"]}, indent=2))
    (ROOT / "results").mkdir(parents=True, exist_ok=True)
    (ROOT / "results" / "retry_test.json").write_text(
        json.dumps(wf, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    assert wf["status"] == "success", wf
    attempts = [
        s for s in wf["steps"] if s["step"] == "appointment_calendar_email"
    ]
    assert len(attempts) == 3
    assert attempts[-1]["status"] == "ok"
    print("retry test OK")


if __name__ == "__main__":
    main()
