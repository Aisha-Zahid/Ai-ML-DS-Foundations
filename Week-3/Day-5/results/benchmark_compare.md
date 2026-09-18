# Match-winner vs public-style benchmark

Holdout = seasons >= 2024 (432 matches).

| Model | Accuracy | ROC AUC | Brier |
|-------|----------|---------|-------|
| Always-home | 56.2% | 0.500 | 0.247 |
| Higher ladder % (naive) | 63.9% | 0.635 | 0.239 |
| Day-2 GBM | 65.0% | 0.709 | 0.213 |

**Takeaway:** GBM beats the ladder heuristic by **+1.2% accuracy** and **+0.074 AUC**
on the same holdout. "Good enough" here means modestly better than a strong public baseline,
not bookmaker-grade — tips must stay probabilistic.

Source: `Week-3/Day-2/results/metrics.json`.
