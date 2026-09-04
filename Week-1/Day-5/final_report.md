# Adult Income Prediction — Final Project Report (Week 1)

## 1. Problem Definition

The goal is to predict whether a person earns more than 50K USD per year using UCI Adult census attributes. A business use case is targeting outreach toward likely high earners while limiting wasted contacts on lower-income individuals. **F1** was chosen as the primary metric because both false positives (wasted outreach) and false negatives (missed high earners) matter.

## 2. Data Preparation

The OpenML Adult dataset (48,842 rows, ~24% positive) was cleaned by mapping `?` to missing values and encoding income as 0/1. A **single stratified 80/20 hold-out split** (`random_state=42`) was fixed on Day 1 and reused all week so test metrics stay comparable.

Preprocessing used median imputation and scaling for numerics, and a `"Missing"` fill plus one-hot encoding for categoricals, all inside sklearn pipelines. Day 3 added eight row-level engineered features (age/hours bins, capital-gain flag and log, higher-education flag, education×hours, etc.). Target encoding was avoided to prevent leakage. `fnlwgt` was dropped in Day 4 as a sampling weight rather than a predictive personal attribute.

Validation strategy: model comparison and tuning used training data only (cross-validation / train-validation slices). The hold-out test set was scored only for final reporting.

## 3. Model Development

| Stage | Approach | Hold-out / CV F1 (approx.) |
|-------|----------|----------------------------|
| Day 1 | Majority baseline; education-num >= 13 rule | 0.00 / 0.49 |
| Day 2 | Logistic Regression; Decision Tree | 0.66 / 0.63 |
| Day 3 | LR, RF, HistGradientBoosting + engineered features (5-fold CV) | HGB ~0.71 CV |
| Day 4–5 | Tuned + calibrated HGB, threshold 0.33 | **0.726 test F1** |

Day 2 showed an unconstrained tree overfits badly. Day 3 confirmed HistGradientBoosting as the strongest family under CV.

## 4. Model Tuning

Day 4 optimized F1 with GridSearch (LR: penalty, C, class_weight) and RandomizedSearch (RF and HGB). Search used stratified 3-fold CV for a realistic compute budget. Best HGB settings: `learning_rate=0.15`, `max_iter=100`, `max_depth=None`, `l2_regularization=0.5`, `min_samples_leaf=10`. Logistic regression improved with `class_weight='balanced'`.

## 5. Diagnostics

Learning curves for tuned HGB showed train and CV F1 moving together without the extreme Day 2 tree gap. C-sweeps for LR and max_depth sweeps for HGB supported moderate regularization. Isotonic calibration slightly improved probability quality (Brier); threshold tuning on a **training validation slice** moved the operating point from 0.50 to **0.33**, raising recall and F1.

## 6. Final Results

Hold-out test (untouched until the end):

| Setup | F1 | Precision | Recall | ROC AUC |
|-------|-----|-----------|--------|---------|
| Uncalibrated @ 0.50 | 0.7155 | 0.7843 | 0.6578 | 0.9298 |
| Calibrated @ 0.50 | 0.7164 | 0.7972 | 0.6506 | 0.9299 |
| **Calibrated @ 0.33** | **0.7262** | 0.6707 | 0.7917 | 0.9299 |

Confusion matrix @ 0.33: TN=6522, FP=909, FN=487, TP=1851. False positives exceed false negatives; the lower threshold intentionally reduces missed high earners.

## 7. Model Interpretation

Permutation importance on the final model ranks **marital-status**, **capital-gain**, **age**, and **education-num** highest, then capital-loss, occupation, workclass, and hours. This matches earlier error analysis: education alone is not enough; life stage, capital activity, and job type matter. Marital status is highly predictive but should be handled carefully for fairness if used in real decisions.

Error patterns: FPs often look married / white-collar but still <=50K; FNs include skilled trades and some non-married high earners with weaker education signals.

## 8. Production Readiness

`final_model.joblib` holds the calibrated pipeline and threshold. Inference loads it, runs `predict_proba` on raw Adult columns, and applies threshold 0.33 — no manual preprocessing. Keep `feature_engineering.py` next to the artifact. After reload, probabilities match the in-memory model. Training and inference steps are in `README.md` (`random_state=42`).

## 9. Limitations and Future Improvements

- Class balance in new data may differ; threshold might need retuning.
- Search used 3-fold CV for speed; 5-fold or nested CV would be more thorough.
- Only a light look at sex/race subgroups — more fairness work before real use.
- Better features, more data, or cost-sensitive learning could cut FN/FP further.
- In production, watch whether probabilities stay well calibrated over time.

---

Week 1 ends with a tuned, calibrated model, a saved pipeline, a working inference script, and docs to reproduce the run.
