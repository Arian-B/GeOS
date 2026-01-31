# dashboard.py

import sys
import json
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QPushButton
)
from PySide6.QtCore import QTimer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")
CONTROL_FILE = os.path.join(BASE_DIR, "control", "control.json")

def read_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def write_control(control):
    with open(CONTROL_FILE, "w") as f:
        json.dump(control, f, indent=2)

class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GeOS")
        self.setFixedSize(500, 400)

        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #E0E0E0;
                font-family: Arial;
            }
            QLabel {
                font-size: 16px;
            }
            QPushButton {
                background-color: #1E1E1E;
                border: 1px solid #333;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2A2A2A;
            }
        """)

        self.mode_label = QLabel("MODE: --")
        self.mode_label.setStyleSheet("font-size: 22px; font-weight: bold;")

        self.ai_label = QLabel("AI: --")
        self.battery_label = QLabel("Battery: --")
        self.sensor_label = QLabel("Sensors: --")

        self.auto_btn = QPushButton("AUTO MODE")
        self.energy_btn = QPushButton("ENERGY SAVER")
        self.balanced_btn = QPushButton("BALANCED")
        self.performance_btn = QPushButton("PERFORMANCE")

        layout = QVBoxLayout()
        layout.addWidget(self.mode_label)
        layout.addWidget(self.ai_label)
        layout.addWidget(self.battery_label)
        layout.addWidget(self.sensor_label)
        layout.addSpacing(10)
        layout.addWidget(self.auto_btn)
        layout.addWidget(self.energy_btn)
        layout.addWidget(self.balanced_btn)
        layout.addWidget(self.performance_btn)

        self.setLayout(layout)

        self.auto_btn.clicked.connect(self.set_auto)
        self.energy_btn.clicked.connect(lambda: self.set_mode("ENERGY_SAVER"))
        self.balanced_btn.clicked.connect(lambda: self.set_mode("BALANCED"))
        self.performance_btn.clicked.connect(lambda: self.set_mode("PERFORMANCE"))

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1500)

    def refresh(self):
        state = read_state()

        self.mode_label.setText(f"MODE: {state['current_mode']}")
        self.ai_label.setText(f"AI SUGGESTION: {state['ml_suggested_mode']}")

        sensors = state["sensors"]
        self.battery_label.setText(
            f"Battery: {sensors.get('battery', '--')}% | "
            f"Health: {sensors.get('battery_health', '--')}%"
        )

        self.sensor_label.setText(
            f"Soil: {sensors.get('soil_moisture', '--')}  "
            f"Temp: {sensors.get('temperature', '--')}°C  "
            f"Humidity: {sensors.get('humidity', '--')}%"
        )

    def set_auto(self):
        write_control({"auto_mode": True, "mode_override": None})

    def set_mode(self, mode):
        write_control({"auto_mode": False, "mode_override": mode})

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec())
