# Week 4 Day 1 — Voice Agent Foundations & Conversation Design

Design day for the **RealEstate Hub** UrduLish voice agent: architecture, flows, persona, TTS choice, and system prompt. No production code yet — that starts Day 2+.

## Deliverables

| Task | Path |
|------|------|
| Architecture + diagram | `docs/01_architecture.md` |
| Conversation flows | `docs/02_conversation_flows.md` |
| UrduLish persona | `docs/03_urdulish_persona.md` |
| Fish Audio evaluation | `docs/04_fish_audio_evaluation.md` |
| System prompt design notes | `docs/05_system_prompt_design.md` |
| Production system prompt | `prompts/realestate_voice_agent_system.txt` |
| Day summary | `docs/day1_summary.md` |

## How to read

1. Architecture → understand the full call stack  
2. Flows → how a sales call should move  
3. Persona → how it should *sound*  
4. Fish Audio eval → why we pick Fish for TTS  
5. System prompt → the contract the LLM must follow  

## Suggested stack (locked for later days)

| Layer | Choice |
|-------|--------|
| STT | Deepgram Nova (Whisper fallback) |
| LLM + tools | GPT / Claude / Gemini + **LangGraph** |
| RAG | ChromaDB / FAISS + structured SQL |
| TTS | **Fish Audio** (primary) |
| Workflows | n8n + LangGraph |
| Calendar / Email | Google Calendar + Gmail/Resend |
| Backend | FastAPI |
| Deploy | Docker + Railway/Render |

## Next (Day 2)

Build the property knowledge base and RAG pipeline so the agent never invents prices or availability.
