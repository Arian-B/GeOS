# core_os/resource_daemon.py

import json
import os
import time

from core_os.resource_manager import apply_policy

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")

REFRESH_SECONDS = 3


def _read_state():
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def run():
    last_mode = None
    while True:
        state = _read_state()
        mode = state.get("current_mode")
        if mode and mode != last_mode:
            try:
                apply_policy(mode)
                last_mode = mode
            except Exception:
                # Resource tuning should never kill the daemon; retry next cycle.
                pass
        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    run()
