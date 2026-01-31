# os_state.py

import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")

DEFAULT_STATE = {
    "current_mode": "BALANCED",
    "ml_suggested_mode": "BALANCED",
    "ml_thresholds": {},
    "sensors": {}
}

def write_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def read_state():
    if not os.path.exists(STATE_FILE):
        write_state(DEFAULT_STATE)
    with open(STATE_FILE, "r") as f:
        return json.load(f)
