"""Latency budget evaluation across scripted turns."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import BUDGET_TOTAL_MS  # noqa: E402
from src.pipeline import VoicePipeline  # noqa: E402
from src.speech_behaviors import BargeInController  # noqa: E402
from src.tts import synthesize  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402

UTTERANCES = [
    "Hello",
    "Karachi mein buy, budget 2.5 crore",
    "Bahria mein apartment chahiye",
    "Builder pe trust nahi aa raha",
    "Maintenance charges kya hote hain?",
    "Us se sasti option?",
]


def test_barge_in() -> dict:
    barge = BargeInController()

    def cancel_soon():
        time.sleep(0.05)
        barge.interrupt()

    threading.Thread(target=cancel_soon, daemon=True).start()
    long_text = "Ji bilkul, " + ("yeh option dekhte hain. " * 40)
    out = synthesize(long_text, barge=barge)
    return {
        "interrupted": bool(out.get("interrupted")),
        "ttfa_ms": out.get("ttfa_ms"),
        "provider": out.get("provider"),
    }


def main() -> None:
    pipe = VoicePipeline()
    rows = []
    for u in UTTERANCES:
        r = pipe.turn(user_text=u, speak=True)
        rows.append(
            {
                "user": u,
                "stt_ms": r["stt_ms"],
                "reason_ms": r["reason_ms"],
                "tts_ttfa_ms": r["tts_ttfa_ms"],
                "tts_ms": r["tts_ms"],
                "total_ms": r["total_ms"],
                "under_2s": r["under_2s"],
                "intent": r["intent"],
            }
        )
        print(f"{r['total_ms']:7.1f} ms | under_2s={r['under_2s']} | {u[:40]}")

    barge = test_barge_in()
    print("barge-in:", barge)

    results = ROOT / "results"
    results.mkdir(parents=True, exist_ok=True)
    with (results / "latency_eval.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    n = len(rows)
    ok = sum(1 for r in rows if r["under_2s"])
    summary = {
        "n": n,
        "under_2s_rate": round(ok / n, 3),
        "avg_total_ms": round(sum(r["total_ms"] for r in rows) / n, 1),
        "p95_total_ms": sorted(r["total_ms"] for r in rows)[max(0, int(0.95 * n) - 1)],
        "budget_ms": BUDGET_TOTAL_MS,
        "barge_in": barge,
    }
    (results / "latency_eval.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md = f"""# Latency evaluation (Day 3)

Mock STT + reasoning + mock streaming TTS (warm Day-2 index).

| Metric | Value |
|--------|-------|
| Turns | {n} |
| Under 2s rate | {summary['under_2s_rate']:.0%} |
| Avg total | {summary['avg_total_ms']} ms |
| p95 total | {summary['p95_total_ms']} ms |
| Budget | {BUDGET_TOTAL_MS} ms |
| Barge-in works | {barge.get('interrupted')} |

Live Deepgram/Fish keys optional via `.env` (`VOICE_MODE=live`).
"""
    (results / "latency_eval.md").write_text(md, encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
