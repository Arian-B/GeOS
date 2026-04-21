import json
import os
import time

try:
    import pandas as pd
    from lightgbm import LGBMClassifier
    from sklearn.base import clone
    from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import StratifiedKFold
    from sklearn.preprocessing import StandardScaler
except Exception as exc:
    pd = None
    LGBMClassifier = None
    clone = None
    ExtraTreesClassifier = None
    HistGradientBoostingClassifier = None
    RandomForestClassifier = None
    SimpleImputer = None
    LogisticRegression = None
    accuracy_score = None
    balanced_accuracy_score = None
    f1_score = None
    Pipeline = None
    StratifiedKFold = None
    StandardScaler = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

try:
    from catboost import CatBoostClassifier
except Exception:
    CatBoostClassifier = None

from ml_engine.policy_features import feature_columns
from ml_engine.train_policy_model import DATASET, TARGET_COLUMN, load_lightgbm_params


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_OUT = os.path.join(BASE_DIR, "ml_engine", "benchmark_results.json")


def _require_dependencies():
    if IMPORT_ERROR is not None:
        raise RuntimeError(
            "Benchmark dependencies are missing. Install lightgbm, pandas, and scikit-learn."
        ) from IMPORT_ERROR


def _pipeline(model):
    imputer = SimpleImputer(strategy="median")
    try:
        imputer.set_output(transform="pandas")
    except Exception:
        pass
    return Pipeline(
        steps=[
            ("imputer", imputer),
            ("model", model),
        ]
    )


def _scaled_pipeline(model):
    imputer = SimpleImputer(strategy="median")
    try:
        imputer.set_output(transform="pandas")
    except Exception:
        pass
    return Pipeline(
        steps=[
            ("imputer", imputer),
            ("scaler", StandardScaler()),
            ("model", model),
        ]
    )


def _candidate_models():
    lightgbm_params = load_lightgbm_params()
    models = {
        "LightGBM": _pipeline(
            LGBMClassifier(**lightgbm_params)
        ),
        "HistGradientBoosting": _pipeline(
            HistGradientBoostingClassifier(
                learning_rate=0.05,
                max_depth=8,
                max_iter=250,
                random_state=42,
            )
        ),
        "RandomForest": _pipeline(
            RandomForestClassifier(
                n_estimators=300,
                max_depth=None,
                min_samples_leaf=1,
                random_state=42,
                n_jobs=1,
            )
        ),
        "ExtraTrees": _pipeline(
            ExtraTreesClassifier(
                n_estimators=300,
                max_depth=None,
                min_samples_leaf=1,
                random_state=42,
                n_jobs=1,
            )
        ),
        "LogisticRegression": _scaled_pipeline(
            LogisticRegression(
                max_iter=4000,
                random_state=42,
            )
        ),
    }
    if CatBoostClassifier is not None:
        models["CatBoost"] = CatBoostClassifier(
            loss_function="MultiClass",
            iterations=250,
            learning_rate=0.05,
            depth=6,
            random_seed=42,
            verbose=False,
        )
    return models


def _chronological_split(df):
    chrono = df.copy()
    if "timestamp" in chrono.columns:
        chrono = chrono.sort_values("timestamp").reset_index(drop=True)
    split_idx = max(1, int(len(chrono) * 0.8))
    train_df = chrono.iloc[:split_idx].copy()
    test_df = chrono.iloc[split_idx:].copy()
    if test_df.empty:
        raise ValueError("Chronological holdout split produced no test rows")
    return train_df, test_df


def _evaluate_model(name, estimator, X_train, y_train, X_test, y_test):
    start_train = time.perf_counter()
    estimator.fit(X_train, y_train)
    train_seconds = time.perf_counter() - start_train

    start_predict = time.perf_counter()
    preds = estimator.predict(X_test)
    predict_seconds = time.perf_counter() - start_predict

    rows = max(1, len(X_test))
    return {
        "model": name,
        "train_seconds": round(train_seconds, 4),
        "predict_seconds": round(predict_seconds, 4),
        "predict_ms_per_row": round((predict_seconds / rows) * 1000.0, 6),
        "accuracy": round(float(accuracy_score(y_test, preds)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_test, preds)), 4),
        "macro_f1": round(float(f1_score(y_test, preds, average="macro")), 4),
    }


def _tail_class_diagnostics(train_df, test_df):
    train_classes = sorted(str(value) for value in train_df[TARGET_COLUMN].dropna().unique().tolist())
    test_classes = sorted(str(value) for value in test_df[TARGET_COLUMN].dropna().unique().tolist())
    missing_in_test = [value for value in train_classes if value not in test_classes]
    counts = test_df[TARGET_COLUMN].value_counts().to_dict()
    dominant_share = 0.0
    if counts:
        dominant_share = max(counts.values()) / max(1, len(test_df))
    return {
        "train_classes": train_classes,
        "test_classes": test_classes,
        "missing_in_test": missing_in_test,
        "dominant_test_share": round(float(dominant_share), 4),
        "is_degenerate": bool(missing_in_test) or dominant_share >= 0.95,
    }


