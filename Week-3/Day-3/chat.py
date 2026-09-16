"""CLI chat for Aussie Footy Desk."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.agent import chat, reset_session  # noqa: E402
from src.fact_cards import build_fact_cards  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="AFL scoped chat agent")
    p.add_argument("--message", "-m", help="Single message (non-interactive)")
    p.add_argument("--session", default="cli")
    p.add_argument("--reset", action="store_true")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    build_fact_cards()
    if args.reset:
        reset_session(args.session)

    if args.message:
        out = chat(args.message, session_id=args.session, verbose=args.verbose)
        print(out["answer"])
        print("\n--- grounding ---")
        print(json.dumps(out["grounding"], indent=2)[:1500])
        return

    print("Aussie Footy Desk (type quit to exit)")
    while True:
        try:
            msg = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not msg or msg.lower() in {"quit", "exit"}:
            break
        out = chat(msg, session_id=args.session, verbose=args.verbose)
        print("bot>", out["answer"])
        g = out["grounding"]
        print(
            f"(tools={g['tool_calls']} grounded_ok={g['grounded_ok']} "
            f"missing={g['numbers_missing_from_tools']})"
        )


if __name__ == "__main__":
    main()
