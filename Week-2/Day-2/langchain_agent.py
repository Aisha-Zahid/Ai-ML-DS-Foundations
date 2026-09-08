"""
Week 2 Day 2 — LangChain tool-calling agent (Groq).

Helpers used by agent_langchain.ipynb:
  tools, LCEL chain, AgentExecutor, message history, structured output.
"""

from __future__ import annotations

import ast
import csv
import json
import operator
import os
import random
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)
# Fall back to Day-1 key if Day-2 .env has no key yet
if not os.getenv("GROQ_API_KEY"):
    load_dotenv(BASE_DIR.parent / "Day-1" / ".env", override=True)

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
PRODUCTS_CSV = BASE_DIR / "data" / "products.csv"

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


def get_llm(temperature: float = 0) -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to Week-2/Day-2/.env")
    return ChatGroq(model=MODEL, temperature=temperature, api_key=api_key)


# ---------------------------------------------------------------------------
# Tools — docstrings become the tool descriptions sent to the model
# ---------------------------------------------------------------------------


@tool
def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression such as '79.5 - 18.99' or '(49.99+39.95)/2'.
    Use this for price differences, totals, and other math. Do not invent numbers."""
    try:
        value = _safe_eval(ast.parse(expression, mode="eval"))
        return json.dumps({"expression": expression, "result": value})
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc), "expression": expression})


@tool
def get_weather(city: str) -> str:
    """Look up stub weather for one city. Known cities: Karachi, Lahore, Islamabad, London, Tokyo.
    Returns temperature in Celsius and a short condition. Call once per city."""
    weather = {
        "karachi": {"temp_c": 32, "condition": "humid"},
        "lahore": {"temp_c": 28, "condition": "clear"},
        "islamabad": {"temp_c": 24, "condition": "cloudy"},
        "london": {"temp_c": 14, "condition": "rain"},
        "tokyo": {"temp_c": 22, "condition": "clear"},
    }
    key = city.strip().lower()
    if key not in weather:
        return json.dumps({"error": f"Unknown city '{city}'", "known_cities": sorted(weather)})
    return json.dumps({"city": city.strip(), **weather[key]})


@tool
def lookup_product(query: str) -> str:
    """Search the local products.csv catalog by product name or product_id (e.g. 'Wireless Mouse' or 'P001').
    Returns matching rows with price_usd and stock. Use this before comparing or recommending products."""
    q = query.strip().lower()
    if not PRODUCTS_CSV.exists():
        return json.dumps({"error": f"Catalog missing: {PRODUCTS_CSV}"})
    matches = []
    with PRODUCTS_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            blob = f"{row['product_id']} {row['name']} {row['category']}".lower()
            if q in blob or any(part and part in blob for part in q.split()):
                matches.append(row)
    if not matches:
        return json.dumps({"query": query, "matches": [], "note": "No products found"})
    return json.dumps({"query": query, "matches": matches[:8]}, indent=2)


@tool
def flaky_divide(a: float, b: float) -> str:
    """Divide a by b. This tool is intentionally unreliable for error-handling demos:
    about half the time it raises a ZeroDivisionError or RuntimeError even when b != 0.
    Prefer calculator for normal math; use this only when asked to test flaky_divide."""
    # Force real failures for the assignment demo
    roll = random.random()
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    if roll < 0.5:
        raise RuntimeError("Simulated tool failure inside flaky_divide")
    return json.dumps({"a": a, "b": b, "result": a / b})


TOOLS = [calculator, get_weather, lookup_product, flaky_divide]


# ---------------------------------------------------------------------------
# Structured final answer (Task 5)
# ---------------------------------------------------------------------------


class Recommendation(BaseModel):
    """Structured recommendation the agent should produce for shopping advice."""

    recommended_product: str = Field(description="Name of the recommended product")
    price_usd: float = Field(description="Price in USD")
    compared_to: Optional[str] = Field(
        default=None, description="Other product considered, if any"
    )
    reason: str = Field(description="Short reason, especially for a budget-conscious client")
    in_stock: bool = Field(description="Whether the recommended product is in stock")


# ---------------------------------------------------------------------------
# LCEL basic chain (Task 1)
# ---------------------------------------------------------------------------


def build_lcel_chain():
    """prompt | llm | parser — LCEL pipe composes Runnables left to right."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a concise assistant. Reply in 1-2 sentences."),
            ("human", "{question}"),
        ]
    )
    llm = get_llm()
    return prompt | llm | StrOutputParser()


# ---------------------------------------------------------------------------
# Agent + memory (Tasks 3–4)
# ---------------------------------------------------------------------------

SYSTEM = """You are a helpful shopping and tools assistant.
Use tools when needed: lookup_product for catalog prices, calculator for math,
get_weather for weather, flaky_divide only if the user asks for that tool.
If a tool returns an error, explain it and retry another approach when possible.
Keep answers grounded in tool results."""

_STORE: dict[str, InMemoryChatMessageHistory] = {}


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in _STORE:
        _STORE[session_id] = InMemoryChatMessageHistory()
    return _STORE[session_id]


def clear_session(session_id: str) -> None:
    _STORE.pop(session_id, None)


def build_agent_executor(*, verbose: bool = True, max_iterations: int = 8) -> AgentExecutor:
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )
    agent = create_tool_calling_agent(llm, TOOLS, prompt)
    return AgentExecutor(
        agent=agent,
        tools=TOOLS,
        verbose=verbose,
        max_iterations=max_iterations,
        handle_tool_error=True,
        return_intermediate_steps=True,
    )


def build_agent_with_memory(*, verbose: bool = True) -> RunnableWithMessageHistory:
    """AgentExecutor wrapped so chat_history is loaded/saved per session_id."""
    executor = build_agent_executor(verbose=verbose)
    return RunnableWithMessageHistory(
        executor,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )


def recommend_structured(user_request: str) -> Recommendation:
    """Force a Recommendation object via with_structured_output (after tools if needed)."""
    llm = get_llm()
    # First let the tool agent gather facts, then structure the final answer.
    executor = build_agent_executor(verbose=False)
    raw = executor.invoke({"input": user_request, "chat_history": []})
    answer_text = raw.get("output", "")
    structured_llm = llm.with_structured_output(Recommendation)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Convert the assistant answer into the Recommendation schema. "
                "Use only facts present in the text.",
            ),
            ("human", "User ask: {ask}\n\nAssistant answer:\n{answer}"),
        ]
    )
    chain = prompt | structured_llm
    return chain.invoke({"ask": user_request, "answer": answer_text})


def concept_map() -> dict[str, str]:
    return {
        "LLM wrapper (ChatGroq)": "Day 1: groq.Groq() + chat.completions.create",
        "Tool (@tool)": "Day 1: TOOLS JSON schemas + execute_tool()",
        "AgentExecutor": "Day 1: while-loop that appends tool results until final text",
        "Memory (message history)": "Day 1: messages list you managed by hand",
        "agent_scratchpad": "Day 1: intermediate tool_calls / observations in the loop",
    }


if __name__ == "__main__":
    chain = build_lcel_chain()
    print("LCEL:", chain.invoke({"question": "In one sentence, what is an AI agent?"}))

    agent = build_agent_executor(verbose=True)
    result = agent.invoke(
        {
            "input": (
                "Look up Wireless Mouse and Mechanical Keyboard prices, "
                "compute the difference with calculator, and say which is cheaper."
            ),
            "chat_history": [],
        }
    )
    print("\nFINAL:", result["output"])
