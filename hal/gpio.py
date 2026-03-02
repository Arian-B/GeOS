# hal/gpio.py

import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE_DIR, "state", "hal_state.json")


def _read_state():
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_state(data):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


class GPIOPin:
    def __init__(self, pin, mode="IN"):
        self.pin = str(pin)
        self.mode = mode

    def set_mode(self, mode):
        self.mode = mode

    def write(self, value):
        state = _read_state()
        gpio = state.setdefault("gpio", {})
        gpio[self.pin] = {"mode": self.mode, "value": int(bool(value))}
        _write_state(state)

    def read(self):
        state = _read_state()
        gpio = state.get("gpio", {})
        entry = gpio.get(self.pin, {})
        return entry.get("value", 0)
