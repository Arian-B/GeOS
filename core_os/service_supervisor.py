# core_os/service_supervisor.py

import json
import os
import signal
import subprocess
import sys
import time

import psutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_FILE = os.path.join(BASE_DIR, "services", "manifest.json")
LOG_DIR = os.path.join(BASE_DIR, "logs")

CHECK_INTERVAL_SECONDS = 2.0


def _read_manifest():
    try:
        with open(MANIFEST_FILE, "r") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _is_running(script_path=None, module_name=None):
    normalized_target = None
    if script_path:
        normalized_target = os.path.normcase(os.path.abspath(script_path))
    for proc in psutil.process_iter(attrs=["cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if module_name and module_name in cmdline:
                return True
            if normalized_target:
                for arg in cmdline:
                    if os.path.normcase(os.path.abspath(arg)) == normalized_target:
                        return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def _start_service(entry):
    name = entry.get("name")
    module = entry.get("module")
    script = entry.get("script")
    args = entry.get("args") or []
    if not module and not script:
        return None
    if _is_running(script_path=script, module_name=module):
        return None

    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f"service_{name}.log")
    log_file = open(log_path, "a", buffering=1)

    if module:
        cmd = [sys.executable, "-m", module] + args
    else:
        cmd = [sys.executable, script] + args

    env = os.environ.copy()
    env["PYTHONPATH"] = BASE_DIR + os.pathsep + env.get("PYTHONPATH", "")

    proc = subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=log_file,
        cwd=BASE_DIR,
        env=env,
        close_fds=True,
    )
    return {"process": proc, "log_file": log_file, "entry": entry}


def _close_info(info):
    if not info:
        return
    log_file = info.get("log_file")
    if log_file:
        try:
            log_file.close()
        except Exception:
            pass


def run():
    processes = {}

    def _handle_signal(signum, frame):
        for info in processes.values():
            proc = info["process"]
            try:
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            log_file = info.get("log_file")
            if log_file:
                log_file.close()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    while True:
        manifest = _read_manifest()
        for entry in manifest:
            name = entry.get("name")
            if not name:
                continue
            autostart = bool(entry.get("autostart", True))
            restart = entry.get("restart", "always")

            info = processes.get(name)
            if info:
                proc = info["process"]
                if proc.poll() is not None:
                    _close_info(info)
                    if restart in ("always", "on-failure"):
                        processes.pop(name, None)
                    else:
                        processes.pop(name, None)
                        continue
            if autostart and name not in processes:
                started = _start_service(entry)
                if started:
                    processes[name] = started

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
