# os_control.py
# Control-plane interface for GeOS

import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTROL_FILE = os.path.join(BASE_DIR, "control", "control.json")

DEFAULT_CONTROL = {
    "mode": "AUTO",          # AUTO or MANUAL
    "irrigation": False,     # Actuator state
    "ventilation": False
}

def write_control(control):
    with open(CONTROL_FILE, "w") as f:
        json.dump(control, f, indent=2)

def read_control():
    if not os.path.exists(CONTROL_FILE):
        write_control(DEFAULT_CONTROL)
        return DEFAULT_CONTROL

    with open(CONTROL_FILE, "r") as f:
        return json.load(f)
