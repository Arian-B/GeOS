import os
import json

try:
    import joblib
    import pandas as pd
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
except Exception as exc:
    joblib = None
    pd = None
    accuracy_score = None
    classification_report = None
    confusion_matrix = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

from ml_engine.policy_features import feature_columns
from ml_engine.train_policy_model import DATASET, MODEL_OUT, TARGET_COLUMN, _build_pipeline, load_lightgbm_params


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_OUT = os.path.join(BASE_DIR, "ml_engine", "evaluation_report.json")


def _require_dependencies():
    if IMPORT_ERROR is not None:
        raise RuntimeError(
            "Evaluation dependencies are missing. Install pandas, joblib, and scikit-learn."
        ) from IMPORT_ERROR


def _load_dataset():
    if not os.path.exists(DATASET):
        raise FileNotFoundError(DATASET)
    df = pd.read_csv(DATASET).dropna(subset=[TARGET_COLUMN]).copy()
    missing = [name for name in feature_columns() if name not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required feature columns: {missing}")
    return df


def _chronological_split(df):
    chrono = df.copy()
    if "timestamp" in chrono.columns:
        chrono = chrono.sort_values("timestamp").reset_index(drop=True)
    split_idx = max(1, int(len(chrono) * 0.8))
    train_df = chrono.iloc[:split_idx].copy()
    holdout_df = chrono.iloc[split_idx:].copy()
    if holdout_df.empty:
        raise ValueError("Chronological holdout split produced no test rows")
    return train_df, holdout_df


def _metric_summary(y_true, y_pred):
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "classification_report": classification_report(y_true, y_pred, output_dict=True),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }


def main():
    _require_dependencies()
    if not os.path.exists(MODEL_OUT):
        raise FileNotFoundError(MODEL_OUT)

    df = _load_dataset()
    columns = feature_columns()
    X = df[columns]
    y = df[TARGET_COLUMN]

    model = joblib.load(MODEL_OUT)
    replay_preds = model.predict(X)
    replay_metrics = _metric_summary(y, replay_preds)

    report = {
        "dataset": os.path.abspath(DATASET),
        "rows": int(len(df)),
        "artifact_replay": replay_metrics,
    }

    print("[ML] Policy evaluation")
    print(f"Rows: {len(df)}")
    print("\nArtifact replay metrics")
    print("Caution: this evaluates the saved artifact on the dataset it was built from.")
    print(f"Accuracy: {replay_metrics['accuracy']:.4f}")
    print("\nClassification report")
    print(classification_report(y, replay_preds))
    print("Confusion matrix")
    print(confusion_matrix(y, replay_preds))

    if "current_mode" in df.columns:
        deployed_agreement = accuracy_score(df["current_mode"], replay_preds)
        report["artifact_replay"]["deployed_mode_agreement"] = round(float(deployed_agreement), 4)
        print(f"\nAgreement with deployed mode column: {deployed_agreement:.4f}")

    train_df, holdout_df = _chronological_split(df)
    fresh_model = _build_pipeline(load_lightgbm_params())
    fresh_model.fit(train_df[columns], train_df[TARGET_COLUMN])
    holdout_preds = fresh_model.predict(holdout_df[columns])
    holdout_metrics = _metric_summary(holdout_df[TARGET_COLUMN], holdout_preds)
    report["fresh_chronological_holdout"] = {
        "rows_train": int(len(train_df)),
        "rows_test": int(len(holdout_df)),
        **holdout_metrics,
    }

    print("\nFresh chronological holdout")
    print("This is the defensible generalization estimate for GeOS.")
    print(f"Train rows: {len(train_df)}")
    print(f"Test rows: {len(holdout_df)}")
    print(f"Accuracy: {holdout_metrics['accuracy']:.4f}")
    print(classification_report(holdout_df[TARGET_COLUMN], holdout_preds))

    with open(REPORT_OUT, "w") as f:
        json.dump(report, f, indent=2)
    print(f"[ML] Saved evaluation report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
