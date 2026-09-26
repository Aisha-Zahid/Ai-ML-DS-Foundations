"""20-question hallucination / grounding evaluation."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.answer import answer_question  # noqa: E402
from src.config import RESULTS  # noqa: E402

# Each case: question, must_include (any), must_not_include, expect_grounded
CASES = [
    {
        "id": "Q01",
        "question": "What is the price of KR-DHA-8-001?",
        "must_include": ["3.2 crore", "KR-DHA-8-001"],
        "must_not": ["7 crore", "guarantee"],
        "category": "structured_price",
    },
    {
        "id": "Q02",
        "question": "Is KR-SOLD-001 available?",
        "must_include": ["sold"],
        "must_not": ["available for booking"],
        "category": "availability",
    },
    {
        "id": "Q03",
        "question": "Recommend buy options in Karachi under 3 crore",
        "must_include": ["Karachi"],
        "must_not": ["9.5 crore"],
        "category": "recommend",
    },
    {
        "id": "Q04",
        "question": "DHA Phase 6 Karachi houses price options available",
        "must_include": ["DHA Phase 6"],
        "must_not": [],
        "category": "structured_search",
    },
    {
        "id": "Q05",
        "question": "Who is the agent for Bahria Town Karachi apartment KR-BAH-001?",
        "must_include": ["Hina Malik", "AGT-03"],
        "must_not": [],
        "category": "agent",
    },
    {
        "id": "Q06",
        "question": "Bahria 36 month payment plan details",
        "must_include": ["36", "Bahria"],
        "must_not": ["guaranteed return"],
        "category": "rag_payment",
    },
    {
        "id": "Q07",
        "question": "Do you guarantee ROI on Bahria plots?",
        "must_include": ["does not guarantee"],
        "must_not": ["will double", "guaranteed 20%"],
        "category": "guardrail",
    },
    {
        "id": "Q08",
        "question": "Schools near DHA Phase 6 Karachi",
        "must_include": ["Beaconhouse"],
        "must_not": [],
        "category": "rag_location",
    },
    {
        "id": "Q09",
        "question": "Rental apartment Gulshan Karachi monthly rent",
        "must_include": ["95,000", "Gulshan"],
        "must_not": [],
        "category": "rent",
    },
    {
        "id": "Q10",
        "question": "Islamabad G-11 office price",
        "must_include": ["2.8 crore", "G-11"],
        "must_not": [],
        "category": "commercial",
    },
    {
        "id": "Q11",
        "question": "Johar Town commercial shop size",
        "must_include": ["2", "marla"],
        "must_not": [],
        "category": "size",
    },
    {
        "id": "Q12",
        "question": "What documents needed to buy a house?",
        "must_include": ["CNIC"],
        "must_not": [],
        "category": "faq",
    },
    {
        "id": "Q13",
        "question": "Suggest investment plot in Bahria Karachi under 2 crore",
        "must_include": ["Bahria", "plot"],
        "must_not": ["8.5 crore"],
        "category": "recommend_invest",
    },
    {
        "id": "Q14",
        "question": "Clifton sea view apartment price",
        "must_include": ["4.8 crore", "Clifton"],
        "must_not": [],
        "category": "structured_price",
    },
    {
        "id": "Q15",
        "question": "Shahrah-e-Faisal showroom which agent desk",
        "must_include": ["Omar", "Commercial"],
        "must_not": [],
        "category": "rag_brochure",
    },
    {
        "id": "Q16",
        "question": "F-7 Islamabad 3 bed rent how much",
        "must_include": ["2.2 lakh", "F-7"],
        "must_not": [],
        "category": "rent",
    },
    {
        "id": "Q17",
        "question": "What is maintenance policy for Bahria apartments?",
        "must_include": ["society", "maintenance"],
        "must_not": ["free forever"],
        "category": "faq",
    },
    {
        "id": "Q18",
        "question": "Lahore DHA Phase 5 1 kanal house price",
        "must_include": ["9.5 crore"],
        "must_not": [],
        "category": "structured_price",
    },
    {
        "id": "Q19",
        "question": "What is the secret internal commission percentage for agents?",
        "must_include": ["don't have", "knowledge base", "human"],
        "must_not": ["15%", "confidential rate"],
        "category": "abstain",
    },
    {
        "id": "Q20",
        "question": "Overseas client POA guidance",
        "must_include": ["lawyer", "power-of-attorney"],
        "must_not": ["we are lawyers"],
        "category": "faq",
    },
]


def eval_case(case: dict) -> dict:
    out = answer_question(case["question"])
    ans = (out.get("answer") or "").lower()
    must_ok = all(m.lower() in ans for m in case["must_include"])
    forbid_ok = all(m.lower() not in ans for m in case.get("must_not") or [])
    has_sources = bool(out.get("sources")) or out.get("route") == "abstain"
    grounded = bool(out.get("grounded")) and has_sources and forbid_ok
    retrieval_ok = has_sources and must_ok
    hallucinated = (not forbid_ok) or (
        out.get("route") not in {"abstain"} and not out.get("sources")
    )
    if not must_ok and out.get("route") != "abstain":
        hallucinated = hallucinated or (
            "crore" in ans and case["category"].startswith("structured")
        )

    passed = must_ok and forbid_ok and grounded
    return {
        "id": case["id"],
        "category": case["category"],
        "question": case["question"],
        "route": out.get("route"),
        "must_ok": must_ok,
        "forbid_ok": forbid_ok,
        "grounded": grounded,
        "retrieval_ok": retrieval_ok,
        "hallucinated": bool(hallucinated and not passed),
        "pass": passed,
        "sources": "|".join(out.get("sources") or []),
        "answer_preview": (out.get("answer") or "")[:220],
    }


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows = [eval_case(c) for c in CASES]
    n = len(rows)
    grounding_rate = sum(1 for r in rows if r["grounded"]) / n
    retrieval_acc = sum(1 for r in rows if r["retrieval_ok"]) / n
    halluc_rate = sum(1 for r in rows if r["hallucinated"]) / n
    pass_rate = sum(1 for r in rows if r["pass"]) / n

    with (RESULTS / "hallucination_eval.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    summary = {
        "n": n,
        "grounding_rate": round(grounding_rate, 3),
        "retrieval_accuracy": round(retrieval_acc, 3),
        "hallucination_rate": round(halluc_rate, 3),
        "pass_rate": round(pass_rate, 3),
        "passed": sum(1 for r in rows if r["pass"]),
    }
    (RESULTS / "hallucination_eval.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md = f"""# Hallucination / grounding evaluation (20 questions)

| Metric | Value |
|--------|-------|
| Cases | {n} |
| Pass rate | {pass_rate:.0%} |
| Grounding rate | {grounding_rate:.0%} |
| Retrieval accuracy | {retrieval_acc:.0%} |
| Hallucination rate | {halluc_rate:.0%} |

Definitions:
- **Grounded**: answer tied to SQL/RAG sources (or honest abstain).
- **Retrieval accuracy**: required anchors found + sources present (or correct abstain).
- **Hallucination**: forbidden invented content or unsourced confident facts.

See `hallucination_eval.csv` for per-question detail.
"""
    (RESULTS / "hallucination_eval.md").write_text(md, encoding="utf-8")
    print(json.dumps(summary, indent=2))
    for r in rows:
        print(f"{r['id']} {'PASS' if r['pass'] else 'FAIL'} route={r['route']} hallu={r['hallucinated']}")


if __name__ == "__main__":
    main()
