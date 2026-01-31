# ml_engine/ablation_study.py

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

DATASET = "datasets/telemetry.csv"

BASE_FEATURES = [
    "cpu_percent",
    "load_avg",
    "memory_percent",
    "battery",
    "soil_moisture",
    "temperature",
    "humidity",
    "hour"
]

df = pd.read_csv(DATASET)
y = df["os_mode"]

print("\nAblation Study Results")
print("----------------------")

for removed in BASE_FEATURES:
    features = [f for f in BASE_FEATURES if f != removed]
    X = df[features]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"Removed {removed:15s} → Accuracy: {acc:.3f}")
