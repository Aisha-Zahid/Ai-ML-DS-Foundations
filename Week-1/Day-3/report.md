# Adult Income Prediction — Day 3 Write-Up

## Engineered Features

I added eight new features. Each one uses only values from the same row (no target encoding), so they fit cleanly inside the CV pipeline without leakage.

| Feature | Type | Rule | Why it might help | Univariate signal (train) |
|---------|------|------|-------------------|---------------------------|
| age_bucket | categorical | bins at 25/35/45/55/65 | Mid-career ages earn more | MI=0.063; >50K rate 2% (<=25) to 39% (46–55) |
| hours_bin | categorical | part-time / full / overtime / extreme | Work intensity is non-linear | MI=0.038; rate 7% (part-time) to 41% (extreme) |
| has_capital_gain | binary | capital-gain > 0 | Most people have zero gain | MI=0.032; rate 0.62 vs 0.21 |
| log_capital_gain | numeric | log1p(capital-gain) | Compresses heavy skew | MI=0.084 (highest) |
| is_higher_edu | binary | education-num >= 13 | Same threshold as Day 1 rule | MI=0.052; rate 0.48 vs 0.16 |
| edu_x_hours | numeric | education-num × hours | Interaction of skill and effort | MI=0.081; quintile spread ~0.45 |
| has_capital_loss | binary | capital-loss > 0 | Rare investment activity flag | MI=0.012; rate 0.50 vs 0.23 |
| is_full_time | binary | hours >= 40 | Simple full-time vs not flag | MI=0.026; rate 0.28 vs 0.09 |

I also considered a few options and skipped them: target encoding (easy to leak labels without nested CV), mean imputation (pulled around by outliers), dropping rows with missing values (loses data), and LabelEncoder (pretends categories are ordered).

---

## Cross-Validated Model Comparison

I used stratified 5-fold CV on the training set only, with the same Day 1 hold-out split left aside. All three models shared the same feature engineering and preprocessing steps.

| Model | F1 (mean ± std) | ROC AUC (mean ± std) | Accuracy mean |
|-------|-----------------|----------------------|---------------|
| HistGradientBoosting | 0.7084 ± 0.0094 | 0.9273 ± 0.0026 | ~0.87 |
| Logistic Regression | 0.6755 ± 0.0108 | 0.9136 ± 0.0033 | ~0.86 |
| Random Forest | 0.6616 ± 0.0085 | 0.9009 ± 0.0047 | ~0.85 |

Day 2 logistic regression had hold-out F1 = 0.6630. With the new features, CV F1 is about 0.676 for logistic regression and 0.708 for HistGradientBoosting — a clear improvement before any tuning. In the notebook boxplots, HGB stays ahead on both F1 and ROC AUC across folds.

---

## Statistical Comparison

The top two models by F1 were HistGradientBoosting and Logistic Regression.

- Mean F1 difference: 0.0329
- Paired t-test: p < 0.001
- Wilcoxon signed-rank: p ≈ 0.06 (only 5 folds, so this test is weak; HGB won every fold)

A roughly 3-point F1 gap is large enough that I will tune HistGradientBoosting first in Day 4. Logistic regression is still useful as a faster, more interpretable backup — especially for trying `class_weight='balanced'` later.

### Engineered features that mattered

- **Random Forest:** `edu_x_hours`, `log_capital_gain`, and `is_higher_edu` ranked highest among the new columns.
- **Logistic Regression:** `log_capital_gain` and `has_capital_gain` dominate (they overlap), then age buckets (young/old negative, mid-career positive) and part-time hours (negative).

That matches what we saw in Day 1 and Day 2: capital activity, education, and hours/life stage matter together. Education alone was never enough.

---

## Feature Selection Decision

| Setup | F1 mean | Notes |
|-------|---------|-------|
| All features | 0.7084 | Strong result |
| SelectKBest k=100 | 0.7088 | Almost the same; MI scoring takes longer |
| SelectKBest k=50 | 0.6990 | Clear drop |

For Day 4 I will keep all eight engineered features and the full feature set for HistGradientBoosting. Cutting to 50 features hurt F1, and k=100 did not really beat the full set.

**Day 4 plan:** tune HGB (learning rate, depth/leaf settings, iterations). I may also retry logistic regression with `class_weight='balanced'` and test dropping either `education` or `education-num`. The hold-out test set stays unused until after tuning.
