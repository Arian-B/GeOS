# hal/i2c.py

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


class I2CBus:
    def __init__(self, bus_id=1):
        self.bus_id = str(bus_id)

    def write(self, address, data):
        state = _read_state()
        i2c = state.setdefault("i2c", {})
        bus = i2c.setdefault(self.bus_id, {})
        bus[str(address)] = list(data)
        _write_state(state)

    def read(self, address, length=1):
        state = _read_state()
        i2c = state.get("i2c", {})
        bus = i2c.get(self.bus_id, {})
        data = bus.get(str(address), [])
        if len(data) < length:
            data = data + [0] * (length - len(data))
        return data[:length]
