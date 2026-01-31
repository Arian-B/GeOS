# threshold_advisor.py

from ml_engine.infer_model import predict_mode

def adjust_thresholds(sensor_data, base_thresholds):
    """
    ML provides a small adjustment to OS thresholds.
    Safety bounds are enforced by the OS.
    """

    ml_mode = predict_mode(sensor_data)

    adjustment = 0

    if ml_mode == "ENERGY_SAVER":
        adjustment = +5    # conserve earlier
    elif ml_mode == "PERFORMANCE":
        adjustment = -5    # delay conservation
    else:
        adjustment = 0     # neutral

    adjusted = {
        "battery_energy_saver": base_thresholds["battery_energy_saver"] + adjustment,
        "soil_performance": base_thresholds["soil_performance"]
    }

    return adjusted, ml_mode
