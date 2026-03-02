# ml_engine/auto_trainer.py

import json
import os
import threading
import time

try:
    import joblib
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor
except Exception:
    joblib = None
    pd = None
    RandomForestRegressor = None

from ml_engine.reward_model import compute_reward_continuous

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_FILE = os.path.join(BASE_DIR, "datasets", "telemetry_log.jsonl")
MODEL_FILE = os.path.join(BASE_DIR, "ml_engine", "policy_reward_model.pkl")
META_FILE = os.path.join(BASE_DIR, "ml_engine", "policy_reward_model.meta.json")

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

MIN_SAMPLES = 200
MAX_SAMPLES = 5000
TRAIN_INTERVAL_SECONDS = 30 * 60

_last_mtime = 0
_trainer_started = False


def _load_recent_records():
    if not os.path.exists(RAW_FILE):
        return []

    records = []
    try:
        with open(RAW_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []

    if len(records) > MAX_SAMPLES:
        records = records[-MAX_SAMPLES:]

    return records


def _build_training_frame(records):
    rows = []
    for rec in records:
        action = rec.get("os_mode")
        if action not in ACTIONS:
            continue

        # Ensure all required features exist and are not None.
        if any(rec.get(f) is None for f in FEATURES):
            continue

        reward = compute_reward_continuous(rec, action)
        row = {f: rec.get(f) for f in FEATURES}
        row["action_id"] = ACTION_TO_ID[action]
        row["reward"] = reward
        rows.append(row)

    if not rows:
        return None

    return pd.DataFrame(rows)


def train_once():
    global _last_mtime
    if joblib is None or pd is None or RandomForestRegressor is None:
        return False

    if not os.path.exists(RAW_FILE):
        return False

    mtime = os.path.getmtime(RAW_FILE)
    if mtime == _last_mtime:
        return False

    records = _load_recent_records()
    df = _build_training_frame(records)
    if df is None or len(df) < MIN_SAMPLES:
        return False

    X = df[FEATURES + ["action_id"]]
    y = df["reward"]

    model = RandomForestRegressor(
        n_estimators=120,
        max_depth=12,
        random_state=42
    )

    model.fit(X, y)
    joblib.dump(model, MODEL_FILE)

    meta = {
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "samples": int(len(df)),
        "features": FEATURES,
        "actions": ACTIONS
    }
    try:
        with open(META_FILE, "w") as f:
            json.dump(meta, f, indent=2)
    except Exception:
        pass

    _last_mtime = mtime
    return True


def _loop():
    while True:
        try:
            train_once()
        except Exception:
            pass
        time.sleep(TRAIN_INTERVAL_SECONDS)


def start_auto_trainer():
    global _trainer_started
    if _trainer_started:
        return None

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    _trainer_started = True
    return t
