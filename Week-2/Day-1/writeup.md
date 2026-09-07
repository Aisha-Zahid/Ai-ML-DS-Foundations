# Week 2 Day 1 Write-up — Agent Foundations

## What an agent is (vs chatbot vs workflow)

A **chatbot** answers turn-by-turn from text alone. A **workflow** runs fixed steps (A→B→C) with little choice. An **agent** is goal-directed: it plans, calls tools, observes results, and decides the next step — including recovering from bad results. Behavior is **agentic** when there is autonomy, tool use, multi-step planning, and self-correction.

This project uses the **Groq** API for chat completions and tool calling.

## ReAct loop

**Reason → Act → Observe → repeat** until a final text answer.

```
messages = [system, user]
while iterations < max_iterations:
    response = LLM(messages, tools)
    if response has tool_calls:
        for each call: result = execute(tool)
        append assistant turn + tool messages
        continue
    else:
        return response.text
```

Conversation **memory** is the growing `messages` list. **Working memory** is a scratchpad (tool calls + observations) used for logging and debugging.

## Tool schemas used

| Tool | Purpose | Key inputs |
|------|---------|------------|
| `calculator` | Safe arithmetic | `expression` (string) |
| `get_weather` | Stub city weather (°C) | `city` |
| `read_file` | Local text under Day-1 | `path` |

Schemas are registered as Groq/OpenAI `type: function` tools (`name`, `description`, `parameters`). Descriptions matter: the model picks tools and arguments from that text. Vague descriptions cause wrong tools or bad arguments; explicit ones (e.g. “call once per city”) improve reliability.

## Failure modes observed & mitigations

| Failure mode | What we saw / expect | Mitigation |
|--------------|----------------------|------------|
| Infinite tool loop | Model keeps calling tools | `max_iterations` hard stop |
| Hallucinated / unknown tool | Asks for email, etc. | Strict registered tool list; return clear error JSON |
| Wrong / missing arguments | Bad JSON or keys | Schema `required`; catch errors and report |
| Tool runtime error | e.g. unknown city Atlantis | Return `{"error": ...}` as tool content |
| Ambiguous user goal | Vague “do the thing…” | System prompt: admit uncertainty; don’t invent |
| Silent failure | Empty or ignored errors | Log every Reason / Act / Observe step |

Deliberate break tests: ambiguous prompt, weather for a fake city, and a task needing an undefined tool (send email). The loop surfaces tool errors or the model admits it cannot complete the request.

## When an agent is overkill

If the job is one formula, one API call, or a fixed pipeline with no branching, a script or single prompt is cheaper and easier to test. Agents earn their keep when intermediate results must change the plan.

## Why frameworks exist

Hand-rolled loops are good for learning. Frameworks like LangChain, LangGraph, and CrewAI save time on retries, memory, tracing, and multi-agent setup so you do not rebuild the same plumbing every time.
