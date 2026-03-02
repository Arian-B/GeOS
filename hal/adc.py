# hal/adc.py

import json
import os
import random

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


class ADCChannel:
    def __init__(self, channel=0):
        self.channel = str(channel)

    def read(self):
        state = _read_state()
        adc = state.get("adc", {})
        if self.channel in adc:
            return adc[self.channel]
        return round(random.uniform(0.0, 1.0), 3)

    def set_simulated_value(self, value):
        state = _read_state()
        adc = state.setdefault("adc", {})
        adc[self.channel] = float(value)
        _write_state(state)
