"""Day-4 faster exploratory tuning run."""
import json
import sys
import time
import warnings
import numpy as np
import pandas as pd

from sklearn.datasets import fetch_openml
from sklearn.model_selection import (
    train_test_split,
    StratifiedKFold,
    RandomizedSearchCV,
    GridSearchCV,
)
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder, FunctionTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    f1_score, precision_score, recall_score, accuracy_score,
    roc_auc_score, average_precision_score, brier_score_loss, confusion_matrix,
)
from sklearn.base import clone
from scipy.stats import randint, uniform

warnings.filterwarnings("ignore")
RANDOM_STATE = 42

def log(msg):
    print(msg, flush=True)

adult = fetch_openml("adult", version=2, as_frame=True, parser="auto")
df = adult.frame.copy()
df = df.rename(columns={"class": "income"})
df = df.replace(r"^\s*\?$", np.nan, regex=True)
df["income"] = df["income"].astype(str).map({"<=50K": 0, ">50K": 1})
X = df.drop("income", axis=1)
y = df["income"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
)
X_tr, X_val, y_tr, y_val = train_test_split(
    X_train, y_train, test_size=0.20, random_state=RANDOM_STATE, stratify=y_train
)
log(f"Train={len(X_train)} Test={len(X_test)} thr-val={len(X_val)}")


def engineer_features(X_df):
    X_out = X_df.copy()
    age = X_out["age"].astype(float)
    hours = X_out["hours-per-week"].astype(float)
    edu = X_out["education-num"].astype(float)
    cg = X_out["capital-gain"].astype(float)
    cl = X_out["capital-loss"].astype(float)
    X_out["age_bucket"] = pd.cut(
        age, bins=[0, 25, 35, 45, 55, 65, 100],
        labels=["<=25", "26-35", "36-45", "46-55", "56-65", "65+"],
        include_lowest=True,
    ).astype(str)
    X_out["hours_bin"] = pd.cut(
        hours, bins=[0, 20, 40, 50, 100],
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


# Dropped fnlwgt (Day-3 note: census sampling weight, weak predictive role)
BASE_NUMERIC = ["age", "education-num", "capital-gain", "capital-loss", "hours-per-week"]
ENG_NUMERIC = [
    "log_capital_gain", "edu_x_hours", "has_capital_gain",
    "is_higher_edu", "has_capital_loss", "is_full_time",
]
BASE_CATEGORICAL = [
    "workclass", "education", "marital-status", "occupation",
    "relationship", "race", "sex", "native-country",
]
ENG_CATEGORICAL = ["age_bucket", "hours_bin"]
ALL_NUMERIC = BASE_NUMERIC + ENG_NUMERIC
ALL_CATEGORICAL = BASE_CATEGORICAL + ENG_CATEGORICAL


def make_preprocessor():
    return ColumnTransformer(
        [
            ("num", Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]), ALL_NUMERIC),
            ("cat", Pipeline([
                ("imputer", SimpleImputer(strategy="constant", fill_value="Missing")),
                ("encoder", OneHotEncoder(handle_unknown="ignore")),
            ]), ALL_CATEGORICAL),
        ],
        sparse_threshold=0,
    )


def make_pipe(estimator):
    return Pipeline([
        ("engineer", FunctionTransformer(engineer_features, validate=False)),
        ("preprocess", make_preprocessor()),
        ("clf", estimator),
    ])


cv_search = StratifiedKFold(n_splits=3, shuffle=True, random_state=RANDOM_STATE)

# LR — liblinear supports l1 and l2 and is faster than saga here
log("=== LR GridSearch (l1/l2 via liblinear) ===")
lr_pipe = make_pipe(LogisticRegression(
    random_state=RANDOM_STATE, solver="liblinear", max_iter=2000
))
lr_grid = {
    "clf__penalty": ["l1", "l2"],
    "clf__C": [0.01, 0.1, 1.0, 3.0, 10.0],
    "clf__class_weight": [None, "balanced"],
}
t0 = time.time()
lr_search = GridSearchCV(lr_pipe, lr_grid, scoring="f1", cv=cv_search, n_jobs=-1)
lr_search.fit(X_train, y_train)
log(f"Best LR F1={lr_search.best_score_:.4f} params={lr_search.best_params_} t={time.time()-t0:.1f}s")
lr_best_search = lr_search
lr_label = "Logistic Regression"

