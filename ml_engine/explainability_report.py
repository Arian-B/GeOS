import json
import os

try:
    import joblib
    import numpy as np
    import pandas as pd
except Exception as exc:
    joblib = None
    np = None
    pd = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

from ml_engine.lightgbm_policy import MODEL_FILE
from ml_engine.policy_features import feature_columns
from ml_engine.train_policy_model import DATASET, TARGET_COLUMN


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_OUT = os.path.join(BASE_DIR, "ml_engine", "explainability_report.json")


def _require_dependencies():
    if IMPORT_ERROR is not None:
        raise RuntimeError(
            "Explainability report dependencies are missing. Install pandas, numpy, and joblib."
        ) from IMPORT_ERROR


def _load_dataset():
    if not os.path.exists(DATASET):
        raise FileNotFoundError(DATASET)
    df = pd.read_csv(DATASET).dropna(subset=[TARGET_COLUMN]).copy()
    missing = [name for name in feature_columns() if name not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required feature columns: {missing}")
    return df


def _contribution_matrix(model, X):
    estimator = model.named_steps["model"]
    imputer = model.named_steps["imputer"]
    transformed = imputer.transform(X)
    contributions = estimator.booster_.predict(transformed, pred_contrib=True)
    arr = np.asarray(contributions)
    n_classes = len(estimator.classes_)
    block_size = arr.shape[1] // max(1, n_classes)
    return arr, [str(value) for value in estimator.classes_], block_size


def _top_feature_rows(feature_names_list, contribution_values, limit=10):
    pairs = sorted(
        zip(feature_names_list, contribution_values),
        key=lambda item: abs(float(item[1])),
        reverse=True,
    )[:limit]
    total = sum(abs(float(score)) for _, score in pairs) or 1.0
    rows = []
    for feature, score in pairs:
        score_value = float(score)
        rows.append(
            {
                "feature": feature,
                "importance": round(abs(score_value) / total, 6),
                "mean_contribution": round(score_value, 6),
                "direction": "supports_prediction" if score_value >= 0 else "opposes_prediction",
            }
        )
    return rows


def main():
    _require_dependencies()
    if not os.path.exists(MODEL_FILE):
        raise FileNotFoundError(MODEL_FILE)

    df = _load_dataset()
    feature_names_list = feature_columns()
    X = df[feature_names_list]
    y = df[TARGET_COLUMN].astype(str)

    model = joblib.load(MODEL_FILE)
    predictions = model.predict(X)
    contribution_array, classes, block_size = _contribution_matrix(model, X)

    class_summaries = {}
    exemplar_rows = {}

    for class_index, class_name in enumerate(classes):
        class_mask = (y == class_name).to_numpy()
        if not class_mask.any():
            continue

        start = class_index * block_size
        end = start + block_size - 1
        class_contribs = contribution_array[class_mask, start:end]
        mean_abs = np.mean(np.abs(class_contribs), axis=0)
        class_summaries[class_name] = _top_feature_rows(feature_names_list, mean_abs, limit=10)

        predicted_mask = np.array([str(value) == class_name for value in predictions]) & class_mask
        if predicted_mask.any():
            exemplar_index = int(np.flatnonzero(predicted_mask)[0])
            exemplar_scores = contribution_array[exemplar_index, start:end]
            exemplar_rows[class_name] = _top_feature_rows(feature_names_list, exemplar_scores, limit=5)

    report = {
        "dataset": os.path.abspath(DATASET),
        "rows": int(len(df)),
        "model": "LightGBMClassifier",
        "class_summaries": class_summaries,
        "example_local_explanations": exemplar_rows,
    }

    with open(REPORT_OUT, "w") as f:
        json.dump(report, f, indent=2)

    print("[ML] Explainability report")
    print(f"Rows: {len(df)}")
    for class_name, rows in class_summaries.items():
        top = ", ".join(row["feature"] for row in rows[:3])
        print(f"{class_name}: {top}")
    print(f"[ML] Saved explainability report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
