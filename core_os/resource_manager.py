# core_os/resource_manager.py

import os
import psutil

WORKLOAD_FILES = {
    "sensor": "sensor_workload.py",
    "irrigation": "irrigation_workload.py",
    "camera": "camera_workload.py",
    "analytics": "analytics_workload.py"
}

MODE_NICE = {
    "ENERGY_SAVER": 12,
    "BALANCED": 0,
    "PERFORMANCE": -2
}


def _iter_workload_processes():
    for proc in psutil.process_iter(attrs=["pid", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            cmd = " ".join(cmdline)
            for name, filename in WORKLOAD_FILES.items():
                if filename in cmd:
                    yield name, proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def apply_policy(mode_name):
    if mode_name not in MODE_NICE:
        return
    target_nice = MODE_NICE[mode_name]
    for _, proc in _iter_workload_processes():
        try:
            proc.nice(target_nice)
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError, ValueError):
            continue


def summarize_workload_pids():
    summary = {}
    for name, proc in _iter_workload_processes():
        summary.setdefault(name, []).append(proc.pid)
    return summary
