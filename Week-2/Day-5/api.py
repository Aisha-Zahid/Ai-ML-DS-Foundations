"""
Week 2 Day 5 — FastAPI wrapper for the Client Inquiry Desk.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent_system import build_graph, log_event, run_inquiry

app = FastAPI(
    title="Web3Geeks Client Inquiry Desk",
    description="Week 2 Day 5 capstone API",
    version="1.0.0",
)

# One graph instance so thread_id approval works across requests
GRAPH, _ = build_graph()

api_logger = logging.getLogger("inquiry_api")
if not api_logger.handlers:
    from pathlib import Path

    log_path = Path(__file__).resolve().parent / "logs" / "api.jsonl"
    log_path.parent.mkdir(exist_ok=True)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    api_logger.setLevel(logging.INFO)
    api_logger.addHandler(fh)


class InquireRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Client message")
    client_name: str = "api-client"
    auto_approve: bool = False


class ApproveRequest(BaseModel):
    thread_id: str
    approve: bool = True
    notes: str = ""


class InquireResponse(BaseModel):
    request_id: str
    thread_id: str
    status: str
    intent: Optional[str] = None
    proposed_action: Optional[str] = None
    needs_approval: bool = False
    reply: str = ""
    error: str = ""
    retrieved: dict[str, Any] = Field(default_factory=dict)
    quality_score: Optional[float] = None
    latency_ms: Optional[float] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    tool_calls: list = Field(default_factory=list)
    action_result: str = ""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/inquire", response_model=InquireResponse)
def inquire(body: InquireRequest) -> InquireResponse:
    t0 = time.time()
    log_event(
        "api_inquire_start",
        client_name=body.client_name,
        message_len=len(body.message),
        auto_approve=body.auto_approve,
    )
    try:
        result = run_inquiry(
            body.message,
            client_name=body.client_name,
            auto_approve=body.auto_approve,
            graph=GRAPH,
        )
    except Exception as exc:  # noqa: BLE001
        log_event("api_inquire_error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    log_event(
        "api_inquire_done",
        request_id=result.get("request_id"),
        status=result.get("status"),
        latency_ms=(time.time() - t0) * 1000,
        tokens_in=result.get("tokens_in"),
        tokens_out=result.get("tokens_out"),
    )
    return InquireResponse(**result)


@app.post("/approve", response_model=InquireResponse)
def approve(body: ApproveRequest) -> InquireResponse:
    log_event(
        "api_approve_start",
        thread_id=body.thread_id,
        approve=body.approve,
    )
    try:
        result = run_inquiry(
            message="",
            thread_id=body.thread_id,
            approve=body.approve,
            notes=body.notes,
            graph=GRAPH,
        )
    except Exception as exc:  # noqa: BLE001
        log_event("api_approve_error", error=str(exc), thread_id=body.thread_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    log_event(
        "api_approve_done",
        thread_id=body.thread_id,
        status=result.get("status"),
    )
    return InquireResponse(**result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
