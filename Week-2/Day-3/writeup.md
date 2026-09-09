# Week 2 Day 3 Write-up — LangGraph

## 1) LangGraph building blocks

- **StateGraph**: a graph where each step reads and updates shared state
- **Nodes**: functions that take state and return updates
- **Edges**: transitions between nodes
- **Conditional edges**: a router picks the next node based on state
- **Shared State**: TypedDict/Pydantic fields kept across the whole run

## 2) Why loops are easier in LangGraph

In AgentExecutor, control flow is mostly one big loop. Adding a critique step that sometimes goes back to generate, and sometimes waits for human approval, gets messy fast. In LangGraph those paths are just edges, so the loop is clear and easier to debug.

## 3) Human-in-the-loop

The graph pauses before `human_review` with `interrupt_before`. After setting `human_approved` to true or false, the run continues from that checkpoint.

HITL makes sense for risky actions (purchase, email, account changes). Full autonomy is fine for read-only work like lookups and drafting.

## 4) Persistence & debugging

`MemorySaver` stores state by `thread_id`, so a paused run can be resumed. `get_state_history` shows earlier snapshots for debugging.

## 5) AgentExecutor vs LangGraph

AgentExecutor is enough for simple tool-calling agents. LangGraph fits better when the workflow needs branching, retries, interrupts, and saved state.
