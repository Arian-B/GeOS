from ml_engine.lightgbm_policy import predict_policy


def predict_mode(features: dict):
    return predict_policy(features).get("mode", "BALANCED")
