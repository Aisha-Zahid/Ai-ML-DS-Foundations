"""
Week 2 Day 1 — Minimal raw-Python ReAct agent (Groq API).

No LangChain / LangGraph. Set GROQ_API_KEY in the environment or in a local .env file.

Usage:
  python agent.py
  python agent.py --prompt "Look up weather in Karachi and Lahore; which is warmer?"
  python agent.py --demo-failures
"""

from __future__ import annotations

import argparse
import ast
import json
import operator
import os
import sys
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
except ImportError:
    pass

from groq import Groq

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
MAX_ITERATIONS = 8
MAX_TOKENS = 1024
BASE_DIR = Path(__file__).resolve().parent

SYSTEM_PROMPT = """You are a careful tool-using assistant.
Use tools when they help answer the user. Prefer calculator for math.
For weather, call get_weather once per city. After you have enough
observations, give a clear final answer in plain text. If a tool errors
or you lack a needed tool, say so honestly instead of inventing results."""

# ---------------------------------------------------------------------------
# Tools (implementations + OpenAI/Groq function schemas)
# ---------------------------------------------------------------------------

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    raise ValueError("Only basic arithmetic expressions are allowed")


def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression (+ - * / ** // %)."""
    try:
        tree = ast.parse(expression, mode="eval")
        value = _safe_eval(tree)
        return json.dumps({"expression": expression, "result": value})
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc), "expression": expression})


WEATHER_DB = {
    "karachi": {"temp_c": 32, "condition": "humid"},
    "lahore": {"temp_c": 28, "condition": "clear"},
    "islamabad": {"temp_c": 24, "condition": "cloudy"},
    "london": {"temp_c": 14, "condition": "rain"},
    "tokyo": {"temp_c": 22, "condition": "clear"},
}


def get_weather(city: str) -> str:
    """Return stub weather for a known city (case-insensitive)."""
    key = city.strip().lower()
    if key not in WEATHER_DB:
        return json.dumps(
            {
                "error": f"Unknown city '{city}'",
                "known_cities": sorted(WEATHER_DB),
            }
        )
    data = WEATHER_DB[key]
    return json.dumps({"city": city.strip(), **data})


def read_file(path: str) -> str:
    """Read a small UTF-8 text file under the Day-1 folder only."""
    try:
        requested = Path(path)
        target = (BASE_DIR / requested).resolve() if not requested.is_absolute() else requested.resolve()
        if not str(target).startswith(str(BASE_DIR.resolve())):
            return json.dumps({"error": "Path must stay inside the Day-1 folder"})
        if not target.exists():
            return json.dumps({"error": f"File not found: {path}"})
        text = target.read_text(encoding="utf-8")
        if len(text) > 4000:
            text = text[:4000] + "\n...[truncated]"
        return json.dumps({"path": str(target.name), "content": text})
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc)})


TOOL_IMPLS = {
    "calculator": lambda args: calculator(args["expression"]),
    "get_weather": lambda args: get_weather(args["city"]),
    "read_file": lambda args: read_file(args["path"]),
}

# Human-readable schemas (used in write-up / notebook). Same params as TOOLS.
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "calculator",
        "description": (
            "Evaluate a basic arithmetic expression. Use for any math "
            "(sums, differences, averages). Input is a single expression string "
            "such as '32 - 28' or '(14 + 22) / 2'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Arithmetic expression using + - * / ** // % and parentheses",
                }
            },
            "required": ["expression"],
        },
    },
    {
        "name": "get_weather",
        "description": (
            "Look up current weather for one city. Call once per city. "
            "Known cities: Karachi, Lahore, Islamabad, London, Tokyo. "
            "Returns temperature in Celsius and a short condition."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name, e.g. Karachi or Lahore",
                }
            },
            "required": ["city"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read a UTF-8 text file from the Week-2/Day-1 project folder. "
            "Use for local notes such as sample_notes.txt."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative filename inside Day-1, e.g. sample_notes.txt",
                }
            },
            "required": ["path"],
        },
    },
]

# Groq / OpenAI function-calling format
TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": s["name"],
            "description": s["description"],
            "parameters": s["input_schema"],
        },
    }
    for s in TOOL_SCHEMAS
]


def execute_tool(name: str, tool_input: dict[str, Any]) -> str:
    """Run a registered tool; return a string observation (including errors)."""
    if name not in TOOL_IMPLS:
        return json.dumps({"error": f"Unknown tool '{name}'. Available: {list(TOOL_IMPLS)}"})
    try:
        return TOOL_IMPLS[name](tool_input)
    except KeyError as exc:
        return json.dumps({"error": f"Missing argument: {exc}", "input": tool_input})
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc)})


def get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Export it or put it in Week-2/Day-1/.env"
        )
    return Groq(api_key=api_key)


def log(section: str, message: str) -> None:
    print(f"\n=== {section} ===")
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode("ascii", errors="replace").decode("ascii"))


def _assistant_message_dict(message: Any) -> dict[str, Any]:
    """Convert Groq assistant message into a plain dict for the next request."""
    payload: dict[str, Any] = {
        "role": "assistant",
        "content": message.content or None,
    }
    tool_calls = getattr(message, "tool_calls", None) or []
    if tool_calls:
        payload["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tool_calls
        ]
    return payload


