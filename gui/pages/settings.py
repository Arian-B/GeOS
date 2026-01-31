from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame
from PySide6.QtCore import QTimer
import json
import os
from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")
CONTROL_FILE = os.path.join(BASE_DIR, "control", "control.json")


def read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(30, 30, 30, 30)

        # === OS INFO ===
        os_frame = self.make_frame("Operating System", [
            "Name: GeOS",
            "Version: 1.0 (Prototype)",
            "Architecture: Linux-based (Edge)",
        ])

        # === HARDWARE INFO ===
        hw_frame = self.make_frame("Hardware Target", [
            "Platform: Raspberry Pi 4 Model B",
            "Display: 7-inch Touchscreen",
            "Deployment: USB / SD Card Boot",
        ])

        # === SYSTEM STATUS ===
        self.status_frame = self.make_frame("System Status", [
            "OS Mode: --",
            "Control Mode: --",
            "Network: --",
        ])

        # === SUSTAINABILITY ===
        sdg_frame = self.make_frame("Sustainability Goals", [
            "SDG 2: Zero Hunger",
            "SDG 7: Affordable & Clean Energy",
            "SDG 12: Responsible Consumption",
        ])

        layout.addWidget(os_frame)
        layout.addWidget(hw_frame)
        layout.addWidget(self.status_frame)
        layout.addWidget(sdg_frame)
        layout.addStretch()

        # === REFRESH ===
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)

        self.refresh()

    def make_frame(self, title, lines):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setSpacing(6)
        layout.setContentsMargins(20, 15, 20, 15)

        header = QLabel(title)
        header.setStyleSheet("font-size: 18px; font-weight: bold;")

        layout.addWidget(header)

        labels = []
        for line in lines:
            lbl = QLabel(line)
            layout.addWidget(lbl)
            labels.append(lbl)

        frame.labels = labels
        return frame

    def refresh(self):
        state = read_json(STATE_FILE)
        control = read_json(CONTROL_FILE)

        if not state or not control:
            return

        os_mode = state.get("current_mode", "UNKNOWN")
        control_mode = control.get("mode", "UNKNOWN")
        network = state.get("sensors", {}).get("network", "UNKNOWN")

        labels = self.status_frame.labels
        labels[0].setText(f"OS Mode: {os_mode}")
        labels[1].setText(f"Control Mode: {control_mode}")
        labels[2].setText(f"Network: {network}")
