import json
import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QScrollArea, QScroller, QVBoxLayout, QWidget

from control.os_control import read_control, write_control
from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")
WORKLOAD_STATE_FILE = os.path.join(BASE_DIR, "workloads", "workload_state.json")


def read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def is_offline(state, max_age_seconds=20):
    if not state:
        return True
    last_updated = state.get("last_updated")
    if last_updated:
        try:
            import datetime

            last_dt = datetime.datetime.fromisoformat(last_updated)
            age = (datetime.datetime.now() - last_dt).total_seconds()
            return age > max_age_seconds
        except Exception:
            pass
    try:
        import datetime

        age = datetime.datetime.now().timestamp() - os.path.getmtime(STATE_FILE)
        return age > max_age_seconds
    except Exception:
        return True


class WaterCard(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 12px;
                border: none;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        self.title = QLabel(title)
        self.title.setStyleSheet(f"font-size: 14px; color: {theme.TEXT_MUTED}; font-weight: bold;")
        self.value = QLabel("--")
        self.value.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.detail = QLabel("--")
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_PRIMARY};")

        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.detail)


class WaterManagerPage(QWidget):
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
            QPushButton {{
                background-color: {theme.BUTTON_BG};
                color: {theme.TEXT_PRIMARY};
                border: 2px solid {theme.SHELL_BORDER};
                border-bottom: 4px solid #051f1c;
                border-radius: 8px;
                padding: 10px 12px;
            }}
            QPushButton:hover {{
                background-color: {theme.BUTTON_HOVER};
                border: 2px solid {theme.TEXT_SECONDARY};
                border-bottom: 4px solid #051f1c;
            }}
            QPushButton:pressed {{
                background-color: {theme.BUTTON_ACTIVE};
                border: 2px solid {theme.TEXT_PRIMARY};
                border-bottom: 2px solid #051f1c;
                padding-top: 12px;
                padding-bottom: 8px;
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
        self.layout.setSpacing(16)
        self.layout.setContentsMargins(24, 24, 24, 24)

        self.title = QLabel("WATER MANAGER")
        self.title.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.layout.addWidget(self.title)

        self.subtitle = QLabel("Irrigation readiness, moisture recovery, and water-related controls.")
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        self.layout.addWidget(self.subtitle)

        self.summary = QLabel("Checking irrigation state...")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet(
            f"""
            font-size: 14px;
            font-weight: bold;
            background-color: {theme.BUTTON_BG};
            border: none;
            border-radius: 10px;
            padding: 10px 12px;
            """
        )
        self.layout.addWidget(self.summary)

        self.irrigation_card = WaterCard("Irrigation State")
        self.moisture_card = WaterCard("Soil Recovery")
        self.workload_card = WaterCard("Watering Workload")
        self.policy_card = WaterCard("Watering Guidance")

        for card in (
            self.irrigation_card,
            self.moisture_card,
            self.workload_card,
            self.policy_card,
        ):
            self.layout.addWidget(card)

        self.enable_irrigation_btn = QPushButton("Enable Irrigation")
        self.disable_irrigation_btn = QPushButton("Disable Irrigation")
        self.toggle_workload_btn = QPushButton("Toggle Irrigation Workload")

        self.enable_irrigation_btn.clicked.connect(lambda: self.set_irrigation(True))
        self.disable_irrigation_btn.clicked.connect(lambda: self.set_irrigation(False))
        self.toggle_workload_btn.clicked.connect(self.toggle_irrigation_workload)

        self.layout.addWidget(self.enable_irrigation_btn)
        self.layout.addWidget(self.disable_irrigation_btn)
        self.layout.addWidget(self.toggle_workload_btn)
        self.layout.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def set_irrigation(self, enabled):
        control = read_control()
        control["irrigation"] = bool(enabled)
        write_control(control)
        self.refresh()

    def toggle_irrigation_workload(self):
        control = read_control()
        workloads = control.get("workloads", {})
        workloads["irrigation"] = not bool(workloads.get("irrigation", True))
        control["workloads"] = workloads
        write_control(control)
        self.refresh()

    def refresh(self):
        state = read_json(STATE_FILE) or {}
        control = read_control()
        workloads = read_json(WORKLOAD_STATE_FILE) or {}

        if is_offline(state):
            self.summary.setText("Offline: waiting for irrigation and soil telemetry.")
            self.irrigation_card.value.setText("--")
            self.irrigation_card.detail.setText("Irrigation state unavailable.")
            self.moisture_card.value.setText("--")
            self.moisture_card.detail.setText("Soil moisture unavailable.")
            self.workload_card.value.setText("--")
            self.workload_card.detail.setText("Workload state unavailable.")
            self.policy_card.value.setText("--")
            self.policy_card.detail.setText("Guidance unavailable.")
            return

        sensors = state.get("sensors", {}) if isinstance(state.get("sensors"), dict) else {}
        soil = sensors.get("soil_moisture")
        irrigation_enabled = bool(control.get("irrigation", False))
        irrigation_workload = bool(control.get("workloads", {}).get("irrigation", True))
        irrigation_active = bool(workloads.get("irrigation", False))

        if irrigation_enabled:
            irrigation_state = "Enabled"
            irrigation_detail = "The irrigation actuator is currently allowed to run."
        else:
            irrigation_state = "Disabled"
            irrigation_detail = "The irrigation actuator is currently blocked."
        self.irrigation_card.value.setText(irrigation_state)
        self.irrigation_card.detail.setText(irrigation_detail)

        if soil is None:
            self.moisture_card.value.setText("N/A")
            self.moisture_card.detail.setText("No soil moisture reading is available yet.")
        elif soil >= 40:
            self.moisture_card.value.setText("Recovered")
            self.moisture_card.detail.setText(f"Soil moisture is healthy at {soil}%.")
        elif soil >= 20:
            self.moisture_card.value.setText("Watch")
            self.moisture_card.detail.setText(f"Soil moisture is {soil}%. Watch for further drying.")
        else:
            self.moisture_card.value.setText("Dry")
            self.moisture_card.detail.setText(f"Soil moisture is critically low at {soil}%.")

        workload_state = "Running" if irrigation_active else "Idle"
        workload_detail = (
            "Irrigation workload is enabled in control state."
            if irrigation_workload
            else "Irrigation workload is disabled in control state."
        )
        self.workload_card.value.setText(workload_state)
        self.workload_card.detail.setText(workload_detail)

        guidance = "Normal watering conditions."
        if soil is not None and soil < 20:
            guidance = "Soil is critically dry. Prioritize irrigation if safe."
        elif soil is not None and soil < 40:
            guidance = "Soil is drying. Monitor recovery and prepare irrigation."
        if not irrigation_workload:
            guidance += " Irrigation workload is currently disabled."
        if not irrigation_enabled:
            guidance += " Irrigation actuator is blocked."

        self.policy_card.value.setText("Guidance")
        self.policy_card.detail.setText(guidance)
        self.summary.setText(
            f"Water status: actuator {'enabled' if irrigation_enabled else 'disabled'} | workload {'enabled' if irrigation_workload else 'disabled'}"
        )
