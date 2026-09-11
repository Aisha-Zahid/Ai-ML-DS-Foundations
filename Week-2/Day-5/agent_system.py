"""
Week 2 Day 5 — Web3Geeks Client Inquiry Desk (LangGraph).

Flow:
  validate -> classify -> retrieve -> draft -> quality_check
    -(loop)-> draft
    -(needs approval)-> human_checkpoint -> apply_action -> finalize
    -(no approval)-> finalize
  any hard failure -> fail_gracefully -> END

External data: products.csv + SQLite tickets.db
HITL: pause before send_quote / escalate
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional, TypedDict

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)
if not os.getenv("GROQ_API_KEY"):
    for day in ("Day-4", "Day-3", "Day-2", "Day-1"):
        load_dotenv(BASE_DIR.parent / day / ".env", override=True)
        if os.getenv("GROQ_API_KEY"):
            break

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
PRODUCTS_CSV = BASE_DIR / "data" / "products.csv"
TICKETS_DB = BASE_DIR / "data" / "tickets.db"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

INPUT_COST_PER_1M = float(os.getenv("GROQ_INPUT_COST_PER_1M", "0.05"))
OUTPUT_COST_PER_1M = float(os.getenv("GROQ_OUTPUT_COST_PER_1M", "0.10"))

logger = logging.getLogger("inquiry_desk")
if not logger.handlers:
    _fh = logging.FileHandler(LOG_DIR / "agent.jsonl", encoding="utf-8")
    _sh = logging.StreamHandler()
    logger.setLevel(logging.INFO)
    logger.addHandler(_fh)
    logger.addHandler(_sh)


def log_event(event: str, **fields: Any) -> None:
    payload = {"event": event, "ts": time.time(), **fields}
    logger.info(json.dumps(payload, ensure_ascii=False, default=str))


class InquiryState(TypedDict, total=False):
    request_id: str
    message: str
    client_name: str
    auto_approve: bool

    valid: bool
    intent: str
    products_mentioned: list
    retrieved: dict
    draft: str
    quality_score: float
    loop_passes: int
    max_loops: int

    needs_approval: bool
    proposed_action: str
    human_approved: Optional[bool]
    human_notes: str
    action_result: str

    reply: str
    status: str
    error: str

    started_at: float
    latency_ms: float
    tokens_in: int
    tokens_out: int
    estimated_cost_usd: float
    tool_calls: list
    trace: list


def init_tickets_db(db_path: Path = TICKETS_DB) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY,
                created_at REAL,
                client_name TEXT,
                message TEXT,
                intent TEXT,
                status TEXT,
                reply TEXT,
                proposed_action TEXT,
                latency_ms REAL,
                tokens_in INTEGER,
                tokens_out INTEGER,
                estimated_cost_usd REAL,
                error TEXT
            )
            """
        )
        conn.commit()


def log_ticket(state: InquiryState, db_path: Path = TICKETS_DB) -> None:
    init_tickets_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO tickets VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                state.get("request_id"),
                time.time(),
                state.get("client_name") or "",
                state.get("message") or "",
                state.get("intent") or "",
                state.get("status") or "",
                state.get("reply") or "",
                state.get("proposed_action") or "none",
                float(state.get("latency_ms") or 0),
                int(state.get("tokens_in") or 0),
                int(state.get("tokens_out") or 0),
                float(state.get("estimated_cost_usd") or 0),
                state.get("error") or "",
            ),
        )
        conn.commit()


def load_catalog(csv_path: Path = PRODUCTS_CSV) -> list[dict]:
    import csv

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


