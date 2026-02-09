from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame, QPushButton
from PySide6.QtCore import QTimer
from control.os_control import read_control, write_control
import json
import os
from core_os.notifications import get_latest_alert
from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")


def read_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None


class HomePage(QWidget):
    def __init__(self):
        super().__init__()

        self.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_PRIMARY};
            }}
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(18)
        self.main_layout.setContentsMargins(30, 30, 30, 30)

        # === MODE SECTION ===
        self.mode_label = QLabel("MODE: --")
        self.mode_label.setStyleSheet("font-size: 26px; font-weight: bold;")

        self.control_state_label = QLabel("CONTROL: --")
        self.control_state_label.setStyleSheet("font-size: 16px;")

        self.force_save = QPushButton("Force Energy Saver")
        self.force_perf = QPushButton("Force Performance")
        self.resume_ai = QPushButton("Resume AI Control")

        for b in (self.force_save, self.force_perf, self.resume_ai):
            b.setFixedHeight(36)
            self.main_layout.addWidget(b)

        self.force_save.clicked.connect(lambda: self.set_mode("ENERGY_SAVER"))
        self.force_perf.clicked.connect(lambda: self.set_mode("PERFORMANCE"))
        self.resume_ai.clicked.connect(lambda: self.set_mode(None))


        # === POWER SECTION ===
        power_frame = QFrame()
        power_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 8px;
            }}
        """)
        power_layout = QVBoxLayout(power_frame)

        self.power_label = QLabel("Power: --")
        self.backup_label = QLabel("Backup: --")

        power_layout.addWidget(self.power_label)
        power_layout.addWidget(self.backup_label)

        # === NETWORK STATUS ===
        self.network_label = QLabel("Network: --")
        self.network_label.setStyleSheet("font-size: 16px;")

        # === ALERT BANNER ===
        self.alert_label = QLabel("")
        self.alert_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #FF6B6B;
        """)

        # === SENSOR SNAPSHOT ===
        sensor_frame = QFrame()
        sensor_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 8px;
            }}
        """)
        sensor_layout = QVBoxLayout(sensor_frame)

        self.soil_label = QLabel("Soil Moisture: --")
        self.temp_label = QLabel("Temperature: --")
        self.humidity_label = QLabel("Humidity: --")

        sensor_layout.addWidget(self.soil_label)
        sensor_layout.addWidget(self.temp_label)
        sensor_layout.addWidget(self.humidity_label)

        # === ADD TO MAIN LAYOUT (ONCE) ===
        self.main_layout.addWidget(self.mode_label)
        self.main_layout.addWidget(self.control_state_label)
        self.main_layout.addWidget(power_frame)
        self.main_layout.addWidget(self.network_label)
        self.main_layout.addWidget(self.alert_label)
        self.main_layout.addWidget(sensor_frame)
        self.main_layout.addStretch()

        # === REFRESH TIMER ===
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1500)

        self.refresh()

    def refresh(self):
        state = read_state()
        if not state:
            self.mode_label.setText("MODE: OS OFFLINE")
            return

        mode = state.get("current_mode", "UNKNOWN")
        sensors = state.get("sensors", {})

        # MODE COLOR
        mode_color = theme.MODE_COLORS.get(mode, theme.TEXT_PRIMARY)
        self.mode_label.setText(f"MODE: {mode}")
        self.mode_label.setStyleSheet(
            f"font-size: 26px; font-weight: bold; color: {mode_color};"
        )

        # CONTROL STATE
        control_state = "AUTO" if state.get("ml_suggested_mode") else "MANUAL"
        self.control_state_label.setText(f"CONTROL: {control_state}")

        # POWER
        battery = sensors.get("battery", 100)
        if battery > 20:
            self.power_label.setText("Power: External (OK)")
        else:
            self.power_label.setText("Power: Backup")

        self.backup_label.setText(f"Backup Level: {battery}%")

        # NETWORK STATUS
        network = sensors.get("network", "UNKNOWN")
        if network == "ONLINE":
            self.network_label.setText("Network: Connected")
            self.network_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
        else:
            self.network_label.setText("Network: Offline")
            self.network_label.setStyleSheet("color: #FF6B6B;")

        # ALERTS
        alert = get_latest_alert()
        if alert:
            self.alert_label.setText(f"[{alert['level']}] {alert['message']}")
        else:
            self.alert_label.setText("")

        # SENSOR SNAPSHOT
        self.soil_label.setText(f"Soil Moisture: {sensors.get('soil_moisture', '--')}%")
        self.temp_label.setText(f"Temperature: {sensors.get('temperature', '--')} °C")
        self.humidity_label.setText(f"Humidity: {sensors.get('humidity', '--')}%")


    def set_mode(self, mode):
        control = read_control()
        control["forced_mode"] = mode
        write_control(control)
