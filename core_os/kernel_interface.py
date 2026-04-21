# core_os/kernel_interface.py

import glob
import json
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE_DIR, "state", "kernel_tuning.json")
CPU_GOVERNOR_GLOB = "/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
CPU_AVAILABLE_GLOB = "/sys/devices/system/cpu/cpu*/cpufreq/scaling_available_governors"
SWAPPINESS_FILE = "/proc/sys/vm/swappiness"

MODE_TUNING = {
    "ENERGY_SAVER": {
        "governor_preference": ["powersave", "ondemand", "schedutil", "performance"],
        "swappiness": 80
    },
    "BALANCED": {
        "governor_preference": ["schedutil", "ondemand", "powersave", "performance"],
        "swappiness": 60
    },
    "PERFORMANCE": {
        "governor_preference": ["performance", "schedutil", "ondemand", "powersave"],
        "swappiness": 30
    }
}


def _read_text(path):
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None


def _write_text(path, value):
    with open(path, "w") as f:
        f.write(str(value))


def _write_state(payload):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass


def _cpu_governor_paths():
    return sorted(glob.glob(CPU_GOVERNOR_GLOB))


def _available_governor_paths():
    return sorted(glob.glob(CPU_AVAILABLE_GLOB))


def current_governor():
    for path in _cpu_governor_paths():
        value = _read_text(path)
        if value:
            return value
    return None


def available_governors():
    for path in _available_governor_paths():
        raw = _read_text(path)
        if raw:
            values = [v.strip() for v in raw.split() if v.strip()]
            if values:
                return values
    return []


def read_swappiness():
    raw = _read_text(SWAPPINESS_FILE)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def set_swappiness(value):
    try:
        value = int(value)
    except Exception:
        return {"ok": False, "error": "invalid_swappiness"}

    value = max(0, min(100, value))
    try:
        _write_text(SWAPPINESS_FILE, value)
        return {"ok": True, "value": value}
    except PermissionError:
        return {"ok": False, "error": "permission_denied"}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}


def set_governor(governor):
    paths = _cpu_governor_paths()
    if not paths:
        return {"ok": False, "applied": 0, "failed": 0, "errors": ["cpu_governor_unavailable"]}

    applied = 0
    errors = []
    for path in paths:
        try:
            _write_text(path, governor)
            applied += 1
        except PermissionError:
            errors.append(f"{path}:permission_denied")
        except OSError as exc:
            errors.append(f"{path}:{exc}")

    return {
        "ok": applied > 0 and not errors,
        "requested": governor,
        "applied": applied,
        "failed": len(paths) - applied,
        "errors": errors
    }


def _select_governor(mode_name):
    tuning = MODE_TUNING.get(mode_name, MODE_TUNING["BALANCED"])
    preferences = tuning.get("governor_preference", [])
    available = available_governors()
    if available:
        for candidate in preferences:
            if candidate in available:
                return candidate
        return available[0]
    return preferences[0] if preferences else None


def tune_for_mode(mode_name):
    tuning = MODE_TUNING.get(mode_name, MODE_TUNING["BALANCED"])
    governor = _select_governor(mode_name)

    governor_result = {"ok": False, "skipped": True}
    if governor:
        governor_result = set_governor(governor)

    swappiness_target = tuning.get("swappiness")
    swappiness_result = {"ok": False, "skipped": True}
    if swappiness_target is not None:
        swappiness_result = set_swappiness(swappiness_target)

    report = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": mode_name,
        "requested_governor": governor,
        "governor_result": governor_result,
        "requested_swappiness": swappiness_target,
        "swappiness_result": swappiness_result,
        "current_governor": current_governor(),
        "current_swappiness": read_swappiness()
    }
    _write_state(report)
    return report
