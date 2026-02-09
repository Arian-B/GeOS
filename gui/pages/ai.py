# gui/pages/ai.py

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame
from PySide6.QtCore import QTimer
import json
import os
from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")
FEATURE_IMPORTANCE_FILE = os.path.join(BASE_DIR, "datasets", "feature_importance.json")


# -----------------------------
# HELPERS
# -----------------------------
def read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


# -----------------------------
# AI PAGE
# -----------------------------
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

        # =============================
        # HEADER
        # =============================
        self.header = QLabel("AI POLICY & DECISION ENGINE")
        self.header.setStyleSheet("""
            font-size: 26px;
            font-weight: bold;
        """)

        # =============================
        # MODE STATUS
        # =============================
        self.current_mode = QLabel("Current OS Mode: --")
        self.ml_mode = QLabel("ML Suggested Mode: --")

        self.current_mode.setStyleSheet("font-size: 16px;")
        self.ml_mode.setStyleSheet("font-size: 16px;")

        # =============================
        # REASONING PANEL
        # =============================
        reasoning_frame = QFrame()
        reasoning_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 8px;
            }}
        """)
        reasoning_layout = QVBoxLayout(reasoning_frame)

        self.reason_label = QLabel("Decision Reasoning: --")
        self.reason_label.setWordWrap(True)
        self.reason_label.setStyleSheet("font-size: 14px;")

        reasoning_layout.addWidget(self.reason_label)

        # =============================
        # RECOMMENDATION PANEL
        # =============================
        recommendation_frame = QFrame()
        recommendation_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 8px;
            }}
        """)
        recommendation_layout = QVBoxLayout(recommendation_frame)

        self.recommendation_label = QLabel("System Recommendation: --")
        self.recommendation_label.setWordWrap(True)
        self.recommendation_label.setStyleSheet("font-size: 14px;")

        recommendation_layout.addWidget(self.recommendation_label)

        # =============================
        # FEATURE IMPORTANCE PANEL
        # =============================
        feature_frame = QFrame()
        feature_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 8px;
            }}
        """)
        feature_layout = QVBoxLayout(feature_frame)

        self.feature_header = QLabel("ML Feature Importance (Policy Model)")
        self.feature_header.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
        """)

        self.feature_text = QLabel("--")
        self.feature_text.setStyleSheet("font-size: 13px;")
        self.feature_text.setWordWrap(True)

        feature_layout.addWidget(self.feature_header)
        feature_layout.addWidget(self.feature_text)

        # =============================
        # ASSEMBLE
        # =============================
        layout.addWidget(self.header)
        layout.addWidget(self.current_mode)
        layout.addWidget(self.ml_mode)
        layout.addWidget(reasoning_frame)
        layout.addWidget(recommendation_frame)
        layout.addWidget(feature_frame)
        layout.addStretch()

        # =============================
        # REFRESH TIMER
        # =============================
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)

        self.refresh()

    # -----------------------------
    # REFRESH LOGIC
    # -----------------------------
    def refresh(self):
        state = read_json(STATE_FILE)
        if not state:
            return

        current = state.get("current_mode", "UNKNOWN")
        suggested = state.get("ml_suggested_mode", "UNKNOWN")
        sensors = state.get("sensors", {})

        self.current_mode.setText(f"Current OS Mode: {current}")
        self.ml_mode.setText(f"ML Suggested Mode: {suggested}")


        last_time = state.get("last_ai_action_time")
        if last_time:
            self.recommendation_label.setText(
                self.recommendation_label.text() +
                f"\n\nLast AI action at: {last_time}"
            )

        # =============================
        # DECISION REASONING
        # =============================
        soil = sensors.get("soil_moisture", 0)
        battery = sensors.get("battery", 100)
        temp = sensors.get("temperature", 0)
        cpu = sensors.get("cpu_percent", 0)

        reasons = []

        if soil < 30:
            reasons.append("Soil moisture below optimal threshold")
        if temp > 35:
            reasons.append("Temperature exceeds safe operating range")
        if battery < 20:
            reasons.append("Battery level critically low")
        if cpu > 60:
            reasons.append("High CPU utilization detected")

        if not reasons:
            reasons.append("All monitored parameters within stable range")

        self.reason_label.setText(
            "Decision Reasoning:\n• " + "\n• ".join(reasons)
        )

        # =============================
        # SYSTEM RECOMMENDATION
        # =============================
        if battery < 20:
            rec = "Prioritize energy saving to maximize system uptime."
        elif soil < 30:
            rec = "Activate irrigation to maintain crop health."
        elif cpu > 60:
            rec = "Reduce workload intensity to avoid system stress."
        else:
            rec = "System operating optimally. No intervention required."

        self.recommendation_label.setText(
            "System Recommendation:\n" + rec
        )

        # =============================
        # FEATURE IMPORTANCE
        # =============================
        importance = read_json(FEATURE_IMPORTANCE_FILE)

        if importance:
            lines = []
            for feature, score in importance.items():
                bar = "█" * int(score * 20)
                lines.append(f"{feature:<15} {bar}")

            self.feature_text.setText("\n".join(lines))
        else:
            self.feature_text.setText(
                "Feature importance data not available.\n"
                "Train ML policy model to generate insights."
            )
