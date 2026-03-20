import json
import os

import psutil
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QScroller, QVBoxLayout, QWidget

from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")
WORKLOAD_STATE_FILE = os.path.join(BASE_DIR, "workloads", "workload_state.json")
MANIFEST_FILE = os.path.join(BASE_DIR, "services", "manifest.json")

SERVICE_LABELS = {
    "boot_manager": "Boot Manager",
    "energy_controller": "Energy Controller",
    "workload_manager": "Workload Manager",
    "collector": "Telemetry Collector",
    "resource_daemon": "Resource Daemon",
    "update_watcher": "Update Watcher",
    "workflow_server": "Workflow API",
    "repl_server": "REPL Server",
    "metrics_server": "Metrics Server",
}

WORKLOAD_LABELS = {
    "sensor": "Sensor Network",
    "irrigation": "Irrigation System",
    "camera": "Farm Surveillance",
    "analytics": "Analytics Engine",
}


def read_json(path, default=None):
    if default is None:
        default = {}
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data
    except Exception:
        return default


def service_status_map():
    manifest = read_json(MANIFEST_FILE, default=[])
    results = []
    for entry in manifest if isinstance(manifest, list) else []:
        name = entry.get("name")
        module = entry.get("module")
        status = "stopped"
        pid = "--"
        if module:
            for proc in psutil.process_iter(attrs=["pid", "cmdline"]):
                try:
                    cmdline = proc.info.get("cmdline") or []
                    if module in cmdline:
                        status = "running"
                        pid = str(proc.info.get("pid", "--"))
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        results.append(
            {
                "name": name,
                "label": SERVICE_LABELS.get(name, str(name).replace("_", " ").title()),
                "status": status,
                "pid": pid,
            }
        )
    return results


class StatusCard(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 10px;
                border: none;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        self.title = QLabel(title)
        self.title.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.status = QLabel("Status: --")
        self.status.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")

        self.meta = QLabel("Details: --")
        self.meta.setWordWrap(True)
        self.meta.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_PRIMARY};")

        layout.addWidget(self.title)
        layout.addWidget(self.status)
        layout.addWidget(self.meta)

    def bind(self, status_text, meta_text, ok=True):
        color = theme.TEXT_SECONDARY if ok else theme.ACCENT_WARN
        self.status.setText(status_text)
        self.status.setStyleSheet(f"font-size: 13px; color: {color};")
        self.meta.setText(meta_text)


class TaskMonitorPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {theme.BACKGROUND};
                font-family: {theme.MONO_FONT};
            }}
            QLabel {{
                color: {theme.TEXT_PRIMARY};
                border: none;
                background: transparent;
            }}
            """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")
        QScroller.grabGesture(self.scroll.viewport(), QScroller.LeftMouseButtonGesture)
        outer.addWidget(self.scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.scroll.setWidget(content)

        self.layout = QVBoxLayout(content)
        self.layout.setSpacing(14)
        self.layout.setContentsMargins(24, 24, 24, 24)

        self.title = QLabel("TASK MONITOR")
        self.title.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.layout.addWidget(self.title)

        self.subtitle = QLabel("Running GeOS services, workloads, and live system load.")
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        self.layout.addWidget(self.subtitle)

        self.summary = QLabel("Gathering runtime data...")
        self.summary.setStyleSheet(f"font-size: 14px; color: {theme.TEXT_SECONDARY};")
        self.layout.addWidget(self.summary)

        self.system_card = StatusCard("System Load")
        self.workload_card = StatusCard("Workload Activity")
        self.layout.addWidget(self.system_card)
        self.layout.addWidget(self.workload_card)

        self.services_header = QLabel("Services")
        self.services_header.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(self.services_header)

        self.service_cards = []
        for name in SERVICE_LABELS.values():
            card = StatusCard(name)
            self.service_cards.append(card)
            self.layout.addWidget(card)

        self.layout.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1500)
        self.refresh()

    def refresh(self):
        state = read_json(STATE_FILE, default={})
        sensors = state.get("sensors", {}) if isinstance(state.get("sensors"), dict) else {}

        cpu = sensors.get("cpu_percent")
        memory = sensors.get("memory_percent")
        load = sensors.get("load_avg")
        current_mode = state.get("current_mode", "--")
        self.system_card.bind(
            f"Mode: {current_mode}",
            f"CPU {cpu if cpu is not None else '--'}% | Memory {memory if memory is not None else '--'}% | Load {load if load is not None else '--'}",
            ok=True,
        )

        workloads = read_json(WORKLOAD_STATE_FILE, default={})
        enabled = []
        for key, label in WORKLOAD_LABELS.items():
            if bool(workloads.get(key, False)):
                enabled.append(label)
        if enabled:
            workload_text = ", ".join(enabled)
            self.workload_card.bind(
                "Workloads active",
                workload_text,
                ok=True,
            )
        else:
            self.workload_card.bind(
                "Workloads idle",
                "No workload modules currently marked active.",
                ok=False,
            )

        services = service_status_map()
        running = sum(1 for item in services if item["status"] == "running")
        self.summary.setText(f"Runtime health: {running}/{len(services)} GeOS services running")

        for card, item in zip(self.service_cards, services):
            ok = item["status"] == "running"
            card.title.setText(item["label"])
            card.bind(
                f"Status: {item['status'].upper()}",
                f"PID: {item['pid']}",
                ok=ok,
            )
