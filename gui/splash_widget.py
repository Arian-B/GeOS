# gui/splash_widget.py

import json
import os
import time

import psutil
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtCore import Qt, QTimer, Signal
from gui import theme
from core_os.network import is_connected


class SplashWidget(QWidget):
    boot_finished = Signal()   # 🔑 signal
    MIN_SPLASH_SECONDS = 4.0

    def __init__(self):
        super().__init__()

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._base_dir = base_dir
        self._boot_start = time.monotonic()
        self._boot_done = False

        self._state_file = os.path.join(base_dir, "state", "os_state.json")
        self._boot_state_file = os.path.join(base_dir, "state", "boot_state.json")
        self._services_manifest = os.path.join(base_dir, "services", "manifest.json")

        services = self._load_services()
        self._diagnostics = [
            ("policy_model.pkl", os.path.join(base_dir, "ml_engine", "policy_model.pkl"), "file"),
            ("workload_state.json", os.path.join(base_dir, "workloads", "workload_state.json"), "file"),
            ("os_state.json", os.path.join(base_dir, "state", "os_state.json"), "file"),
            ("telemetry/ (dir)", os.path.join(base_dir, "telemetry"), "dir"),
            ("network connectivity", None, "network")
        ]
        for service in services:
            name = service.get("name")
            module = service.get("module")
            if name and module:
                self._diagnostics.append((f"service: {name}", module, "service"))
        self._diagnostic_ok = {label: False for label, _, _ in self._diagnostics}
        self._scan_index = 0
        self._scan_phase = 0  # 0=loading text, 1=result text

        self.setStyleSheet(f"background-color: {theme.BACKGROUND};")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        logo = QLabel("GeOS")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("""
            font-size: 64px;
            font-weight: 900;
            color: #C7F9CC;
            letter-spacing: 3px;
        """)

        subtitle = QLabel("prototype version 1.0")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 16px;
            color: #A8DADC;
        """)

        self.status = QLabel("Initializing system modules...")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("""
            font-size: 14px;
            color: #A8DADC;
        """)

        bar_layout = QHBoxLayout()
        bar_layout.setSpacing(6)

        self.blocks = []
        for _ in range(12):
            block = QFrame()
            block.setFixedSize(22, 14)
            block.setStyleSheet("background-color: #1B4332; border-radius: 2px;")
            self.blocks.append(block)
            bar_layout.addWidget(block)

        layout.addStretch()
        layout.addWidget(logo)
        layout.addWidget(subtitle)
        layout.addSpacing(30)
        layout.addLayout(bar_layout)
        layout.addWidget(self.status)
        layout.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.timer.start(70)

    def _read_json(self, path, default=None):
        if default is None:
            default = {}
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else default
        except Exception:
            return default

    def _load_services(self):
        data = self._read_json(self._services_manifest, default=[])
        if isinstance(data, list):
            return data
        return []

    def _is_service_running(self, module_name):
        for proc in psutil.process_iter(attrs=["cmdline"]):
            try:
                cmdline = proc.info.get("cmdline") or []
                if module_name and module_name in cmdline:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def _read_boot_phase(self):
        boot_state = self._read_json(self._boot_state_file, default={})
        if boot_state.get("phase"):
            return boot_state.get("phase"), boot_state.get("message")
        state = self._read_json(self._state_file, default={})
        return state.get("boot_phase"), state.get("boot_message")

    def _check_diagnostic(self, path, kind):
        if kind == "file":
            return os.path.exists(path)
        if kind == "dir":
            return os.path.isdir(path)
        if kind == "service":
            return self._is_service_running(path)
        # Network check: uses existing connectivity helper.
        return bool(is_connected())

    def _update_progress_bar(self):
        ok_count = sum(1 for ok in self._diagnostic_ok.values() if ok)
        total = len(self._diagnostics)
        filled = 0 if total == 0 else min(len(self.blocks), int((ok_count / total) * len(self.blocks)))
        for idx, block in enumerate(self.blocks):
            if idx < filled:
                block.setStyleSheet("background-color: #74C69D; border-radius: 2px;")
            else:
                block.setStyleSheet("background-color: #1B4332; border-radius: 2px;")
        return ok_count, total

    def advance(self):
        phase, message = self._read_boot_phase()
        if self._diagnostics:
            label, path, kind = self._diagnostics[self._scan_index]
            if self._scan_phase == 0:
                self.status.setText(f"loading {label}...")
                self._scan_phase = 1
            else:
                ok = self._check_diagnostic(path, kind)
                self._diagnostic_ok[label] = ok
                if ok:
                    self.status.setText(f"initialized {label}")
                else:
                    self.status.setText(f"waiting {label}")
                self._scan_phase = 0
                self._scan_index = (self._scan_index + 1) % len(self._diagnostics)

        ok_count, total = self._update_progress_bar()
        all_ok = (ok_count == total and total > 0)

        if phase in ("READY", "RECOVERY"):
            self.status.setText(f"{phase}: {message or 'Boot complete'}")

        ready = phase in ("READY", "RECOVERY")
        elapsed = time.monotonic() - self._boot_start
        can_finish = elapsed >= self.MIN_SPLASH_SECONDS
        if can_finish and (ready or all_ok):
            if not self._boot_done:
                self._boot_done = True
                self.timer.stop()
                QTimer.singleShot(200, self.boot_finished.emit)
