import datetime
import json
import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QScroller, QVBoxLayout, QWidget

from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")
WORKLOAD_STATE_FILE = os.path.join(BASE_DIR, "workloads", "workload_state.json")


def read_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None


def read_workload_state():
    try:
        with open(WORKLOAD_STATE_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def is_offline(state, max_age_seconds=20):
    if not state:
        return True
    last_updated = state.get("last_updated")
    if last_updated:
        try:
            last_dt = datetime.datetime.fromisoformat(last_updated)
            age = (datetime.datetime.now() - last_dt).total_seconds()
            return age > max_age_seconds
        except Exception:
            pass
    try:
        age = datetime.datetime.now().timestamp() - os.path.getmtime(STATE_FILE)
        return age > max_age_seconds
    except Exception:
        return True


def field_status(soil, temp, humidity):
    issues = []
    if soil is not None and soil < 20:
        issues.append("critical soil dryness")
    elif soil is not None and soil < 40:
        issues.append("dry soil")
    if temp is not None and temp > 40:
        issues.append("extreme heat")
    elif temp is not None and temp > 35:
        issues.append("high temperature")
    if humidity is not None and (humidity < 30 or humidity > 80):
        issues.append("humidity imbalance")

    if not issues:
        return "Stable", "Field conditions are currently in a healthy operating range."
    if any(issue.startswith("critical") or issue == "extreme heat" for issue in issues):
        return "Critical", "Immediate attention required: " + ", ".join(issues) + "."
    return "Watch", "Monitor conditions: " + ", ".join(issues) + "."


def format_sensor(value, suffix=""):
    if value is None:
        return "N/A"
    return f"{value}{suffix}"


class SensorCard(QFrame):
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
        layout.setSpacing(6)
        layout.setContentsMargins(18, 16, 18, 16)

        self.title = QLabel(title)
        self.title.setStyleSheet(f"font-size: 14px; color: {theme.TEXT_MUTED}; font-weight: bold;")
        self.value = QLabel("--")
        self.value.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.status = QLabel("--")
        self.status.setWordWrap(True)
        self.status.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_PRIMARY};")

        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.status)


class SensorsPage(QWidget):
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

        self.layout = QVBoxLayout(content)
        self.layout.setSpacing(16)
        self.layout.setContentsMargins(24, 24, 24, 24)

        self.title = QLabel("FIELD MONITOR")
        self.title.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.layout.addWidget(self.title)

        self.subtitle = QLabel("Live field conditions, environment quality, and sensor freshness.")
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        self.layout.addWidget(self.subtitle)

        self.summary = QLabel("Waiting for field data...")
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

        self.soil_card = SensorCard("Soil Moisture")
        self.temp_card = SensorCard("Temperature")
        self.humidity_card = SensorCard("Humidity")
        self.battery_card = SensorCard("Battery Reserve")
        self.network_card = SensorCard("Field Connectivity")
        self.compute_card = SensorCard("System Load")

        for card in (
            self.soil_card,
            self.temp_card,
            self.humidity_card,
            self.battery_card,
            self.network_card,
            self.compute_card,
        ):
            self.layout.addWidget(card)

        self.layout.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def refresh(self):
        state = read_state()
        if is_offline(state):
            self._set_offline()
            return

        sensors = state.get("sensors", {}) if isinstance(state.get("sensors"), dict) else {}
        workloads = read_workload_state()

        soil = sensors.get("soil_moisture")
        temp = sensors.get("temperature")
        humidity = sensors.get("humidity")
        battery = sensors.get("battery")
        network = sensors.get("network", "OFFLINE")
        cpu = sensors.get("cpu_percent")
        memory = sensors.get("memory_percent")
        load = sensors.get("load_avg")

        status, description = field_status(soil, temp, humidity)
        active_modules = [name for name, enabled in workloads.items() if enabled]
        if active_modules:
            description += " Active modules: " + ", ".join(active_modules) + "."
        self.summary.setText(f"{status}: {description}")

        self.soil_card.value.setText(format_sensor(soil, "%"))
        if soil is None:
            self.soil_card.status.setText("No soil reading available yet.")
        elif soil >= 40:
            self.soil_card.status.setText("Moisture is in a healthy range.")
        elif soil >= 20:
            self.soil_card.status.setText("Soil is drying. Watch irrigation need.")
        else:
            self.soil_card.status.setText("Soil is critically dry. Irrigation should be prioritized.")

        self.temp_card.value.setText(format_sensor(temp, " C"))
        if temp is None:
            self.temp_card.status.setText("No temperature reading available yet.")
        elif 18 <= temp <= 35:
            self.temp_card.status.setText("Temperature is within the normal field range.")
        elif 35 < temp <= 40:
            self.temp_card.status.setText("Temperature is elevated. Watch heat stress.")
        else:
            self.temp_card.status.setText("Temperature is outside the safe operating range.")

        self.humidity_card.value.setText(format_sensor(humidity, "%"))
        if humidity is None:
            self.humidity_card.status.setText("No humidity reading available yet.")
        elif 40 <= humidity <= 70:
            self.humidity_card.status.setText("Air humidity is in a healthy range.")
        else:
            self.humidity_card.status.setText("Humidity is outside the preferred range.")

        self.battery_card.value.setText(format_sensor(battery, "%"))
        if battery is None:
            self.battery_card.status.setText("Battery data not reported by this platform.")
        elif battery >= 50:
            self.battery_card.status.setText("Power reserve is healthy.")
        elif battery >= 20:
            self.battery_card.status.setText("Battery reserve is shrinking. Monitor power use.")
        else:
            self.battery_card.status.setText("Battery reserve is low. Protect uptime.")

        self.network_card.value.setText(network)
        self.network_card.status.setText(
            "Field network link is available." if network == "ONLINE" else "Field network link is currently offline."
        )

        self.compute_card.value.setText(format_sensor(cpu, "%"))
        self.compute_card.status.setText(
            f"Memory {format_sensor(memory, '%')} | Load {load if load is not None else '--'}"
        )

    def _set_offline(self):
        self.summary.setText("Offline: waiting for live telemetry from the field controller.")
        for card, message in (
            (self.soil_card, "Soil data unavailable."),
            (self.temp_card, "Temperature data unavailable."),
            (self.humidity_card, "Humidity data unavailable."),
            (self.battery_card, "Power data unavailable."),
            (self.network_card, "Connectivity data unavailable."),
            (self.compute_card, "System load data unavailable."),
        ):
            card.value.setText("--")
            card.status.setText(message)
