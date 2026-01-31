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


class AIPage(QWidget):
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

        # === HEADER ===
        self.header = QLabel("AI SYSTEM INSIGHTS")
        self.header.setStyleSheet("font-size: 26px; font-weight: bold;")

        # === MODE INFO ===
        self.current_mode = QLabel("Current Mode: --")
        self.ml_mode = QLabel("ML Suggested Mode: --")

        # === REASONING ===
        reasoning_frame = QFrame()
        reasoning_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 8px;
            }}
        """)
        reasoning_layout = QVBoxLayout(reasoning_frame)

        self.reason_label = QLabel("Reasoning: --")
        self.reason_label.setWordWrap(True)

        reasoning_layout.addWidget(self.reason_label)

        # === RECOMMENDATION ===
        recommendation_frame = QFrame()
        recommendation_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 8px;
            }}
        """)
        recommendation_layout = QVBoxLayout(recommendation_frame)

        self.recommendation_label = QLabel("Recommendation: --")
        self.recommendation_label.setWordWrap(True)

        recommendation_layout.addWidget(self.recommendation_label)

        # === ADD TO LAYOUT ===
        layout.addWidget(self.header)
        layout.addWidget(self.current_mode)
        layout.addWidget(self.ml_mode)
        layout.addWidget(reasoning_frame)
        layout.addWidget(recommendation_frame)
        layout.addStretch()

        # === REFRESH ===
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)

        self.refresh()

    def refresh(self):
        state = read_state()
        if not state:
            return

        current = state.get("current_mode", "UNKNOWN")
        suggested = state.get("ml_suggested_mode", "UNKNOWN")
        sensors = state.get("sensors", {})

        self.current_mode.setText(f"Current Mode: {current}")
        self.ml_mode.setText(f"ML Suggested Mode: {suggested}")

        # SIMPLE EXPLANATION (HONEST)
        soil = sensors.get("soil_moisture", 0)
        battery = sensors.get("battery", 100)
        temp = sensors.get("temperature", 0)

        reasons = []
        if soil < 30:
            reasons.append("Low soil moisture detected")
        if temp > 35:
            reasons.append("High temperature detected")
        if battery < 20:
            reasons.append("Low battery level")

        if not reasons:
            reasons.append("Environmental conditions are stable")

        self.reason_label.setText("Reasoning:\n• " + "\n• ".join(reasons))

        # RECOMMENDATION
        if soil < 30:
            rec = "Irrigation is recommended to maintain crop health."
        elif battery < 20:
            rec = "Energy saving is recommended to extend system uptime."
        else:
            rec = "No immediate action required. System operating optimally."

        self.recommendation_label.setText(f"Recommendation:\n{rec}")
