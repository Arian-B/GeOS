# irrigation_workload.py
import time
import random
import json
import os


DEFAULT_CONFIG = {
    "sensor_interval": 2,
    "camera_interval": 5,
    "analytics_intensity": "MEDIUM"
}
CONFIG_REFRESH_SECONDS = 2
INTENSITY_SCALE = {"LOW": 1, "MEDIUM": 2, "HIGH": 4}
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "workload_config.json"))


def _normalize_config(data):
    sensor_interval = data.get("sensor_interval", DEFAULT_CONFIG["sensor_interval"])
    camera_interval = data.get("camera_interval", DEFAULT_CONFIG["camera_interval"])
    analytics_intensity = data.get("analytics_intensity", DEFAULT_CONFIG["analytics_intensity"])

    if not isinstance(sensor_interval, (int, float)) or sensor_interval <= 0:
        sensor_interval = DEFAULT_CONFIG["sensor_interval"]
    if not isinstance(camera_interval, (int, float)) or camera_interval <= 0:
        camera_interval = DEFAULT_CONFIG["camera_interval"]
    if isinstance(analytics_intensity, str):
        analytics_intensity = analytics_intensity.upper()
    if analytics_intensity not in INTENSITY_SCALE:
        analytics_intensity = DEFAULT_CONFIG["analytics_intensity"]

    return {
        "sensor_interval": sensor_interval,
        "camera_interval": camera_interval,
        "analytics_intensity": analytics_intensity
    }


def _load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Invalid config format")
        return _normalize_config(data)
    except (OSError, ValueError, json.JSONDecodeError):
        return DEFAULT_CONFIG.copy()

def run():
    config = DEFAULT_CONFIG.copy()
    last_config_load = 0
    while True:
        # Adaptive scaling: refresh workload config periodically to match energy mode.
        now = time.time()
        if now - last_config_load >= CONFIG_REFRESH_SECONDS:
            config = _load_config()
            last_config_load = now

        # Random irrigation event
        if random.random() < 0.2:  # 20% chance
            start = time.time()
            # Adaptive scaling: adjust pump computation based on intensity.
            intensity = config["analytics_intensity"]
            scale = INTENSITY_SCALE.get(intensity, INTENSITY_SCALE["MEDIUM"])
            while time.time() - start < 2:
                # Simulate pump computation
                _ = sum(i*i for i in range(2000 * scale))

        # Adaptive scaling: tie irrigation check interval to sensor cadence.
        sleep_interval = max(1, config["sensor_interval"] + 1)
        time.sleep(sleep_interval)
