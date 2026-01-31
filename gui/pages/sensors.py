from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame
from PySide6.QtCore import QTimer
import json
import os
from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")


def read_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None


def status_color(level):
    if level == "OK":
        return theme.MODE_COLORS["BALANCED"]
    elif level == "WARN":
        return "#FFD166"   # warning yellow
    else:
        return "#FF6B6B"   # critical red


class SensorCard(QFrame):
    def __init__(self, title):
        super().__init__()

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(20, 15, 20, 15)

        self.title = QLabel(title)
        self.title.setStyleSheet(f"""
            font-size: 18px;
            color: {theme.TEXT_PRIMARY};
        """)

        self.value = QLabel("--")
        self.value.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {theme.TEXT_PRIMARY};
        """)

        self.status = QLabel("STATUS: --")
        self.status.setStyleSheet(f"""
            font-size: 14px;
            color: {theme.TEXT_SECONDARY};
        """)

        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.status)


class SensorsPage(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        self.soil_card = SensorCard("Soil Moisture")
        self.temp_card = SensorCard("Temperature")
        self.humidity_card = SensorCard("Humidity")

        main_layout.addWidget(self.soil_card)
        main_layout.addWidget(self.temp_card)
        main_layout.addWidget(self.humidity_card)
        main_layout.addStretch()

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1500)

        self.refresh()

    def refresh(self):
        state = read_state()
        if not state:
            return

        sensors = state.get("sensors", {})

        # --- SOIL MOISTURE ---
        soil = sensors.get("soil_moisture", 0)
        if soil >= 40:
            soil_status = "OK"
        elif soil >= 20:
            soil_status = "WARN"
        else:
            soil_status = "CRITICAL"

        self.soil_card.value.setText(f"{soil}%")
        self.soil_card.status.setText(f"STATUS: {soil_status}")
        self.soil_card.status.setStyleSheet(
            f"font-size: 14px; color: {status_color(soil_status)};"
        )

        # --- TEMPERATURE ---
        temp = sensors.get("temperature", 0)
        if 18 <= temp <= 35:
            temp_status = "OK"
        elif 36 <= temp <= 40:
            temp_status = "WARN"
        else:
            temp_status = "CRITICAL"

        self.temp_card.value.setText(f"{temp} °C")
        self.temp_card.status.setText(f"STATUS: {temp_status}")
        self.temp_card.status.setStyleSheet(
            f"font-size: 14px; color: {status_color(temp_status)};"
        )

        # --- HUMIDITY ---
        humidity = sensors.get("humidity", 0)
        if 40 <= humidity <= 70:
            humidity_status = "OK"
        elif 30 <= humidity < 40 or 70 < humidity <= 80:
            humidity_status = "WARN"
        else:
            humidity_status = "CRITICAL"

        self.humidity_card.value.setText(f"{humidity}%")
        self.humidity_card.status.setText(f"STATUS: {humidity_status}")
        self.humidity_card.status.setStyleSheet(
            f"font-size: 14px; color: {status_color(humidity_status)};"
        )
