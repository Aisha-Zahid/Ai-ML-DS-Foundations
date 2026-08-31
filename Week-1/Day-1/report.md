# Adult Income Prediction — ML Foundations

## Problem

Predict whether an individual earns more than $50K per year (1 = >50K, 0 = <=50K).

## Business Objective

The goal is to identify people likely to earn above $50K so outreach can focus on promising customers instead of spending effort on lower-income individuals.

## Primary Metric

F1 score was selected as the main evaluation metric. Precision alone would reduce wasted outreach but miss many actual high-income people. Recall alone would find more of them but increase false targets. F1 balances both types of error, which fits this use case.

---

## Dataset

| Stat | Value |
|------|-------|
| Rows | 48,842 |
| Features | 14 |
| Positive class (>50K) | 23.93% |
| Negative class (<=50K) | 76.07% |

Age is centered around the late 30s, hours-per-week clusters near 40, capital-gain is heavily skewed toward zero, and HS-grad / Bachelors are the most common education levels.

---

## Baseline Results

| Model | Accuracy | Precision | Recall | F1 | ROC AUC | PR AUC |
|-------|----------|-----------|--------|-----|---------|--------|
| Majority Baseline | 0.7607 | 0.0000 | 0.000 | 0.0000 | 0.5000 | 0.2393 |
| Education Rule (edu-num >= 13) | 0.7530 | 0.4844 | 0.4970 | 0.4906 | 0.6653 | 0.3611 |

The education rule performs better on F1 (0.49 vs 0.00). A stronger model would need to improve clearly on that score.

---

## Error Analysis

**False Positives (1,237):** Many have Bachelors-level education but still earn <=50K, often in lower-paying roles such as Adm-clerical or Other-service.

**False Negatives (1,176):** Several high-income individuals have education-num below 13 but show other signals such as higher capital-gain, longer hours, or professional occupations.

---

## Data Issues Identified

1. Missing values in workclass, occupation, and native-country
2. Categorical columns need encoding before modeling
3. Skewed numeric features (capital-gain, capital-loss)
4. Class imbalance (~24% positive)
5. Single-feature rule is too limited
6. Feature interactions (e.g. education + occupation) are not captured

---

## Conclusion

F1 will remain the primary metric. The majority baseline reached F1 = 0.00, while the education rule reached F1 = 0.4906. Further modeling work will aim to improve on that baseline while keeping precision and recall at reasonable levels.
