# ml_engine/train_policy_model.py
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

DATASET = "datasets/telemetry.csv"
MODEL_OUT = "ml_engine/policy_model.pkl"

def main():
    df = pd.read_csv(DATASET)

    features = [
        "cpu_percent",
        "load_avg",
        "memory_percent",
        "battery",
        "soil_moisture",
        "temperature",
        "humidity",
        "hour"
    ]

    X = df[features]
    y = df["os_mode"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestClassifier(
        n_estimators=150,
        max_depth=12,
        random_state=42
    )

    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    print("[ML] Evaluation")
    print(classification_report(y_test, preds))

    joblib.dump(model, MODEL_OUT)
    print(f"[ML] Model saved to {MODEL_OUT}")

if __name__ == "__main__":
    main()
