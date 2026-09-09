"""
Week 2 Day 3 — LangGraph Stateful Agent (conditional edges, cycles, interrupts, persistence).

This file implements a graph workflow over a shared State object:
  plan -> retrieve -> generate -> critique -(loop)-> generate
  critique -> human_review -(interrupt)-> format -> END

We reuse the same "shopping recommendation" domain from Day 2 (products.csv).

Notes:
  - Uses LangGraph's interrupt_before/interrupt_after via graph.compile(...)
  - Uses MemorySaver checkpointer for persistence across runs/sessions.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional, TypedDict

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)
if not os.getenv("GROQ_API_KEY"):
    # Fall back to Day-1/Day-2 env if user only kept it there
    load_dotenv(BASE_DIR.parent / "Day-2" / ".env", override=True)
    load_dotenv(BASE_DIR.parent / "Day-1" / ".env", override=True)


MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "6"))


class ShoppingState(TypedDict, total=False):
    # input
    request: str
    product_a: str
    product_b: str

    # working state
    plan: List[str]
    retrieved: dict
    draft: str
    quality_score: float

    # control
    retries: int
    max_retries: int
    quality_threshold: float
    loop_passes: int

    # human-in-the-loop
    human_approved: Optional[bool]
    human_notes: Optional[str]

    # final
    formatted: str

    # debugging
    trace: List[str]


def get_llm(temperature: float = 0) -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY missing. Put it in Week-2/Day-3/.env (or reuse Day-2/.env).")
    return ChatGroq(model=MODEL, temperature=temperature, api_key=api_key)


def load_catalog(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Catalog missing: {csv_path}")
    with csv_path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@dataclass(frozen=True)
class ProductInfo:
    product_id: str
    name: str
    category: str
    price_usd: float
    in_stock: bool


def find_product(catalog: list[dict], query: str) -> ProductInfo:
    q = query.strip().lower()
    for row in catalog:
        blob = f"{row.get('product_id','')} {row.get('name','')} {row.get('category','')}".lower()
        if q == row.get("product_id", "").strip().lower() or q in blob:
            return ProductInfo(
                product_id=row["product_id"],
                name=row["name"],
                category=row["category"],
                price_usd=float(row["price_usd"]),
                in_stock=str(row.get("in_stock", "true")).strip().lower() in {"true", "1", "yes"},
            )
    raise KeyError(f"No product match for query={query!r}")


def _append_trace(state: ShoppingState, msg: str) -> list:
    """Return a new trace list (do not rely on in-place mutation alone)."""
    trace = list(state.get("trace") or [])
    trace.append(msg)
    return trace


def plan_node(state: ShoppingState) -> dict:
    plan = [
        "Retrieve catalog info for product A and B.",
        "Draft a comparison and budget-friendly recommendation.",
        "Critique draft quality; loop back to draft if needed.",
        "Ask for human approval before formatting final response.",
    ]
    trace = _append_trace(state, f"[plan_node] plan={plan}")
    return {"plan": plan, "trace": trace}


def retrieve_node(state: ShoppingState) -> dict:
    catalog = load_catalog(BASE_DIR / "data" / "products.csv")
    a = find_product(catalog, state["product_a"])
    b = find_product(catalog, state["product_b"])
    retrieved = {
        "a": {"product_id": a.product_id, "name": a.name, "price_usd": a.price_usd, "in_stock": a.in_stock},
        "b": {"product_id": b.product_id, "name": b.name, "price_usd": b.price_usd, "in_stock": b.in_stock},
    }
    trace = _append_trace(
        state, f"[retrieve_node] retrieved={json.dumps(retrieved, ensure_ascii=False)}"
    )
    return {"retrieved": retrieved, "trace": trace}


def generate_node(state: ShoppingState) -> dict:
    """
    We intentionally generate a "weak" first draft when retries==0 to trigger the critique loop.
    On later passes, we include the full price difference and explicit cheaper recommendation.
    """
    retrieved = state["retrieved"]
    a_name = retrieved["a"]["name"]
    b_name = retrieved["b"]["name"]
    a_price = float(retrieved["a"]["price_usd"])
    b_price = float(retrieved["b"]["price_usd"])
    diff = abs(a_price - b_price)
    cheaper = a_name if a_price <= b_price else b_name

    # "quality" trigger: first pass (before any critique) omits numbers
    if int(state.get("loop_passes", 0)) == 0:
        draft = (
            f"Compare {a_name} vs {b_name} for budget-conscious buying. "
            f"The cheaper option is likely {cheaper}. "
            f"Add more precise price details after review."
        )
    else:
        draft = (
            f"Budget comparison for {a_name} vs {b_name}.\n\n"
            f"- {a_name}: ${a_price:.2f}\n"
            f"- {b_name}: ${b_price:.2f}\n\n"
            f"Price difference: ${diff:.2f}.\n"
            f"Recommended (cheapest): {cheaper}."
        )

    trace = _append_trace(
        state, f"[generate_node] retries={state.get('retries')} draft_len={len(draft)}"
    )
    return {"draft": draft, "trace": trace}


def critique_node(state: ShoppingState) -> dict:
    """
    Heuristic quality scoring to decide whether to loop back.
    Score high only if draft contains both product names and at least two '$' prices.
    """
    draft = state.get("draft", "")
    retrieved = state.get("retrieved", {})
    a_name = retrieved.get("a", {}).get("name", "")
    b_name = retrieved.get("b", {}).get("name", "")

    has_names = (a_name in draft) and (b_name in draft)
    has_prices = draft.count("$") >= 2
    score = 0.2
    if has_names:
        score += 0.4
    if has_prices:
        score += 0.4

    score = min(1.0, score)
    new_passes = int(state.get("loop_passes", 0)) + 1

    # If draft is weak, we increment retries here so the next generate pass can improve.
    threshold = float(state.get("quality_threshold", 0.8))
    retries = int(state.get("retries", 0))
    max_retries = int(state.get("max_retries", MAX_ITERATIONS))
    next_retries = retries
    if score < threshold and retries < max_retries:
        next_retries = retries + 1

    trace = _append_trace(
        state,
        f"[critique_node] quality_score={score} (threshold={threshold}) pass={new_passes} retries={retries}->{next_retries}",
    )
    return {
        "quality_score": score,
        "loop_passes": new_passes,
        "retries": next_retries,
        "trace": trace,
    }


def critique_router(state: ShoppingState) -> Literal["generate", "human_review"]:
    threshold = float(state.get("quality_threshold", 0.8))
    loop_passes = int(state.get("loop_passes", 0))
    max_retries = int(state.get("max_retries", MAX_ITERATIONS))

    # Loop while quality is still low AND we still have critique budget.
    if state.get("quality_score", 0.0) < threshold and loop_passes < max_retries:
        return "generate"
    return "human_review"


def critique_router_to_format(state: ShoppingState) -> Literal["generate", "format"]:
    """Task-3 helper: skip human interrupt and finish when quality is good."""
    nxt = critique_router(state)
    return "generate" if nxt == "generate" else "format"


def human_review_node(state: ShoppingState) -> dict:
    """
    This node runs AFTER human_approved is filled in via graph.update_state(...)
    (because we interrupt before this node).
    """
    approved = state.get("human_approved")
    notes = state.get("human_notes") or ""

    if approved is True:
        trace = _append_trace(state, f"[human_review_node] APPROVED notes={notes!r}")
        return {"formatted": "", "trace": trace}

    # If rejected, increment retries and ask generate_node to improve.
    next_retries = int(state.get("retries", 0)) + 1
    trace = _append_trace(
        state, f"[human_review_node] REJECTED approved={approved} notes={notes!r}"
    )
    return {"retries": next_retries, "human_notes": notes, "trace": trace}


def human_review_router(state: ShoppingState) -> Literal["format", "generate"]:
    approved = state.get("human_approved")
    if approved is True:
        return "format"
    return "generate"


def format_node(state: ShoppingState) -> dict:
    retrieved = state["retrieved"]
    a_name = retrieved["a"]["name"]
    b_name = retrieved["b"]["name"]
    a_price = float(retrieved["a"]["price_usd"])
    b_price = float(retrieved["b"]["price_usd"])
    diff = abs(a_price - b_price)

    cheaper = a_name if a_price <= b_price else b_name
    approval_txt = (
        "Human approved the recommendation."
        if state.get("human_approved") is True
        else "Auto-finished (or latest revision after human rejection)."
    )
    formatted = (
        f"FINAL RECOMMENDATION\n\n"
        f"Products: {a_name} (${a_price:.2f}) vs {b_name} (${b_price:.2f})\n"
        f"Difference: ${diff:.2f}\n"
        f"Recommendation: {cheaper}\n\n"
        f"Why: {state.get('draft','')}\n"
        f"({approval_txt})"
    )
    trace = _append_trace(state, f"[format_node] formatted_len={len(formatted)}")
    return {"formatted": formatted, "trace": trace}


def build_linear_graph() -> tuple:
    """Task 2: plan -> retrieve -> generate -> format (no cycles)."""
    graph = StateGraph(ShoppingState)
    graph.add_node("plan", plan_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_node("format", format_node)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "format")
    graph.add_edge("format", END)
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer), checkpointer


def build_conditional_graph(checkpointer: MemorySaver) -> object:
    """Task 3: conditional edge + self-correction loop (critique -> generate)."""
    graph = StateGraph(ShoppingState)
    graph.add_node("plan", plan_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_node("critique", critique_node)
    graph.add_node("format", format_node)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "critique")
    graph.add_conditional_edges("critique", critique_router_to_format)
    graph.add_edge("format", END)
    return graph.compile(checkpointer=checkpointer)


def build_human_in_loop_graph(checkpointer: MemorySaver) -> object:
    """
    Task 4 + 5:
      - interrupt_before="human_review" to request human approval
      - persistence via MemorySaver
    """
    graph = StateGraph(ShoppingState)
    graph.add_node("plan", plan_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_node("critique", critique_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("format", format_node)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "critique")
    graph.add_conditional_edges("critique", critique_router)

    graph.add_conditional_edges("human_review", human_review_router)
    graph.add_edge("format", END)

    # Pause right before the "human_review" node.
    return graph.compile(checkpointer=checkpointer, interrupt_before=["human_review"])


def default_initial_state(
    *,
    request: str,
    product_a: str,
    product_b: str,
    quality_threshold: float = 0.8,
    max_retries: int = 3,
) -> ShoppingState:
    return {
        "request": request,
        "product_a": product_a,
        "product_b": product_b,
        "plan": [],
        "retrieved": {},
        "draft": "",
        "quality_score": 0.0,
        "retries": 0,
        "max_retries": max_retries,
        "quality_threshold": quality_threshold,
        "loop_passes": 0,
        "human_approved": None,
        "human_notes": None,
        "formatted": "",
        "trace": [],
    }


def get_default_checkpointer() -> MemorySaver:
    return MemorySaver()


if __name__ == "__main__":
    # Quick smoke test for the linear graph.
    graph, _ = build_linear_graph()
    init = default_initial_state(
        request="compare",
        product_a="Wireless Mouse",
        product_b="Mechanical Keyboard",
    )
    cfg = {"configurable": {"thread_id": "cli-linear"}}
    out = graph.invoke(init, cfg)
    print(out.get("formatted", "")[:400])
    print("---")
    print("trace passes:", len(out.get("trace") or []))

