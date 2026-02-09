# workloads/workload_manager.py

import multiprocessing
import time
import json
import os

from sensor_workload import run as sensor
from irrigation_workload import run as irrigation
from camera_workload import run as camera
from analytics_workload import run as analytics


BASE_DIR = os.path.dirname(__file__)
STATE_FILE = os.path.join(BASE_DIR, "workload_state.json")


# -----------------------------
# STATE HELPERS
# -----------------------------
def init_state():
    state = {
        "sensor": False,
        "irrigation": False,
        "camera": False,
        "analytics": False
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def update_state(name, value):
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
    except Exception:
        state = {}

    state[name] = value

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# -----------------------------
# WRAPPER FOR EACH WORKLOAD
# -----------------------------
def workload_wrapper(name, fn):
    update_state(name, True)
    try:
        fn()
    finally:
        update_state(name, False)


# -----------------------------
# MANAGER
# -----------------------------
def start():
    init_state()

    workloads = {
        "sensor": sensor,
        "irrigation": irrigation,
        "camera": camera,
        "analytics": analytics
    }

    processes = []

    print("[WORKLOAD MANAGER] Starting agricultural workloads...")

    for name, fn in workloads.items():
        p = multiprocessing.Process(
            target=workload_wrapper,
            args=(name, fn),
            name=name
        )
        p.start()
        processes.append(p)
        print(f"[WORKLOAD MANAGER] {name.capitalize()} workload started (PID={p.pid})")

    print("[WORKLOAD MANAGER] All workloads running.\n")

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n[WORKLOAD MANAGER] Shutting down workloads...")
        for p in processes:
            p.terminate()
        init_state()
        print("[WORKLOAD MANAGER] Clean shutdown complete.")


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    start()
