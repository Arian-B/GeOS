import json
import os
import shutil
import time

try:
    import joblib
    import pandas as pd
    from lightgbm import LGBMClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.isotonic import IsotonicRegression
except Exception as exc:
    joblib = None
    pd = None
    LGBMClassifier = None
    SimpleImputer = None
    accuracy_score = None
    classification_report = None
    train_test_split = None
    Pipeline = None
    IsotonicRegression = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

from ml_engine.policy_features import feature_columns


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(BASE_DIR, "datasets", "telemetry.csv")
MODEL_OUT = os.path.join(BASE_DIR, "ml_engine", "policy_model.pkl")
META_OUT = os.path.join(BASE_DIR, "ml_engine", "policy_model.meta.json")
CALIBRATOR_OUT = os.path.join(BASE_DIR, "ml_engine", "policy_confidence_calibrator.pkl")
REGISTRY_DIR = os.path.join(BASE_DIR, "ml_engine", "model_registry")
REGISTRY_INDEX_OUT = os.path.join(REGISTRY_DIR, "registry_index.json")
FEATURE_IMPORTANCE_OUT = os.path.join(BASE_DIR, "datasets", "feature_importance.json")
LIGHTGBM_PARAMS_FILE = os.path.join(BASE_DIR, "ml_engine", "lightgbm_params.json")

TARGET_COLUMN = "os_mode"
MIN_ROWS = 120
DEFAULT_LIGHTGBM_PARAMS = {
    "objective": "multiclass",
    "n_estimators": 250,
    "learning_rate": 0.05,
    "num_leaves": 31,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "random_state": 42,
    "force_col_wise": True,
    "verbosity": -1,
}


def _require_dependencies():
    if IMPORT_ERROR is not None:
        raise RuntimeError(
            "LightGBM training dependencies are missing. "
            "Install lightgbm, pandas, joblib, and scikit-learn."
        ) from IMPORT_ERROR


def load_lightgbm_params():
    params = dict(DEFAULT_LIGHTGBM_PARAMS)
    if os.path.exists(LIGHTGBM_PARAMS_FILE):
        try:
            with open(LIGHTGBM_PARAMS_FILE, "r") as f:
                data = json.load(f)
            if isinstance(data, dict):
                params.update(data)
        except Exception:
            pass
    return params


def _build_pipeline(lightgbm_params=None):
    imputer = SimpleImputer(strategy="median")
    try:
        imputer.set_output(transform="pandas")
    except Exception:
        pass
    params = dict(DEFAULT_LIGHTGBM_PARAMS)
    if isinstance(lightgbm_params, dict):
        params.update(lightgbm_params)
    return Pipeline(
        steps=[
            ("imputer", imputer),
            (
                "model",
                LGBMClassifier(**params),
            ),
        ]
    )


def _fit_confidence_calibrator(model, X_calibration, y_calibration):
    if IsotonicRegression is None:
        return None, {}

    try:
        probabilities = model.predict_proba(X_calibration)
    except Exception:
        return None, {}

    raw_confidences = []
    correctness = []
    predictions = model.predict(X_calibration)

    for predicted, actual, row in zip(predictions, y_calibration.tolist(), probabilities):
        raw_confidences.append(float(max(row)))
        correctness.append(1.0 if str(predicted) == str(actual) else 0.0)

    if not raw_confidences:
        return None, {}

    calibrator = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    calibrator.fit(raw_confidences, correctness)
    calibrated = calibrator.predict(raw_confidences)

    def _brier(predicted_values, targets):
        total = 0.0
        count = 0
        for predicted_confidence, target in zip(predicted_values, targets):
            total += (float(predicted_confidence) - float(target)) ** 2
            count += 1
        return total / max(1, count)

    summary = {
        "method": "isotonic_on_top_probability",
        "rows": len(raw_confidences),
        "raw_brier": round(_brier(raw_confidences, correctness), 6),
        "calibrated_brier": round(_brier(calibrated, correctness), 6),
    }
    return calibrator, summary


def _save_registry_artifacts(version_id, meta):
    os.makedirs(REGISTRY_DIR, exist_ok=True)

    version_paths = {
        "model": os.path.join(REGISTRY_DIR, f"policy_model_{version_id}.pkl"),
        "meta": os.path.join(REGISTRY_DIR, f"policy_model_{version_id}.meta.json"),
        "calibrator": os.path.join(REGISTRY_DIR, f"policy_confidence_calibrator_{version_id}.pkl"),
    }

    shutil.copyfile(MODEL_OUT, version_paths["model"])
    shutil.copyfile(META_OUT, version_paths["meta"])
    if os.path.exists(CALIBRATOR_OUT):
        shutil.copyfile(CALIBRATOR_OUT, version_paths["calibrator"])
    else:
        version_paths["calibrator"] = None

    existing = []
    if os.path.exists(REGISTRY_INDEX_OUT):
        try:
            with open(REGISTRY_INDEX_OUT, "r") as f:
                existing = json.load(f)
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []

    entry = {
        "version_id": version_id,
        "trained_at": meta.get("trained_at"),
        "model_type": meta.get("model_type"),
        "rows": meta.get("rows"),
        "accuracy": meta.get("accuracy"),
        "paths": version_paths,
    }
    existing.insert(0, entry)

    with open(REGISTRY_INDEX_OUT, "w") as f:
        json.dump(existing[:20], f, indent=2)

    return entry


