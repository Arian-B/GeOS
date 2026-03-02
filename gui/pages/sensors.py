from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame, QScrollArea, QScroller
from PySide6.QtCore import QTimer, Qt
import json
import os
import datetime
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


def status_color(level):
    if level == "OK":
        return theme.TEXT_SECONDARY
    elif level == "WARN":
        return theme.TEXT_PRIMARY
    else:
        return theme.TEXT_PRIMARY

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


class SensorCard(QFrame):
    def __init__(self, title):
        super().__init__()

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 10px;
                border: none;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(20, 15, 20, 15)

        self.title = QLabel(title)
        self.title.setStyleSheet(f"""
            font-size: 18px;
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.MONO_FONT};
        """)

        self.value = QLabel("--")
        self.value.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.MONO_FONT};
        """)

        self.status = QLabel("STATUS: --")
        self.status.setStyleSheet(f"""
            font-size: 14px;
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.MONO_FONT};
        """)

        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.status)

    def set_title_color(self, color_hex):
        self.title.setStyleSheet(f"""
            font-size: 18px;
            color: {color_hex};
            font-family: {theme.MONO_FONT};
        """)


class SensorsPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.BACKGROUND};
                font-family: {theme.MONO_FONT};
            }}
            QLabel {{
                color: {theme.TEXT_PRIMARY};
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")
        QScroller.grabGesture(self.scroll.viewport(), QScroller.LeftMouseButtonGesture)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll)

        main_layout = QVBoxLayout(content)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(30, 30, 30, 30)

        self.soil_card = SensorCard("Soil Moisture")
        self.temp_card = SensorCard("Temperature")
        self.humidity_card = SensorCard("Humidity")
        self.battery_card = SensorCard("Battery Level")
        self.health_card = SensorCard("Battery Health")
        self.network_card = SensorCard("Network Status")
        self.cpu_card = SensorCard("CPU Utilization")
        self.mem_card = SensorCard("Memory Utilization")
        self.load_card = SensorCard("Load Average")

        main_layout.addWidget(self.soil_card)
        main_layout.addWidget(self.temp_card)
        main_layout.addWidget(self.humidity_card)
        main_layout.addWidget(self.battery_card)
        main_layout.addWidget(self.health_card)
        main_layout.addWidget(self.network_card)
        main_layout.addWidget(self.cpu_card)
        main_layout.addWidget(self.mem_card)
        main_layout.addWidget(self.load_card)
        main_layout.addStretch()

        self.anim_toggle = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(500)

        self.refresh()

    def refresh(self):
        state = read_state()
        if is_offline(state):
            self._set_offline()
            return

        sensors = state.get("sensors", {})

        # --- SOIL MOISTURE ---
        soil = sensors.get("soil_moisture")
        if soil is None:
            soil_status = "NO DATA"
            self.soil_card.value.setText("N/A")
            self.soil_card.status.setText(f"STATUS: {soil_status}")
            self.soil_card.status.setStyleSheet(
                f"font-size: 14px; color: {theme.TEXT_SECONDARY}; font-family: {theme.MONO_FONT};"
            )
        else:
            if soil >= 40:
                soil_status = "OK"
            elif soil >= 20:
                soil_status = "WARN"
            else:
                soil_status = "CRITICAL"
            self.soil_card.value.setText(f"{soil}%")
            self.soil_card.status.setText(f"STATUS: {soil_status}")
            self.soil_card.status.setStyleSheet(
                f"font-size: 14px; color: {status_color(soil_status)}; font-family: {theme.MONO_FONT};"
            )

        # --- TEMPERATURE ---
        temp = sensors.get("temperature")
        if temp is None:
            temp_status = "NO DATA"
            self.temp_card.value.setText("N/A")
            self.temp_card.status.setText(f"STATUS: {temp_status}")
            self.temp_card.status.setStyleSheet(
                f"font-size: 14px; color: {theme.TEXT_SECONDARY}; font-family: {theme.MONO_FONT};"
            )
        else:
            if 18 <= temp <= 35:
                temp_status = "OK"
            elif 36 <= temp <= 40:
                temp_status = "WARN"
            else:
                temp_status = "CRITICAL"
            self.temp_card.value.setText(f"{temp} °C")
            self.temp_card.status.setText(f"STATUS: {temp_status}")
            self.temp_card.status.setStyleSheet(
                f"font-size: 14px; color: {status_color(temp_status)}; font-family: {theme.MONO_FONT};"
            )

        # --- HUMIDITY ---
        humidity = sensors.get("humidity")
        if humidity is None:
            humidity_status = "NO DATA"
            self.humidity_card.value.setText("N/A")
            self.humidity_card.status.setText(f"STATUS: {humidity_status}")
            self.humidity_card.status.setStyleSheet(
                f"font-size: 14px; color: {theme.TEXT_SECONDARY}; font-family: {theme.MONO_FONT};"
            )
        else:
            if 40 <= humidity <= 70:
                humidity_status = "OK"
            elif 30 <= humidity < 40 or 70 < humidity <= 80:
                humidity_status = "WARN"
            else:
                humidity_status = "CRITICAL"
            self.humidity_card.value.setText(f"{humidity}%")
            self.humidity_card.status.setText(f"STATUS: {humidity_status}")
            self.humidity_card.status.setStyleSheet(
                f"font-size: 14px; color: {status_color(humidity_status)}; font-family: {theme.MONO_FONT};"
            )

        # --- BATTERY LEVEL ---
        battery = sensors.get("battery")
        if battery is None:
            battery_status = "NO DATA"
            self.battery_card.value.setText("N/A")
            self.battery_card.status.setText(f"STATUS: {battery_status}")
            self.battery_card.status.setStyleSheet(
                f"font-size: 14px; color: {theme.TEXT_SECONDARY}; font-family: {theme.MONO_FONT};"
            )
        else:
            if battery >= 50:
                battery_status = "OK"
            elif battery >= 20:
                battery_status = "WARN"
            else:
                battery_status = "CRITICAL"
            self.battery_card.value.setText(f"{battery}%")
            self.battery_card.status.setText(f"STATUS: {battery_status}")
            self.battery_card.status.setStyleSheet(
                f"font-size: 14px; color: {status_color(battery_status)}; font-family: {theme.MONO_FONT};"
            )

        # --- BATTERY HEALTH ---
        health = sensors.get("battery_health")
        if health is None:
            health_status = "NO DATA"
            self.health_card.value.setText("N/A")
            self.health_card.status.setText(f"STATUS: {health_status}")
            self.health_card.status.setStyleSheet(
                f"font-size: 14px; color: {theme.TEXT_SECONDARY}; font-family: {theme.MONO_FONT};"
            )
        else:
            if health >= 80:
                health_status = "OK"
            elif health >= 50:
                health_status = "WARN"
            else:
                health_status = "CRITICAL"
            self.health_card.value.setText(f"{health}%")
            self.health_card.status.setText(f"STATUS: {health_status}")
            self.health_card.status.setStyleSheet(
                f"font-size: 14px; color: {status_color(health_status)}; font-family: {theme.MONO_FONT};"
            )

        # --- NETWORK STATUS ---
        network = sensors.get("network")
        if network is None:
            network_status = "NO DATA"
            self.network_card.value.setText("N/A")
            self.network_card.status.setText(f"STATUS: {network_status}")
            self.network_card.status.setStyleSheet(
                f"font-size: 14px; color: {theme.TEXT_SECONDARY}; font-family: {theme.MONO_FONT};"
            )
        else:
            network_status = "OK" if network == "ONLINE" else "WARN"
            self.network_card.value.setText(network)
            self.network_card.status.setText(f"STATUS: {network_status}")
            self.network_card.status.setStyleSheet(
                f"font-size: 14px; color: {status_color(network_status)}; font-family: {theme.MONO_FONT};"
            )

        # --- CPU UTILIZATION ---
        cpu = sensors.get("cpu_percent", 0)
        if cpu < 60:
            cpu_status = "OK"
        elif cpu < 80:
            cpu_status = "WARN"
        else:
            cpu_status = "CRITICAL"

        self.cpu_card.value.setText(f"{cpu}%")
        self.cpu_card.status.setText(f"STATUS: {cpu_status}")
        self.cpu_card.status.setStyleSheet(
            f"font-size: 14px; color: {status_color(cpu_status)}; font-family: {theme.MONO_FONT};"
        )

        # --- MEMORY UTILIZATION ---
        mem = sensors.get("memory_percent", 0)
        if mem < 60:
            mem_status = "OK"
        elif mem < 80:
            mem_status = "WARN"
        else:
            mem_status = "CRITICAL"

        self.mem_card.value.setText(f"{mem}%")
        self.mem_card.status.setText(f"STATUS: {mem_status}")
        self.mem_card.status.setStyleSheet(
            f"font-size: 14px; color: {status_color(mem_status)}; font-family: {theme.MONO_FONT};"
        )

        # --- LOAD AVERAGE ---
        load = sensors.get("load_avg", 0)
        if load < 1.0:
            load_status = "OK"
        elif load < 2.0:
            load_status = "WARN"
        else:
            load_status = "CRITICAL"

        self.load_card.value.setText(f"{load}")
        self.load_card.status.setText(f"STATUS: {load_status}")
        self.load_card.status.setStyleSheet(
            f"font-size: 14px; color: {status_color(load_status)}; font-family: {theme.MONO_FONT};"
        )

        # --- SUBTLE ANIMATIONS ---
        workloads = read_workload_state()
        analytics_active = workloads.get("analytics", False)
        irrigation_active = workloads.get("irrigation", False)

        self.anim_toggle = not self.anim_toggle

        if analytics_active:
            color = theme.TEXT_SECONDARY if self.anim_toggle else theme.TEXT_PRIMARY
            self.cpu_card.set_title_color(color)
        else:
            self.cpu_card.set_title_color(theme.TEXT_PRIMARY)

        if irrigation_active:
            color = theme.TEXT_SECONDARY if self.anim_toggle else theme.TEXT_PRIMARY
            self.soil_card.set_title_color(color)
        else:
            self.soil_card.set_title_color(theme.TEXT_PRIMARY)

    def _set_offline(self):
        for card, title in (
            (self.soil_card, "Soil Moisture"),
            (self.temp_card, "Temperature"),
            (self.humidity_card, "Humidity"),
            (self.battery_card, "Battery Level"),
            (self.health_card, "Battery Health"),
            (self.network_card, "Network Status"),
            (self.cpu_card, "CPU Utilization"),
            (self.mem_card, "Memory Utilization"),
            (self.load_card, "Load Average"),
        ):
            card.set_title_color(theme.TEXT_SECONDARY)
            card.value.setText("--")
            card.status.setText("STATUS: OFFLINE")
            card.status.setStyleSheet(
                f"font-size: 14px; color: {theme.TEXT_SECONDARY}; font-family: {theme.MONO_FONT};"
            )
