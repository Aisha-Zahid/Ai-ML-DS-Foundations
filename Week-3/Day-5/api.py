"""FastAPI wrapper for the AFL LangGraph assistant."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
# Also pick up Day-4 env if present
load_dotenv(ROOT.parent / "Day-4" / ".env")

from src.assistant import chat, reset_conversation  # noqa: E402

app = FastAPI(
    title="AFL Assistant API",
    description="Domain-locked AFL chat + retrieval + prediction (LangGraph).",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    intent: Optional[str] = None
    route: Optional[str] = None
    tool_name: Optional[str] = None
    prediction: Optional[dict[str, Any]] = None
    latency_ms: Optional[float] = None
    token_usage: Optional[dict[str, Any]] = None
    blocked_reason: Optional[str] = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "afl-assistant"}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(body: ChatRequest) -> ChatResponse:
    cid = body.conversation_id or str(uuid.uuid4())
    try:
        out = chat(body.message, conversation_id=cid)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ChatResponse(
        conversation_id=out["conversation_id"],
        response=out["response"],
        intent=out.get("intent"),
        route=out.get("route"),
        tool_name=out.get("tool_name"),
        prediction=out.get("prediction"),
        latency_ms=out.get("latency_ms"),
        token_usage=out.get("token_usage"),
        blocked_reason=out.get("blocked_reason"),
    )


@app.post("/conversations/{conversation_id}/reset")
def reset(conversation_id: str) -> dict:
    reset_conversation(conversation_id)
    return {"ok": True, "conversation_id": conversation_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
