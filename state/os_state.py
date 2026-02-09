# state/os_state.py
# Global persistent OS state for GeOS

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")

DEFAULT_STATE = {
    "current_mode": "BOOTING",
    "ml_suggested_mode": None,
    "rl_action": None,

    # New additions (safe defaults)
    "maintenance_mode": False,
    "forced_mode": None,
    "last_ai_action_time": None,

    "ml_thresholds": {},
    "sensors": {}
}

def write_state(state):
    state["last_updated"] = datetime.now().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def read_state():
    if not os.path.exists(STATE_FILE):
        write_state(DEFAULT_STATE)
        return DEFAULT_STATE

    with open(STATE_FILE, "r") as f:
        data = json.load(f)

    # Forward compatibility: add missing keys
    for k, v in DEFAULT_STATE.items():
        if k not in data:
            data[k] = v

    return data
