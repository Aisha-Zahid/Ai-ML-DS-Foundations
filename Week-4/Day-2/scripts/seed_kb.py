"""Seed RealEstate Hub structured + semantic knowledge base."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from config import PROCESSED, SEMANTIC, STRUCTURED  # noqa: E402

# Properties, developers, agents, plans — same data as designed for RealEstate Hub
PROPERTIES = [
    {"property_id": "KR-DHA-6-001", "title": "DHA Phase 6 — 500 sq yd house", "city": "Karachi", "area": "DHA Phase 6", "purpose": "buy", "property_type": "house", "bedrooms": 5, "bathrooms": 6, "size_value": 500, "size_unit": "sq_yd", "price_pkr": 85000000, "price_display": "8.5 crore", "status": "available", "developer_id": "DEV-DHA", "agent_id": "AGT-01", "amenities": "generator;security;lawn;servant_quarter", "schools_nearby": "Beaconhouse DHA;The City School DHA", "hospitals_nearby": "South City Hospital;Aga Khan (drive)", "payment_plan_id": "PP-CASH", "investment_tag": "residential_prime"},
    {"property_id": "KR-DHA-6-002", "title": "DHA Phase 6 — 300 sq yd house", "city": "Karachi", "area": "DHA Phase 6", "purpose": "buy", "property_type": "house", "bedrooms": 4, "bathrooms": 4, "size_value": 300, "size_unit": "sq_yd", "price_pkr": 55000000, "price_display": "5.5 crore", "status": "available", "developer_id": "DEV-DHA", "agent_id": "AGT-01", "amenities": "generator;security;car_porch", "schools_nearby": "Beaconhouse DHA", "hospitals_nearby": "South City Hospital", "payment_plan_id": "PP-CASH", "investment_tag": "residential_prime"},
    {"property_id": "KR-DHA-8-001", "title": "DHA Phase 8 — 200 sq yd house", "city": "Karachi", "area": "DHA Phase 8", "purpose": "buy", "property_type": "house", "bedrooms": 3, "bathrooms": 3, "size_value": 200, "size_unit": "sq_yd", "price_pkr": 32000000, "price_display": "3.2 crore", "status": "available", "developer_id": "DEV-DHA", "agent_id": "AGT-02", "amenities": "generator;security", "schools_nearby": "Foundation Public School", "hospitals_nearby": "Medicare Hospital", "payment_plan_id": "PP-CASH", "investment_tag": "residential_value"},
    {"property_id": "KR-BAH-001", "title": "Bahria Town Karachi — Precinct 10 apartment", "city": "Karachi", "area": "Bahria Town", "purpose": "buy", "property_type": "apartment", "bedrooms": 3, "bathrooms": 3, "size_value": 1600, "size_unit": "sq_ft", "price_pkr": 22000000, "price_display": "2.2 crore", "status": "available", "developer_id": "DEV-BAHRIA", "agent_id": "AGT-03", "amenities": "gym;pool;security;parking", "schools_nearby": "Bahria College", "hospitals_nearby": "Bahria Medical Complex", "payment_plan_id": "PP-BAHRIA-36", "investment_tag": "apartment_growth"},
    {"property_id": "KR-BAH-002", "title": "Bahria Town Karachi — Precinct 2 plot 125 sq yd", "city": "Karachi", "area": "Bahria Town", "purpose": "buy", "property_type": "plot", "bedrooms": 0, "bathrooms": 0, "size_value": 125, "size_unit": "sq_yd", "price_pkr": 12500000, "price_display": "1.25 crore", "status": "available", "developer_id": "DEV-BAHRIA", "agent_id": "AGT-03", "amenities": "society_security;parks", "schools_nearby": "Bahria College", "hospitals_nearby": "Bahria Medical Complex", "payment_plan_id": "PP-BAHRIA-36", "investment_tag": "plot_long_term"},
    {"property_id": "KR-CLT-001", "title": "Clifton Block 5 — sea-view apartment", "city": "Karachi", "area": "Clifton", "purpose": "buy", "property_type": "apartment", "bedrooms": 3, "bathrooms": 3, "size_value": 2200, "size_unit": "sq_ft", "price_pkr": 48000000, "price_display": "4.8 crore", "status": "available", "developer_id": "DEV-PRIVATE", "agent_id": "AGT-02", "amenities": "generator;security;sea_view;parking", "schools_nearby": "Karachi Grammar School", "hospitals_nearby": "South City Hospital;Aga Khan", "payment_plan_id": "PP-CASH", "investment_tag": "lifestyle_premium"},
    {"property_id": "KR-RENT-001", "title": "DHA Phase 5 — 3 bed rental house", "city": "Karachi", "area": "DHA Phase 5", "purpose": "rent", "property_type": "house", "bedrooms": 3, "bathrooms": 3, "size_value": 240, "size_unit": "sq_yd", "price_pkr": 250000, "price_display": "2.5 lakh / month", "status": "available", "developer_id": "DEV-DHA", "agent_id": "AGT-01", "amenities": "generator;furnished_partial;security", "schools_nearby": "Beaconhouse DHA", "hospitals_nearby": "South City Hospital", "payment_plan_id": "PP-RENT-STD", "investment_tag": "n/a"},
    {"property_id": "KR-RENT-002", "title": "Gulshan-e-Iqbal — 2 bed rental apartment", "city": "Karachi", "area": "Gulshan-e-Iqbal", "purpose": "rent", "property_type": "apartment", "bedrooms": 2, "bathrooms": 2, "size_value": 1100, "size_unit": "sq_ft", "price_pkr": 95000, "price_display": "95,000 / month", "status": "available", "developer_id": "DEV-PRIVATE", "agent_id": "AGT-04", "amenities": "parking;security", "schools_nearby": "The Educators Gulshan", "hospitals_nearby": "Liaquat National Hospital", "payment_plan_id": "PP-RENT-STD", "investment_tag": "n/a"},
    {"property_id": "LH-DHA-R-001", "title": "DHA Lahore Phase 5 — 1 kanal house", "city": "Lahore", "area": "DHA Phase 5", "purpose": "buy", "property_type": "house", "bedrooms": 5, "bathrooms": 6, "size_value": 1, "size_unit": "kanal", "price_pkr": 95000000, "price_display": "9.5 crore", "status": "available", "developer_id": "DEV-DHA", "agent_id": "AGT-05", "amenities": "lawn;generator;security;servant_quarter", "schools_nearby": "LGS DHA;Beaconhouse DHA", "hospitals_nearby": "National Hospital DHA", "payment_plan_id": "PP-CASH", "investment_tag": "residential_prime"},
    {"property_id": "LH-BAH-001", "title": "Bahria Town Lahore — Sector C apartment", "city": "Lahore", "area": "Bahria Town", "purpose": "buy", "property_type": "apartment", "bedrooms": 2, "bathrooms": 2, "size_value": 1200, "size_unit": "sq_ft", "price_pkr": 18000000, "price_display": "1.8 crore", "status": "available", "developer_id": "DEV-BAHRIA", "agent_id": "AGT-05", "amenities": "gym;security;parking", "schools_nearby": "Bahria College Lahore", "hospitals_nearby": "Bahria International Hospital", "payment_plan_id": "PP-BAHRIA-36", "investment_tag": "apartment_growth"},
    {"property_id": "LH-JOH-001", "title": "Johar Town — commercial shop 2 marla", "city": "Lahore", "area": "Johar Town", "purpose": "commercial", "property_type": "shop", "bedrooms": 0, "bathrooms": 1, "size_value": 2, "size_unit": "marla", "price_pkr": 35000000, "price_display": "3.5 crore", "status": "available", "developer_id": "DEV-PRIVATE", "agent_id": "AGT-06", "amenities": "main_boulevard;parking_street", "schools_nearby": "n/a", "hospitals_nearby": "Hameed Latif Hospital", "payment_plan_id": "PP-CASH", "investment_tag": "commercial_yield"},
    {"property_id": "ISB-G11-001", "title": "G-11 Markaz — office space 1500 sq ft", "city": "Islamabad", "area": "G-11", "purpose": "commercial", "property_type": "office", "bedrooms": 0, "bathrooms": 2, "size_value": 1500, "size_unit": "sq_ft", "price_pkr": 28000000, "price_display": "2.8 crore", "status": "available", "developer_id": "DEV-PRIVATE", "agent_id": "AGT-07", "amenities": "lift;parking;backup_power", "schools_nearby": "n/a", "hospitals_nearby": "PIMS;Islamabad Specialist Clinic", "payment_plan_id": "PP-CASH", "investment_tag": "commercial_yield"},
    {"property_id": "ISB-BAH-001", "title": "Bahria Enclave — 5 marla house", "city": "Islamabad", "area": "Bahria Enclave", "purpose": "buy", "property_type": "house", "bedrooms": 3, "bathrooms": 4, "size_value": 5, "size_unit": "marla", "price_pkr": 26000000, "price_display": "2.6 crore", "status": "available", "developer_id": "DEV-BAHRIA", "agent_id": "AGT-07", "amenities": "security;park;generator", "schools_nearby": "Roots Millennium", "hospitals_nearby": "Advanced International Hospital", "payment_plan_id": "PP-BAHRIA-36", "investment_tag": "residential_value"},
    {"property_id": "ISB-F7-RENT", "title": "F-7 — 3 bed apartment rental", "city": "Islamabad", "area": "F-7", "purpose": "rent", "property_type": "apartment", "bedrooms": 3, "bathrooms": 3, "size_value": 1800, "size_unit": "sq_ft", "price_pkr": 220000, "price_display": "2.2 lakh / month", "status": "available", "developer_id": "DEV-PRIVATE", "agent_id": "AGT-07", "amenities": "furnished;generator;parking", "schools_nearby": "Roots IVY F-7", "hospitals_nearby": "Shifa International", "payment_plan_id": "PP-RENT-STD", "investment_tag": "n/a"},
    {"property_id": "KR-SOLD-001", "title": "DHA Phase 2 — sold example (unavailable)", "city": "Karachi", "area": "DHA Phase 2", "purpose": "buy", "property_type": "house", "bedrooms": 4, "bathrooms": 4, "size_value": 400, "size_unit": "sq_yd", "price_pkr": 70000000, "price_display": "7 crore", "status": "sold", "developer_id": "DEV-DHA", "agent_id": "AGT-01", "amenities": "generator;security", "schools_nearby": "Beaconhouse", "hospitals_nearby": "Aga Khan", "payment_plan_id": "PP-CASH", "investment_tag": "residential_prime"},
    {"property_id": "KR-COMM-001", "title": "Shahrah-e-Faisal — showroom 4000 sq ft", "city": "Karachi", "area": "Shahrah-e-Faisal", "purpose": "commercial", "property_type": "showroom", "bedrooms": 0, "bathrooms": 2, "size_value": 4000, "size_unit": "sq_ft", "price_pkr": 120000000, "price_display": "12 crore", "status": "available", "developer_id": "DEV-PRIVATE", "agent_id": "AGT-04", "amenities": "frontage;parking;high_visibility", "schools_nearby": "n/a", "hospitals_nearby": "Liaquat National Hospital", "payment_plan_id": "PP-CASH", "investment_tag": "commercial_yield"},
]

DEVELOPERS = [
    {"developer_id": "DEV-DHA", "name": "Defence Housing Authority", "trust_notes": "Established cantonment / DHA societies; transfers via DHA procedures.", "cities": "Karachi;Lahore;Islamabad"},
    {"developer_id": "DEV-BAHRIA", "name": "Bahria Town", "trust_notes": "Large master-planned communities; verify precinct development status before booking.", "cities": "Karachi;Lahore;Islamabad"},
    {"developer_id": "DEV-PRIVATE", "name": "Private / Independent owners", "trust_notes": "Title and NOC checks required; RealEstate Hub verifies docs before visit.", "cities": "Karachi;Lahore;Islamabad"},
]

AGENTS = [
    {"agent_id": "AGT-01", "name": "Sara Ahmed", "phone": "+92-300-1110001", "desk": "Karachi DHA"},
    {"agent_id": "AGT-02", "name": "Bilal Khan", "phone": "+92-300-1110002", "desk": "Karachi Clifton/DHA"},
    {"agent_id": "AGT-03", "name": "Hina Malik", "phone": "+92-300-1110003", "desk": "Karachi Bahria"},
    {"agent_id": "AGT-04", "name": "Omar Sheikh", "phone": "+92-300-1110004", "desk": "Karachi Commercial"},
    {"agent_id": "AGT-05", "name": "Ayesha Raza", "phone": "+92-300-1110005", "desk": "Lahore"},
    {"agent_id": "AGT-06", "name": "Usman Ali", "phone": "+92-300-1110006", "desk": "Lahore Commercial"},
    {"agent_id": "AGT-07", "name": "Fatima Noor", "phone": "+92-300-1110007", "desk": "Islamabad"},
]

PAYMENT_PLANS = [
    {"payment_plan_id": "PP-CASH", "name": "Cash / bank transfer", "summary": "Full payment on token + remaining on transfer. No installment markup."},
    {"payment_plan_id": "PP-BAHRIA-36", "name": "Bahria 36-month plan", "summary": "Typical 10-20% booking, remaining over up to 36 months as per precinct schedule. Exact schedule in brochure."},
    {"payment_plan_id": "PP-RENT-STD", "name": "Standard rental", "summary": "Usually 1-2 months advance + 1 month security. Utilities separate unless stated furnished package."},
]


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def write_semantic() -> None:
    (SEMANTIC / "brochures").mkdir(parents=True, exist_ok=True)
    (SEMANTIC / "faqs.md").write_text(
        """# RealEstate Hub — FAQs

