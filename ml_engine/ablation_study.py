import os

try:
    import pandas as pd
    from lightgbm import LGBMClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import accuracy_score
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
except Exception as exc:
    pd = None
    LGBMClassifier = None
    SimpleImputer = None
    accuracy_score = None
    train_test_split = None
    Pipeline = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

from ml_engine.policy_features import feature_columns
from ml_engine.train_policy_model import DATASET, TARGET_COLUMN


def _require_dependencies():
    if IMPORT_ERROR is not None:
        raise RuntimeError(
            "Ablation dependencies are missing. Install lightgbm, pandas, and scikit-learn."
        ) from IMPORT_ERROR


def _train_score(df, columns):
    X = df[columns]
    y = df[TARGET_COLUMN]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    imputer = SimpleImputer(strategy="median")
    try:
        imputer.set_output(transform="pandas")
    except Exception:
        pass
    pipeline = Pipeline(
        steps=[
            ("imputer", imputer),
            (
                "model",
                LGBMClassifier(
                    objective="multiclass",
                    n_estimators=200,
                    learning_rate=0.05,
                    num_leaves=31,
                    random_state=42,
                ),
            ),
        ]
    )
    pipeline.fit(X_train, y_train)
    return accuracy_score(y_test, pipeline.predict(X_test))


def main():
    _require_dependencies()
    if not os.path.exists(DATASET):
        raise FileNotFoundError(DATASET)

    df = pd.read_csv(DATASET).dropna(subset=[TARGET_COLUMN])
    base_columns = feature_columns()

    print("\n[ML] Ablation study results")
    print("---------------------------")
    base_score = _train_score(df, base_columns)
    print(f"Base accuracy: {base_score:.4f}")

    groups = {
        "cpu": [c for c in base_columns if c.startswith("cpu_percent")],
        "load": [c for c in base_columns if c.startswith("load_avg")],
        "memory": [c for c in base_columns if c.startswith("memory_percent")],
        "battery": [c for c in base_columns if c.startswith("battery")],
        "soil": [c for c in base_columns if c.startswith("soil_moisture") or c == "soil_dry_streak"],
        "temperature": [c for c in base_columns if c.startswith("temperature") or c == "temp_high_streak"],
        "humidity": [c for c in base_columns if c.startswith("humidity")],
        "time": [c for c in ("hour", "hour_sin", "hour_cos")],
        "network": ["network_online"],
        "context": [
            c for c in base_columns
            if c in (
                "control_auto",
                "control_manual",
                "maintenance_enabled",
                "safe_mode_enabled",
                "emergency_shutdown_enabled",
                "irrigation_enabled",
                "ventilation_enabled",
                "workload_sensor_enabled",
                "workload_irrigation_enabled",
                "workload_camera_enabled",
                "workload_analytics_enabled",
                "workload_enabled_count",
                "workload_enabled_count_avg",
                "workload_enabled_count_delta",
                "workload_active_count",
                "workload_active_count_avg",
                "workload_active_count_delta",
            )
        ],
    }

    for name, removed in groups.items():
        columns = [col for col in base_columns if col not in removed]
        score = _train_score(df, columns)
        print(f"Without {name:12s}: {score:.4f} (delta {score - base_score:+.4f})")


if __name__ == "__main__":
    main()
