"""Match winner model training."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import MATCH_CAT_COLS, MATCH_NUM_COLS
from .metrics import classification_report_dict


def available_columns(df: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c in df.columns]


def build_match_preprocessor(num_cols: list[str], cat_cols: list[str]) -> ColumnTransformer:
    num_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    cat_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", num_pipe, num_cols),
            ("cat", cat_pipe, cat_cols),
        ]
    )


def make_match_pipelines(num_cols: list[str], cat_cols: list[str]) -> dict[str, Pipeline]:
    pre_scaled = build_match_preprocessor(num_cols, cat_cols)
    pre_tree = ColumnTransformer(
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
    return {
        "logreg": Pipeline(
            steps=[
                ("pre", pre_scaled),
                (
                    "clf",
                    LogisticRegression(max_iter=2000, class_weight="balanced"),
                ),
            ]
        ),
        "gbm": Pipeline(
            steps=[
                ("pre", pre_tree),
                (
                    "clf",
                    GradientBoostingClassifier(
                        n_estimators=150,
                        max_depth=3,
                        learning_rate=0.08,
                        random_state=42,
                    ),
                ),
            ]
        ),
    }


def train_match_models(
    train: pd.DataFrame, holdout: pd.DataFrame
) -> tuple[dict[str, Pipeline], dict[str, dict], list[str], list[str]]:
    num_cols = available_columns(train, MATCH_NUM_COLS)
    cat_cols = available_columns(train, MATCH_CAT_COLS)
    pipes = make_match_pipelines(num_cols, cat_cols)

    X_tr = train[num_cols + cat_cols]
    y_tr = train["home_win"].astype(int)
    X_ho = holdout[num_cols + cat_cols]
    y_ho = holdout["home_win"].astype(int)

    metrics: dict[str, dict] = {}
    fitted: dict[str, Pipeline] = {}
    for name, pipe in pipes.items():
        pipe.fit(X_tr, y_tr)
        prob = pipe.predict_proba(X_ho)[:, 1]
        pred = (prob >= 0.5).astype(int)
        metrics[name] = classification_report_dict(y_ho, pred, prob)
        fitted[name] = pipe
    return fitted, metrics, num_cols, cat_cols


def match_feature_importance(pipe: Pipeline, num_cols: list[str], cat_cols: list[str]) -> pd.DataFrame:
    """Coefficients (logreg) or impurity-based importances when available."""
    pre = pipe.named_steps["pre"]
    clf = pipe.named_steps["clf"]
    feat_names = list(pre.get_feature_names_out())

    if hasattr(clf, "coef_"):
        vals = np.ravel(clf.coef_)
        kind = "coefficient"
    elif hasattr(clf, "feature_importances_"):
        vals = np.asarray(clf.feature_importances_)
        kind = "importance"
    else:
        # HistGradientBoosting has no feature_importances_ in older sklearn — use permutation-free stub
        return pd.DataFrame({"feature": feat_names, "value": np.nan, "kind": "unavailable"})

    out = pd.DataFrame({"feature": feat_names, "value": vals, "kind": kind})
    out["abs_value"] = out["value"].abs()
    return out.sort_values("abs_value", ascending=False).reset_index(drop=True)