def _recommended_thresholds(df):
    battery_series = df.get("battery")
    soil_series = df.get("soil_moisture")
    temp_series = df.get("temperature")

    battery_threshold = 25
    soil_threshold = 35
    temp_threshold = 38

    if battery_series is not None and not battery_series.dropna().empty:
        battery_threshold = float(max(15, min(40, battery_series.quantile(0.2))))
    if soil_series is not None and not soil_series.dropna().empty:
        soil_threshold = float(max(20, min(50, soil_series.quantile(0.35))))
    if temp_series is not None and not temp_series.dropna().empty:
        temp_threshold = float(max(34, min(42, temp_series.quantile(0.85))))

    return {
        "battery_energy_saver": round(battery_threshold, 2),
        "soil_performance": round(soil_threshold, 2),
        "temperature_energy_saver": round(temp_threshold, 2),
    }


def train_from_dataframe(df, dataset_path=DATASET):
    _require_dependencies()

    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Dataset must include target column '{TARGET_COLUMN}'")

    columns = [name for name in feature_columns() if name in df.columns]
    if len(columns) != len(feature_columns()):
        missing = [name for name in feature_columns() if name not in df.columns]
        raise ValueError(f"Dataset is missing required feature columns: {missing}")

    train_df = df.dropna(subset=[TARGET_COLUMN]).copy()
    if len(train_df) < MIN_ROWS:
        raise ValueError(f"Need at least {MIN_ROWS} labeled rows for training")

    X = train_df[columns]
    y = train_df[TARGET_COLUMN]

    X_train_full, X_test, y_train_full, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    X_train, X_calibration, y_train, y_calibration = train_test_split(
        X_train_full,
        y_train_full,
        test_size=0.2,
        random_state=42,
        stratify=y_train_full,
    )

    active_params = load_lightgbm_params()
    pipeline = _build_pipeline(active_params)
    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_test)
    accuracy = float(accuracy_score(y_test, predictions))

    model = pipeline.named_steps["model"]
    importances = getattr(model, "feature_importances_", None)
    importance_rows = []
    if importances is not None:
        positive_importances = [max(0.0, float(value)) for value in importances]
        total = float(sum(positive_importances)) or 1.0
        for feature, score in sorted(
            zip(columns, positive_importances),
            key=lambda item: item[1],
            reverse=True,
        ):
            importance_rows.append(
                {"feature": feature, "importance": round(float(score) / total, 6)}
            )

    os.makedirs(os.path.dirname(MODEL_OUT), exist_ok=True)
    joblib.dump(pipeline, MODEL_OUT)

    if importance_rows:
        os.makedirs(os.path.dirname(FEATURE_IMPORTANCE_OUT), exist_ok=True)
        with open(FEATURE_IMPORTANCE_OUT, "w") as f:
            json.dump(importance_rows, f, indent=2)

    calibrator, calibration_summary = _fit_confidence_calibrator(
        pipeline,
        X_calibration,
        y_calibration,
    )
    if calibrator is not None:
        joblib.dump(calibrator, CALIBRATOR_OUT)
    elif os.path.exists(CALIBRATOR_OUT):
        os.remove(CALIBRATOR_OUT)

    trained_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    meta = {
        "model_type": "LightGBMClassifier",
        "trained_at": trained_at,
        "dataset": os.path.abspath(dataset_path),
        "rows": int(len(train_df)),
        "features": columns,
        "classes": sorted(str(value) for value in y.unique().tolist()),
        "accuracy": round(accuracy, 4),
        "lightgbm_params": active_params,
        "confidence_calibration": calibration_summary,
        "recommended_thresholds": _recommended_thresholds(train_df),
        "notes": [
            "Primary GeOS deployment model is LightGBM",
            "Hard safety overrides remain outside the ML model",
            "Temporal features are included via rolling averages and deltas",
            "Confidence score is calibrated from a held-out calibration split when available",
        ],
    }
    with open(META_OUT, "w") as f:
        json.dump(meta, f, indent=2)

    version_id = trained_at.replace(":", "").replace("-", "")
    registry_entry = _save_registry_artifacts(version_id, meta)
    meta["registry_entry"] = registry_entry
    with open(META_OUT, "w") as f:
        json.dump(meta, f, indent=2)

    print("[ML] LightGBM evaluation")
    print(classification_report(y_test, predictions))
    print(f"[ML] Accuracy: {accuracy:.4f}")
    print(f"[ML] Model saved to {MODEL_OUT}")
    print(f"[ML] Metadata saved to {META_OUT}")
    if calibration_summary:
        print(
            "[ML] Confidence calibration "
            f"(raw_brier={calibration_summary['raw_brier']:.6f}, "
            f"calibrated_brier={calibration_summary['calibrated_brier']:.6f})"
        )
    print(f"[ML] Versioned registry entry saved under {REGISTRY_DIR}")

    return {"accuracy": accuracy, "rows": len(train_df), "meta": meta}


def main():
    _require_dependencies()
    df = pd.read_csv(DATASET)
    train_from_dataframe(df)


if __name__ == "__main__":
    main()
