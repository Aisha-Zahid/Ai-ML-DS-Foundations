# Voice pipeline (Day 3 Task 1)

```mermaid
flowchart LR
  U[Caller audio/text] --> STT[STT Deepgram or mock]
  STT --> Mem[Call memory]
  Mem --> Agent[UrduLish agent]
  Agent --> KB[Day-2 SQL + RAG]
  Agent --> Obj[Objection handlers]
  Agent --> TTS[Fish Audio or mock stream]
  TTS --> U
  U -.->|barge-in| TTS
```

## Budget

| Stage | Target |
|-------|--------|
| STT finalize | ≤ 500 ms |
| Reason + tools | ≤ 800 ms |
| TTS time-to-first-audio | ≤ 400 ms |
| **Total** | **≤ 2000 ms** |

Mock mode simulates partial STT, tool thinking fillers, and chunked TTS. Live keys swap providers without changing the agent.
