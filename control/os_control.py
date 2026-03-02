# os_control.py
# Control-plane interface for GeOS

import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTROL_FILE = os.path.join(BASE_DIR, "control", "control.json")

DEFAULT_CONTROL = {
    "mode": "AUTO",          # AUTO or MANUAL
    "irrigation": False,     # Actuator state
    "ventilation": False,
    "forced_mode": None,     # ENERGY_SAVER / BALANCED / PERFORMANCE (legacy)
    "manual_override_mode": None,  # ENERGY_SAVER / BALANCED / PERFORMANCE
    "emergency_shutdown": False,
    "safe_mode": False,
    "workloads": {
        "sensor": True,
        "irrigation": True,
        "camera": True,
        "analytics": True
    },
    "maintenance": False
}

def write_control(control):
    with open(CONTROL_FILE, "w") as f:
        json.dump(control, f, indent=2)

def read_control():
    if not os.path.exists(CONTROL_FILE):
        write_control(DEFAULT_CONTROL)
        return DEFAULT_CONTROL

    with open(CONTROL_FILE, "r") as f:
        data = json.load(f)

    # Backward compatibility: translate legacy keys if present
    if "auto_mode" in data and "mode" not in data:
        data["mode"] = "AUTO" if data.get("auto_mode") else "MANUAL"
    if "mode_override" in data and "forced_mode" not in data:
        data["forced_mode"] = data.get("mode_override")
    if "forced_mode" in data and "manual_override_mode" not in data:
        data["manual_override_mode"] = data.get("forced_mode")
    if "manual_override_mode" in data and "forced_mode" not in data:
        data["forced_mode"] = data.get("manual_override_mode")

    # Forward compatibility: ensure missing keys exist
    for k, v in DEFAULT_CONTROL.items():
        if k not in data:
            data[k] = v
    if "workloads" not in data or not isinstance(data["workloads"], dict):
        data["workloads"] = DEFAULT_CONTROL["workloads"].copy()
    else:
        for k, v in DEFAULT_CONTROL["workloads"].items():
            if k not in data["workloads"]:
                data["workloads"][k] = v

    return data
