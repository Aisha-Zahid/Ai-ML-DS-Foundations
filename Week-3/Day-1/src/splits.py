"""Reusable time-based train / hold-out splits for Week 3."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

# Default contract for the week: train on seasons before HOLDOUT_YEAR,
# hold out HOLDOUT_YEAR+ (most recent complete-ish season in the dump).
DEFAULT_HOLDOUT_YEAR = 2024


def time_based_split(
    df: pd.DataFrame,
    *,
    year_col: str = "year",
    holdout_year: int = DEFAULT_HOLDOUT_YEAR,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Strict time split: train = year < holdout_year, holdout = year >= holdout_year.

    A random split would mix future games into training and leak information that
    would not be available when predicting a live round (form features built with
    care still assume chronological evaluation).
    """
    if year_col not in df.columns:
        raise KeyError(f"{year_col} missing from frame")
    train = df[df[year_col] < holdout_year].copy()
    holdout = df[df[year_col] >= holdout_year].copy()
    return train, holdout


def time_based_split_mask(
    df: pd.DataFrame,
    *,
    year_col: str = "year",
    holdout_year: int = DEFAULT_HOLDOUT_YEAR,
) -> pd.Series:
    """Boolean mask: True = holdout rows."""
    return df[year_col] >= holdout_year


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
            int(train[year_col].min()),
            int(train[year_col].max()),
        )
        if len(train)
        else None,
        "holdout_years": (
            int(holdout[year_col].min()),
            int(holdout[year_col].max()),
        )
        if len(holdout)
        else None,
    }


CEILING_NOTE = (
    "AFL match outcomes are noisy: injuries, weather, travel, umpiring, and in-game variance "
    "mean even strong models rarely clear ~60–70% accuracy on home/away winner over a long span. "
    "Margin MAE of several goals is normal. Near-perfect accuracy on a holdout season would be a "
    "red flag for leakage (e.g. using same-game stats, post-match ladder, or a shuffled split)."
)
