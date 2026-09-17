"""Compile the AFL LangGraph orchestrator."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .nodes import (
    AFLState,
    after_router,
    after_validate,
    clarify_node,
    format_node,
    predict_match_node,
    predict_player_node,
    refuse_node,
    retrieve_node,
    router_node,
    validate_node,
)


_APP = None


def build_graph():
    global _APP
    if _APP is not None:
        return _APP
    g = StateGraph(AFLState)
    g.add_node("router", router_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("predict_match", predict_match_node)
    g.add_node("predict_player", predict_player_node)
    g.add_node("refuse", refuse_node)
    g.add_node("clarify", clarify_node)
    g.add_node("validate", validate_node)
    g.add_node("format", format_node)

    g.add_edge(START, "router")
    g.add_conditional_edges(
        "router",
        after_router,
        {
            "retrieve": "retrieve",
            "predict_match": "predict_match",
            "predict_player": "predict_player",
            "refuse": "refuse",
            "clarify": "clarify",
        },
    )
    g.add_edge("retrieve", "validate")
    g.add_edge("predict_match", "validate")
    g.add_edge("predict_player", "validate")
    g.add_conditional_edges("validate", after_validate)
    # clarify / refuse already set final_response; still go to format for trace consistency
    g.add_edge("clarify", "format")
    g.add_edge("refuse", "format")
    g.add_edge("format", END)
    _APP = g.compile()
    return _APP


def run_query(query: str, history: list | None = None) -> AFLState:
    app = build_graph()
    # Multi-turn: if this turn is thin, prepend prior user text for entity resolve
    effective = query
    if history:
        prior = " ".join(
            str(h.get("content") or h) for h in history if isinstance(h, (dict, str))
        )
        if prior and len(query.split()) <= 6:
            effective = f"{prior}\nUser follow-up: {query}"
    init: AFLState = {
        "user_query": effective,
        "history": history or [],
        "teams": [],
        "tool_result": {},
        "tool_error": "",
        "needs_clarification": False,
        "final_response": "",
        "trace": [],
    }
    out = app.invoke(init)
    return out  # type: ignore[return-value]
