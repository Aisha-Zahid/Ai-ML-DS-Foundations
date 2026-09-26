# Natural speech behaviors (Day 3 Task 2)

| Behavior | Implementation |
|----------|----------------|
| Fillers | `Hmm…`, `Acha…`, `Ek second sir…` before tool-backed replies |
| Acknowledgements | `Ji bilkul`, `Samajh gaya`, `Theek hai` |
| Thinking pauses | Short sleep + thinking phrase while KB runs |
| Soft laughter | Triggered if user jokes |
| Interruptions / barge-in | `BargeInController` cancels TTS stream mid-utterance |
| Streaming | Reply emitted in ~40-char chunks (mock) or Fish byte stream (live) |

Code: `src/speech_behaviors.py`, wired in `src/agent.py` + `src/tts.py`.
