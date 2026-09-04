"""Shared row-level feature engineering for Adult income pipelines."""
import numpy as np
import pandas as pd


def engineer_features(X_df):
    """Add engineered columns using only current-row values (no leakage)."""
    X_out = X_df.copy()
    age = X_out["age"].astype(float)
    hours = X_out["hours-per-week"].astype(float)
    edu = X_out["education-num"].astype(float)
    cg = X_out["capital-gain"].astype(float)
    cl = X_out["capital-loss"].astype(float)

    X_out["age_bucket"] = pd.cut(
        age,
        bins=[0, 25, 35, 45, 55, 65, 100],
        labels=["<=25", "26-35", "36-45", "46-55", "56-65", "65+"],
        include_lowest=True,
    ).astype(str)
    X_out["hours_bin"] = pd.cut(
        hours,
        bins=[0, 20, 40, 50, 100],
        labels=["part_time", "full_time", "overtime", "extreme"],
        include_lowest=True,
    ).astype(str)
    X_out["has_capital_gain"] = (cg > 0).astype(int)
    X_out["log_capital_gain"] = np.log1p(cg)
    X_out["is_higher_edu"] = (edu >= 13).astype(int)
    X_out["edu_x_hours"] = edu * hours
    X_out["has_capital_loss"] = (cl > 0).astype(int)
    X_out["is_full_time"] = (hours >= 40).astype(int)
    return X_out
