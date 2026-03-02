# hal/spi.py

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


class SPIBus:
    def __init__(self, bus_id=0, device_id=0):
        self.bus_id = str(bus_id)
        self.device_id = str(device_id)

    def transfer(self, data):
        state = _read_state()
        spi = state.setdefault("spi", {})
        bus = spi.setdefault(self.bus_id, {})
        key = f"dev_{self.device_id}"
        bus[key] = list(data)
        _write_state(state)
        return list(data)
