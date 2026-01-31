# ml_engine/feature_importance.py

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

model = joblib.load(MODEL_FILE)

importances = model.feature_importances_

df = pd.DataFrame({
    "feature": FEATURES,
    "importance": importances
}).sort_values(by="importance", ascending=False)

print("\nFeature Importance Ranking")
print("--------------------------")
print(df.to_string(index=False))

