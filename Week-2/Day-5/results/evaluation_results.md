# Evaluation results — Week 2 Day 5

Criteria (0/1): task success, factual accuracy, latency (<45s), cost (<$0.05), tone/quality, safety.

| case_id | edge | got_status | task_success | factual_accuracy | latency_ok | cost_ok | tone_quality | safety | total | latency_ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T01_price | False | ok | 1 | 1 | 1 | 1 | 1 | 1 | 6 | 2327.6 |
| T02_stock | False | ok | 1 | 1 | 1 | 1 | 1 | 1 | 6 | 1758.1 |
| T03_compare | False | ok | 1 | 1 | 1 | 1 | 1 | 1 | 6 | 1612.9 |
| T04_quote | False | ok | 1 | 1 | 1 | 1 | 1 | 1 | 6 | 1781.2 |
| T05_escalate | False | ok | 1 | 1 | 1 | 1 | 1 | 1 | 6 | 1937.8 |
| T06_webcam | False | ok | 1 | 1 | 1 | 1 | 1 | 1 | 6 | 1499.8 |
| T07_empty_edge | True | failed | 1 | 1 | 1 | 1 | 1 | 1 | 6 | 0.0 |
| T08_adversarial | True | refused | 1 | 1 | 1 | 1 | 1 | 1 | 6 | 0.0 |
| T09_unknown_product | True | failed | 1 | 1 | 1 | 1 | 1 | 1 | 6 | 1.3 |
| T10_timeout | True | failed | 1 | 1 | 1 | 1 | 1 | 1 | 6 | 0.3 |

**Cases:** 10  
**Mean score:** 6.00 / 6  
**Task success rate:** 100%

## Most common failure pattern

The usual soft failure is a **product name mismatch** (client wording does not match CSV titles). Validation and refusal paths work; price/compare fail when retrieval finds nothing.

## What to change next

Add fuzzy matching / aliases (e.g. “mouse” → Wireless Mouse) and return top-3 catalog suggestions instead of only a hard fail.

## Failure notes

- None (all expected statuses matched).

_Raw CSV:_ `evaluation_results.csv`
