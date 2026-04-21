from ml_engine.lightgbm_policy import current_thresholds, predict_policy


def adjust_thresholds(sensor_data, base_thresholds):
    thresholds = current_thresholds()
    merged = dict(base_thresholds)
    merged.update(thresholds)
    decision = predict_policy(sensor_data)
    return merged, decision.get("mode", "BALANCED")
