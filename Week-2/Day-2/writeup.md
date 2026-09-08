# Week 2 Day 2 Write-up — Raw Python vs LangChain

## Concept map

| LangChain | Day 1 raw Python |
|-----------|------------------|
| `ChatGroq` LLM wrapper | `groq.Groq` + `chat.completions.create` |
| `@tool` + docstrings | JSON tool schemas + `execute_tool` |
| `AgentExecutor` | `while` loop with `max_iterations` |
| `chat_history` / `RunnableWithMessageHistory` | Manual `messages` list |
| `agent_scratchpad` | Intermediate tool calls you appended yourself |

## What LCEL `|` does

`prompt | llm | parser` builds a **Runnable sequence**. Each step’s output becomes the next step’s input. Under the hood LangChain wires `.invoke` / `.stream` across components so you compose a pipeline without writing nested function calls.

## Annotated multi-step trace (product compare)

Example ask: look up Wireless Mouse and Mechanical Keyboard, compute the price gap, say which is cheaper.

1. **Reason** — model decides it needs catalog data (tool plan in the verbose log).
2. **Act** — `lookup_product("Wireless Mouse")` then `lookup_product("Mechanical Keyboard")` (or one broader search).
3. **Observe** — CSV rows with `price_usd` (e.g. 18.99 vs 79.50).
4. **Act** — `calculator` with something like `79.50 - 18.99`.
5. **Observe** — numeric difference.
6. **Final** — text answer: mouse is cheaper by ~60.51.

Same Reason → Act → Observe loop as Day 1. LangChain **hides** message formatting, tool-call parsing, and scratchpad assembly inside `AgentExecutor`. Verbose mode surfaces the loop again; without it, that plumbing is opaque.

## Memory test

Three turns (“price of X” → “compare to Y” → “recommend for a budget client”) work because prior human/AI messages are re-injected via `chat_history`. Day 1 had the same idea, but you owned the list; here `RunnableWithMessageHistory` stores turns per `session_id`.

## Structured output & errors

`with_structured_output(Recommendation)` forces fields like `recommended_product`, `price_usd`, `reason`. `handle_tool_error=True` turns `flaky_divide` exceptions into tool observations so the agent can apologize or retry instead of crashing the process.

## Easier vs leaky

LangChain made registration, the agent loop, memory, and structured answers much shorter than Day 1. The “magic” shows up when versions change (`create_tool_calling_agent` APIs), when verbose logs are the only window into failures, and when wrappers obscure the exact messages sent to the model. You trade control for speed — fine for demos, worth peeling back when debugging production agents.
