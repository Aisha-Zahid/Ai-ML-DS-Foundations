"""Multi-turn memory demo: budget → DHA options → cheaper follow-up."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pipeline import VoicePipeline  # noqa: E402


SCRIPT = [
    "Assalam-o-Alaikum",
    "Budget 3 crore hai, Karachi mein buy karna hai",
    "DHA mein kya options hain?",
    "Us se sasti koi option?",
    "Thoda mehnga lag raha hai",
]


def main() -> None:
    pipe = VoicePipeline()
    turns = []
    for line in SCRIPT:
        row = pipe.turn(user_text=line, speak=True)
        turns.append(
            {
                "user": row["user"],
                "assistant": row["reply"],
                "intent": row["intent"],
                "total_ms": row["total_ms"],
                "under_2s": row["under_2s"],
                "memory_summary": {
                    "budget": row["memory"].get("budget_text"),
                    "city": row["memory"].get("city"),
                    "area": row["memory"].get("area"),
                    "shortlist": [
                        p.get("property_id") for p in (row["memory"].get("last_shortlist") or [])
                    ],
                },
            }
        )
        print(f"USER: {line}")
        print(f"ALI ({row['total_ms']} ms): {row['reply'][:220]}")
        print("---")

    out = ROOT / "results" / "memory_demo.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(turns, indent=2, ensure_ascii=False), encoding="utf-8")
    pipe.save_latency_log(ROOT / "results" / "latency_log.json")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
