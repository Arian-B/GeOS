# core_os/boot_manager.py

import datetime
import json
import os
import time

from control.os_control import read_control, write_control
from state.os_state import read_state, write_state
from core_os import update_manager
from core_os import provisioning

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(BASE_DIR, "state")
CONTROL_DIR = os.path.join(BASE_DIR, "control")

BOOT_STATE_FILE = os.path.join(STATE_DIR, "boot_state.json")
BOOT_SUCCESS_FILE = os.path.join(STATE_DIR, "boot_success.flag")
BOOT_ATTEMPTS_FILE = os.path.join(STATE_DIR, "boot_attempts.json")
BOOT_POLICY_FILE = os.path.join(STATE_DIR, "boot_policy.json")

SAFE_MODE_FLAG = os.path.join(CONTROL_DIR, "SAFE_MODE")
SAFE_MODE_FILE = os.path.join(CONTROL_DIR, "safe_mode.json")
SAFE_MODE_RESTORE_FILE = os.path.join(CONTROL_DIR, "safe_mode_restore.json")

CHECK_INTERVAL_SECONDS = 3
DEFAULT_BOOT_POLICY = {
    "safe_mode_on_failed_boot": True,
    "max_failed_boots": 2,
    "safe_mode_on_update_failure": True
}


def _read_json(path, default):
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else default
    except Exception:
        return default


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _set_boot_state(phase, message=None):
    state = {
        "phase": phase,
        "message": message,
        "time": datetime.datetime.now().isoformat(timespec="seconds")
    }
    _write_json(BOOT_STATE_FILE, state)


def _read_policy():
    policy = _read_json(BOOT_POLICY_FILE, DEFAULT_BOOT_POLICY.copy())
    if not isinstance(policy, dict):
        policy = DEFAULT_BOOT_POLICY.copy()
    changed = False
    for k, v in DEFAULT_BOOT_POLICY.items():
        if k not in policy:
            policy[k] = v
            changed = True
    if changed:
        _write_json(BOOT_POLICY_FILE, policy)
    return policy


def _read_boot_attempts():
    data = _read_json(BOOT_ATTEMPTS_FILE, {"failed": 0, "last_failed": None, "last_success": None})
    if not isinstance(data, dict):
        data = {"failed": 0, "last_failed": None, "last_success": None}
    return data


def _write_boot_attempts(data):
    _write_json(BOOT_ATTEMPTS_FILE, data)


def _safe_mode_requested():
    if os.path.exists(SAFE_MODE_FLAG):
        return True
    data = _read_json(SAFE_MODE_FILE, {})
    return bool(data.get("enabled"))


def _apply_safe_mode(enabled, reason=None):
    control = read_control()
    if enabled:
        if not control.get("safe_mode"):
            restore = {
                "mode": control.get("mode"),
                "manual_override_mode": control.get("manual_override_mode"),
                "forced_mode": control.get("forced_mode"),
                "maintenance": bool(control.get("maintenance", False)),
                "workloads": control.get("workloads")
            }
            _write_json(SAFE_MODE_RESTORE_FILE, restore)
        control["maintenance"] = True
        control["mode"] = "MANUAL"
        control["manual_override_mode"] = "ENERGY_SAVER"
        control["forced_mode"] = "ENERGY_SAVER"
        control["safe_mode"] = True
        control["workloads"] = {
            "sensor": False,
            "irrigation": False,
            "camera": False,
                "analytics": False
        }
    else:
        restore = _read_json(SAFE_MODE_RESTORE_FILE, {})
        control["safe_mode"] = False
        control["maintenance"] = bool(restore.get("maintenance", False))
        control["mode"] = restore.get("mode") if restore.get("mode") in ("AUTO", "MANUAL") else "AUTO"
        control["manual_override_mode"] = restore.get("manual_override_mode")
        control["forced_mode"] = restore.get("forced_mode")

        restored_workloads = restore.get("workloads")
        if isinstance(restored_workloads, dict):
            workloads = {}
            for key in ("sensor", "irrigation", "camera", "analytics"):
                workloads[key] = bool(restored_workloads.get(key, True))
            control["workloads"] = workloads
        else:
            workloads = control.get("workloads", {})
            if not isinstance(workloads, dict):
                workloads = {}
            if all(not bool(workloads.get(k, False)) for k in ("sensor", "irrigation", "camera", "analytics")):
                control["workloads"] = {
                    "sensor": True,
                    "irrigation": True,
                    "camera": True,
                    "analytics": True
                }

        try:
            os.remove(SAFE_MODE_RESTORE_FILE)
        except FileNotFoundError:
            pass
    write_control(control)

    state = read_state()
    state["recovery_mode"] = bool(enabled)
    if enabled:
        state["boot_phase"] = "RECOVERY"
        if reason:
            state["boot_message"] = reason
    else:
        state["boot_phase"] = "READY"
        state["boot_message"] = None
    write_state(state)


def _mark_boot_success():
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(BOOT_SUCCESS_FILE, "w") as f:
        f.write(datetime.datetime.now().isoformat(timespec="seconds"))

    attempts = _read_boot_attempts()
    attempts["failed"] = 0
    attempts["last_success"] = datetime.datetime.now().isoformat(timespec="seconds")
    _write_boot_attempts(attempts)


def _clear_boot_success():
    try:
        os.remove(BOOT_SUCCESS_FILE)
    except FileNotFoundError:
        pass


def boot_once():
    _set_boot_state("BOOTING", "Starting boot sequence")

    policy = _read_policy()
    prev_boot_ok = os.path.exists(BOOT_SUCCESS_FILE)
    attempts = _read_boot_attempts()
    if prev_boot_ok:
        attempts["failed"] = 0
    else:
        attempts["failed"] = int(attempts.get("failed", 0)) + 1
        attempts["last_failed"] = datetime.datetime.now().isoformat(timespec="seconds")
    _write_boot_attempts(attempts)

    update_manager.handle_boot(prev_boot_ok=prev_boot_ok)
    _clear_boot_success()

    provisioning.ensure_device_identity()

    failed_count = int(attempts.get("failed", 0))
    pending_update = bool(update_manager.pending_slot())
    safe_on_failed = bool(policy.get("safe_mode_on_failed_boot", True))
    safe_on_update = bool(policy.get("safe_mode_on_update_failure", True))
    max_failed = int(policy.get("max_failed_boots", 2))

    auto_safe = False
    if safe_on_failed and failed_count > 0:
        auto_safe = True
    if max_failed > 0 and failed_count >= max_failed:
        auto_safe = True
    if safe_on_update and pending_update and not prev_boot_ok:
        auto_safe = True

    if _safe_mode_requested() or auto_safe:
        _set_boot_state("RECOVERY", "Safe mode requested")
        _apply_safe_mode(True, reason="SAFE_MODE")
    else:
        _apply_safe_mode(False)
        _set_boot_state("READY", "Boot complete")

    _mark_boot_success()


def run():
    boot_once()
    # Monitor safe-mode toggles after boot for operational recovery.
    last_safe = _safe_mode_requested()
    while True:
        time.sleep(CHECK_INTERVAL_SECONDS)
        safe_now = _safe_mode_requested()
        if safe_now != last_safe:
            if safe_now:
                _set_boot_state("RECOVERY", "Safe mode enabled")
                _apply_safe_mode(True, reason="SAFE_MODE")
            else:
                _set_boot_state("READY", "Safe mode cleared")
                _apply_safe_mode(False)
            last_safe = safe_now


if __name__ == "__main__":
    run()
