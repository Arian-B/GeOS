# ml_engine/policy_optimizer.py

import os
import joblib
import pandas as pd

from ml_engine.infer_model import predict_mode

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_FILE = os.path.join(BASE_DIR, "ml_engine", "policy_reward_model.pkl")

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

ACTIONS = ["ENERGY_SAVER", "BALANCED", "PERFORMANCE"]
ACTION_TO_ID = {"ENERGY_SAVER": 0, "BALANCED": 1, "PERFORMANCE": 2}

_model = None


def _load_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_FILE):
            return None
        _model = joblib.load(MODEL_FILE)
    return _model


def predict_best_mode(features: dict):
    """
    Predict the best mode using the reward model if available.
    Falls back to the policy classifier when data/model is missing.
    Returns: (mode_name, confidence_float)
    """
    missing = [f for f in FEATURES if features.get(f) is None]
    if missing:
        try:
            return predict_mode(features), 0.25
        except Exception:
            return "BALANCED", 0.1

    model = _load_model()
    if model is None:
        try:
            return predict_mode(features), 0.25
        except Exception:
            return "BALANCED", 0.1

    rows = []
    for action in ACTIONS:
        row = [features[f] for f in FEATURES]
        row.append(ACTION_TO_ID[action])
        rows.append(row)

    df = pd.DataFrame(rows, columns=FEATURES + ["action_id"])
    try:
        rewards = model.predict(df).tolist()
    except Exception:
        try:
            return predict_mode(features), 0.25
        except Exception:
            return "BALANCED", 0.1

    best_idx = max(range(len(rewards)), key=lambda i: rewards[i])
    best_action = ACTIONS[best_idx]

    sorted_rewards = sorted(rewards, reverse=True)
    if len(sorted_rewards) > 1:
        margin = sorted_rewards[0] - sorted_rewards[1]
    else:
        margin = abs(sorted_rewards[0])

    denom = abs(sorted_rewards[0]) + 1e-6
    confidence = max(0.1, min(0.95, margin / denom))

    return best_action, confidence