def search_catalog(query: str, catalog: list[dict] | None = None) -> list[ProductInfo]:
    catalog = catalog if catalog is not None else load_catalog()
    q = query.strip().lower()
    if not q:
        return []
    hits: list[ProductInfo] = []
    for row in catalog:
        blob = f"{row.get('product_id','')} {row.get('name','')} {row.get('category','')}".lower()
        if q == str(row.get("product_id", "")).strip().lower() or q in blob:
            hits.append(
                ProductInfo(
                    product_id=row["product_id"],
                    name=row["name"],
                    category=row["category"],
                    price_usd=float(row["price_usd"]),
                    in_stock=str(row.get("in_stock", "true")).strip().lower()
                    in {"true", "1", "yes"},
                )
            )
    return hits


def calculator(expression: str) -> float:
    allowed = re.fullmatch(r"[\d\.\+\-\*/\(\)\s]+", expression or "")
    if not allowed:
        raise ValueError("Calculator only allows basic arithmetic.")
    return float(eval(expression, {"__builtins__": {}}, {}))  # noqa: S307


def _product_to_dict(p: ProductInfo) -> dict:
    return {
        "product_id": p.product_id,
        "name": p.name,
        "category": p.category,
        "price_usd": p.price_usd,
        "in_stock": p.in_stock,
    }


KNOWN_PRODUCT_NAMES = [
    "Wireless Mouse",
    "Mechanical Keyboard",
    "USB-C Hub",
    "Budget Laptop Stand",
    "Premium Laptop Stand",
    "Noise-Cancel Headset",
    "Studio Headset",
    "Webcam HD",
    "4K Webcam",
    "Portable SSD 1TB",
]


def extract_product_mentions(text: str) -> list[str]:
    found = []
    lower = text.lower()
    for name in KNOWN_PRODUCT_NAMES:
        if name.lower() in lower:
            found.append(name)
    for pid in re.findall(r"\bP0\d{2}\b", text, flags=re.I):
        found.append(pid.upper())
    seen = set()
    out = []
    for x in found:
        key = x.lower()
        if key not in seen:
            seen.add(key)
            out.append(x)
    return out


def get_llm(temperature: float = 0.2):
    from langchain_groq import ChatGroq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY missing. Add it to Week-2/Day-5/.env")
    return ChatGroq(model=MODEL, temperature=temperature, api_key=api_key)


def _usage_from_response(resp: Any) -> tuple[int, int]:
    meta = getattr(resp, "response_metadata", None) or {}
    usage = meta.get("token_usage") or meta.get("usage") or {}
    tin = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    tout = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    return tin, tout


def estimate_cost(tokens_in: int, tokens_out: int) -> float:
    return (tokens_in / 1_000_000) * INPUT_COST_PER_1M + (
        tokens_out / 1_000_000
    ) * OUTPUT_COST_PER_1M


def _append_trace(state: InquiryState, msg: str) -> list:
    trace = list(state.get("trace") or [])
    trace.append(msg)
    return trace


def _append_tool(state: InquiryState, name: str, detail: str) -> list:
    calls = list(state.get("tool_calls") or [])
    calls.append({"tool": name, "detail": detail, "ts": time.time()})
    return calls


def validate_input(state: InquiryState) -> dict:
    msg = (state.get("message") or "").strip()
    trace = _append_trace(state, "[validate] checking message")
    if not msg:
        return {
            "valid": False,
            "status": "failed",
            "error": "Empty message. Please describe what you need (price, stock, compare, quote).",
            "trace": _append_trace({**state, "trace": trace}, "[validate] FAIL empty"),
        }
    if len(msg) < 8:
        return {
            "valid": False,
            "status": "failed",
            "error": "Message too short. Add a bit more detail (product name helps).",
            "trace": _append_trace({**state, "trace": trace}, "[validate] FAIL too_short"),
        }
    blocked = [
        "ignore previous",
        "ignore all instructions",
        "system prompt",
        "exfiltrate",
        "drop table",
    ]
    lower = msg.lower()
    if any(b in lower for b in blocked):
        return {
            "valid": False,
            "status": "refused",
            "intent": "refused",
            "error": "Request looks unsafe / off-policy. Refusing to run tools.",
            "trace": _append_trace({**state, "trace": trace}, "[validate] REFUSED"),
        }
    return {
        "valid": True,
        "error": "",
        "trace": _append_trace({**state, "trace": trace}, "[validate] OK"),
    }


