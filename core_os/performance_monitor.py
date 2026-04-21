# core_os/performance_monitor.py

import os
import json
import time
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "performance_metrics.json")
WRITE_INTERVAL_SECONDS = 2.0

_state = None
_last_update_ts = None
_last_write_ts = 0.0


def _initial_state():
    return {
        "current_mode": None,
        "total_switches": 0,
        "last_updated": None,
        "last_mode_change": None,
        "modes": {}
    }


def _ensure_mode(state, mode_name):
    if mode_name not in state["modes"]:
        state["modes"][mode_name] = {
            "duration_seconds": 0.0,
            "avg_cpu": 0.0,
            "avg_memory": 0.0,
            "samples": 0,
            "switch_count": 0
        }


def _load_state():
    state = _initial_state()
    if not os.path.exists(LOG_FILE):
        return state

    try:
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            state.update({k: v for k, v in data.items() if k in state})
            modes = data.get("modes")
            if isinstance(modes, dict):
                state["modes"].update(modes)
    except Exception:
        return _initial_state()

    # Normalize mode entries to ensure required fields exist
    for mode_name, entry in list(state.get("modes", {}).items()):
        if not isinstance(entry, dict):
            state["modes"].pop(mode_name, None)
            continue
        entry.setdefault("duration_seconds", 0.0)
        entry.setdefault("avg_cpu", 0.0)
        entry.setdefault("avg_memory", 0.0)
        entry.setdefault("samples", 0)
        entry.setdefault("switch_count", 0)

    return state


def _safe_write(state):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        tmp_path = LOG_FILE + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, LOG_FILE)
    except Exception:
        # Avoid blocking the OS loop on logging failures.
        pass


def _ensure_loaded():
    global _state
    if _state is None:
        _state = _load_state()


def log_mode_change(mode_name):
    """
    Record a mode switch without blocking the OS loop.
    """
    global _last_write_ts
    _ensure_loaded()
    if not mode_name:
        return

    _ensure_mode(_state, mode_name)
    _state["current_mode"] = mode_name
    _state["last_mode_change"] = datetime.datetime.now().isoformat()
    _state["total_switches"] = int(_state.get("total_switches", 0)) + 1
    _state["modes"][mode_name]["switch_count"] = (
        int(_state["modes"][mode_name].get("switch_count", 0)) + 1
    )

    now = time.monotonic()
    if now - _last_write_ts >= WRITE_INTERVAL_SECONDS:
        _safe_write(_state)
        _last_write_ts = now


def update(current_mode, cpu_percent, memory_percent):
    """
    Update per-mode metrics. Safe, lightweight, and throttled.
    """
    global _last_update_ts, _last_write_ts

    _ensure_loaded()
    if not current_mode:
        return

    _ensure_mode(_state, current_mode)

    now = time.monotonic()
    if _last_update_ts is not None:
        dt = max(0.0, now - _last_update_ts)
    else:
        dt = 0.0
    _last_update_ts = now

    entry = _state["modes"][current_mode]
    entry["duration_seconds"] = float(entry.get("duration_seconds", 0.0)) + dt

    if cpu_percent is not None and memory_percent is not None:
        try:
            samples = int(entry.get("samples", 0))
            avg_cpu = float(entry.get("avg_cpu", 0.0))
            avg_mem = float(entry.get("avg_memory", 0.0))

            cpu_sum = avg_cpu * samples + float(cpu_percent)
            mem_sum = avg_mem * samples + float(memory_percent)
            samples += 1

            entry["samples"] = samples
            entry["avg_cpu"] = round(cpu_sum / samples, 2)
            entry["avg_memory"] = round(mem_sum / samples, 2)
        except (TypeError, ValueError):
            pass

    _state["current_mode"] = current_mode
    _state["last_updated"] = datetime.datetime.now().isoformat()

    # Throttle disk writes to avoid performance degradation.
    if now - _last_write_ts >= WRITE_INTERVAL_SECONDS:
        _safe_write(_state)
        _last_write_ts = now
