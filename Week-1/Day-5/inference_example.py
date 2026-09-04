"""
Load final_model.joblib and score a few hold-out rows.

Run from the Day-5 folder:
    python inference_example.py
"""
import numpy as np
import pandas as pd
import joblib
from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split

RANDOM_STATE = 42


def predict_income(new_data, artifact_path="final_model.joblib"):
    artifact = joblib.load(artifact_path)
    model = artifact["model"]
    threshold = artifact["threshold"]
    if isinstance(new_data, dict):
        new_data = pd.DataFrame([new_data])
    proba = model.predict_proba(new_data)[:, 1]
    pred = (proba >= threshold).astype(int)
    return pd.DataFrame({
        "prediction": pred,
        "probability_over_50k": proba,
        "label": np.where(pred == 1, ">50K", "<=50K"),
    })


if __name__ == "__main__":
    adult = fetch_openml("adult", version=2, as_frame=True, parser="auto")
    df = adult.frame.copy()
    df = df.rename(columns={"class": "income"})
    df = df.replace(r"^\s*\?$", np.nan, regex=True)
    df["income"] = df["income"].astype(str).map({"<=50K": 0, ">50K": 1})
    X = df.drop("income", axis=1)
    y = df["income"]
    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
    )

    sample = X_test.sample(8, random_state=RANDOM_STATE)
    out = predict_income(sample)
    out["actual"] = y_test.loc[sample.index].values
    print(out.round(4).to_string(index=False))
    print("\nCorrect:", int((out["prediction"] == out["actual"]).sum()), "/", len(out))
    print("Threshold used:", joblib.load("final_model.joblib")["threshold"])