## Token money
Token amount depends on property. For DHA houses it is often negotiated (commonly a few lakhs to a percentage). Always confirm with the assigned agent before paying.

## Transfer fees
DHA and society transfer fees are separate from the sale price. Buyer and seller share may vary by society rules. Ask the agent for the current fee schedule.

## Site visit
Visits are by appointment. Bring CNIC. For under-construction Bahria units, site office may be required.

## Overseas clients
We can arrange video tours and power-of-attorney guidance. We do not give legal advice; use a registered lawyer for POA.

## ROI / investment returns
RealEstate Hub does not guarantee investment returns. We only share published location facts, payment plans, and historical context from our files.

## Maintenance
Apartment and Bahria society maintenance charges are billed by the society. Confirm monthly charges before booking.

## Documents checklist (buy)
CNIC copies, recent utility bill, sale agreement, society/DHA NOC where applicable, payment receipts.

## Documents checklist (rent)
CNIC, employment or business proof if requested, advance + security as per PP-RENT-STD.
""",
        encoding="utf-8",
    )
    (SEMANTIC / "payment_plans.md").write_text(
        """# Payment plans (detailed)

## PP-CASH — Cash / bank transfer
Best for ready houses in DHA and private buildings. Timeline: token → agreement → remaining payment → transfer.
No installment interest from RealEstate Hub. Bank mortgage is client's own arrangement.

