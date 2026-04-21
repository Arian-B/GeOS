import math
from collections import deque


BASE_NUMERIC_FIELDS = [
    "cpu_percent",
    "load_avg",
    "memory_percent",
    "battery",
    "soil_moisture",
    "temperature",
    "humidity",
]

CONTEXT_BINARY_FIELDS = [
    "network_online",
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
]

CONTEXT_COUNT_FIELDS = [
    "workload_enabled_count",
    "workload_active_count",
]

WINDOW_SIZE = 5


def _as_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(values):
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def _delta(values):
    valid = [v for v in values if v is not None]
    if len(valid) < 2:
        return 0.0
    return valid[-1] - valid[0]


def _as_int(value, default=0):
    try:
        if value is None:
            return int(default)
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _streak(condition_values):
    streak = 0
    for value in reversed(condition_values):
        if value:
            streak += 1
        else:
            break
    return streak


class PolicyFeatureBuilder:
    """
    Builds runtime features from the latest telemetry and a short rolling history.
    The same feature contract is reused by the offline dataset builder.
    """

    def __init__(self, window_size=WINDOW_SIZE):
        self.window_size = max(2, int(window_size))
        self._history = deque(maxlen=self.window_size)

    def add_snapshot(self, snapshot):
        normalized = {}
        for field in BASE_NUMERIC_FIELDS:
            normalized[field] = _as_float(snapshot.get(field))
        normalized["hour"] = int(snapshot.get("hour", 0) or 0)
        normalized["network"] = str(snapshot.get("network", "UNKNOWN") or "UNKNOWN").upper()
        for field in CONTEXT_BINARY_FIELDS:
            normalized[field] = 1 if bool(snapshot.get(field, 0)) else 0
        for field in CONTEXT_COUNT_FIELDS:
            normalized[field] = _as_int(snapshot.get(field, 0), default=0)
        self._history.append(normalized)

    def current_features(self):
        if not self._history:
            return {}
        return build_policy_features(list(self._history))


def build_policy_features(history):
    if not history:
        return {}

    current = history[-1]
    features = {}

    for field in BASE_NUMERIC_FIELDS:
        series = [_as_float(row.get(field)) for row in history]
        current_value = series[-1]
        rolling_mean = _mean(series)
        features[field] = current_value
        features[f"{field}_avg"] = rolling_mean
        features[f"{field}_delta"] = _delta(series)

    hour = int(current.get("hour", 0) or 0)
    angle = (2.0 * math.pi * hour) / 24.0
    features["hour"] = hour
    features["hour_sin"] = math.sin(angle)
    features["hour_cos"] = math.cos(angle)

    network = str(current.get("network", "UNKNOWN") or "UNKNOWN").upper()
    features["network_online"] = 1 if network == "ONLINE" else 0

    for field in CONTEXT_BINARY_FIELDS:
        if field == "network_online":
            continue
        features[field] = 1 if bool(current.get(field, 0)) else 0

    for field in CONTEXT_COUNT_FIELDS:
        series = [_as_int(row.get(field, 0), default=0) for row in history]
        features[field] = series[-1]
        features[f"{field}_avg"] = _mean(series)
        features[f"{field}_delta"] = _delta(series)

    battery_series = [_as_float(row.get("battery")) for row in history]
    soil_series = [_as_float(row.get("soil_moisture")) for row in history]
    temp_series = [_as_float(row.get("temperature")) for row in history]

    features["battery_low_streak"] = _streak(
        [(value is not None and value < 25) for value in battery_series]
    )
    features["soil_dry_streak"] = _streak(
        [(value is not None and value < 35) for value in soil_series]
    )
    features["temp_high_streak"] = _streak(
        [(value is not None and value > 35) for value in temp_series]
    )

    return features


def feature_columns():
    columns = []
    for field in BASE_NUMERIC_FIELDS:
        columns.extend([field, f"{field}_avg", f"{field}_delta"])
    columns.extend(
        [
            "hour",
            "hour_sin",
            "hour_cos",
            "network_online",
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
            "battery_low_streak",
            "soil_dry_streak",
            "temp_high_streak",
        ]
    )
    return columns
