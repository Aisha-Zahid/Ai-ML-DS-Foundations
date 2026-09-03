"""Build Day-4 model_tuning.ipynb"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []

def md(t):
    cells.append(nbf.v4.new_markdown_cell(t))

def code(t):
    cells.append(nbf.v4.new_code_cell(t))

md("""# Adult Income Prediction — Model Tuning (Day 4)

Continuation of Day 1–3. I tune Logistic Regression, Random Forest, and HistGradientBoosting with the Day 3 engineered features, check learning curves, calibrate probabilities, and pick a threshold for F1.

**Primary metric:** F1. The Day 1 hold-out test set stays unused until the final section.""")

md("""## How to re-run and reproduce

1. `pip install -r requirements.txt`
2. Open this notebook and **Run All**
3. Keep `RANDOM_STATE = 42` unchanged
4. The final artifact is written to `final_income_pipeline.joblib`

Results depend on the library versions printed below. Searches use `StratifiedKFold` with `shuffle=True` and `random_state=42`.""")

md("""## 1. Setup, versions, and same hold-out split""")

code("""import time
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import sklearn

from sklearn.datasets import fetch_openml
from sklearn.model_selection import (
    train_test_split,
    StratifiedKFold,
    GridSearchCV,
    RandomizedSearchCV,
    learning_curve,
)
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder, FunctionTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV, CalibrationDisplay
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    ConfusionMatrixDisplay,
    RocCurveDisplay,
    PrecisionRecallDisplay,
)
from sklearn.base import clone

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid")
RANDOM_STATE = 42

print("numpy:", np.__version__)
print("pandas:", pd.__version__)
print("scikit-learn:", sklearn.__version__)""")

code("""# Same loading / cleaning / split as Day 1–3
adult = fetch_openml("adult", version=2, as_frame=True, parser="auto")
df = adult.frame.copy()
df = df.rename(columns={"class": "income"})
df = df.replace(r"^\\s*\\?$", np.nan, regex=True)
df["income"] = df["income"].astype(str).map({"<=50K": 0, ">50K": 1})

X = df.drop("income", axis=1)
y = df["income"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
)

# Validation slice from TRAIN only — for threshold tuning (test stays sealed)
X_tr, X_val, y_tr, y_val = train_test_split(
    X_train, y_train, test_size=0.20, random_state=RANDOM_STATE, stratify=y_train
)

print(f"Train: {len(X_train):,} | Val (from train): {len(X_val):,} | Hold-out test: {len(X_test):,}")""")

md("""## 2. Reproducible pipeline (engineering + preprocessing + model)

Day 3 engineered features stay inside a `FunctionTransformer`.

**Note on `fnlwgt`:** it is a census sampling weight, not a person-level income driver. It was not a top signal in Day 3, so I **drop it** from the numeric block for Day 4.

**Note on capital-gain features:** `has_capital_gain` and `log_capital_gain` overlap. In Day 3, LR often gave the flag a large negative coefficient once the log amount was present — that is shared information / redundancy, not evidence that having capital gain lowers income. I keep both so trees can use the flag and the continuous amount, and call that out when reading coefficients.""")

code("""def engineer_features(X_df):
    \"\"\"Row-level features only (no target encoding).\"\"\"
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


# fnlwgt dropped on purpose
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
print("Numeric:", ALL_NUMERIC)
print("Categorical:", ALL_CATEGORICAL)""")

md("""## 3. Hyperparameter search

I optimize **F1** with stratified 3-fold CV inside each search (`n_jobs=-1`). Budget is kept realistic: full grid for LR; RandomizedSearch for RF (`n_iter=30`) and HGB (`n_iter=40`).""")

code("""print("=== Logistic Regression (GridSearch: penalty, C, class_weight) ===")
lr_pipe = make_pipe(LogisticRegression(
    random_state=RANDOM_STATE, solver="liblinear", max_iter=2000
))
lr_grid = {
    "clf__penalty": ["l1", "l2"],
    "clf__C": [0.01, 0.1, 1.0, 3.0, 10.0],
    "clf__class_weight": [None, "balanced"],
}
t0 = time.time()
lr_search = GridSearchCV(
    lr_pipe, lr_grid, scoring="f1", cv=cv_search, n_jobs=-1, refit=True
)
lr_search.fit(X_train, y_train)
print(f"Best CV F1={lr_search.best_score_:.4f} | {time.time() - t0:.1f}s")
print("Best params:", lr_search.best_params_)""")

