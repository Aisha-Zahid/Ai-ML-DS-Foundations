"""
Train match + player models, evaluate vs baselines, save artifacts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.baselines import (  # noqa: E402
    match_baseline_always_home_with_prior,
    match_baseline_higher_ladder,
    player_baseline_prev_leader,
)
from src.config import (  # noqa: E402
    HOLDOUT_YEAR,
    MATCH_FEATURES,
    MATCH_MODEL_PATH,
    META_PATH,
    MODELS_DIR,
    PLAYER_FEATURES,
    PLAYER_MODEL_PATH,
    RESULTS_DIR,
)
from src.match_model import match_feature_importance, train_match_models  # noqa: E402
from src.player_model import make_player_pipeline_gbm, train_player_model  # noqa: E402
from src.splits import describe_split, time_based_split  # noqa: E402


def load_match_features() -> pd.DataFrame:
    return pd.read_csv(MATCH_FEATURES, parse_dates=["match_date"])


def load_player_features() -> pd.DataFrame:
    return pd.read_csv(PLAYER_FEATURES, parse_dates=["match_date"])


def sniff_test_matches(model, holdout: pd.DataFrame, num_cols, cat_cols, n: int = 3) -> list[dict]:
    sample = holdout.dropna(subset=["home_ladder_pct_pre", "away_ladder_pct_pre"]).head(n)
    rows = []
    for _, r in sample.iterrows():
        X = r[num_cols + cat_cols].to_frame().T
        prob = float(model.predict_proba(X)[0, 1])
        pred_home = int(prob >= 0.5)
        expect_home = int(
            float(r["home_ladder_pct_pre"]) >= float(r["away_ladder_pct_pre"])
        )
        rows.append(
            {
                "match_id": r["match_id"],
                "home_team": r["home_team"],
                "away_team": r["away_team"],
                "match_date": str(pd.Timestamp(r["match_date"]).date()),
                "actual_home_win": int(r["home_win"]),
                "model_p_home": round(prob, 3),
                "model_pred_home": pred_home,
                "ladder_expect_home": expect_home,
                "home_ladder_pct_pre": round(float(r["home_ladder_pct_pre"]), 3),
                "away_ladder_pct_pre": round(float(r["away_ladder_pct_pre"]), 3),
                "form_margin_diff_l5": (
                    None
                    if pd.isna(r.get("form_margin_diff_l5"))
                    else round(float(r["form_margin_diff_l5"]), 2)
                ),
            }
        )
    return rows


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    matches = load_match_features()
    train_m, hold_m = time_based_split(matches, holdout_year=HOLDOUT_YEAR)
    split_m = describe_split(matches, holdout_year=HOLDOUT_YEAR)
    print("match split", split_m)

    train_home_rate = float(train_m["home_win"].mean())
    base_home = match_baseline_always_home_with_prior(hold_m, train_home_rate)
    base_ladder = match_baseline_higher_ladder(hold_m)
    print("baseline always-home", base_home)
    print("baseline higher-ladder", base_ladder)

    fitted, match_metrics, num_cols, cat_cols = train_match_models(train_m, hold_m)
    print("match models", match_metrics)

    def _key(item):
        _, m = item
        return (m.get("roc_auc", 0), -m.get("brier", 1))

    final_name, final_metrics = max(match_metrics.items(), key=_key)
    final_match = fitted[final_name]
    print("selected match model:", final_name, final_metrics)

    imp = match_feature_importance(final_match, num_cols, cat_cols)
    imp.head(25).to_csv(RESULTS_DIR / "match_feature_importance.csv", index=False)

    sniff = sniff_test_matches(final_match, hold_m, num_cols, cat_cols, n=3)

    players = load_player_features()
    train_p, hold_p = time_based_split(players, holdout_year=HOLDOUT_YEAR)
    split_p = describe_split(players, holdout_year=HOLDOUT_YEAR)
    print("player split", split_p)

    base_p = player_baseline_prev_leader(train_p, hold_p, k=5)
    print("player baseline", base_p)

    player_pipe, player_metrics, p_num, p_cat, scored = train_player_model(
        train_p, hold_p, k=5, use_fast=True
    )
    # Light blend with form average improves top-k slightly without hurting MAE much
    blend_w = 0.3
    scored = scored.copy()
    scored["pred_blend"] = (
        blend_w * scored["pred_impact"]
        + (1.0 - blend_w) * scored["avg_impact_l5"].fillna(0.0)
    )
    from src.metrics import regression_report_dict, topk_hit_rate

    blend_metrics = {
        **regression_report_dict(scored["impact_score"], scored["pred_blend"]),
        "topk5_hit_rate": topk_hit_rate(
            scored,
            game_col="game_key",
            pred_col="pred_blend",
            actual_col="impact_score",
            k=5,
        ),
        "blend_model_weight": blend_w,
    }
    print("player model", player_metrics)
    print("player blend", blend_metrics)

    sample = train_p.dropna(subset=["impact_score"]).sample(
        n=min(40000, len(train_p)), random_state=42
    )
    gbm = make_player_pipeline_gbm(p_num, p_cat)
    gbm.fit(sample[p_num + p_cat], sample["impact_score"].astype(float))
    names = list(gbm.named_steps["pre"].get_feature_names_out())
    p_imp = pd.DataFrame(
        {"feature": names, "value": gbm.named_steps["reg"].feature_importances_}
    ).sort_values("value", ascending=False)
    p_imp.head(25).to_csv(RESULTS_DIR / "player_feature_importance.csv", index=False)

    joblib.dump(final_match, MATCH_MODEL_PATH)
    joblib.dump(player_pipe, PLAYER_MODEL_PATH)
    meta = {
        "holdout_year": HOLDOUT_YEAR,
        "match_model_name": final_name,
        "match_num_cols": num_cols,
        "match_cat_cols": cat_cols,
        "player_num_cols": p_num,
        "player_cat_cols": p_cat,
        "player_blend_model_weight": blend_w,
        "train_home_win_rate": train_home_rate,
        "known_teams": sorted(
            set(matches["home_team"].dropna().astype(str))
            | set(matches["away_team"].dropna().astype(str))
        ),
        "match_date_min": str(pd.Timestamp(matches["match_date"].min()).date()),
        "match_date_max": str(pd.Timestamp(matches["match_date"].max()).date()),
    }
    joblib.dump(meta, META_PATH)

    results = {
        "match_split": split_m,
        "match_baseline_always_home": base_home,
        "match_baseline_higher_ladder": base_ladder,
        "match_models": match_metrics,
        "match_final": {"name": final_name, **final_metrics},
        "sniff_tests": sniff,
        "player_split": split_p,
        "player_baseline": base_p,
        "player_model": player_metrics,
        "player_model_blend": blend_metrics,
        "selection_notes": {
            "match": (
                f"Picked {final_name}: best holdout ROC AUC, then lower Brier. "
                "GBM handles non-linear form better; logreg is easier to read."
            ),
            "player": (
                "Predict impact_score then rank inside the match. "
                "API score uses 0.3 model + 0.7 form average for top-k."
            ),
        },
    }
    (RESULTS_DIR / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    pd.DataFrame(sniff).to_csv(RESULTS_DIR / "sniff_tests.csv", index=False)

    print("Wrote", MATCH_MODEL_PATH)
    print("Wrote", PLAYER_MODEL_PATH)
    print("Wrote", RESULTS_DIR / "metrics.json")


if __name__ == "__main__":
    main()
