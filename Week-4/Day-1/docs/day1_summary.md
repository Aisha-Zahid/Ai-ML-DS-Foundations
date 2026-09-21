# Week 4 Day 1 — Summary

## Done today

1. **Architecture** — telephony → STT → LangGraph (memory, RAG, SQL, tools) → Fish TTS → n8n/CRM (`docs/01_architecture.md`).  
2. **Flows** — buyer, rental, commercial, investment, returning, reschedule, cancel (`docs/02_conversation_flows.md`).  
3. **Persona** — Ali @ RealEstate Hub, UrduLish phrase bank (`docs/03_urdulish_persona.md`).  
4. **TTS choice** — Fish Audio primary vs ElevenLabs optional (`docs/04_fish_audio_evaluation.md`).  
5. **System prompt** — production prompt + design notes (`prompts/realestate_voice_agent_system.txt`).

## Decisions locked

| Decision | Choice |
|----------|--------|
| TTS | Fish Audio |
| STT | Deepgram (Whisper fallback) |
| Agent | LangGraph |
| Language | UrduLish |
| Booking truth | Calendar free/busy + CRM log |

## Next (Day 2)

Property datasets + RAG pipeline + structured vs semantic retrieval + recommendation engine + 20-question hallucination eval.
