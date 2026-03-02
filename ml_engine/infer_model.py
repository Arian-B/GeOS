# ml_engine/infer_model.py

import joblib
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_FILE = os.path.join(BASE_DIR, "ml_engine", "policy_model.pkl")

FEATURES = [
    "cpu_percent",
    "load_avg",
    "memory_percent",
    "battery",
    "soil_moisture",
    "temperature",
    "humidity",
    "hour"
]

_model = None

def load_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_FILE):
            raise FileNotFoundError(
                f"ML model not found at {MODEL_FILE}. Train the model first."
            )
        _model = joblib.load(MODEL_FILE)
    return _model

def predict_mode(features: dict):
    """
    Predict OS mode using ML policy.
    Input: dict with system + sensor features.
    """
    # If critical features are missing, fall back to a neutral mode.
    for key in FEATURES:
        if features.get(key) is None:
            return "BALANCED"

    model = load_model()

    X = pd.DataFrame([[features[f] for f in FEATURES]], columns=FEATURES)
    return model.predict(X)[0]
