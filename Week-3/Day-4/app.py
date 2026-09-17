"""CLI for the LangGraph AFL orchestrator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.graph import run_query  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("-m", "--message", required=True)
    p.add_argument("--trace", action="store_true")
    args = p.parse_args()
    out = run_query(args.message)
    print(out.get("final_response", ""))
    if args.trace:
        print("\n--- trace ---")
        for line in out.get("trace") or []:
            print(line)
        print("--- meta ---")
        print(
            json.dumps(
                {
                    "intent": out.get("intent"),
                    "route": out.get("route"),
                    "teams": out.get("teams"),
                    "tool_name": out.get("tool_name"),
                    "tool_error": out.get("tool_error"),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
