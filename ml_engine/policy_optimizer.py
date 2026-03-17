from ml_engine.lightgbm_policy import predict_policy


def predict_best_mode(features: dict):
    decision = predict_policy(features)
    return decision.get("mode", "BALANCED"), decision.get("confidence", 0.0)
