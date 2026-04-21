import json
import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QScrollArea, QScroller, QVBoxLayout, QWidget

from control.os_control import read_control, write_control
from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")
SAFE_MODE_FLAG = os.path.join(BASE_DIR, "control", "SAFE_MODE")


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


class PowerCard(QFrame):
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


class PowerCenterPage(QWidget):
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
        QScroller.grabGesture(self.scroll.viewport(), QScroller.TouchGesture)
        outer.addWidget(self.scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.scroll.setWidget(content)

        self.layout = QVBoxLayout(content)
        self.layout.setSpacing(16)
        self.layout.setContentsMargins(24, 24, 24, 24)

        self.title = QLabel("POWER CENTER")
        self.title.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.layout.addWidget(self.title)

        self.subtitle = QLabel("Energy mode, battery reserve, and GeOS power protection behavior.")
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        self.layout.addWidget(self.subtitle)

        self.summary = QLabel("Checking power state...")
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

        self.mode_card = PowerCard("Energy Mode")
        self.battery_card = PowerCard("Battery Reserve")
        self.health_card = PowerCard("Battery Health")
        self.policy_card = PowerCard("Power Guidance")
        self.runtime_card = PowerCard("Runtime Load")

        for card in (
            self.mode_card,
            self.battery_card,
            self.health_card,
            self.policy_card,
            self.runtime_card,
        ):
            self.layout.addWidget(card)

        self.energy_saver_btn = QPushButton("Switch To ENERGY_SAVER")
        self.balanced_btn = QPushButton("Switch To BALANCED")
        self.performance_btn = QPushButton("Switch To PERFORMANCE")
        self.auto_btn = QPushButton("Return To Automatic")
        self.safe_mode_btn = QPushButton("Toggle Safe Mode")

        self.energy_saver_btn.clicked.connect(lambda: self.set_mode("ENERGY_SAVER"))
        self.balanced_btn.clicked.connect(lambda: self.set_mode("BALANCED"))
        self.performance_btn.clicked.connect(lambda: self.set_mode("PERFORMANCE"))
        self.auto_btn.clicked.connect(lambda: self.set_mode(None))
        self.safe_mode_btn.clicked.connect(self.toggle_safe_mode)

        for button in (
            self.energy_saver_btn,
            self.balanced_btn,
            self.performance_btn,
            self.auto_btn,
            self.safe_mode_btn,
        ):
            self.layout.addWidget(button)

        self.layout.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def set_mode(self, mode):
        control = read_control()
        control["forced_mode"] = mode
        control["manual_override_mode"] = mode
        control["mode"] = "AUTO" if mode is None else "MANUAL"
        write_control(control)
        self.refresh()

    def toggle_safe_mode(self):
        enable = not os.path.exists(SAFE_MODE_FLAG)
        if enable:
            with open(SAFE_MODE_FLAG, "w") as f:
                f.write("1")
        else:
            try:
                os.remove(SAFE_MODE_FLAG)
            except FileNotFoundError:
                pass
        control = read_control()
        control["safe_mode"] = enable
        write_control(control)
        self.refresh()

    def refresh(self):
        state = read_json(STATE_FILE) or {}
        control = read_control()

        if is_offline(state):
            self.summary.setText("Offline: waiting for power and runtime telemetry.")
            for card in (
                self.mode_card,
                self.battery_card,
                self.health_card,
                self.policy_card,
                self.runtime_card,
            ):
                card.value.setText("--")
                card.detail.setText("Power data unavailable.")
            return

        sensors = state.get("sensors", {}) if isinstance(state.get("sensors"), dict) else {}
        current_mode = state.get("current_mode", "UNKNOWN")
        suggested_mode = state.get("ml_suggested_mode", "UNKNOWN")
        battery = sensors.get("battery")
        battery_health = sensors.get("battery_health")
        cpu = sensors.get("cpu_percent")
        memory = sensors.get("memory_percent")
        load = sensors.get("load_avg")
        safe_mode = bool(control.get("safe_mode", False)) or os.path.exists(SAFE_MODE_FLAG)

        self.mode_card.value.setText(current_mode)
        self.mode_card.detail.setText(
            f"Control mode: {control.get('mode', 'UNKNOWN')} | suggested: {suggested_mode}"
        )

        if battery is None:
            self.battery_card.value.setText("External")
            self.battery_card.detail.setText("This platform is not reporting a battery reserve.")
        elif battery >= 50:
            self.battery_card.value.setText(f"{battery}%")
            self.battery_card.detail.setText("Battery reserve is healthy.")
        elif battery >= 20:
            self.battery_card.value.setText(f"{battery}%")
            self.battery_card.detail.setText("Battery reserve is shrinking. Monitor energy usage.")
        else:
            self.battery_card.value.setText(f"{battery}%")
            self.battery_card.detail.setText("Battery reserve is low. Protect uptime.")

        self.health_card.value.setText(f"{battery_health}%" if battery_health is not None else "N/A")
        self.health_card.detail.setText(
            "Battery health is available from telemetry." if battery_health is not None else "Battery health is not reported by this platform."
        )

        guidance = "Normal energy conditions."
        if safe_mode:
            guidance = "Safe mode is active. GeOS is restricting workloads."
        elif battery is not None and battery < 20:
            guidance = "Use ENERGY_SAVER and avoid heavy workloads."
        elif cpu is not None and cpu > 60:
            guidance = "Reduce load or choose a lower-power mode."
        elif suggested_mode == "ENERGY_SAVER":
            guidance = "GeOS currently prefers energy preservation."
        self.policy_card.value.setText("Guidance")
        self.policy_card.detail.setText(guidance)

        self.runtime_card.value.setText(f"{cpu if cpu is not None else '--'}% CPU")
        self.runtime_card.detail.setText(
            f"Memory {memory if memory is not None else '--'}% | Load {load if load is not None else '--'}"
        )

        safe_text = "safe mode on" if safe_mode else "safe mode off"
        self.summary.setText(f"Power status: mode {current_mode.lower()} | {safe_text}")
        self.safe_mode_btn.setText("Disable Safe Mode" if safe_mode else "Enable Safe Mode")
