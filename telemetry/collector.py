# telemetry/collector.py
import time
import json
import os
import psutil
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "datasets")
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")
CONTROL_FILE = os.path.join(BASE_DIR, "control", "control.json")
WORKLOAD_STATE_FILE = os.path.join(BASE_DIR, "workloads", "workload_state.json")

os.makedirs(DATASET_DIR, exist_ok=True)
DATASET_FILE = os.path.join(DATASET_DIR, "telemetry_log.jsonl")

def read_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _read_json(path):
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _safe_get_load_avg():
    try:
        return os.getloadavg()[0]
    except (AttributeError, OSError):
        try:
            return psutil.getloadavg()[0]
        except Exception:
            cpu = psutil.cpu_percent(interval=None)
            cores = psutil.cpu_count() or 1
            return (cpu / 100.0) * cores

def collect():
    state = read_state()
    sensors = state.get("sensors", {})
    control = _read_json(CONTROL_FILE)
    workloads = control.get("workloads", {}) if isinstance(control.get("workloads"), dict) else {}
    workload_state = _read_json(WORKLOAD_STATE_FILE)

    workload_enabled_count = sum(1 for name in ("sensor", "irrigation", "camera", "analytics") if workloads.get(name))
    workload_active_count = sum(1 for name in ("sensor", "irrigation", "camera", "analytics") if workload_state.get(name))

    record = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "cpu_percent": psutil.cpu_percent(interval=None),
        "load_avg": _safe_get_load_avg(),
        "memory_percent": psutil.virtual_memory().percent,
        "battery": sensors.get("battery"),
        "soil_moisture": sensors.get("soil_moisture"),
        "temperature": sensors.get("temperature"),
        "humidity": sensors.get("humidity"),
        "network": sensors.get("network"),
        "hour": datetime.datetime.now().hour,
        "os_mode": state.get("current_mode"),
        "control_auto": control.get("mode", "AUTO") == "AUTO",
        "control_manual": control.get("mode") == "MANUAL",
        "maintenance_enabled": bool(control.get("maintenance", False)),
        "safe_mode_enabled": bool(control.get("safe_mode", False)),
        "emergency_shutdown_enabled": bool(control.get("emergency_shutdown", False)),
        "irrigation_enabled": bool(control.get("irrigation", False)),
        "ventilation_enabled": bool(control.get("ventilation", False)),
        "workload_sensor_enabled": bool(workloads.get("sensor", True)),
        "workload_irrigation_enabled": bool(workloads.get("irrigation", True)),
        "workload_camera_enabled": bool(workloads.get("camera", True)),
        "workload_analytics_enabled": bool(workloads.get("analytics", True)),
        "workload_enabled_count": workload_enabled_count,
        "workload_active_count": workload_active_count,
    }

    with open(DATASET_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")

def run(interval=2):
    print("[TELEMETRY] Collector started")
    try:
        while True:
            collect()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[TELEMETRY] Collector stopped")

if __name__ == "__main__":
    run()
