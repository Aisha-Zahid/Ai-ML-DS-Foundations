"""Top-player model: regress upcoming impact_score, then rank within match."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .baselines import add_player_game_key
from .config import PLAYER_CAT_COLS, PLAYER_NUM_COLS
from .metrics import regression_report_dict, topk_hit_rate


def available_columns(df: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c in df.columns]


def make_player_pipeline(num_cols: list[str], cat_cols: list[str]) -> Pipeline:
    pre = ColumnTransformer(
        transformers=[
            ("num", SimpleImputer(strategy="median"), num_cols),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "onehot",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                cat_cols,
            ),
        ]
    )
    # HistGBM is faster on 200k+ rows
    return Pipeline(
        steps=[
            ("pre", pre),
            (
                "reg",
                HistGradientBoostingRegressor(
                    max_depth=6,
                    learning_rate=0.08,
                    max_iter=200,
                    random_state=42,
                ),
            ),
        ]
    )


def make_player_pipeline_gbm(num_cols: list[str], cat_cols: list[str]) -> Pipeline:
    """Smaller GBM for importance reporting on a sample if needed."""
    pre = ColumnTransformer(
        transformers=[
            ("num", SimpleImputer(strategy="median"), num_cols),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "onehot",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                cat_cols,
            ),
        ]
    )
    return Pipeline(
        steps=[
            ("pre", pre),
            (
                "reg",
                GradientBoostingRegressor(
                    n_estimators=100,
                    max_depth=3,
                    learning_rate=0.08,
                    random_state=42,
                ),
            ),
        ]
    )


def train_player_model(
    train: pd.DataFrame,
    holdout: pd.DataFrame,
    *,
    k: int = 5,
    use_fast: bool = True,
) -> tuple[Pipeline, dict, list[str], list[str], pd.DataFrame]:
    """
    Regress impact_score from pre-match features, then rank players inside the game.
    Gives a score per player so we can return a ranked list; full learning-to-rank
    would be heavier for a small accuracy gain here.
    """
    tr = add_player_game_key(train).dropna(subset=["impact_score"])
    ho = add_player_game_key(holdout).dropna(subset=["impact_score"])

    num_cols = available_columns(tr, PLAYER_NUM_COLS)
    cat_cols = available_columns(tr, PLAYER_CAT_COLS)
    pipe = make_player_pipeline(num_cols, cat_cols) if use_fast else make_player_pipeline_gbm(
        num_cols, cat_cols
    )

    X_tr = tr[num_cols + cat_cols]
    y_tr = tr["impact_score"].astype(float)
    X_ho = ho[num_cols + cat_cols]
    y_ho = ho["impact_score"].astype(float)

    pipe.fit(X_tr, y_tr)
    pred = pipe.predict(X_ho)
    scored = ho.copy()
    scored["pred_impact"] = pred

    metrics = {
        **regression_report_dict(y_ho, pred),
        f"topk{k}_hit_rate": topk_hit_rate(
            scored,
            game_col="game_key",
            pred_col="pred_impact",
            actual_col="impact_score",
            k=k,
        ),
        "n_holdout_rows": int(len(scored)),
        "n_holdout_games": int(scored["game_key"].nunique()),
    }
    return pipe, metrics, num_cols, cat_cols, scored


def player_numeric_importance_proxy(pipe: Pipeline, num_cols: list[str]) -> pd.DataFrame:
    """
    HistGBM has no classic feature_importances_. Use a small GBM on numeric-only
    columns as a readable proxy for the notebook, or return empty if unavailable.
    """
    reg = pipe.named_steps.get("reg")
    if hasattr(reg, "feature_importances_"):
        names = list(pipe.named_steps["pre"].get_feature_names_out())
        vals = reg.feature_importances_
        out = pd.DataFrame({"feature": names, "value": vals})
        return out.sort_values("value", ascending=False).reset_index(drop=True)
    return pd.DataFrame({"feature": num_cols, "value": np.nan})