def classify_intent(state: InquiryState) -> dict:
    msg = state["message"]
    mentions = extract_product_mentions(msg)
    lower = msg.lower()

    intent = "unknown"
    if any(w in lower for w in ("escalate", "manager", "complaint", "refund", "angry")):
        intent = "escalate"
    elif any(w in lower for w in ("quote", "proposal", "send me a quote", "formal quote")):
        intent = "quote"
    elif any(w in lower for w in ("compare", " vs ", "versus", "cheaper", "which should")):
        intent = "compare"
    elif any(w in lower for w in ("stock", "available", "in stock", "out of stock")):
        intent = "stock"
    elif any(w in lower for w in ("price", "cost", "how much", "$")):
        intent = "price"

    tokens_in = int(state.get("tokens_in") or 0)
    tokens_out = int(state.get("tokens_out") or 0)

    if intent == "unknown" and os.getenv("GROQ_API_KEY"):
        try:
            llm = get_llm(0)
            prompt = (
                "Classify this client message into one label only: "
                "price, stock, compare, quote, escalate, unknown.\n"
                f"Message: {msg}\n"
                "Reply with the label only."
            )
            resp = llm.invoke(prompt)
            tin, tout = _usage_from_response(resp)
            tokens_in += tin
            tokens_out += tout
            label = (resp.content or "").strip().lower().split()[0]
            label = label.strip(".,:;\"'")
            if label in {"price", "stock", "compare", "quote", "escalate", "unknown"}:
                intent = label
        except Exception as exc:  # noqa: BLE001
            log_event("classify_llm_error", error=str(exc), request_id=state.get("request_id"))

    needs_approval = intent in {"quote", "escalate"}
    proposed = "send_quote" if intent == "quote" else ("escalate" if intent == "escalate" else "none")

    trace = _append_trace(
        state,
        f"[classify] intent={intent} mentions={mentions} needs_approval={needs_approval}",
    )
    log_event(
        "classified",
        request_id=state.get("request_id"),
        intent=intent,
        mentions=mentions,
    )
    return {
        "intent": intent,
        "products_mentioned": mentions,
        "needs_approval": needs_approval,
        "proposed_action": proposed,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "estimated_cost_usd": estimate_cost(tokens_in, tokens_out),
        "trace": trace,
    }


