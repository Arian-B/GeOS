import json
import os

try:
    import pandas as pd
    from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
except Exception as exc:
    pd = None
    accuracy_score = None
    balanced_accuracy_score = None
    f1_score = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

from ml_engine.policy_features import feature_columns
from ml_engine.train_policy_model import DATASET, TARGET_COLUMN, _build_pipeline, load_lightgbm_params


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_OUT = os.path.join(BASE_DIR, "ml_engine", "rolling_backtest_report.json")


def _require_dependencies():
    if IMPORT_ERROR is not None:
        raise RuntimeError(
            "Rolling backtest dependencies are missing. Install pandas and scikit-learn."
        ) from IMPORT_ERROR


def _load_dataset():
    if not os.path.exists(DATASET):
        raise FileNotFoundError(DATASET)
    df = pd.read_csv(DATASET).dropna(subset=[TARGET_COLUMN]).copy()
    if "timestamp" in df.columns:
        df = df.sort_values("timestamp").reset_index(drop=True)
    missing = [name for name in feature_columns() if name not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required feature columns: {missing}")
    return df


def _window_ranges(total_rows, train_ratio=0.5, test_ratio=0.1, max_windows=5):
    train_size = max(200, int(total_rows * train_ratio))
    test_size = max(100, int(total_rows * test_ratio))
    windows = []
    train_end = train_size
    while train_end + test_size <= total_rows and len(windows) < max_windows:
        windows.append((0, train_end, train_end, train_end + test_size))
        train_end += test_size
    return windows


def _summarize_classes(series):
    return {str(key): int(value) for key, value in series.value_counts().to_dict().items()}


def main():
    _require_dependencies()
    df = _load_dataset()
    columns = feature_columns()
    params = load_lightgbm_params()

    results = []
    for window_id, (train_start, train_end, test_start, test_end) in enumerate(
        _window_ranges(len(df)),
        start=1,
    ):
        train_df = df.iloc[train_start:train_end].copy()
        test_df = df.iloc[test_start:test_end].copy()
        if train_df.empty or test_df.empty:
            continue

        model = _build_pipeline(params)
        model.fit(train_df[columns], train_df[TARGET_COLUMN])
        preds = model.predict(test_df[columns])

        results.append(
            {
                "window": window_id,
                "train_rows": int(len(train_df)),
                "test_rows": int(len(test_df)),
                "train_classes": _summarize_classes(train_df[TARGET_COLUMN]),
                "test_classes": _summarize_classes(test_df[TARGET_COLUMN]),
                "accuracy": round(float(accuracy_score(test_df[TARGET_COLUMN], preds)), 4),
                "balanced_accuracy": round(float(balanced_accuracy_score(test_df[TARGET_COLUMN], preds)), 4),
                "macro_f1": round(float(f1_score(test_df[TARGET_COLUMN], preds, average="macro")), 4),
            }
        )

    def avg(metric):
        return round(sum(item[metric] for item in results) / max(1, len(results)), 4)

    report = {
        "dataset": os.path.abspath(DATASET),
        "rows": int(len(df)),
        "windows": results,
        "average_accuracy": avg("accuracy") if results else None,
        "average_balanced_accuracy": avg("balanced_accuracy") if results else None,
        "average_macro_f1": avg("macro_f1") if results else None,
        "lightgbm_params": params,
    }

    with open(REPORT_OUT, "w") as f:
        json.dump(report, f, indent=2)

    print("[ML] Rolling backtest results")
    print(f"Rows: {len(df)}")
    for row in results:
        print(
            f"window={row['window']} train={row['train_rows']} test={row['test_rows']} "
            f"acc={row['accuracy']:.4f} balanced_acc={row['balanced_accuracy']:.4f} macro_f1={row['macro_f1']:.4f}"
        )
    if results:
        print(f"Average accuracy: {report['average_accuracy']:.4f}")
        print(f"Average balanced accuracy: {report['average_balanced_accuracy']:.4f}")
        print(f"Average macro F1: {report['average_macro_f1']:.4f}")
    print(f"[ML] Saved rolling backtest report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