log("=== RF RandomizedSearch n_iter=30 ===")
rf_pipe = make_pipe(RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=1))
rf_dist = {
    "clf__n_estimators": [100, 150, 200],
    "clf__max_depth": [8, 12, 16, 24, None],
    "clf__min_samples_leaf": [1, 2, 5, 10, 15],
    "clf__max_features": ["sqrt", "log2", 0.3],
}
t0 = time.time()
rf_search = RandomizedSearchCV(
    rf_pipe, rf_dist, n_iter=30, scoring="f1", cv=cv_search,
    random_state=RANDOM_STATE, n_jobs=-1, refit=True,
)
rf_search.fit(X_train, y_train)
log(f"Best RF F1={rf_search.best_score_:.4f} params={rf_search.best_params_} t={time.time()-t0:.1f}s")

log("=== HGB RandomizedSearch n_iter=40 ===")
hgb_pipe = make_pipe(HistGradientBoostingClassifier(random_state=RANDOM_STATE))
hgb_dist = {
    "clf__learning_rate": [0.05, 0.08, 0.1, 0.15, 0.2],
    "clf__max_iter": [100, 150, 200],
    "clf__max_depth": [3, 5, 7, 10, None],
    "clf__l2_regularization": [0.0, 0.1, 0.3, 0.5, 1.0],
    "clf__min_samples_leaf": [10, 20, 30, 40],
}
t0 = time.time()
hgb_search = RandomizedSearchCV(
    hgb_pipe, hgb_dist, n_iter=40, scoring="f1", cv=cv_search,
    random_state=RANDOM_STATE, n_jobs=-1, refit=True,
)
hgb_search.fit(X_train, y_train)
log(f"Best HGB F1={hgb_search.best_score_:.4f} params={hgb_search.best_params_} t={time.time()-t0:.1f}s")

candidates = {
    lr_label: lr_best_search,
    "Random Forest": rf_search,
    "HistGradientBoosting": hgb_search,
}
best_name = max(candidates, key=lambda n: candidates[n].best_score_)
best_search = candidates[best_name]
log(f"WINNER: {best_name} CV F1={best_search.best_score_:.4f}")

# Calibration + threshold on train/val split
log("=== Calibration + threshold ===")
cal_base = clone(best_search.best_estimator_)
cal = CalibratedClassifierCV(estimator=cal_base, method="isotonic", cv=3)
t0 = time.time()
cal.fit(X_tr, y_tr)
log(f"Calibrated on train-split t={time.time()-t0:.1f}s")
proba_val = cal.predict_proba(X_val)[:, 1]

best_thr, best_f1 = 0.5, -1.0
for thr in np.linspace(0.15, 0.85, 71):
    pred = (proba_val >= thr).astype(int)
    f1 = f1_score(y_val, pred, zero_division=0)
    if f1 > best_f1:
        best_f1, best_thr = float(f1), float(thr)
log(f"Best thr={best_thr:.2f} val F1={best_f1:.4f}")

# Final: fit calibrated on full train
final_cal = CalibratedClassifierCV(
    estimator=clone(best_search.best_estimator_), method="isotonic", cv=3
)
t0 = time.time()
final_cal.fit(X_train, y_train)
log(f"Final calibrated fit t={time.time()-t0:.1f}s")

uncal = best_search.best_estimator_
proba_uncal = uncal.predict_proba(X_test)[:, 1]
proba_cal = final_cal.predict_proba(X_test)[:, 1]


def metrics(y_true, y_pred, y_score):
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_score)),
        "pr_auc": float(average_precision_score(y_true, y_score)),
        "brier": float(brier_score_loss(y_true, y_score)),
        "cm": confusion_matrix(y_true, y_pred).tolist(),
    }


def ser_params(d):
    out = {}
    for k, v in d.items():
        if v is None or isinstance(v, (str, bool)):
            out[k] = v
        elif isinstance(v, (np.floating, float)):
            out[k] = float(v)
        elif isinstance(v, (np.integer, int)):
            out[k] = int(v)
        else:
            out[k] = v
    return out

result = {
    "lr_best_params": ser_params(lr_best_search.best_params_),
    "lr_best_cv": float(lr_best_search.best_score_),
    "rf_best_params": ser_params(rf_search.best_params_),
    "rf_best_cv": float(rf_search.best_score_),
    "hgb_best_params": ser_params(hgb_search.best_params_),
    "hgb_best_cv": float(hgb_search.best_score_),
    "winner": best_name,
    "best_threshold": best_thr,
    "val_f1_at_thr": best_f1,
    "test_uncal_0.5": metrics(y_test, (proba_uncal >= 0.5).astype(int), proba_uncal),
    "test_cal_0.5": metrics(y_test, (proba_cal >= 0.5).astype(int), proba_cal),
    "test_cal_tuned": metrics(y_test, (proba_cal >= best_thr).astype(int), proba_cal),
}
log(json.dumps(result, indent=2))
with open(r"d:\Netixsol\Week-1\Day-4\_metrics.json", "w") as f:
    json.dump(result, f, indent=2)
log("Saved _metrics.json")