def retrieve_catalog(state: InquiryState) -> dict:
    tool_calls = list(state.get("tool_calls") or [])
    trace = list(state.get("trace") or [])

    if "FORCE_TIMEOUT" in (state.get("message") or ""):
        tool_calls = _append_tool(state, "search_catalog", "timeout_simulated")
        return {
            "status": "failed",
            "error": "Catalog tool timed out. Try again in a moment.",
            "tool_calls": tool_calls,
            "trace": _append_trace({**state, "trace": trace}, "[retrieve] TIMEOUT"),
        }

    try:
        catalog = load_catalog()
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "failed",
            "error": f"Catalog unavailable: {exc}",
            "tool_calls": _append_tool(state, "load_catalog", str(exc)),
            "trace": _append_trace(state, f"[retrieve] catalog error {exc}"),
        }

    mentions = list(state.get("products_mentioned") or [])
    intent = state.get("intent") or "unknown"

    if intent == "compare" and len(mentions) < 2:
        if "mouse" in (state.get("message") or "").lower():
            mentions.append("Wireless Mouse")
        if "keyboard" in (state.get("message") or "").lower():
            mentions.append("Mechanical Keyboard")

    retrieved: dict[str, Any] = {"products": [], "notes": []}
    for m in mentions:
        hits = search_catalog(m, catalog)
        tool_calls.append({"tool": "search_catalog", "detail": m, "ts": time.time()})
        if not hits:
            retrieved["notes"].append(f"No catalog match for {m!r}")
        else:
            retrieved["products"].append(_product_to_dict(hits[0]))

    if intent in {"price", "stock"} and not retrieved["products"]:
        return {
            "retrieved": retrieved,
            "status": "failed",
            "error": "Could not find that product in the catalog. Check the name or product id.",
            "tool_calls": tool_calls,
            "trace": _append_trace(state, "[retrieve] miss"),
        }

    if intent == "compare" and len(retrieved["products"]) < 2:
        return {
            "retrieved": retrieved,
            "status": "failed",
            "error": "Compare needs two catalog products. Name both items clearly.",
            "tool_calls": tool_calls,
            "trace": _append_trace(state, "[retrieve] compare_incomplete"),
        }

    if len(retrieved["products"]) >= 2:
        a = retrieved["products"][0]["price_usd"]
        b = retrieved["products"][1]["price_usd"]
        try:
            gap = calculator(f"{a}-{b}")
            retrieved["price_difference_usd"] = abs(float(gap))
            tool_calls.append(
                {"tool": "calculator", "detail": f"abs({a}-{b})", "ts": time.time()}
            )
        except Exception as exc:  # noqa: BLE001
            retrieved["notes"].append(f"calculator failed: {exc}")

    trace = _append_trace(
        state, f"[retrieve] products={len(retrieved['products'])} notes={retrieved['notes']}"
    )
    log_event(
        "tool_retrieve",
        request_id=state.get("request_id"),
        n_products=len(retrieved["products"]),
    )
    return {
        "retrieved": retrieved,
        "tool_calls": tool_calls,
        "error": "",
        "trace": trace,
    }


def draft_reply(state: InquiryState) -> dict:
    intent = state.get("intent") or "unknown"
    retrieved = state.get("retrieved") or {}
    products = retrieved.get("products") or []
    msg = state.get("message") or ""
    tokens_in = int(state.get("tokens_in") or 0)
    tokens_out = int(state.get("tokens_out") or 0)

    facts = json.dumps(retrieved, ensure_ascii=False)
    prompt = (
        "You are the Web3Geeks client inquiry desk.\n"
        "Write a short helpful reply using ONLY the catalog facts below.\n"
        "Do not invent prices or stock. If facts are empty, say you need a product name.\n"
        "Keep it under 120 words. Professional tone.\n"
        f"Intent: {intent}\n"
        f"Client message: {msg}\n"
        f"Catalog facts JSON: {facts}\n"
    )

    draft = ""
    try:
        llm = get_llm(0.2)
        resp = llm.invoke(prompt)
        tin, tout = _usage_from_response(resp)
        tokens_in += tin
        tokens_out += tout
        draft = (resp.content or "").strip()
        if not draft:
            raise RuntimeError("empty model draft")
    except Exception as exc:  # noqa: BLE001
        log_event("draft_error", error=str(exc), request_id=state.get("request_id"))
        if products:
            lines = [
                f"- {p['name']}: ${p['price_usd']:.2f} "
                f"({'in stock' if p['in_stock'] else 'out of stock'})"
                for p in products
            ]
            draft = "Here is what I found in our catalog:\n" + "\n".join(lines)
            if "price_difference_usd" in retrieved:
                draft += f"\nPrice difference: ${retrieved['price_difference_usd']:.2f}."
        else:
            draft = (
                "Could not build a catalog reply yet. "
                f"(model/tool issue: {exc})"
            )

    passes = int(state.get("loop_passes") or 0)
    if passes == 0 and products and "$" not in draft:
        p0 = products[0]
        draft = (
            draft
            + f"\n\nCatalog check: {p0['name']} is ${p0['price_usd']:.2f} "
            + ("(in stock)." if p0["in_stock"] else "(out of stock).")
        )

    trace = _append_trace(state, f"[draft] len={len(draft)} pass={passes}")
    return {
        "draft": draft,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "estimated_cost_usd": estimate_cost(tokens_in, tokens_out),
        "trace": trace,
    }


