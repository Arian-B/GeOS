import json
import os
import time

try:
    import pandas as pd
    from sklearn.base import clone
    from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
    from sklearn.model_selection import ParameterGrid, StratifiedKFold
except Exception as exc:
    pd = None
    clone = None
    accuracy_score = None
    balanced_accuracy_score = None
    f1_score = None
    ParameterGrid = None
    StratifiedKFold = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

from ml_engine.policy_features import feature_columns
from ml_engine.train_policy_model import (
    DATASET,
    TARGET_COLUMN,
    LIGHTGBM_PARAMS_FILE,
    _build_pipeline,
    load_lightgbm_params,
)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_OUT = os.path.join(BASE_DIR, "ml_engine", "lightgbm_tuning_report.json")


def _require_dependencies():
    if IMPORT_ERROR is not None:
        raise RuntimeError(
            "Tuning dependencies are missing. Install pandas and scikit-learn."
        ) from IMPORT_ERROR


def _load_dataset():
    if not os.path.exists(DATASET):
        raise FileNotFoundError(DATASET)
    df = pd.read_csv(DATASET).dropna(subset=[TARGET_COLUMN]).copy()
    missing = [name for name in feature_columns() if name not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required feature columns: {missing}")
    return df


def _candidate_param_sets():
    baseline = load_lightgbm_params()
    grid = {
        "n_estimators": [200, 300],
        "learning_rate": [0.03, 0.05],
        "num_leaves": [31, 63],
        "min_child_samples": [20, 40],
        "subsample": [0.8, 0.95],
        "colsample_bytree": [0.8, 0.95],
    }
    candidates = []
    seen = set()

    def _normalized(params):
        return tuple(sorted(params.items()))

    candidates.append(dict(baseline))
    seen.add(_normalized(dict(baseline)))

    for params in ParameterGrid(grid):
        merged = dict(baseline)
        merged.update(params)
        key = _normalized(merged)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(merged)
        if len(candidates) >= 17:
            break
    return candidates


def _score_candidate(params, X, y, folds=5):
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
    rows = []
    for fold_index, (train_idx, test_idx) in enumerate(splitter.split(X, y), start=1):
        model = clone(_build_pipeline(params))
        X_train = X.iloc[train_idx]
        y_train = y.iloc[train_idx]
        X_test = X.iloc[test_idx]
        y_test = y.iloc[test_idx]

        started = time.perf_counter()
        model.fit(X_train, y_train)
        train_seconds = time.perf_counter() - started

        preds = model.predict(X_test)
        rows.append(
            {
                "fold": fold_index,
                "accuracy": float(accuracy_score(y_test, preds)),
                "balanced_accuracy": float(balanced_accuracy_score(y_test, preds)),
                "macro_f1": float(f1_score(y_test, preds, average="macro")),
                "train_seconds": float(train_seconds),
            }
        )

    def avg(metric):
        return round(sum(item[metric] for item in rows) / len(rows), 4)

    return {
        "params": params,
        "accuracy": avg("accuracy"),
        "balanced_accuracy": avg("balanced_accuracy"),
        "macro_f1": avg("macro_f1"),
        "train_seconds": avg("train_seconds"),
        "fold_metrics": rows,
    }


def _score_key(result):
    return (
        result["balanced_accuracy"],
        result["macro_f1"],
        result["accuracy"],
        -result["train_seconds"],
    )


def main():
    _require_dependencies()
    df = _load_dataset()
    X = df[feature_columns()]
    y = df[TARGET_COLUMN]

    results = []
    for params in _candidate_param_sets():
        results.append(_score_candidate(params, X, y))

    results.sort(key=_score_key, reverse=True)
    best = results[0]

    with open(LIGHTGBM_PARAMS_FILE, "w") as f:
        json.dump(best["params"], f, indent=2)

    report = {
        "dataset": os.path.abspath(DATASET),
        "rows": int(len(df)),
        "best": best,
        "candidates": results,
    }
    with open(REPORT_OUT, "w") as f:
        json.dump(report, f, indent=2)

    print("[ML] LightGBM tuning results")
    print(f"Rows: {len(df)}")
    print(f"Best balanced accuracy: {best['balanced_accuracy']:.4f}")
    print(f"Best macro F1: {best['macro_f1']:.4f}")
    print("Best params:")
    print(json.dumps(best["params"], indent=2))
    print(f"[ML] Saved tuned params to {LIGHTGBM_PARAMS_FILE}")
    print(f"[ML] Saved tuning report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
