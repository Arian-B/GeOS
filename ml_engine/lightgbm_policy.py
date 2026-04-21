import json
import os
import math

try:
    import joblib
    import numpy as np
    import pandas as pd
except Exception:
    joblib = None
    np = None
    pd = None

from ml_engine.policy_features import feature_columns


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_FILE = os.path.join(BASE_DIR, "ml_engine", "policy_model.pkl")
META_FILE = os.path.join(BASE_DIR, "ml_engine", "policy_model.meta.json")
CALIBRATOR_FILE = os.path.join(BASE_DIR, "ml_engine", "policy_confidence_calibrator.pkl")
FEATURE_IMPORTANCE_FILE = os.path.join(BASE_DIR, "datasets", "feature_importance.json")

DEFAULT_MODE = "BALANCED"
DEFAULT_THRESHOLDS = {
    "battery_energy_saver": 25,
    "soil_performance": 35,
    "temperature_energy_saver": 38,
}

_model = None
_meta = None
_feature_importance = None
_calibrator = None


def _read_json(path, default):
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data if isinstance(data, (dict, list)) else default
    except Exception:
        return default


def feature_names():
    return feature_columns()


def load_metadata():
    global _meta
    if _meta is None:
        _meta = _read_json(META_FILE, {})
    return _meta


def load_feature_importance():
    global _feature_importance
    if _feature_importance is None:
        data = _read_json(FEATURE_IMPORTANCE_FILE, [])
        if isinstance(data, list):
            _feature_importance = data
        else:
            _feature_importance = []
    return _feature_importance


def load_model():
    global _model
    if _model is not None:
        return _model
    if joblib is None:
        raise RuntimeError("joblib is required to load the ML model")
    if not os.path.exists(MODEL_FILE):
        raise FileNotFoundError(f"ML model not found at {MODEL_FILE}")
    _model = joblib.load(MODEL_FILE)
    return _model


def load_calibrator():
    global _calibrator
    if _calibrator is not None:
        return _calibrator
    if joblib is None or not os.path.exists(CALIBRATOR_FILE):
        return None
    try:
        _calibrator = joblib.load(CALIBRATOR_FILE)
    except Exception:
        _calibrator = None
    return _calibrator


def _prepare_frame(feature_row):
    columns = feature_names()
    row = {name: feature_row.get(name) for name in columns}
    if pd is not None:
        return pd.DataFrame([row], columns=columns), columns
    return [[row.get(name) for name in columns]], columns


def _local_top_features(model, frame, prediction, limit=3):
    estimator = getattr(model, "named_steps", {}).get("model", model)
    imputer = getattr(model, "named_steps", {}).get("imputer")
    booster = getattr(estimator, "booster_", None)
    classes = [str(value) for value in getattr(estimator, "classes_", [])]

    if booster is None or np is None or not classes:
        return []

    try:
        transformed = imputer.transform(frame) if imputer is not None else frame
        contributions = booster.predict(transformed, pred_contrib=True)
    except Exception:
        return []

    try:
        contribution_array = np.asarray(contributions)
    except Exception:
        return []

    if contribution_array.ndim != 2 or contribution_array.shape[0] < 1:
        return []

    n_classes = len(classes)
    block_size = contribution_array.shape[1] // max(1, n_classes)
    if block_size <= 1:
        return []

    try:
        class_index = classes.index(str(prediction))
    except ValueError:
        class_index = 0

    start = class_index * block_size
    end = start + block_size
    class_block = contribution_array[0][start:end]
    feature_scores = class_block[:-1]
    feature_names_list = feature_names()
    pairs = list(zip(feature_names_list, feature_scores))

    positive_pairs = [item for item in pairs if float(item[1]) > 0]
    ranked = sorted(
        positive_pairs if positive_pairs else pairs,
        key=lambda item: abs(float(item[1])),
        reverse=True,
    )
    top = ranked[:limit]
    total = sum(abs(float(score)) for _, score in top) or 1.0

    rows = []
    for feature, score in top:
        score_value = float(score)
        rows.append(
            {
                "feature": feature,
                "importance": round(abs(score_value) / total, 6),
                "contribution": round(score_value, 6),
                "direction": "supports_prediction" if score_value >= 0 else "opposes_prediction",
            }
        )
    return rows


def model_ready():
    return os.path.exists(MODEL_FILE)


def current_thresholds():
    meta = load_metadata()
    thresholds = meta.get("recommended_thresholds")
    if isinstance(thresholds, dict):
        merged = DEFAULT_THRESHOLDS.copy()
        merged.update(thresholds)
        return merged
    return DEFAULT_THRESHOLDS.copy()


def top_features(limit=3):
    items = []
    for entry in load_feature_importance():
        if not isinstance(entry, dict):
            continue
        feature = entry.get("feature")
        importance = entry.get("importance")
        if feature is None or importance is None:
            continue
        items.append({"feature": feature, "importance": float(importance)})
    return items[:limit]


def predict_policy(feature_row):
    meta = load_metadata()
    model_type = meta.get("model_type", "UnknownModel")
    result = {
        "mode": DEFAULT_MODE,
        "confidence": 0.0,
        "source": "FALLBACK",
        "model_type": model_type,
        "top_features": top_features(),
    }

    if not feature_row:
        return result

    if model_type != "LightGBMClassifier":
        result["source"] = "INVALID_MODEL_ARTIFACT"
        return result

    try:
        model = load_model()
    except Exception:
        return result

    frame, _ = _prepare_frame(feature_row)
    prediction = model.predict(frame)[0]
    raw_confidence = 0.55

    if hasattr(model, "predict_proba"):
        try:
            proba = model.predict_proba(frame)[0]
            raw_confidence = max(float(value) for value in proba)
        except Exception:
            raw_confidence = 0.55

    confidence = raw_confidence
    calibrator = load_calibrator()
    if calibrator is not None:
        try:
            calibrated = calibrator.predict([raw_confidence])[0]
            confidence = float(calibrated)
            result["confidence_source"] = "CALIBRATED"
            result["raw_confidence"] = max(0.0, min(1.0, raw_confidence))
        except Exception:
            confidence = raw_confidence

    result["mode"] = str(prediction)
    result["confidence"] = max(0.0, min(1.0, confidence))
    result["source"] = "LIGHTGBM"
    local_features = _local_top_features(model, frame, prediction)
    if local_features:
        result["top_features"] = local_features
    return result
