"""CLI for appointment management."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import appointments, crm  # noqa: E402
from src.slots import offer_slots, parse_slot  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("book")
    b.add_argument("--name", required=True)
    b.add_argument("--phone", required=True)
    b.add_argument("--when", required=True, help="e.g. 'Saturday 4pm'")
    b.add_argument("--property-id", default="KR-DHA-8-001")
    b.add_argument("--requirements", default="")

    r = sub.add_parser("reschedule")
    r.add_argument("--id", required=True)
    r.add_argument("--when", required=True)

    c = sub.add_parser("cancel")
    c.add_argument("--id", required=True)
    c.add_argument("--reason", default="")

    sub.add_parser("list")
    sub.add_parser("slots")

    args = p.parse_args()
    crm.init_db()

    if args.cmd == "slots":
        print(json.dumps(offer_slots(), indent=2))
        return
    if args.cmd == "list":
        print(json.dumps(crm.list_appointments(), indent=2, default=str))
        return
    if args.cmd == "book":
        import csv

        prop = {"property_id": args.property_id, "title": args.property_id, "city": "Karachi", "status": "available", "agent_id": "AGT-01"}
        path = ROOT.parent / "Day-2" / "data" / "structured" / "properties.csv"
        if path.exists():
            with path.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row["property_id"] == args.property_id:
                        prop = row
                        break
        out = appointments.book_from_phrase(
            client_name=args.name,
            client_phone=args.phone,
            when_text=args.when,
            property_row=prop,
            requirements=args.requirements,
        )
        print(json.dumps(out, indent=2, default=str))
        return
    if args.cmd == "reschedule":
        dt = parse_slot(args.when)
        out = appointments.reschedule_appointment(args.id, dt)
        print(json.dumps(out, indent=2, default=str))
        return
    if args.cmd == "cancel":
        out = appointments.cancel_appointment(args.id, reason=args.reason)
        print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
