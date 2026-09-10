"""
Week 2 Day 4 — CrewAI multi-agent crew.

Business task:
  Review the product catalog, compare two budget options, and write a
  short stakeholder-ready recommendation brief.

Agents (no overlapping jobs):
  1) Catalog Researcher — find products in products.csv
  2) Pricing Analyst — compute price gaps / budget fit with calculator
  3) Brief Writer — turn facts into a stakeholder summary

Process modes:
  - sequential
  - hierarchical (manager delegates / reviews)
"""

from __future__ import annotations

import argparse
import csv
import json
import operator
import ast
import os
import time
import asyncio
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)
if not os.getenv("GROQ_API_KEY"):
    load_dotenv(BASE_DIR.parent / "Day-3" / ".env", override=True)
    load_dotenv(BASE_DIR.parent / "Day-2" / ".env", override=True)
    load_dotenv(BASE_DIR.parent / "Day-1" / ".env", override=True)

# CrewAI uses GROQ_API_KEY via the OpenAI-compatible Groq endpoint below.
os.environ.setdefault("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
CREW_MODEL = os.getenv("CREWAI_MODEL", f"groq/{MODEL}")

PRODUCTS_CSV = BASE_DIR / "data" / "products.csv"

# Approximate USD per 1M tokens (adjust if your Groq pricing differs).
INPUT_COST_PER_1M = float(os.getenv("GROQ_INPUT_COST_PER_1M", "0.05"))
OUTPUT_COST_PER_1M = float(os.getenv("GROQ_OUTPUT_COST_PER_1M", "0.10"))


# ---------------------------------------------------------------------------
# Tools (role-scoped)
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
    raise ValueError("Only basic arithmetic is allowed")


def _load_catalog() -> list[dict[str, str]]:
    if not PRODUCTS_CSV.exists():
        raise FileNotFoundError(f"Missing catalog: {PRODUCTS_CSV}")
    with PRODUCTS_CSV.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def search_catalog(query: str) -> str:
    """Search products.csv by name, id, or category. Returns matching rows as JSON."""
    q = query.strip().lower()
    rows = _load_catalog()
    matches = []
    for row in rows:
        blob = f"{row.get('product_id','')} {row.get('name','')} {row.get('category','')}".lower()
        if q in blob or any(part and part in blob for part in q.split()):
            matches.append(row)
    if not matches:
        return json.dumps({"query": query, "matches": [], "note": "No products found"})
    return json.dumps({"query": query, "matches": matches[:8]}, indent=2)


def list_in_stock_by_category(category: str) -> str:
    """List in-stock products for one category (accessories, office, audio, video, storage)."""
    cat = category.strip().lower()
    rows = [
        r
        for r in _load_catalog()
        if r.get("category", "").lower() == cat
        and str(r.get("in_stock", "")).lower() in {"true", "1", "yes"}
    ]
    return json.dumps({"category": category, "in_stock": rows}, indent=2)


def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression such as '79.50 - 18.99'."""
    try:
        value = _safe_eval(ast.parse(expression, mode="eval"))
        return json.dumps({"expression": expression, "result": value})
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc), "expression": expression})


def build_tools():
    """Wrap plain functions as CrewAI tools."""
    from crewai.tools import tool

    @tool("search_catalog")
    def search_catalog_tool(query: str) -> str:
        """Search the local product catalog by name, product id, or category keyword."""
        return search_catalog(query)

    @tool("list_in_stock_by_category")
    def list_stock_tool(category: str) -> str:
        """List in-stock products for one category from products.csv."""
        return list_in_stock_by_category(category)

    @tool("calculator")
    def calculator_tool(expression: str) -> str:
        """Do arithmetic for price differences and budget checks. Example: 79.50 - 18.99"""
        return calculator(expression)

    return search_catalog_tool, list_stock_tool, calculator_tool


def get_llm():
    from crewai import LLM

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to Week-2/Day-4/.env")
    # Groq OpenAI-compatible endpoint
    return LLM(
        model=f"openai/{MODEL}",
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.2,
    )


# ---------------------------------------------------------------------------
# Agents / Tasks / Crews
# ---------------------------------------------------------------------------

DEFAULT_REQUEST = (
    "A budget-conscious client needs a recommendation between Wireless Mouse "
    "and Mechanical Keyboard. Research the catalog, compare prices, and write "
    "a short stakeholder brief that recommends the cheaper in-stock option."
)


def build_agents(llm):
    from crewai import Agent

    search_catalog_tool, list_stock_tool, calculator_tool = build_tools()

    researcher = Agent(
        role="Catalog Researcher",
        goal="Pull accurate product facts from the catalog for the products under review.",
        backstory=(
            "You work with the store catalog only. You look up product ids, prices, "
            "categories, and stock. You do not invent prices or write marketing copy."
        ),
        tools=[search_catalog_tool, list_stock_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    analyst = Agent(
        role="Pricing Analyst",
        goal="Compare prices with calculator and state which option fits a tight budget.",
        backstory=(
            "You turn catalog facts into clear numbers: price gap, cheaper product, "
            "and whether each item is in stock. You do not rewrite the final brief."
        ),
        tools=[calculator_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    writer = Agent(
        role="Stakeholder Brief Writer",
        goal="Write a short, clear recommendation brief for non-technical stakeholders.",
        backstory=(
            "You write for managers. You use only the researcher and analyst outputs. "
            "Keep the brief short and clear."
        ),
        tools=[],  # writing only — no catalog/math tools
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    return researcher, analyst, writer


def build_tasks(researcher, analyst, writer, request: str):
    from crewai import Task

    # Ask for JSON so the next agent gets clear prices.
    research_task = Task(
        description=(
            f"Business request:\n{request}\n\n"
            "Use search_catalog (and list_in_stock_by_category if useful) to gather "
            "facts for Wireless Mouse and Mechanical Keyboard. "
            "Do not invent prices."
        ),
        expected_output=(
            "A short summary PLUS a JSON block named CATALOG_FACTS with this shape:\n"
            "{\n"
            '  "products": [\n'
            '    {"name": "...", "product_id": "...", "price_usd": 0.0, "in_stock": true},\n'
            '    {"name": "...", "product_id": "...", "price_usd": 0.0, "in_stock": true}\n'
            "  ]\n"
            "}\n"
            "No other products."
        ),
        agent=researcher,
    )

    analysis_task = Task(
        description=(
            "Read the Catalog Researcher output, especially CATALOG_FACTS. "
            "Use the calculator tool to compute the price difference. "
            "State which product is cheaper and whether both are in stock."
        ),
        expected_output=(
            "A short analysis PLUS a JSON block named PRICE_ANALYSIS:\n"
            "{\n"
            '  "cheaper_product": "...",\n'
            '  "price_difference_usd": 0.0,\n'
            '  "both_in_stock": true,\n'
            '  "budget_recommendation": "..."\n'
            "}"
        ),
        agent=analyst,
        context=[research_task],
    )

    brief_task = Task(
        description=(
            "Using CATALOG_FACTS and PRICE_ANALYSIS from earlier tasks, write a "
            "stakeholder-ready brief. Include: recommendation, price gap, stock note, "
            "and one sentence why this fits a budget-conscious client."
        ),
        expected_output=(
            "A stakeholder brief with these headings:\n"
            "## Recommendation\n"
            "## Price comparison\n"
            "## Stock\n"
            "## Why this fits budget\n"
            "Keep it under 180 words. No JSON."
        ),
        agent=writer,
        context=[research_task, analysis_task],
    )

    return research_task, analysis_task, brief_task


def build_manager(llm):
    from crewai import Agent

    return Agent(
        role="Project Manager",
        goal="Delegate catalog research, pricing, and brief writing; check outputs stay on task.",
        backstory=(
            "You coordinate specialists. You assign the right person to each step and "
            "push back if an output is incomplete before the next step."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=True,
    )


def build_sequential_crew(request: str = DEFAULT_REQUEST):
    from crewai import Crew, Process

    llm = get_llm()
    researcher, analyst, writer = build_agents(llm)
    tasks = build_tasks(researcher, analyst, writer, request)
    crew = Crew(
        agents=[researcher, analyst, writer],
        tasks=list(tasks),
        process=Process.sequential,
        verbose=True,
        tracing=False,
    )
    return crew


def build_hierarchical_crew(request: str = DEFAULT_REQUEST):
    from crewai import Crew, Process

    llm = get_llm()
    researcher, analyst, writer = build_agents(llm)
    manager = build_manager(llm)
    tasks = build_tasks(researcher, analyst, writer, request)
    crew = Crew(
        agents=[researcher, analyst, writer],
        tasks=list(tasks),
        process=Process.hierarchical,
        manager_agent=manager,
        verbose=True,
        tracing=False,
    )
    return crew


def extract_token_usage(result: Any) -> dict[str, Any]:
    """Read token usage from a CrewAI result when available."""
    usage: dict[str, Any] = {
        "total_tokens": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "raw": None,
    }
    token_usage = getattr(result, "token_usage", None)
    if token_usage is None and isinstance(result, dict):
        token_usage = result.get("token_usage")
    if token_usage is None:
        return usage

    usage["raw"] = str(token_usage)
    # Support object or dict-like shapes
    for key_src, key_dst in [
        ("total_tokens", "total_tokens"),
        ("prompt_tokens", "prompt_tokens"),
        ("completion_tokens", "completion_tokens"),
        ("successful_requests", "successful_requests"),
    ]:
        if hasattr(token_usage, key_src):
            usage[key_dst] = getattr(token_usage, key_src)
        elif isinstance(token_usage, dict) and key_src in token_usage:
            usage[key_dst] = token_usage[key_src]
    return usage


def estimate_cost_usd(prompt_tokens: int | None, completion_tokens: int | None) -> float | None:
    if prompt_tokens is None and completion_tokens is None:
        return None
    p = float(prompt_tokens or 0)
    c = float(completion_tokens or 0)
    return (p / 1_000_000.0) * INPUT_COST_PER_1M + (c / 1_000_000.0) * OUTPUT_COST_PER_1M


def run_crew(mode: str, request: str = DEFAULT_REQUEST) -> dict[str, Any]:
    if mode == "sequential":
        crew = build_sequential_crew(request)
    elif mode == "hierarchical":
        crew = build_hierarchical_crew(request)
    else:
        raise ValueError("mode must be 'sequential' or 'hierarchical'")

    # If an event loop is already running (notebook), kickoff in a thread.
    def _kick():
        return crew.kickoff()

    t0 = time.perf_counter()
    try:
        asyncio.get_running_loop()
        in_async = True
    except RuntimeError:
        in_async = False

    if in_async:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(_kick).result()
    else:
        result = _kick()
    elapsed = time.perf_counter() - t0

    usage = extract_token_usage(result)
    cost = estimate_cost_usd(usage.get("prompt_tokens"), usage.get("completion_tokens"))
    output_text = str(result)

    return {
        "mode": mode,
        "elapsed_sec": round(elapsed, 2),
        "output": output_text,
        "usage": usage,
        "approx_cost_usd": cost,
        "model": f"openai/{MODEL} @ groq",
    }


def score_output(text: str) -> dict[str, int]:
    """
    Simple 0/1 checks for the three success criteria.
    """
    lower = text.lower()
    factual = int(
        ("18.99" in text or "18.99" in lower)
        and ("79.50" in text or "79.5" in text)
    )
    complete = int(
        ("recommend" in lower)
        and ("stock" in lower or "in stock" in lower)
        and ("$" in text or "usd" in lower or "price" in lower)
    )
    tone = int(
        ("## recommendation" in lower or "recommendation" in lower)
        and ("stakeholder" not in lower[:40])  # not required
        and len(text.split()) <= 250
    )
    # tone: has clear headings-ish structure and stays concise
    has_structure = int("##" in text or "recommendation" in lower)
    tone = int(has_structure and len(text.split()) <= 250)
    return {
        "factual_grounding": factual,
        "completeness": complete,
        "tone_structure": tone,
        "total": factual + complete + tone,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Week 2 Day 4 CrewAI crew")
    parser.add_argument(
        "--mode",
        choices=["sequential", "hierarchical", "both"],
        default="both",
    )
    parser.add_argument("--request", default=DEFAULT_REQUEST)
    args = parser.parse_args()

    modes = ["sequential", "hierarchical"] if args.mode == "both" else [args.mode]
    for mode in modes:
        print("\n" + "=" * 72)
        print(f"MODE: {mode}")
        print("=" * 72)
        out = run_crew(mode, args.request)
        print(f"elapsed_sec={out['elapsed_sec']}")
        print(f"usage={out['usage']}")
        print(f"approx_cost_usd={out['approx_cost_usd']}")
        print("--- output ---")
        print(out["output"])
        print("--- scores ---")
        print(score_output(out["output"]))


if __name__ == "__main__":
    main()
