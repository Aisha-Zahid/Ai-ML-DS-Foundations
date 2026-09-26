# Human evaluation (Day 3 Task 5)

## Rubric (1–5)

| Score | Meaning |
|-------|---------|
| 5 | Feels like a strong Pakistani sales exec |
| 4 | Natural with minor stiffness |
| 3 | Acceptable demo quality |
| 2 | Robotic / confusing |
| 1 | Broken |

Dimensions: **naturalness, persuasiveness, fluency, latency, conversation_flow**.

## Recordings

Three scripted calls in `recordings/` with embedded reviewer scores. Aggregate with:

```powershell
python scripts/human_eval_score.py
```

Output: `results/human_eval.md`.

## Live listening (optional)

1. Run `python scripts/demo_conversation.py`
2. If Fish keys set, listen to `audio_out/`
3. Update `*.scores.json` beside a recording after peer review