def quality_check(state: InquiryState) -> dict:
    draft = state.get("draft") or ""
    products = (state.get("retrieved") or {}).get("products") or []
    intent = state.get("intent") or "unknown"

    score = 0.2
    if len(draft) >= 40:
        score += 0.2
    if products:
        if any(p["name"] in draft for p in products):
            score += 0.3
        if any(
            f"${p['price_usd']:.2f}" in draft or str(p["price_usd"]) in draft for p in products
        ):
            score += 0.3
    elif intent in {"escalate", "quote", "unknown"}:
        if len(draft) >= 40:
            score = 0.85

    score = min(1.0, score)
    passes = int(state.get("loop_passes") or 0) + 1
    trace = _append_trace(state, f"[quality] score={score:.2f} pass={passes}")
    return {"quality_score": score, "loop_passes": passes, "trace": trace}


def quality_router(
    state: InquiryState,
) -> Literal["draft_reply", "human_checkpoint", "finalize", "fail_gracefully"]:
    if state.get("status") in {"failed", "refused"} and state.get("error"):
        return "fail_gracefully"
    score = float(state.get("quality_score") or 0)
    passes = int(state.get("loop_passes") or 0)
    max_loops = int(state.get("max_loops") or 2)
    if score < 0.7 and passes < max_loops:
        return "draft_reply"
    if state.get("needs_approval"):
        return "human_checkpoint"
    return "finalize"


def human_checkpoint(state: InquiryState) -> dict:
    auto = bool(state.get("auto_approve"))
    approved = state.get("human_approved")
    if auto and approved is None:
        approved = True

    action = state.get("proposed_action") or "none"
    notes = state.get("human_notes") or ""
    if approved is True:
        trace = _append_trace(state, f"[human] APPROVED action={action} notes={notes!r}")
        return {"human_approved": True, "status": "ok", "trace": trace}
    if approved is False:
        trace = _append_trace(state, f"[human] REJECTED action={action}")
        return {
            "human_approved": False,
            "status": "failed",
            "error": "Human rejected the proposed action. No quote/escalation sent.",
            "trace": trace,
        }
    trace = _append_trace(state, f"[human] WAITING approval for {action}")
    return {"status": "needs_approval", "trace": trace}


def human_router(
    state: InquiryState,
) -> Literal["apply_action", "draft_reply", "fail_gracefully", "finalize"]:
    if state.get("human_approved") is True:
        return "apply_action"
    if state.get("human_approved") is False:
        return "fail_gracefully"
    return "finalize"


def apply_action(state: InquiryState) -> dict:
    action = state.get("proposed_action") or "none"
    rid = state.get("request_id")
    if action == "send_quote":
        result = f"QUOTE_SENT ticket={rid} (email send not wired yet)"
    elif action == "escalate":
        result = f"ESCALATED ticket={rid} to human support queue"
    else:
        result = "NO_ACTION"
    tool_calls = _append_tool(state, "log_ticket", action)
    trace = _append_trace(state, f"[action] {result}")
    log_event("action_applied", request_id=rid, action=action, result=result)
    return {"action_result": result, "tool_calls": tool_calls, "status": "ok", "trace": trace}