## PP-BAHRIA-36 — Bahria 36-month style plan
Used for selected Bahria Town apartments and plots.
- Booking: typically 10% to 20% (confirm precinct file)
- Installments: monthly / quarterly as per developer schedule up to about 36 months
- Possession: linked to construction / plot allocation status — verify before promising dates
Never invent a custom schedule; quote only what is in the precinct brochure.

## PP-RENT-STD — Rental standard
- Advance rent: 1–2 months common in Karachi/Lahore/Islamabad
- Security deposit: usually 1 month
- Brokerage: as agreed with client (disclose clearly)
""",
        encoding="utf-8",
    )
    (SEMANTIC / "locations.md").write_text(
        """# Locations & nearby facilities

## Karachi — DHA Phase 6
Prime residential. Near commercial lanes, parks, and good schools (Beaconhouse DHA, City School DHA). Hospitals: South City; Aga Khan is a drive away. Security is managed under DHA.

## Karachi — DHA Phase 8
Growing residential inventory; often better value per sq yd than Phase 6. Check flood-prone pockets and access roads before recommending.

## Karachi — Bahria Town
Master-planned: parks, mosques, Bahria College, medical complex. Confirm which precinct is developed. Ideal for installment buyers and first-time investors.

## Karachi — Clifton
Lifestyle and sea-view demand. Higher prices. Schools like KGS nearby; hospitals South City / AKUH accessible.