def run_agent(
    user_prompt: str,
    *,
    max_iterations: int = MAX_ITERATIONS,
    tools: list[dict[str, Any]] | None = None,
    working_memory: dict[str, Any] | None = None,
) -> str:
    """
    Minimal ReAct-style loop (Groq tool_calls):
      send messages → if tool_calls → execute → append role=tool → repeat
      until final text or max_iterations.

    Conversation memory = `messages` history.
    Working memory = optional scratchpad dict we update while running.
    """
    client = get_client()
    tool_defs = tools if tools is not None else TOOLS
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    scratch = working_memory if working_memory is not None else {}
    scratch.setdefault("tool_calls", [])
    scratch.setdefault("observations", [])

    log("USER", user_prompt)

    for iteration in range(1, max_iterations + 1):
        log("ITERATION", f"{iteration}/{max_iterations}")

        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            tools=tool_defs,
            tool_choice="auto",
            messages=messages,
        )
        message = response.choices[0].message
        tool_calls = message.tool_calls or []

        if message.content and message.content.strip():
            log("REASONING / TEXT", message.content)

        if tool_calls:
            messages.append(_assistant_message_dict(message))

            for tc in tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                    observation = json.dumps(
                        {"error": "Invalid JSON arguments", "raw": tc.function.arguments}
                    )
                else:
                    observation = execute_tool(name, args)

                log(
                    "ACT (tool_call)",
                    f"name={name}\nid={tc.id}\ninput={json.dumps(args)}",
                )
                log("OBSERVE (tool_result)", observation)
                scratch["tool_calls"].append({"name": name, "input": args})
                scratch["observations"].append(observation)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": name,
                        "content": observation,
                    }
                )
            continue

        final = (message.content or "").strip() or "(empty final response)"
        log("FINAL ANSWER", final)
        scratch["final"] = final
        scratch["iterations_used"] = iteration
        return final

    msg = (
        f"Stopped after {max_iterations} iterations (max_iterations safeguard). "
        "The model kept requesting tools or did not finish."
    )
    log("GUARDRAIL", msg)
    scratch["final"] = msg
    scratch["iterations_used"] = max_iterations
    return msg


def demo_single_tool_roundtrip(client: Groq | None = None) -> None:
    """Task 2: one request → manual tool execution → tool result → final text."""
    client = client or get_client()
    log("TASK 2", "Single-turn tool calling round-trip")
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "What is 17 * 23? Use the calculator tool."},
    ]
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=TOOLS,
        tool_choice="auto",
        messages=messages,
    )
    message = response.choices[0].message
    log("ASSISTANT RAW", str(message))

    tool_calls = message.tool_calls or []
    if not tool_calls:
        log("NOTE", "Model did not call a tool; stopping Task 2 demo.")
        return

    messages.append(_assistant_message_dict(message))
    for tc in tool_calls:
        args = json.loads(tc.function.arguments or "{}")
        result = execute_tool(tc.function.name, args)
        log("MANUAL TOOL RESULT", result)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "name": tc.function.name,
                "content": result,
            }
        )

    final = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=TOOLS,
        messages=messages,
    )
    text = final.choices[0].message.content or ""
    log("TASK 2 FINAL", text)


def run_failure_demos() -> None:
    """Task 5: deliberately stress the agent and print what happens."""
    cases = [
        ("ambiguous", "Do the thing with the numbers for that city."),
        ("tool_error", "Get the weather in Atlantis."),
        ("missing_tool", "Send an email to alice@example.com saying hello."),
    ]
    for name, prompt in cases:
        log("FAILURE CASE", name)
        try:
            run_agent(prompt, max_iterations=4)
        except Exception as exc:  # noqa: BLE001
            log("EXCEPTION", str(exc))


def main() -> None:
    parser = argparse.ArgumentParser(description="Week 2 Day 1 raw Python agent (Groq)")
    parser.add_argument(
        "--prompt",
        default=(
            "Look up the weather in Karachi and Lahore, then use the calculator "
            "to compute the temperature difference. Which city is warmer?"
        ),
        help="User task for the agent loop",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=MAX_ITERATIONS,
        help="Safeguard against infinite tool loops",
    )
    parser.add_argument(
        "--single-tool-demo",
        action="store_true",
        help="Run Task 2 single tool round-trip only",
    )
    parser.add_argument(
        "--demo-failures",
        action="store_true",
        help="Run Task 5 failure-mode prompts",
    )
    args = parser.parse_args()

    if not os.getenv("GROQ_API_KEY"):
        print(
            "ERROR: Set GROQ_API_KEY before running.\n"
            "  PowerShell:  $env:GROQ_API_KEY = 'gsk_...'\n"
            "  Or create Week-2/Day-1/.env with GROQ_API_KEY=...",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.single_tool_demo:
        demo_single_tool_roundtrip()
        return

    if args.demo_failures:
        run_failure_demos()
        return

    scratch: dict[str, Any] = {}
    answer = run_agent(args.prompt, max_iterations=args.max_iterations, working_memory=scratch)
    print("\n----- summary -----")
    print(f"iterations: {scratch.get('iterations_used')}")
    print(f"tool_calls: {len(scratch.get('tool_calls', []))}")
    print(f"answer: {answer}")


if __name__ == "__main__":
    main()
