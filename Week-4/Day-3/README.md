# Week 4 Day 3 — Voice Agent & Natural Conversation

UrduLish voice loop for RealEstate Hub: STT → agent (Day-2 KB + memory) → TTS, with fillers, barge-in, objections, and human eval.

## Setup

```powershell
cd Week-4/Day-3
pip install -r requirements.txt
# Day-2 KB must be built once:
cd ..\Day-2
python scripts/seed_kb.py
python scripts/build_kb.py
cd ..\Day-3
```

Optional live voice (`.env`):

```
VOICE_MODE=live
DEEPGRAM_API_KEY=...
FISH_API_KEY=...
FISH_REFERENCE_ID=...
```

Default is **mock** STT/TTS (classroom-friendly, still measures streaming + barge-in).

## Run

```powershell
python app_cli.py
python app_cli.py -m "Budget 3 crore hai, Karachi"
python scripts/demo_conversation.py
python scripts/evaluate_latency.py
python scripts/human_eval_score.py
jupyter notebook voice_agent_day3.ipynb
```

## Deliverables

| Task | Path |
|------|------|
| Streaming pipeline | `src/pipeline.py`, `src/stt.py`, `src/tts.py` |
| Natural speech | `src/speech_behaviors.py`, `docs/natural_speech.md` |
| Context memory | `src/memory.py`, `results/memory_demo.json` |
| Objections | `src/objections.py`, `docs/objection_playbook.md` |
| Latency eval | `results/latency_eval.md` |
| Human eval | `recordings/`, `results/human_eval.md` |

## Latency target

End-to-end turn **under 2 seconds** on warm mock path (see `results/latency_eval.md`).
