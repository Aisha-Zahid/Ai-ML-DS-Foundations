"""Score recorded conversations on the human-eval rubric (self + template)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDINGS = ROOT / "recordings"
RESULTS = ROOT / "results"

# Rubric 1-5 for each dimension
DIMENSIONS = [
    "naturalness",
    "persuasiveness",
    "fluency",
    "latency",
    "conversation_flow",
]


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    # Expected: recordings/*.scores.json written by reviewer, or use bundled samples
    rows = []
    for path in sorted(RECORDINGS.glob("*.json")):
        if path.name.endswith(".scores.json"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        scores_path = path.with_suffix(".scores.json")
        if scores_path.exists():
            scores = json.loads(scores_path.read_text(encoding="utf-8"))
        else:
            # Bootstrapped reviewer scores for the three scripted demos (honest classroom baseline)
            scores = data.get("human_scores") or {}
        row = {
            "recording": path.name,
            "title": data.get("title", path.stem),
            **{d: scores.get(d) for d in DIMENSIONS},
        }
        vals = [scores.get(d) for d in DIMENSIONS if scores.get(d) is not None]
        row["average"] = round(sum(vals) / len(vals), 2) if vals else None
        rows.append(row)

    if not rows:
        print("No recordings found")
        return

    with (RESULTS / "human_eval_scores.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    avgs = {d: [] for d in DIMENSIONS}
    for r in rows:
        for d in DIMENSIONS:
            if r.get(d) is not None:
                avgs[d].append(r[d])
    summary = {
        d: round(sum(v) / len(v), 2) if v else None for d, v in avgs.items()
    }
    summary["n_recordings"] = len(rows)
    (RESULTS / "human_eval_summary.json").write_text(
        json.dumps({"per_recording": rows, "means": summary}, indent=2), encoding="utf-8"
    )

    md = [
        "# Human evaluation scores",
        "",
        "Scale 1–5 (5 = excellent). Dimensions: naturalness, persuasiveness, fluency, latency, conversation flow.",
        "",
        "| Recording | Nat | Pers | Flu | Lat | Flow | Avg |",
        "|-----------|-----|------|-----|-----|------|-----|",
    ]
    for r in rows:
        md.append(
            f"| {r['title']} | {r.get('naturalness')} | {r.get('persuasiveness')} | "
            f"{r.get('fluency')} | {r.get('latency')} | {r.get('conversation_flow')} | {r.get('average')} |"
        )
    md += [
        "",
        "## Means",
        "",
        "| Dimension | Mean |",
        "|-----------|------|",
    ]
    for d in DIMENSIONS:
        md.append(f"| {d} | {summary.get(d)} |")
    (RESULTS / "human_eval.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
