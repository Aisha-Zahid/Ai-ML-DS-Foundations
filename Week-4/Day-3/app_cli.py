"""Interactive CLI for Day-3 voice agent (text in, spoken-style out)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.pipeline import VoicePipeline  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="RealEstate Hub UrduLish voice agent (Day 3)")
    p.add_argument("-m", "--message", help="Single utterance")
    p.add_argument("--no-speak", action="store_true", help="Skip TTS mock")
    p.add_argument("--interrupt-demo", action="store_true", help="Fire barge-in mid TTS")
    args = p.parse_args()

    pipe = VoicePipeline()

    if args.message:
        if args.interrupt_demo:
            import threading
            import time

            def boom():
                time.sleep(0.08)
                pipe.interrupt()
                print("[barge-in] caller interrupted")

            threading.Thread(target=boom, daemon=True).start()
        row = pipe.turn(user_text=args.message, speak=not args.no_speak)
        print(row["reply"])
        print(
            f"\n[{row['total_ms']} ms | under_2s={row['under_2s']} | intent={row['intent']}]"
        )
        return

    print("RealEstate Hub — Ali (UrduLish). Type 'quit' to exit, 'interrupt' to barge-in next reply.\n")
    pending_interrupt = False
    while True:
        try:
            line = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in {"quit", "exit"}:
            break
        if line.lower() == "interrupt":
            pending_interrupt = True
            print("(next reply will be interrupted)")
            continue
        if pending_interrupt:
            import threading
            import time

            def boom():
                time.sleep(0.08)
                pipe.interrupt()

            threading.Thread(target=boom, daemon=True).start()
            pending_interrupt = False
        row = pipe.turn(user_text=line, speak=not args.no_speak)
        print(f"Ali: {row['reply']}")
        print(f"  ({row['total_ms']} ms, {row['intent']})\n")


if __name__ == "__main__":
    main()