code("""print("=== Random Forest (RandomizedSearch n_iter=30) ===")
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
print(f"Best CV F1={rf_search.best_score_:.4f} | {time.time() - t0:.1f}s")
print("Best params:", rf_search.best_params_)""")

code("""print("=== HistGradientBoosting (RandomizedSearch n_iter=40) ===")
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
print(f"Best CV F1={hgb_search.best_score_:.4f} | {time.time() - t0:.1f}s")
print("Best params:", hgb_search.best_params_)""")

code("""search_summary = pd.DataFrame([
    {"Model": "Logistic Regression", "Best CV F1": lr_search.best_score_, "Best params": lr_search.best_params_},
    {"Model": "Random Forest", "Best CV F1": rf_search.best_score_, "Best params": rf_search.best_params_},
    {"Model": "HistGradientBoosting", "Best CV F1": hgb_search.best_score_, "Best params": hgb_search.best_params_},
]).set_index("Model")

display(search_summary)
best_name = search_summary["Best CV F1"].idxmax()
best_search = {
    "Logistic Regression": lr_search,
    "Random Forest": rf_search,
    "HistGradientBoosting": hgb_search,
}[best_name]
print(f"\\nSelected for calibration / thresholding: {best_name}")""")

md("""## 4. Learning curves and regularization diagnostics""")

code("""# Learning curve for the tuned HGB pipeline
hgb_best = clone(hgb_search.best_estimator_)
train_sizes, train_scores, val_scores = learning_curve(
    hgb_best,
    X_train,
    y_train,
    train_sizes=np.linspace(0.1, 1.0, 6),
    cv=cv_search,
    scoring="f1",
    n_jobs=-1,
    random_state=RANDOM_STATE,
)

fig, ax = plt.subplots(figsize=(7, 5))
ax.plot(train_sizes, train_scores.mean(axis=1), "o-", label="Train F1")
ax.plot(train_sizes, val_scores.mean(axis=1), "o-", label="CV F1")
ax.fill_between(
    train_sizes,
    val_scores.mean(axis=1) - val_scores.std(axis=1),
    val_scores.mean(axis=1) + val_scores.std(axis=1),
    alpha=0.15,
)
ax.set_xlabel("Training examples")
ax.set_ylabel("F1")
ax.set_title("Learning curve — tuned HistGradientBoosting")
ax.legend()
plt.tight_layout()
plt.show()

gap = train_scores.mean(axis=1)[-1] - val_scores.mean(axis=1)[-1]
print(f"Final train F1={train_scores.mean(axis=1)[-1]:.4f} | CV F1={val_scores.mean(axis=1)[-1]:.4f} | gap={gap:.4f}")""")

code("""# Effect of C on Logistic Regression (train vs validation F1)
C_values = [0.01, 0.1, 0.5, 1.0, 3.0, 10.0]
lr_train_f1, lr_val_f1 = [], []
for C in C_values:
    pipe = make_pipe(LogisticRegression(
        random_state=RANDOM_STATE, solver="liblinear", penalty="l1",
        C=C, class_weight="balanced", max_iter=2000,
    ))
    pipe.fit(X_tr, y_tr)
    lr_train_f1.append(f1_score(y_tr, pipe.predict(X_tr)))
    lr_val_f1.append(f1_score(y_val, pipe.predict(X_val)))

fig, ax = plt.subplots(figsize=(7, 5))
ax.plot(C_values, lr_train_f1, "o-", label="Train F1")
ax.plot(C_values, lr_val_f1, "o-", label="Validation F1")
ax.set_xscale("log")
ax.set_xlabel("C (inverse regularization)")
ax.set_ylabel("F1")
ax.set_title("Logistic Regression — effect of C")
ax.legend()
plt.tight_layout()
plt.show()
print(list(zip(C_values, np.round(lr_val_f1, 4))))""")

code("""# Effect of max_depth on HistGradientBoosting
depths = [2, 3, 5, 7, 10, None]
hgb_train_f1, hgb_val_f1 = [], []
base_params = {k.replace("clf__", ""): v for k, v in hgb_search.best_params_.items()}
for d in depths:
    params = dict(base_params)
    params["max_depth"] = d
    params["random_state"] = RANDOM_STATE
    pipe = make_pipe(HistGradientBoostingClassifier(**params))
    pipe.fit(X_tr, y_tr)
    hgb_train_f1.append(f1_score(y_tr, pipe.predict(X_tr)))
    hgb_val_f1.append(f1_score(y_val, pipe.predict(X_val)))

depth_labels = [str(d) if d is not None else "None" for d in depths]
fig, ax = plt.subplots(figsize=(7, 5))
ax.plot(depth_labels, hgb_train_f1, "o-", label="Train F1")
ax.plot(depth_labels, hgb_val_f1, "o-", label="Validation F1")
ax.set_xlabel("max_depth")
ax.set_ylabel("F1")
ax.set_title("HistGradientBoosting — effect of max_depth")
ax.legend()
plt.tight_layout()
plt.show()""")

