# workloads/workload_manager.py

import multiprocessing
import time
import json
import os
import signal
import sys

# Ensure project root is on sys.path when running as a script.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from workloads.sensor_workload import run as sensor
from workloads.irrigation_workload import run as irrigation
from workloads.camera_workload import run as camera
from workloads.analytics_workload import run as analytics
from control.os_control import read_control


BASE_DIR = os.path.dirname(__file__)
STATE_FILE = os.path.join(BASE_DIR, "workload_state.json")
LOCK_FILE = os.path.join(BASE_DIR, "workload_state.lock")
LOCK_TIMEOUT_SECONDS = 2.0


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
    _acquire_lock()
    try:
        _write_state_unlocked(state)
    finally:
        _release_lock()


def update_state(name, value):
    _acquire_lock()
    try:
        state = _read_state_unlocked()
        state[name] = value
        _write_state_unlocked(state)
    finally:
        _release_lock()


def _read_state_unlocked():
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        if not isinstance(state, dict):
            raise ValueError("Invalid state format")
    except Exception:
        state = {}

    # Ensure all keys exist to prevent overwriting other workload flags.
    for key in ("sensor", "irrigation", "camera", "analytics"):
        if key not in state:
            state[key] = False
    return state


def _acquire_lock():
    start = time.time()
    while True:
        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            if time.time() - start > LOCK_TIMEOUT_SECONDS:
                try:
                    os.remove(LOCK_FILE)
                except Exception:
                    pass
                start = time.time()
            time.sleep(0.05)


def _release_lock():
    try:
        os.remove(LOCK_FILE)
    except Exception:
        pass


def _write_state_unlocked(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _sync_state(processes):
    """
    Write a full snapshot of workload activity based on actual process state.
    This prevents stale or partial updates from individual workers.
    """
    snapshot = {
        "sensor": False,
        "irrigation": False,
        "camera": False,
        "analytics": False
    }

    for name, proc in processes.items():
        try:
            snapshot[name] = bool(proc and proc.is_alive())
        except Exception:
            snapshot[name] = False

    _acquire_lock()
    try:
        _write_state_unlocked(snapshot)
    finally:
        _release_lock()


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
def shutdown(processes):
    # Prevent re-entrant shutdowns
    if getattr(shutdown, "_running", False):
        return
    shutdown._running = True

    # Ignore further SIGINT while cleaning up
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    except Exception:
        pass

    print("\n[WORKLOAD MANAGER] Shutting down workloads...")
    for name, proc in processes.items():
        try:
            if proc.is_alive():
                proc.terminate()
        except Exception:
            pass

    # Give processes a moment to exit cleanly
    for name, proc in processes.items():
        try:
            proc.join(timeout=2)
        except Exception:
            pass

    # Force kill if still alive
    for name, proc in processes.items():
        try:
            if proc.is_alive() and hasattr(proc, "kill"):
                proc.kill()
        except Exception:
            pass

    init_state()
    print("[WORKLOAD MANAGER] Clean shutdown complete.")


def start():
    init_state()

    workloads = {
        "sensor": sensor,
        "irrigation": irrigation,
        "camera": camera,
        "analytics": analytics
    }

    processes = {}

    print("[WORKLOAD MANAGER] Monitoring workload toggles...")

    def _start_workload(name, fn):
        if name in processes and processes[name].is_alive():
            return
        p = multiprocessing.Process(
            target=workload_wrapper,
            args=(name, fn),
            name=name
        )
        p.start()
        processes[name] = p
        update_state(name, True)
        print(f"[WORKLOAD MANAGER] {name.capitalize()} workload started (PID={p.pid})")

    def _stop_workload(name):
        proc = processes.get(name)
        if not proc:
            update_state(name, False)
            return
        try:
            if proc.is_alive():
                proc.terminate()
        except Exception:
            pass
        try:
            proc.join(timeout=2)
        except Exception:
            pass
        try:
            if proc.is_alive() and hasattr(proc, "kill"):
                proc.kill()
        except Exception:
            pass
        processes.pop(name, None)
        update_state(name, False)
        print(f"[WORKLOAD MANAGER] {name.capitalize()} workload stopped")

    def _handle_signal(signum, frame):
        shutdown(processes)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    try:
        while True:
            control = read_control()
            desired = control.get("workloads", {})
            for name, fn in workloads.items():
                enabled = desired.get(name, True)
                proc = processes.get(name)

                if enabled:
                    if not proc or not proc.is_alive():
                        _start_workload(name, fn)
                else:
                    if proc and proc.is_alive():
                        _stop_workload(name)
                    else:
                        update_state(name, False)

            # Refresh state based on actual running processes.
            _sync_state(processes)

            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(processes)


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    start()
