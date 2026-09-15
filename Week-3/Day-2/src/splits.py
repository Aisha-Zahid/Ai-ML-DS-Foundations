"""Time-based split (same contract as Week-3 Day-1)."""

from __future__ import annotations

import pandas as pd

DEFAULT_HOLDOUT_YEAR = 2024


def time_based_split(
    df: pd.DataFrame,
    *,
    year_col: str = "year",
    holdout_year: int = DEFAULT_HOLDOUT_YEAR,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if year_col not in df.columns:
        raise KeyError(f"{year_col} missing from frame")
    train = df[df[year_col] < holdout_year].copy()
    holdout = df[df[year_col] >= holdout_year].copy()
    return train, holdout


def describe_split(
    df: pd.DataFrame,
    *,
    year_col: str = "year",
    holdout_year: int = DEFAULT_HOLDOUT_YEAR,
) -> dict:
    train, holdout = time_based_split(df, year_col=year_col, holdout_year=holdout_year)
    return {
        "holdout_year": holdout_year,
        "train_rows": len(train),
        "holdout_rows": len(holdout),
        "train_years": (
            (int(train[year_col].min()), int(train[year_col].max())) if len(train) else None
        ),
        "holdout_years": (
            (int(holdout[year_col].min()), int(holdout[year_col].max()))
            if len(holdout)
            else None
        ),
    }