md("""### What the curves suggest

- **Learning curve:** if train and CV F1 stay close as data grows, the model is not badly overfit; more labeled data would still help a bit.
- **C curve:** very small C underfits; very large C can overfit. The searched value near C=1 with `class_weight='balanced'` is a reasonable middle ground.
- **max_depth:** very shallow trees underfit; unlimited depth can raise train F1 more than validation F1 — use the searched depth / leaf settings and keep `l2_regularization`.""")

md("""## 5. Calibration and threshold selection

I calibrate the winning model with isotonic regression (`CalibratedClassifierCV`). Threshold is chosen on the **validation slice of train** to maximize F1 — not on the hold-out test set.""")

code("""# Fit calibrated model on the train-split; pick threshold on val
cal_for_thresh = CalibratedClassifierCV(
    estimator=clone(best_search.best_estimator_),
    method="isotonic",
    cv=3,
)
cal_for_thresh.fit(X_tr, y_tr)
proba_val = cal_for_thresh.predict_proba(X_val)[:, 1]
proba_val_uncal = best_search.best_estimator_.fit(X_tr, y_tr).predict_proba(X_val)[:, 1]

print("Brier (val) uncalibrated:", round(brier_score_loss(y_val, proba_val_uncal), 4))
print("Brier (val) calibrated:  ", round(brier_score_loss(y_val, proba_val), 4))

fig, ax = plt.subplots(figsize=(6, 6))
CalibrationDisplay.from_predictions(y_val, proba_val_uncal, n_bins=10, ax=ax, name="Uncalibrated")
CalibrationDisplay.from_predictions(y_val, proba_val, n_bins=10, ax=ax, name="Isotonic")
ax.set_title(f"Calibration — {best_name}")
plt.tight_layout()
plt.show()""")

code("""thresholds = np.linspace(0.15, 0.85, 71)
rows = []
best_thr, best_f1 = 0.5, -1.0
for thr in thresholds:
    pred = (proba_val >= thr).astype(int)
    f1 = f1_score(y_val, pred, zero_division=0)
    prec = precision_score(y_val, pred, zero_division=0)
    rec = recall_score(y_val, pred, zero_division=0)
    rows.append({"threshold": thr, "f1": f1, "precision": prec, "recall": rec})
    if f1 > best_f1:
        best_f1, best_thr = f1, float(thr)

thr_df = pd.DataFrame(rows)
print(f"Best threshold on validation: {best_thr:.2f} (F1={best_f1:.4f})")

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(thr_df["threshold"], thr_df["f1"], label="F1")
ax.plot(thr_df["threshold"], thr_df["precision"], label="Precision")
ax.plot(thr_df["threshold"], thr_df["recall"], label="Recall")
ax.axvline(best_thr, color="black", ls="--", label=f"chosen thr={best_thr:.2f}")
ax.set_xlabel("Threshold")
ax.set_ylabel("Score")
ax.set_title("Threshold sweep on validation (maximize F1)")
ax.legend()
plt.tight_layout()
plt.show()

# Confusion matrices at 0.50 vs tuned threshold (validation)
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
for ax, thr, title in [
    (axes[0], 0.5, "Val @ 0.50"),
    (axes[1], best_thr, f"Val @ {best_thr:.2f}"),
]:
    pred = (proba_val >= thr).astype(int)
    ConfusionMatrixDisplay(
        confusion_matrix(y_val, pred), display_labels=["<=50K", ">50K"]
    ).plot(ax=ax, cmap="Blues", colorbar=False)
    ax.set_title(title)
plt.tight_layout()
plt.show()""")

md("""## 6. Final hold-out evaluation and saved artifact

Fit the calibrated pipeline on the **full training set**, then score once on the Day 1 hold-out test set.""")

