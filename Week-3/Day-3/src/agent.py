"""LangChain AFL chat agent with tools + session memory."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_groq import ChatGroq

from .grounding import grounding_check
from .prompts import SYSTEM_PROMPT, format_refusal_block
from .tools import clear_tool_log, get_all_tools, get_tool_log

DAY3 = Path(__file__).resolve().parents[1]
load_dotenv(DAY3 / ".env", override=True)
if not os.getenv("GROQ_API_KEY"):
    for rel in (
        DAY3.parent / "Day-2" / ".env",
        DAY3.parents[1] / "Week-2" / "Day-5" / ".env",
        DAY3.parents[1] / "Week-2" / "Day-4" / ".env",
    ):
        load_dotenv(rel, override=True)
        if os.getenv("GROQ_API_KEY"):
            break

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

_STORE: dict[str, InMemoryChatMessageHistory] = {}


def get_llm(temperature: float = 0.2) -> ChatGroq:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY missing. Add it to Week-3/Day-3/.env")
    return ChatGroq(model=MODEL, temperature=temperature, api_key=key)


def _history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in _STORE:
        _STORE[session_id] = InMemoryChatMessageHistory()
    return _STORE[session_id]


def build_agent(verbose: bool = False) -> RunnableWithMessageHistory:
    llm = get_llm()
    tools = get_all_tools()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT + "\n\n" + format_refusal_block()),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )
    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=verbose,
        handle_parsing_errors=True,
        max_iterations=6,
    )
    return RunnableWithMessageHistory(
        executor,
        _history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )


def chat(
    message: str,
    *,
    session_id: str = "default",
    agent: RunnableWithMessageHistory | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run one turn; returns answer + tool log + grounding check."""
    clear_tool_log()
    if agent is None:
        agent = build_agent(verbose=verbose)
    result = agent.invoke(
        {"input": message},
        config={"configurable": {"session_id": session_id}},
    )
    answer = result.get("output") if isinstance(result, dict) else str(result)
    tools = get_tool_log()
    ground = grounding_check(answer or "", tools)
    return {
        "answer": answer,
        "session_id": session_id,
        "tool_log": tools,
        "grounding": ground,
    }


def reset_session(session_id: str = "default") -> None:
    _STORE.pop(session_id, None)
