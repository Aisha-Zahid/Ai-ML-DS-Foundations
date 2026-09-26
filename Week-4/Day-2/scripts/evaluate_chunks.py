"""Evaluate chunk sizes on a fixed probe set (retrieval hit quality)."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import CHUNK_VARIANTS, RESULTS, VECTORSTORE  # noqa: E402
from src.rag import TfidfStore  # noqa: E402

# query -> substrings that should appear in retrieved text if chunking is good
PROBES = [
    ("Does RealEstate Hub guarantee ROI?", ["does not guarantee", "investment returns"]),
    ("Bahria 36 month payment plan booking percent", ["10%", "20%", "36"]),
    ("DHA Phase 6 schools and hospitals", ["Beaconhouse", "South City"]),
    ("Shahrah-e-Faisal showroom size", ["4000", "showroom"]),
    ("Rental advance and security deposit", ["1–2 months", "security", "1 month"]),
    ("Bahria Town Karachi apartment precinct 10", ["Precinct 10", "1600"]),
    ("Islamabad G-11 office nearby hospital", ["PIMS", "G-11"]),
    ("Overseas clients power of attorney", ["power-of-attorney", "lawyer"]),
]


def score_variant(variant: str) -> dict:
    store = TfidfStore()
    store.load(VECTORSTORE / f"tfidf_{variant}")
    hits_ok = 0
    rows = []
    for q, needles in PROBES:
        results = store.search(q, top_k=3)
        blob = " ".join(r["text"] for r in results).lower()
        found = [n for n in needles if n.lower() in blob]
        ok = len(found) >= max(1, len(needles) // 2)
        hits_ok += int(ok)
        rows.append(
            {
                "variant": variant,
                "query": q,
                "ok": ok,
                "found": ";".join(found),
                "top_sources": ";".join(r["source"] for r in results),
                "top_score": results[0]["score"] if results else 0,
            }
        )
    return {
        "variant": variant,
        "hit_rate": hits_ok / len(PROBES),
        "hits": hits_ok,
        "n": len(PROBES),
        "rows": rows,
    }


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    all_rows = []
    summary = []
    for variant in CHUNK_VARIANTS:
        s = score_variant(variant)
        summary.append(
            {
                "variant": s["variant"],
                "chunk_size": CHUNK_VARIANTS[variant],
                "hit_rate": round(s["hit_rate"], 3),
                "hits": s["hits"],
                "n": s["n"],
            }
        )
        all_rows.extend(s["rows"])
        print(f"{variant}: hit_rate={s['hit_rate']:.0%} ({s['hits']}/{s['n']})")

    best = max(summary, key=lambda x: x["hit_rate"])
    with (RESULTS / "chunk_eval.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)
    with (RESULTS / "chunk_eval_summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    md = [
        "# Chunk size evaluation",
        "",
        "Probe queries check whether the right FAQ/brochure facts land in top-3 chunks.",
        "",
        "| Variant | Chunk size | Hit rate |",
        "|---------|------------|----------|",
    ]
    for s in summary:
        md.append(f"| {s['variant']} | {s['chunk_size']} | {s['hit_rate']:.0%} |")
    md += [
        "",
        f"**Best for this KB:** `{best['variant']}` ({best['hit_rate']:.0%} hit rate).",
        "",
        "Default index used by the agent: `medium_800` unless hit rate clearly favors another.",
        "Smaller chunks help precise FAQ lines; larger chunks keep brochure context.",
    ]
    (RESULTS / "chunk_eval.md").write_text("\n".join(md), encoding="utf-8")
    (RESULTS / "chunk_eval.json").write_text(
        json.dumps({"summary": summary, "best": best}, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
