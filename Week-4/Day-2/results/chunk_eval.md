# Chunk size evaluation

Probe queries check whether the right FAQ/brochure facts land in top-3 chunks.

| Variant | Chunk size | Hit rate |
|---------|------------|----------|
| small_400 | 400 | 100% |
| medium_800 | 800 | 100% |
| large_1200 | 1200 | 100% |

**Best for this KB:** `small_400` (100% hit rate).

Default index used by the agent: `medium_800` unless hit rate clearly favors another.
Smaller chunks help precise FAQ lines; larger chunks keep brochure context.