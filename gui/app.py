# gui/app.py

import os
import subprocess
import sys

import psutil
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow


STARTED_SERVICE_PROCESSES = []
_SERVICES_STARTED = False
SYSTEMD_MANAGED_ENV = "GEOS_MANAGED_BY_SYSTEMD"
SERVICE_ENTRIES = [
    {
        "name": "boot_manager",
        "module": "core_os.boot_manager",
        "script": "core_os/boot_manager.py",
    },
    {
        "name": "energy_controller",
        "module": "core_os.energy_controller",
        "script": "core_os/energy_controller.py",
    },
    {
        "name": "workload_manager",
        "module": "workloads.workload_manager",
        "script": "workloads/workload_manager.py",
    },
    {
        "name": "collector",
        "module": "telemetry.collector",
        "script": "telemetry/collector.py",
    },
    {
        "name": "resource_daemon",
        "module": "core_os.resource_daemon",
        "script": "core_os/resource_daemon.py",
    },
    {
        "name": "update_watcher",
        "module": "core_os.update_watcher",
        "script": "core_os/update_watcher.py",
    },
    {
        "name": "workflow_server",
        "module": "interface.workflow_server",
        "script": "interface/workflow_server.py",
    },
    {
        "name": "repl_server",
        "module": "interface.repl_server",
        "script": "interface/repl_server.py",
    },
    {
        "name": "metrics_server",
        "module": "telemetry.metrics_server",
        "script": "telemetry/metrics_server.py",
    },
]


def _project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _is_script_running(script_path=None, module_name=None):
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


def start_background_services():
    """
    Start required backend services if they're not already running.
    Keeps track of only the processes started by GeOS for graceful shutdown.
    """
    global _SERVICES_STARTED
    if _SERVICES_STARTED:
        return
    if str(os.environ.get(SYSTEMD_MANAGED_ENV, "")).strip().lower() in ("1", "true", "yes", "on"):
        return

    project_root = _project_root()
    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    services = []
    for entry in SERVICE_ENTRIES:
        expanded = dict(entry)
        expanded["script"] = os.path.join(project_root, entry["script"])
        services.append(expanded)

    env = os.environ.copy()
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")

    for service in services:
        name = service["name"]
        module_name = service["module"]
        script_path = service["script"]
        # Prevent duplicate instances by checking for existing running scripts.
        if _is_script_running(script_path=script_path, module_name=module_name):
            continue

        # Start the service non-blocking and redirect output to a per-service log file.
        log_path = os.path.join(logs_dir, f"service_{name}.log")
        log_file = open(log_path, "a", buffering=1)
        process = subprocess.Popen(
            [sys.executable, "-m", module_name],
            stdout=log_file,
            stderr=log_file,
            cwd=project_root,
            env=env,
            close_fds=True,
        )

        # Track only the Popen handles started here for later termination.
        STARTED_SERVICE_PROCESSES.append({"process": process, "log_file": log_file})

    _SERVICES_STARTED = True


def _shutdown_background_services():
    # Gracefully terminate only the processes started by GeOS.
    for entry in STARTED_SERVICE_PROCESSES:
        process = entry["process"]
        try:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        finally:
            log_file = entry.get("log_file")
            if log_file:
                log_file.close()

    # Also terminate any managed GeOS services already running in this environment.
    managed_modules = {entry["module"] for entry in SERVICE_ENTRIES}
    for proc in psutil.process_iter(attrs=["pid", "cmdline"]):
        try:
            if proc.pid == os.getpid():
                continue
            cmdline = proc.info.get("cmdline") or []
            if not cmdline:
                continue
            if any(module in cmdline for module in managed_modules):
                proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Best-effort wait/kill for remaining managed services.
    for proc in psutil.process_iter(attrs=["pid", "cmdline"]):
        try:
            if proc.pid == os.getpid():
                continue
            cmdline = proc.info.get("cmdline") or []
            if not cmdline:
                continue
            if any(module in cmdline for module in managed_modules):
                try:
                    proc.wait(timeout=3)
                except psutil.TimeoutExpired:
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def main():
    # Ensure backend services are up before any GUI (including splash) loads.
    start_background_services()
    app = QApplication(sys.argv)
    if str(os.environ.get(SYSTEMD_MANAGED_ENV, "")).strip().lower() not in ("1", "true", "yes", "on"):
        app.aboutToQuit.connect(_shutdown_background_services)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
