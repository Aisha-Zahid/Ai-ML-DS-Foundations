"""End-to-end booking / reschedule / cancel demo."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import appointments, crm  # noqa: E402
from src.slots import offer_slots  # noqa: E402
from src.workflow import run_booking_workflow  # noqa: E402


def _sample_property() -> dict:
    # Prefer Day-2 inventory row if CSV readable
    import csv

    path = ROOT.parent / "Day-2" / "data" / "structured" / "properties.csv"
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("status") == "available" and row.get("property_id") == "KR-DHA-8-001":
                    return row
            f.seek(0)
            next(csv.DictReader(f))
            f.seek(0)
            for row in csv.DictReader(f):
                if row.get("status") == "available":
                    return row
    return {
        "property_id": "KR-DHA-8-001",
        "title": "DHA Phase 8 — 200 sq yd house",
        "city": "Karachi",
        "status": "available",
        "agent_id": "AGT-02",
    }


def main() -> None:
    crm.init_db()
    prop = _sample_property()
    print("Offered slots:", offer_slots(3))

    wf = run_booking_workflow(
        transcript=[
            {"role": "user", "text": "Budget 3 crore, DHA Karachi"},
            {"role": "assistant", "text": "DHA Phase 8 option mil gaya"},
            {"role": "user", "text": "Saturday 4pm visit book kar do"},
        ],
        intent="buy",
        client_name="Ayesha",
        client_phone="03001234567",
        city="Karachi",
        preferences={
            "purpose": "buy",
            "city": "Karachi",
            "area": "DHA",
            "budget_text": "3 crore",
            "budget_pkr": 30000000,
            "bedrooms": 3,
        },
        property_row=prop,
        when_text="Saturday 4pm",
        requirements="3 bed DHA, budget ~3 crore",
    )
    print("WORKFLOW:", wf["status"], wf.get("run_id"))
    if wf["status"] != "success":
        print(wf)
        raise SystemExit(1)

    apt_id = wf["booking"]["appointment_id"]
    print("BOOKED", apt_id, wf["booking"]["starts_at"])

    # reschedule
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    new_dt = datetime.now(ZoneInfo("Asia/Karachi")) + timedelta(days=3)
    new_dt = new_dt.replace(hour=17, minute=0, second=0, microsecond=0)
    rs = appointments.reschedule_appointment(apt_id, new_dt, note="Client asked evening slot")
    print("RESCHEDULED", rs["starts_at"])

    # cancel
    # book a second one to cancel cleanly demo — cancel the rescheduled
    cl = appointments.cancel_appointment(apt_id, reason="Client travelling")
    print("CANCELLED", cl["status"])

    out = {
        "workflow": {k: wf[k] for k in ("run_id", "status", "client_id", "call_id") if k in wf},
        "booking_appointment_id": apt_id,
        "steps": wf.get("steps"),
        "appointments": crm.list_appointments(),
    }
    results = ROOT / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "booking_demo.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print("Wrote results/booking_demo.json")


if __name__ == "__main__":
    main()
