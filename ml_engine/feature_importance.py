import json
import os

try:
    import joblib
    from sklearn.inspection import permutation_importance
except Exception:
    joblib = None
    permutation_importance = None

from ml_engine.lightgbm_policy import FEATURE_IMPORTANCE_FILE, MODEL_FILE


def main():
    if joblib is None:
        raise RuntimeError("joblib is required to inspect model feature importance")
    if not os.path.exists(MODEL_FILE):
        raise FileNotFoundError(f"Model not found: {MODEL_FILE}")

    model = joblib.load(MODEL_FILE)
    estimator = getattr(model, "named_steps", {}).get("model", model)
    feature_names = getattr(model, "feature_names_in_", None)
    if feature_names is None and hasattr(model, "named_steps"):
        feature_names = getattr(model.named_steps.get("model"), "feature_name_", None)
    importances = getattr(estimator, "feature_importances_", None)
    if importances is None and permutation_importance is not None:
        raise RuntimeError(
            "This model does not expose direct feature importances. "
            "Regenerate importance during training or provide an evaluation dataset."
        )

    if importances is None:
        raise RuntimeError("Loaded model does not expose feature_importances_")
    if feature_names is None:
        feature_names = [f"feature_{idx}" for idx in range(len(importances))]

    total = float(sum(importances)) or 1.0
    rows = [
        {"feature": str(name), "importance": round(float(score) / total, 6)}
        for name, score in sorted(
            zip(feature_names, importances),
            key=lambda item: item[1],
            reverse=True,
        )
    ]

    os.makedirs(os.path.dirname(FEATURE_IMPORTANCE_FILE), exist_ok=True)
    with open(FEATURE_IMPORTANCE_FILE, "w") as f:
        json.dump(rows, f, indent=2)

    print("[ML] Feature importance ranking")
    for row in rows[:10]:
        print(f"{row['feature']}: {row['importance']:.4f}")
    print(f"[ML] Saved to {FEATURE_IMPORTANCE_FILE}")


if __name__ == "__main__":
    main()
