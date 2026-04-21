# core_os/update_watcher.py

import json
import os
import time

from core_os import update_manager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCOMING_DIR = os.path.join(BASE_DIR, "updates", "incoming")
PROCESSED_DIR = os.path.join(INCOMING_DIR, "processed")
REJECTED_DIR = os.path.join(INCOMING_DIR, "rejected")
STATE_FILE = os.path.join(BASE_DIR, "state", "update_incoming.json")

SCAN_INTERVAL_SECONDS = 5


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


def _find_sidecar(base_name, ext_list):
    for ext in ext_list:
        path = os.path.join(INCOMING_DIR, base_name + ext)
        if os.path.exists(path):
            return path
    return None


def _move_to(folder, filename, sidecars):
    os.makedirs(folder, exist_ok=True)
    src = os.path.join(INCOMING_DIR, filename)
    dest = os.path.join(folder, filename)
    try:
        os.replace(src, dest)
    except Exception:
        return
    for sidecar in sidecars:
        if sidecar and os.path.exists(sidecar):
            target = os.path.join(folder, os.path.basename(sidecar))
            try:
                os.replace(sidecar, target)
            except Exception:
                pass


def _record_status(state, filename, status, detail=None, stat_info=None):
    entry = state.get(filename, {})
    entry["status"] = status
    entry["detail"] = detail
    try:
        stat = stat_info if stat_info is not None else os.stat(os.path.join(INCOMING_DIR, filename))
        entry["size"] = stat.st_size
        entry["mtime"] = stat.st_mtime
    except Exception:
        pass
    state[filename] = entry
    _write_state(state)


def run():
    os.makedirs(INCOMING_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(REJECTED_DIR, exist_ok=True)

    while True:
        policy = update_manager.read_policy()
        if not policy.get("auto_stage_updates", True):
            time.sleep(SCAN_INTERVAL_SECONDS)
            continue

        state = _read_state()
        updates = update_manager.list_incoming_updates()
        for filename in updates:
            path = os.path.join(INCOMING_DIR, filename)
            try:
                stat = os.stat(path)
            except Exception:
                continue
            entry = state.get(filename)
            if entry and entry.get("mtime") == stat.st_mtime and entry.get("size") == stat.st_size:
                if entry.get("status") in ("staged", "rejected"):
                    continue

            base_name = os.path.splitext(filename)[0]
            sig_path = _find_sidecar(base_name, [".sig", ".sig.json"])
            sha_path = _find_sidecar(base_name, [".sha256"])

            try:
                slot = update_manager.stage_update_with_policy(
                    path,
                    signature_path=sig_path,
                    sha256_path=sha_path
                )
                _record_status(state, filename, "staged", f"slot:{slot}", stat_info=stat)
                _move_to(PROCESSED_DIR, filename, [sig_path, sha_path])
            except Exception as exc:
                _record_status(state, filename, "rejected", str(exc), stat_info=stat)
                _move_to(REJECTED_DIR, filename, [sig_path, sha_path])

        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