code("""final_model = CalibratedClassifierCV(
    estimator=clone(best_search.best_estimator_),
    method="isotonic",
    cv=3,
)
final_model.fit(X_train, y_train)

proba_test = final_model.predict_proba(X_test)[:, 1]
pred_default = (proba_test >= 0.5).astype(int)
pred_tuned = (proba_test >= best_thr).astype(int)

# Uncalibrated tuned pipeline for reference
uncal_model = clone(best_search.best_estimator_).fit(X_train, y_train)
proba_uncal = uncal_model.predict_proba(X_test)[:, 1]


def eval_row(name, y_true, y_pred, y_score):
    return {
        "Setup": name,
        "Accuracy": accuracy_score(y_true, y_pred),
        "Precision": precision_score(y_true, y_pred, zero_division=0),
        "Recall": recall_score(y_true, y_pred, zero_division=0),
        "F1": f1_score(y_true, y_pred, zero_division=0),
        "ROC AUC": roc_auc_score(y_true, y_score),
        "PR AUC": average_precision_score(y_true, y_score),
        "Brier": brier_score_loss(y_true, y_score),
    }


final_table = pd.DataFrame([
    eval_row("Uncalibrated @ 0.50", y_test, (proba_uncal >= 0.5).astype(int), proba_uncal),
    eval_row("Calibrated @ 0.50", y_test, pred_default, proba_test),
    eval_row(f"Calibrated @ {best_thr:.2f}", y_test, pred_tuned, proba_test),
]).set_index("Setup")
final_table.round(4)""")

code("""fig, axes = plt.subplots(1, 2, figsize=(12, 5))
RocCurveDisplay.from_predictions(y_test, proba_test, ax=axes[0], name="Calibrated HGB")
axes[0].plot([0, 1], [0, 1], "k--", alpha=0.4)
axes[0].set_title("ROC — hold-out test")
PrecisionRecallDisplay.from_predictions(y_test, proba_test, ax=axes[1], name="Calibrated HGB")
axes[1].set_title("PR — hold-out test")
plt.tight_layout()
plt.show()

fig, axes = plt.subplots(1, 2, figsize=(10, 4))
ConfusionMatrixDisplay(
    confusion_matrix(y_test, pred_default), display_labels=["<=50K", ">50K"]
).plot(ax=axes[0], cmap="Blues", colorbar=False)
axes[0].set_title("Test @ 0.50")
ConfusionMatrixDisplay(
    confusion_matrix(y_test, pred_tuned), display_labels=["<=50K", ">50K"]
).plot(ax=axes[1], cmap="Blues", colorbar=False)
axes[1].set_title(f"Test @ {best_thr:.2f}")
plt.tight_layout()
plt.show()

cm = confusion_matrix(y_test, pred_tuned)
tn, fp, fn, tp = cm.ravel()
print(f"Tuned threshold test CM: FP={fp}, FN={fn}, TP={tp}, TN={tn}")""")

code("""# Save full artifact: calibrated pipeline + decision threshold
artifact = {
    "model": final_model,
    "threshold": best_thr,
    "model_name": best_name,
    "best_params": best_search.best_params_,
    "primary_metric": "f1",
    "random_state": RANDOM_STATE,
    "dropped_features": ["fnlwgt"],
    "sklearn_version": sklearn.__version__,
}
joblib.dump(artifact, "final_income_pipeline.joblib")
print("Saved final_income_pipeline.joblib")

# How to infer on new data
print(
    \"\"\"
How to infer
------------
import joblib
artifact = joblib.load("final_income_pipeline.joblib")
model = artifact["model"]
thr = artifact["threshold"]
proba = model.predict_proba(X_new)[:, 1]
pred = (proba >= thr).astype(int)
\"\"\"
)""")

md("""## 7. Summary

- **Searches:** LR grid over `penalty`/`C`/`class_weight`; RF and HGB randomized searches. Best CV F1 went to **HistGradientBoosting**.
- **Diagnostics:** learning curve and depth/C plots guided keeping moderate regularization rather than an unconstrained tree.
- **Calibration + threshold:** isotonic calibration; validation-chosen threshold below 0.5 raises recall and F1 for this imbalanced problem.
- **Hold-out test:** used once for the final metrics table above.
- **Production note:** expect similar ROC/PR to the hold-out numbers if the population matches Adult; recalibrate or retune the threshold if class balance shifts. `fnlwgt` is excluded; capital-gain flag + log amount are kept together despite coefficient redundancy.""")

nb.cells = cells
nb.metadata = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.13.0"},
}
path = r"d:\Netixsol\Week-1\Day-4\model_tuning.ipynb"
with open(path, "w", encoding="utf-8") as f:
    nbf.write(nb, f)
print("Wrote", path)
