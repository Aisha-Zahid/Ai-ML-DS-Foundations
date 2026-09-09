# Week 2 Day 3 Write-up — LangGraph vs Raw Loops

## 1) LangGraph core building blocks

- **StateGraph**: defines a directed graph where each node reads/writes a shared State object.
- **Nodes**: Python functions that take the current State and return partial updates.
- **Edges**: transitions between nodes (including conditional edges that choose the next node).
- **Shared State**: a schema (TypedDict/Pydantic) that keeps everything the workflow needs in one place.

## 2) Why cycles feel natural in LangGraph

AgentExecutor loops are linear: you typically keep a single loop that repeatedly calls the model until “done.” Self-correction with multiple branches (critique → generate, then human approval → either finish or revise) becomes messy and harder to control. LangGraph makes those transitions explicit via edges/routers, so you can reason about control flow and state changes directly.

## 3) Human-in-the-loop interrupts

LangGraph can pause execution before a risky node using `interrupt_before`. In this project, the graph pauses before `human_review` (right before final formatting) so you can approve or reject the draft. After you update state (e.g. `human_approved=True/False`), you resume the graph without re-running earlier nodes.

**When HITL is needed:** purchases, emails, account changes, or any irreversible/external side effect.  
**When full autonomy is fine:** read-only lookups, drafting, ranking, and other reversible/internal steps.

## 4) Persistence & debugging

We use `MemorySaver` as a checkpointer so graph state persists across runs/sessions. You can resume a paused thread and also inspect state history (`get_state_history`) to “time travel” through what happened during a run.

## 5) When to use LangChain AgentExecutor vs LangGraph

Use **LangChain AgentExecutor** when you want a quick agent loop with tool calling and minimal control-flow complexity. Use **LangGraph** when workflows need explicit state transitions, conditional routing, loops, interrupts, and reliable persistence/debugging across long multi-step tasks.
