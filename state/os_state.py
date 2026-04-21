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
    "ml_confidence": None,
    "ml_raw_confidence": None,
    "ml_confidence_source": None,
    "policy_source": None,
    "ml_top_features": [],
    "ml_reason_codes": [],

    # New additions (safe defaults)
    "maintenance_mode": False,
    "forced_mode": None,
    "last_ai_action_time": None,

    # Boot + recovery metadata
    "boot_phase": "BOOTING",
    "boot_message": None,
    "recovery_mode": False,

    "ml_thresholds": {},
    "sensors": {}
}

def write_state(state):
    state["last_updated"] = datetime.now().isoformat()
    state.pop("rl_action", None)
    existing = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                existing = json.load(f)
        except Exception:
            existing = {}
    if isinstance(existing, dict):
        existing.update(state)
        state = existing
    if isinstance(state, dict):
        state.pop("rl_action", None)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def read_state():
    if not os.path.exists(STATE_FILE):
        write_state(DEFAULT_STATE)
        return DEFAULT_STATE

    with open(STATE_FILE, "r") as f:
        data = json.load(f)
    if isinstance(data, dict) and "rl_action" in data:
        data.pop("rl_action", None)

    # Forward compatibility: add missing keys
    for k, v in DEFAULT_STATE.items():
        if k not in data:
            data[k] = v

    return data
