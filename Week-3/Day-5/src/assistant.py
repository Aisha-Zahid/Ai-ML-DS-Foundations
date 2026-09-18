"""Hardened assistant wrapper over Day-4 LangGraph."""

from __future__ import annotations

import concurrent.futures
import importlib.util
import sys
import types
from typing import Any

from .abuse import AbuseGuard
from .config import DAY4, TOOL_TIMEOUT_SEC
from .logging_util import Timer, log_event

_CACHE: dict[str, Any] = {}
_GUARD = AbuseGuard()
_STORE: dict[str, list[dict]] = {}

PREDICTION_DISCLAIMER = (
    "Predicted probability, not a certainty — treat this as a model tip from "
    "historical form features, not a guarantee."
)


def _load_day4():
    if "day4" in _CACHE:
        return _CACHE["day4"]

    pkg_name = "day4src"
    src_dir = DAY4 / "src"
    if pkg_name not in sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [str(src_dir)]
        sys.modules[pkg_name] = pkg

    def _sub(mod_name: str):
        full = f"{pkg_name}.{mod_name}"
        if full in sys.modules:
            return sys.modules[full]
        path = src_dir / f"{mod_name}.py"
        spec = importlib.util.spec_from_file_location(
            full,
            path,
            submodule_search_locations=[str(src_dir)],
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules[full] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    # Load dependency order for relative imports inside day4src
    for name in (
        "config",
        "aliases",
        "router",
        "fixtures",
        "services",
        "nodes",
        "graph",
    ):
        _sub(name)

    bundle = {
        "run_query": sys.modules[f"{pkg_name}.graph"].run_query,
        "classify_intent": sys.modules[f"{pkg_name}.router"].classify_intent,
        "disclaimer": getattr(
            sys.modules[f"{pkg_name}.nodes"],
            "PREDICTION_DISCLAIMER",
            PREDICTION_DISCLAIMER,
        ),
    }
    _CACHE["day4"] = bundle
    return bundle


def _ensure_disclaimer(text: str, intent: str, disclaimer: str) -> str:
    if not intent.startswith("prediction"):
        return text
    if "predicted probability, not a certainty" in (text or "").lower():
        return text
    if not text:
        return disclaimer
    return f"{text.rstrip()} {disclaimer}"


def _prediction_meta(state: dict, disclaimer: str) -> dict[str, Any] | None:
    tool = state.get("tool_name") or ""
    result = state.get("tool_result") or {}
    if tool == "predict_match_winner" and result:
        return {
            "type": "match_winner",
            "winner": result.get("winner"),
            "home_team": result.get("home_team"),
            "away_team": result.get("away_team"),
            "match_date": result.get("match_date"),
            "home_win_probability": result.get("home_win_probability"),
            "away_win_probability": result.get("away_win_probability"),
            "drivers": result.get("drivers"),
            "disclaimer": disclaimer,
        }
    if tool == "predict_top_player" and result:
        return {
            "type": "top_player",
            "match_date": result.get("match_date"),
            "players": (result.get("players") or [])[:5],
            "disclaimer": disclaimer,
        }
    return None


def _run_with_timeout(run_query, query: str, history: list | None, timeout: float) -> dict:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(run_query, query, history)
        try:
            return fut.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return {
                "intent": "error",
                "route": "timeout",
                "tool_name": "",
                "tool_result": {},
                "tool_error": f"Tool/graph timed out after {timeout:.0f}s",
                "final_response": (
                    f"That AFL request took too long (>{timeout:.0f}s). "
                    "Try a simpler lookup or a named fixture date."
                ),
                "trace": [f"[timeout] {timeout}s"],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "intent": "error",
                "route": "error",
                "tool_name": "",
                "tool_result": {},
                "tool_error": str(exc),
                "final_response": f"Something went wrong handling that AFL request: {exc}",
                "trace": [f"[error] {exc}"],
            }


def chat(
    message: str,
    conversation_id: str = "default",
    *,
    timeout_sec: float | None = None,
) -> dict[str, Any]:
    """
    Chat entrypoint: abuse check → Day-4 graph (timed) → disclaimer → log.
    """
    timer = Timer()
    cid = conversation_id or "default"
    history = list(_STORE.get(cid) or [])
    day4 = _load_day4()
    disclaimer = day4["disclaimer"]

    pre = _GUARD.check(cid, message)
    if pre.blocked and pre.reason in {"rate_limit", "prompt_injection"}:
        out = {
            "conversation_id": cid,
            "response": pre.response,
            "intent": "off_topic" if pre.reason == "prompt_injection" else "rate_limit",
            "route": "refuse",
            "tool_name": None,
            "prediction": None,
            "latency_ms": timer.ms(),
            "token_usage": None,
            "blocked_reason": pre.reason,
            "trace": [f"[abuse] {pre.reason}"],
        }
        log_event(
            {
                "conversation_id": cid,
                "query": message,
                "intent": out["intent"],
                "tools_called": None,
                "latency_ms": out["latency_ms"],
                "token_usage": None,
                "blocked_reason": pre.reason,
            }
        )
        return out

    # Only prior *user* turns for entity resolve (assistant text can confuse the router)
    user_hist = [h for h in history if isinstance(h, dict) and h.get("role") == "user"]
    state = _run_with_timeout(
        day4["run_query"], message, user_hist, timeout_sec or TOOL_TIMEOUT_SEC
    )
    intent = state.get("intent") or day4["classify_intent"](message)
    route = state.get("route") or ""

    post = _GUARD.check(
        cid, message, is_offtopic_route=(route == "refuse"), count_hit=False
    )
    if post.blocked and post.reason == "offtopic_probe":
        response = post.response
        intent = "off_topic"
        route = "refuse"
        tool_name = None
        pred = None
        trace = list(state.get("trace") or []) + [f"[abuse] {post.reason}"]
        tool_error = ""
    else:
        response = _ensure_disclaimer(state.get("final_response") or "", intent, disclaimer)
        tool_name = state.get("tool_name")
        pred = _prediction_meta(state, disclaimer)
        trace = state.get("trace") or []
        tool_error = state.get("tool_error") or ""

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response})
    _STORE[cid] = history[-16:]

    latency = timer.ms()
    token_usage = {
        "approx_prompt_tokens": max(1, len(message.split())),
        "approx_completion_tokens": max(1, len((response or "").split())),
        "note": "Heuristic word counts; Day-4 router is rule-based (0 LLM tokens).",
    }

    result = {
        "conversation_id": cid,
        "response": response,
        "intent": intent,
        "route": route,
        "tool_name": tool_name,
        "teams": state.get("teams") or [],
        "prediction": pred,
        "latency_ms": latency,
        "token_usage": token_usage,
        "tool_error": tool_error,
        "trace": trace,
        "blocked_reason": None,
    }
    log_event(
        {
            "conversation_id": cid,
            "query": message,
            "intent": intent,
            "tools_called": tool_name,
            "latency_ms": latency,
            "token_usage": token_usage,
            "route": route,
            "tool_error": tool_error or None,
        }
    )
    return result


def reset_conversation(conversation_id: str) -> None:
    _STORE.pop(conversation_id, None)
