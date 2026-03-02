# telemetry/collector.py
import time
import json
import os
import psutil
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "datasets")
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")

os.makedirs(DATASET_DIR, exist_ok=True)
DATASET_FILE = os.path.join(DATASET_DIR, "telemetry_log.jsonl")

def read_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
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
        "os_mode": state.get("current_mode")
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
