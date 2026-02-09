# ml_engine/feature_importance.py
"""
Feature importance extractor for GeOS ML policy model.

Outputs:
- Console ranking (for demo/review)
- CSV file (for plots / paper)
- JSON file (for GUI consumption)
"""

import os
import json
import joblib
import pandas as pd

# -----------------------------
# PATHS
# -----------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_FILE = os.path.join(BASE_DIR, "ml_engine", "policy_model.pkl")
OUT_DIR = os.path.join(BASE_DIR, "datasets")

os.makedirs(OUT_DIR, exist_ok=True)

CSV_OUT = os.path.join(OUT_DIR, "feature_importance.csv")
JSON_OUT = os.path.join(OUT_DIR, "feature_importance.json")

# -----------------------------
# FEATURE LIST (MUST MATCH TRAINING)
# -----------------------------
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

# -----------------------------
# LOAD MODEL
# -----------------------------
if not os.path.exists(MODEL_FILE):
    raise FileNotFoundError(f"Model not found: {MODEL_FILE}")

model = joblib.load(MODEL_FILE)

if not hasattr(model, "feature_importances_"):
    raise RuntimeError("Loaded model does not expose feature_importances_")

importances = model.feature_importances_

# -----------------------------
# BUILD DATAFRAME
# -----------------------------
df = pd.DataFrame({
    "feature": FEATURES,
    "importance": importances
})

# Normalize for readability (sum = 1)
df["importance"] = df["importance"] / df["importance"].sum()

df = df.sort_values(by="importance", ascending=False).reset_index(drop=True)

# -----------------------------
# SAVE OUTPUTS
# -----------------------------
df.to_csv(CSV_OUT, index=False)
df.to_json(JSON_OUT, orient="records", indent=2)

# -----------------------------
# CONSOLE OUTPUT (REVIEW FRIENDLY)
# -----------------------------
print("\n[ML] Feature Importance Ranking")
print("--------------------------------")
print(df.to_string(index=False))

print(f"\n[ML] Saved:")
print(f" - CSV : {CSV_OUT}")
print(f" - JSON: {JSON_OUT}")