def finalize(state: InquiryState) -> dict:
    started = float(state.get("started_at") or time.time())
    latency_ms = (time.time() - started) * 1000.0
    draft = state.get("draft") or ""
    status = state.get("status") or "ok"

    if status == "needs_approval":
        reply = (
            "Approval required before I can continue.\n\n"
            f"Proposed action: {state.get('proposed_action')}\n\n"
            f"Draft reply:\n{draft}"
        )
    else:
        reply = draft
        if state.get("action_result"):
            reply = reply + f"\n\n[{state['action_result']}]"

    tokens_in = int(state.get("tokens_in") or 0)
    tokens_out = int(state.get("tokens_out") or 0)
    cost = estimate_cost(tokens_in, tokens_out)

    if state.get("status") == "needs_approval":
        final_status = "needs_approval"
    elif state.get("error") and state.get("status") in {"failed", "refused"}:
        final_status = state["status"]
        reply = state.get("error") or reply
    else:
        final_status = "ok" if not state.get("error") else (state.get("status") or "ok")

    out = {
        "reply": reply,
        "latency_ms": latency_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "estimated_cost_usd": cost,
        "status": final_status,
        "trace": _append_trace(state, f"[finalize] status={final_status} latency_ms={latency_ms:.1f}"),
    }
    merged = {**state, **out}
    try:
        log_ticket(merged)
        out["tool_calls"] = _append_tool(state, "log_ticket", "sqlite_write")
    except Exception as exc:  # noqa: BLE001
        log_event("ticket_log_error", error=str(exc))

    log_event(
        "finalize",
        request_id=state.get("request_id"),
        status=out["status"],
        latency_ms=latency_ms,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        estimated_cost_usd=cost,
    )
    return out


def fail_gracefully(state: InquiryState) -> dict:
    started = float(state.get("started_at") or time.time())
    latency_ms = (time.time() - started) * 1000.0
    err = state.get("error") or "Unknown failure"
    status = state.get("status") or "failed"
    out = {
        "reply": err,
        "status": status,
        "latency_ms": latency_ms,
        "trace": _append_trace(state, f"[fail] {err}"),
    }
    merged = {**state, **out}
    try:
        log_ticket(merged)
    except Exception as exc:  # noqa: BLE001
        log_event("ticket_log_error", error=str(exc))
    log_event(
        "failed",
        request_id=state.get("request_id"),
        status=status,
        error=err,
        latency_ms=latency_ms,
    )
    return out


def after_validate(state: InquiryState) -> Literal["classify_intent", "fail_gracefully"]:
    if state.get("valid"):
        return "classify_intent"
    return "fail_gracefully"


def after_retrieve(state: InquiryState) -> Literal["draft_reply", "fail_gracefully"]:
    if state.get("status") == "failed" and state.get("error"):
        return "fail_gracefully"
    return "draft_reply"


def build_graph(checkpointer: MemorySaver | None = None):
    checkpointer = checkpointer or MemorySaver()
    g = StateGraph(InquiryState)

    g.add_node("validate_input", validate_input)
    g.add_node("classify_intent", classify_intent)
    g.add_node("retrieve_catalog", retrieve_catalog)
    g.add_node("draft_reply", draft_reply)
    g.add_node("quality_check", quality_check)
    g.add_node("human_checkpoint", human_checkpoint)
    g.add_node("apply_action", apply_action)
    g.add_node("finalize", finalize)
    g.add_node("fail_gracefully", fail_gracefully)

    g.add_edge(START, "validate_input")
    g.add_conditional_edges("validate_input", after_validate)
    g.add_edge("classify_intent", "retrieve_catalog")
    g.add_conditional_edges("retrieve_catalog", after_retrieve)
    g.add_edge("draft_reply", "quality_check")
    g.add_conditional_edges("quality_check", quality_router)
    g.add_conditional_edges("human_checkpoint", human_router)
    g.add_edge("apply_action", "finalize")
    g.add_edge("finalize", END)
    g.add_edge("fail_gracefully", END)

    return g.compile(checkpointer=checkpointer, interrupt_before=["human_checkpoint"]), checkpointer


def initial_state(
    message: str,
    *,
    client_name: str = "client",
    auto_approve: bool = False,
    request_id: str | None = None,
    max_loops: int = 2,
) -> InquiryState:
    return {
        "request_id": request_id or str(uuid.uuid4()),
        "message": message,
        "client_name": client_name,
        "auto_approve": auto_approve,
        "valid": False,
        "intent": "",
        "products_mentioned": [],
        "retrieved": {},
        "draft": "",
        "quality_score": 0.0,
        "loop_passes": 0,
        "max_loops": max_loops,
        "needs_approval": False,
        "proposed_action": "none",
        "human_approved": True if auto_approve else None,
        "human_notes": "",
        "action_result": "",
        "reply": "",
        "status": "",
        "error": "",
        "started_at": time.time(),
        "latency_ms": 0.0,
        "tokens_in": 0,
        "tokens_out": 0,
        "estimated_cost_usd": 0.0,
        "tool_calls": [],
        "trace": [],
    }


