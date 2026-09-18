"""Compare Day-2 match model vs ladder-position naive benchmark (from metrics.json)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DAY2_METRICS = ROOT.parent / "Day-2" / "results" / "metrics.json"
RESULTS = ROOT / "results"


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    if not DAY2_METRICS.exists():
        raise SystemExit(f"Missing {DAY2_METRICS} — run Day-2 training first.")

    m = json.loads(DAY2_METRICS.read_text(encoding="utf-8"))
    gbm = m["match_final"]
    ladder = m["match_baseline_higher_ladder"]
    home = m["match_baseline_always_home"]

    rows = [
        {
            "model": "Always-home baseline",
            "accuracy": round(home["accuracy"], 4),
            "roc_auc": round(home["roc_auc"], 4),
            "brier": round(home["brier"], 4),
        },
        {
            "model": "Higher-ladder (naive public-style)",
            "accuracy": round(ladder["accuracy"], 4),
            "roc_auc": round(ladder["roc_auc"], 4),
            "brier": round(ladder["brier"], 4),
        },
        {
            "model": f"Day-2 GBM ({gbm['name']})",
            "accuracy": round(gbm["accuracy"], 4),
            "roc_auc": round(gbm["roc_auc"], 4),
            "brier": round(gbm["brier"], 4),
        },
    ]

    delta_acc = gbm["accuracy"] - ladder["accuracy"]
    delta_auc = gbm["roc_auc"] - ladder["roc_auc"]

    md = f"""# Match-winner vs public-style benchmark

Holdout = seasons >= {m['match_split']['holdout_year']} ({m['match_split']['holdout_rows']} matches).

| Model | Accuracy | ROC AUC | Brier |
|-------|----------|---------|-------|
| Always-home | {home['accuracy']:.1%} | {home['roc_auc']:.3f} | {home['brier']:.3f} |
| Higher ladder % (naive) | {ladder['accuracy']:.1%} | {ladder['roc_auc']:.3f} | {ladder['brier']:.3f} |
| Day-2 GBM | {gbm['accuracy']:.1%} | {gbm['roc_auc']:.3f} | {gbm['brier']:.3f} |

**Takeaway:** GBM beats the ladder heuristic by **{delta_acc:+.1%} accuracy** and **{delta_auc:+.3f} AUC**
on the same holdout. "Good enough" here means modestly better than a strong public baseline,
not bookmaker-grade — tips must stay probabilistic.

Source: `Week-3/Day-2/results/metrics.json`.
"""
    (RESULTS / "benchmark_compare.md").write_text(md, encoding="utf-8")
    (RESULTS / "benchmark_compare.json").write_text(
        json.dumps({"rows": rows, "delta_acc_vs_ladder": delta_acc, "delta_auc_vs_ladder": delta_auc}, indent=2),
        encoding="utf-8",
    )
    print(md.encode("ascii", errors="replace").decode("ascii"))


if __name__ == "__main__":
    main()