def _cross_validated_result(name, estimator, X, y, n_splits=5):
    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    fold_metrics = []

    for fold_index, (train_idx, test_idx) in enumerate(splitter.split(X, y), start=1):
        model = clone(estimator)
        X_train = X.iloc[train_idx]
        y_train = y.iloc[train_idx]
        X_test = X.iloc[test_idx]
        y_test = y.iloc[test_idx]

        row = _evaluate_model(name, model, X_train, y_train, X_test, y_test)
        row["fold"] = fold_index
        fold_metrics.append(row)

    def avg(metric):
        return round(sum(item[metric] for item in fold_metrics) / len(fold_metrics), 4)

    return {
        "model": name,
        "cv_folds": n_splits,
        "accuracy": avg("accuracy"),
        "balanced_accuracy": avg("balanced_accuracy"),
        "macro_f1": avg("macro_f1"),
        "train_seconds": avg("train_seconds"),
        "predict_seconds": avg("predict_seconds"),
        "predict_ms_per_row": avg("predict_ms_per_row"),
        "fold_metrics": fold_metrics,
    }


def _score_key(result):
    return (
        result["balanced_accuracy"],
        result["macro_f1"],
        result["accuracy"],
        -result["predict_ms_per_row"],
        -result["train_seconds"],
    )


def main():
    _require_dependencies()
    if not os.path.exists(DATASET):
        raise FileNotFoundError(DATASET)

    df = pd.read_csv(DATASET).dropna(subset=[TARGET_COLUMN]).copy()
    columns = feature_columns()
    missing = [name for name in columns if name not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required feature columns: {missing}")

    train_df, test_df = _chronological_split(df)
    tail_diagnostics = _tail_class_diagnostics(train_df, test_df)

    X_all = df[columns]
    y_all = df[TARGET_COLUMN]
    cv_results = []
    for name, estimator in _candidate_models().items():
        try:
            cv_results.append(_cross_validated_result(name, estimator, X_all, y_all))
        except Exception as exc:
            cv_results.append(
                {
                    "model": name,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    successful = [row for row in cv_results if "error" not in row]
    successful.sort(key=_score_key, reverse=True)
    winner = successful[0]["model"] if successful else None

    tail_results = []
    for name, estimator in _candidate_models().items():
        try:
            tail_results.append(
                _evaluate_model(
                    name,
                    clone(estimator),
                    train_df[columns],
                    train_df[TARGET_COLUMN],
                    test_df[columns],
                    test_df[TARGET_COLUMN],
                )
            )
        except Exception as exc:
            tail_results.append({"model": name, "error": f"{type(exc).__name__}: {exc}"})

    payload = {
        "dataset": os.path.abspath(DATASET),
        "rows_total": int(len(df)),
        "rows_train": int(len(train_df)),
        "rows_test": int(len(test_df)),
        "primary_method": "stratified_5_fold_cv",
        "chronological_tail_method": "chronological_80_20",
        "chronological_tail_diagnostics": tail_diagnostics,
        "winner": winner,
        "results": cv_results,
        "ranked_results": successful,
        "chronological_tail_results": tail_results,
    }

    with open(RESULTS_OUT, "w") as f:
        json.dump(payload, f, indent=2)

    print("[ML] Benchmark results")
    print(f"Dataset rows: {len(df)}")
    print("Primary benchmark: stratified 5-fold cross-validation")
    for row in successful:
        print(
            f"{row['model']:<22} "
            f"acc={row['accuracy']:.4f} "
            f"macro_f1={row['macro_f1']:.4f} "
            f"balanced_acc={row['balanced_accuracy']:.4f} "
            f"train_s={row['train_seconds']:.4f} "
            f"ms_per_row={row['predict_ms_per_row']:.6f}"
        )
    for row in cv_results:
        if "error" in row:
            print(f"{row['model']:<22} ERROR {row['error']}")
    print("\nChronological tail diagnostic")
    print(f"Train rows: {len(train_df)}")
    print(f"Test rows: {len(test_df)}")
    print(f"Test classes: {tail_diagnostics['test_classes']}")
    print(f"Missing classes in test tail: {tail_diagnostics['missing_in_test']}")
    print(f"Dominant test-class share: {tail_diagnostics['dominant_test_share']:.4f}")
    if tail_diagnostics["is_degenerate"]:
        print("Warning: chronological tail is class-degenerate, so it is not used to choose the benchmark winner.")
    else:
        for row in tail_results:
            if "error" in row:
                print(f"{row['model']:<22} ERROR {row['error']}")
                continue
            print(
                f"{row['model']:<22} "
                f"acc={row['accuracy']:.4f} "
                f"macro_f1={row['macro_f1']:.4f} "
                f"balanced_acc={row['balanced_accuracy']:.4f}"
            )
    print(f"[ML] Winner: {winner}")
    print(f"[ML] Saved benchmark report to {RESULTS_OUT}")


if __name__ == "__main__":
    main()