def _run_auto(state: InquiryState) -> InquiryState:
    state = {**state, **validate_input(state)}
    if not state.get("valid"):
        return {**state, **fail_gracefully(state)}
    state = {**state, **classify_intent(state)}
    state = {**state, **retrieve_catalog(state)}
    if state.get("status") == "failed" and state.get("error"):
        return {**state, **fail_gracefully(state)}
    for _ in range(int(state.get("max_loops") or 2)):
        state = {**state, **draft_reply(state)}
        state = {**state, **quality_check(state)}
        nxt = quality_router(state)
        if nxt != "draft_reply":
            break
    if state.get("needs_approval"):
        state = {**state, **human_checkpoint(state)}
        if state.get("human_approved") is True:
            state = {**state, **apply_action(state)}
            return {**state, **finalize(state)}
        return {**state, **fail_gracefully(state)}
    return {**state, **finalize(state)}


def _public_result(result: dict, thread_id: str) -> dict[str, Any]:
    return {
        "request_id": result.get("request_id") or thread_id,
        "thread_id": thread_id,
        "status": result.get("status") or "ok",
        "intent": result.get("intent"),
        "proposed_action": result.get("proposed_action"),
        "needs_approval": result.get("status") == "needs_approval",
        "reply": result.get("reply") or result.get("error") or "",
        "error": result.get("error") or "",
        "retrieved": result.get("retrieved") or {},
        "quality_score": result.get("quality_score"),
        "latency_ms": result.get("latency_ms"),
        "tokens_in": result.get("tokens_in"),
        "tokens_out": result.get("tokens_out"),
        "estimated_cost_usd": result.get("estimated_cost_usd"),
        "tool_calls": result.get("tool_calls") or [],
        "action_result": result.get("action_result") or "",
        "trace": result.get("trace") or [],
    }


def run_inquiry(
    message: str,
    *,
    client_name: str = "client",
    auto_approve: bool = False,
    thread_id: str | None = None,
    approve: bool | None = None,
    notes: str = "",
    graph=None,
) -> dict[str, Any]:
    init_tickets_db()
    if graph is None:
        graph, _ = build_graph()

    tid = thread_id or str(uuid.uuid4())
    cfg = {"configurable": {"thread_id": tid}}

    if approve is not None and thread_id:
        graph.update_state(
            cfg,
            {
                "human_approved": bool(approve),
                "human_notes": notes,
                "auto_approve": False,
            },
        )
        result = graph.invoke(None, cfg)
    elif auto_approve:
        state = initial_state(
            message, client_name=client_name, auto_approve=True, request_id=tid
        )
        result = _run_auto(state)
    else:
        state = initial_state(
            message, client_name=client_name, auto_approve=False, request_id=tid
        )
        result = graph.invoke(state, cfg)
        # paused before human_checkpoint
        snap = graph.get_state(cfg)
        if snap.next:
            merged = {**result, "status": "needs_approval"}
            if not merged.get("reply"):
                merged["reply"] = (
                    "Approval required before I can continue.\n\n"
                    f"Proposed action: {merged.get('proposed_action')}\n\n"
                    f"Draft reply:\n{merged.get('draft') or ''}"
                )
            result = merged

    return _public_result(result, thread_id=tid)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Web3Geeks Client Inquiry Desk")
    parser.add_argument("--message", required=True)
    parser.add_argument("--client", default="cli-user")
    parser.add_argument("--auto-approve", action="store_true")
    args = parser.parse_args()

    out = run_inquiry(args.message, client_name=args.client, auto_approve=args.auto_approve)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