## Lahore — DHA Phase 5
Family residential with lawn culture. Schools LGS/Beaconhouse DHA; National Hospital DHA nearby.

## Lahore — Johar Town commercial
Boulevard shops suit retail. High visibility; parking can be street-side — mention to commercial clients.

## Islamabad — G-11
Office demand near markaz. Good for SMEs. PIMS and clinics within city drive.

## Islamabad — Bahria Enclave
Suburban residential with society amenities. Confirm commute time to Blue Area / airport for the client.
""",
        encoding="utf-8",
    )
    brochures = {
        "dha_phase6_house.md": """# Brochure — DHA Phase 6 houses (Karachi)

Defence Housing Authority Phase 6 offers established residential living with parks, mosques, and controlled access.
Typical inventory: 200–500 sq yd houses. Construction quality varies by owner; visits are mandatory.
Amenities often include generator backup, car porch, and servant quarters on larger units.
Schools: Beaconhouse DHA campus access. Hospitals: South City Hospital nearby.
Sales note: price is market-driven; confirm latest asking before quoting on a call.
""",
        "bahria_karachi_apt.md": """# Brochure — Bahria Town Karachi apartments

Bahria apartments suit buyers who prefer gated living with gym, parks, and installment plans.
Precinct 10 sample: ~1600 sq ft, 3 bed. Payment may follow PP-BAHRIA-36 style schedule.
Nearby: Bahria College and Bahria Medical Complex.
Caution: always verify construction status and allotment letter before token.
""",
        "commercial_faisal.md": """# Brochure — Shahrah-e-Faisal showroom

High-visibility commercial frontage on Shahrah-e-Faisal. Suitable for auto, electronics, or brand outlets.
Size example: 4000 sq ft showroom. Parking and frontage are key selling points.
Assigned desk: Karachi Commercial (Omar Sheikh).
""",
    }
    for name, text in brochures.items():
        (SEMANTIC / "brochures" / name).write_text(text, encoding="utf-8")


def main() -> None:
    STRUCTURED.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    _write_csv(STRUCTURED / "properties.csv", PROPERTIES)
    _write_csv(STRUCTURED / "developers.csv", DEVELOPERS)
    _write_csv(STRUCTURED / "agents.csv", AGENTS)
    _write_csv(STRUCTURED / "payment_plans.csv", PAYMENT_PLANS)
    write_semantic()
    print(f"Wrote {len(PROPERTIES)} properties + supporting tables + semantic docs")


if __name__ == "__main__":
    main()
