import datetime
import json
import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QScroller, QVBoxLayout, QWidget

from core_os.notifications import get_active_alerts
from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")
PERF_FILE = os.path.join(BASE_DIR, "logs", "performance_metrics.json")
TELEMETRY_FILE = os.path.join(BASE_DIR, "datasets", "telemetry_log.jsonl")


def read_json(path):
    try:
        with open(path, "r") as handle:
            return json.load(handle)
    except Exception:
        return None


def telemetry_line_count(limit_path):
    try:
        with open(limit_path, "r") as handle:
            return sum(1 for _ in handle)
    except Exception:
        return 0


def current_mode_metrics(perf, mode_name):
    if not isinstance(perf, dict):
        return {}
    modes = perf.get("modes")
    if not isinstance(modes, dict):
        return {}
    entry = modes.get(mode_name)
    return entry if isinstance(entry, dict) else {}


class ReportCard(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border: 2px solid {theme.SHELL_BORDER};
                border-bottom: 4px solid #051f1c;
                border-radius: 12px;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        self.title = QLabel(title)
        self.title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.TEXT_SECONDARY};")
        self.value = QLabel("--")
        self.value.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.detail = QLabel("--")
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")

        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.detail)


class ReportsAppPage(QWidget):
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
        QScroller.grabGesture(self.scroll.viewport(), QScroller.TouchGesture)
        outer.addWidget(self.scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("REPORTS")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        subtitle = QLabel("Local operating summaries from current GeOS state, alerts, telemetry, and performance logs.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.summary = QLabel("Loading local reports...")
        self.summary.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_SECONDARY};")
        layout.addWidget(self.summary)

        self.mode_card = ReportCard("Current Operating Mode")
        self.alerts_card = ReportCard("Recent Alerts")
        self.performance_card = ReportCard("System Performance")
        self.telemetry_card = ReportCard("Telemetry Volume")
        self.runtime_card = ReportCard("Runtime Snapshot")

        for card in (
            self.mode_card,
            self.alerts_card,
            self.performance_card,
            self.telemetry_card,
            self.runtime_card,
        ):
            layout.addWidget(card)

        layout.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(5000)
        self.refresh()

    def refresh(self):
        state = read_json(STATE_FILE) or {}
        perf = read_json(PERF_FILE) or {}
        alerts = get_active_alerts(limit=25)
        telemetry_count = telemetry_line_count(TELEMETRY_FILE)

        mode = state.get("current_mode") or "--"
        policy = state.get("policy_source") or "--"
        self.mode_card.value.setText(mode)
        self.mode_card.detail.setText(f"Policy source: {policy}")

        critical = sum(1 for alert in alerts if str(alert.get("level", "")).upper() == "CRITICAL")
        warn = sum(1 for alert in alerts if str(alert.get("level", "")).upper() == "WARN")
        self.alerts_card.value.setText(str(len(alerts)))
        latest_message = alerts[0].get("message", "--") if alerts else "No recent alerts."
        self.alerts_card.detail.setText(
            f"{critical} critical, {warn} warnings in the recent alert window. Latest: {latest_message}"
        )

        mode_metrics = current_mode_metrics(perf, mode)
        avg_cpu = mode_metrics.get("avg_cpu", "--")
        avg_memory = mode_metrics.get("avg_memory", "--")
        switches = perf.get("total_switches", "--")
        duration = mode_metrics.get("duration_seconds", 0.0)
        try:
            duration_text = f"{float(duration):.1f}s"
        except (TypeError, ValueError):
            duration_text = "--"
        self.performance_card.value.setText(f"{switches} switches")
        self.performance_card.detail.setText(
            f"Mode runtime: {duration_text} | Avg CPU: {avg_cpu}% | Avg memory: {avg_memory}%"
        )

        self.telemetry_card.value.setText(str(telemetry_count))
        self.telemetry_card.detail.setText("Telemetry entries available in the local dataset log.")

        sensors = state.get("sensors", {}) if isinstance(state.get("sensors"), dict) else {}
        battery = sensors.get("battery")
        network = sensors.get("network", "--")
        runtime_value = f"{battery}% battery" if battery is not None else "External power"
        self.runtime_card.value.setText(runtime_value)
        self.runtime_card.detail.setText(
            f"Network: {network} | Last update: {state.get('last_updated', '--')} | Perf updated: {perf.get('last_updated', '--')}"
        )

        self.summary.setText(f"Report generated at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
