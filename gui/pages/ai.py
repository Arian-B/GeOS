# gui/pages/ai.py

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame, QScrollArea, QScroller
from PySide6.QtCore import QTimer, Qt
import json
import os
import joblib
import datetime
from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")
FEATURE_IMPORTANCE_FILE = os.path.join(BASE_DIR, "datasets", "feature_importance.json")
MODEL_FILE = os.path.join(BASE_DIR, "ml_engine", "policy_model.pkl")
CONTROL_FILE = os.path.join(BASE_DIR, "control", "control.json")
SAFE_MODE_FLAG = os.path.join(BASE_DIR, "control", "SAFE_MODE")
FEATURE_FRIENDLY_NAMES = {
    "battery": "Battery level",
    "soil_moisture": "Soil moisture",
    "temperature": "Temperature",
    "humidity": "Air humidity",
    "cpu_percent": "CPU usage",
    "memory_percent": "Memory usage",
    "load_avg": "System load",
    "hour": "Time of day",
}


# -----------------------------
# HELPERS
# -----------------------------

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


# -----------------------------
# AI PAGE
# -----------------------------
class AIPage(QWidget):
    _cached_importance = None
    _cached_top_features = None

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

        layout = QVBoxLayout(content)
        layout.setSpacing(18)
        layout.setContentsMargins(30, 30, 30, 30)

        # =============================
        # HEADER
        # =============================
        self.header = QLabel("FARM ASSISTANT")
        self.header.setStyleSheet("""
            font-size: 30px;
            font-weight: bold;
        """)
        self.subtitle = QLabel("Simple guidance from GeOS based on your live farm conditions")
        self.subtitle.setStyleSheet("font-size: 14px;")
        self.subtitle.setWordWrap(True)

        # =============================
        # MODE STATUS
        # =============================
        self.current_mode = QLabel("Current system mode: --")
        self.ml_mode = QLabel("AI recommendation: --")
        self.rl_action = QLabel("Decision source: --")
        self.confidence_label = QLabel("Confidence: --")
        self.top_features_label = QLabel("Main factors: --")

        for lbl in (self.current_mode, self.ml_mode, self.rl_action, self.confidence_label, self.top_features_label):
            lbl.setStyleSheet("font-size: 17px;")

        # =============================
        # REASONING PANEL
        # =============================
        reasoning_frame = QFrame()
        reasoning_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 8px;
                border: none;
            }}
        """)
        reasoning_layout = QVBoxLayout(reasoning_frame)

        self.reason_label = QLabel("Why this mode was chosen: --")
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
                border: none;
            }}
        """)
        recommendation_layout = QVBoxLayout(recommendation_frame)

        self.recommendation_label = QLabel("What you should do now: --")
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
                border: none;
            }}
        """)
        feature_layout = QVBoxLayout(feature_frame)

        self.feature_header = QLabel("What influences AI decisions most")
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
        layout.addWidget(self.subtitle)
        layout.addWidget(self.current_mode)
        layout.addWidget(self.ml_mode)
        layout.addWidget(self.rl_action)
        layout.addWidget(self.confidence_label)
        layout.addWidget(self.top_features_label)
        layout.addWidget(reasoning_frame)
        layout.addWidget(recommendation_frame)
        layout.addWidget(feature_frame)
        layout.addStretch()

        # =============================
        # INIT DATA (CACHED)
        # =============================
        self._load_feature_importance_once()

        # =============================
        # REFRESH TIMER
        # =============================
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(500)

        self.refresh()

    # -----------------------------
    # CACHE FEATURE IMPORTANCE ONCE
    # -----------------------------
    def _load_feature_importance_once(self):
        if AIPage._cached_importance is not None:
            return

        items = []
        importance = read_json(FEATURE_IMPORTANCE_FILE)

        if isinstance(importance, list):
            for entry in importance:
                if not isinstance(entry, dict):
                    continue
                feature = entry.get("feature")
                score = entry.get("importance")
                if feature is None or score is None:
                    continue
                items.append((feature, score))
        elif isinstance(importance, dict):
            items = list(importance.items())

        if not items:
            try:
                model = joblib.load(MODEL_FILE)
                if hasattr(model, "feature_importances_"):
                    importances = list(model.feature_importances_)
                    names = []
                    if hasattr(model, "feature_names_in_"):
                        names = list(model.feature_names_in_)
                    if not names or len(names) != len(importances):
                        names = [f"feature_{i}" for i in range(len(importances))]
                    items = list(zip(names, importances))
            except Exception:
                items = []

        items = sorted(items, key=lambda x: x[1], reverse=True)
        AIPage._cached_importance = items
        AIPage._cached_top_features = items[:3]

    # -----------------------------
    # UI HELPERS
    # -----------------------------
    def _confidence_bar(self, percent):
        total = 10
        filled = int(round(percent / 10))
        filled = max(0, min(total, filled))
        bar = "█" * filled + "░" * (total - filled)
        if percent >= 75:
            level = "high"
        elif percent >= 45:
            level = "medium"
        else:
            level = "low"
        return f"[{bar}] {percent}% ({level})"

    # -----------------------------
    # REFRESH LOGIC
    # -----------------------------
    def refresh(self):
        state = read_json(STATE_FILE)
        if is_offline(state):
            self._set_offline()
            return

        current = state.get("current_mode", "UNKNOWN")
        suggested = state.get("ml_suggested_mode", "UNKNOWN")
        rl_action = state.get("rl_action", "UNKNOWN")
        sensors = state.get("sensors", {})
        control = read_json(CONTROL_FILE) or {}
        safe_mode = bool(control.get("safe_mode")) or os.path.exists(SAFE_MODE_FLAG)
        maintenance = bool(control.get("maintenance", False))

        self.current_mode.setText(f"Current system mode: {current}")
        self.ml_mode.setText(f"AI recommendation: {suggested}")
        self.rl_action.setText(f"Decision source: {rl_action}")

        confidence = state.get("ml_confidence")
        if isinstance(confidence, (int, float)):
            confidence = int(round(max(0.0, min(1.0, confidence)) * 100))
        else:
            confidence = 80 if current == suggested else 55
        self.confidence_label.setText(f"Confidence: {self._confidence_bar(confidence)}")

        if AIPage._cached_top_features:
            top_parts = []
            for name, score in AIPage._cached_top_features:
                friendly = FEATURE_FRIENDLY_NAMES.get(name, name.replace("_", " ").title())
                top_parts.append(f"{friendly} ({int(round(score * 100))}%)")
            self.top_features_label.setText("Main factors: " + ", ".join(top_parts))
        else:
            self.top_features_label.setText("Main factors: --")

        last_time = state.get("last_ai_action_time")

        # =============================
        # DECISION REASONING
        # =============================
        soil = sensors.get("soil_moisture")
        battery = sensors.get("battery")
        temp = sensors.get("temperature")
        cpu = sensors.get("cpu_percent", 0)

        reasons = []

        if soil is not None and soil < 30:
            reasons.append("Soil moisture is low")
        if temp is not None and temp > 35:
            reasons.append("Temperature is above the safe range")
        if battery is not None and battery < 20:
            reasons.append("Battery is low")
        if cpu > 60:
            reasons.append("System load is high")
        if safe_mode:
            reasons.append("Safe mode is on, so workloads are reduced")
        if maintenance:
            reasons.append("Maintenance mode is on")

        if soil is None or temp is None or battery is None:
            reasons.append("Some sensor readings are missing")

        if not reasons:
            reasons.append("All readings are in a stable range")

        self.reason_label.setText(
            "Why this mode was chosen:\n• " + "\n• ".join(reasons)
        )

        # =============================
        # SYSTEM RECOMMENDATION
        # =============================
        if safe_mode:
            rec = "Keep Safe Mode on until sensor and workload values look stable."
        elif battery is not None and battery < 20:
            rec = "Use ENERGY_SAVER to protect uptime."
        elif soil is not None and soil < 30:
            rec = "Enable irrigation workload and monitor moisture recovery."
        elif cpu > 60:
            rec = "Reduce workload intensity until CPU usage drops."
        elif soil is None or temp is None or battery is None:
            rec = "Check sensor workload/input so AI can use complete data."
        else:
            rec = "System is healthy. Continue normal operation."

        rec_text = "What you should do now:\n" + rec
        if last_time:
            rec_text += f"\n\nLast AI action at: {last_time}"
        self.recommendation_label.setText(rec_text)

        # =============================
        # FEATURE IMPORTANCE
        # =============================
        if AIPage._cached_importance:
            lines = []
            for feature, score in AIPage._cached_importance[:5]:
                name = FEATURE_FRIENDLY_NAMES.get(feature, feature.replace("_", " ").title())
                try:
                    score_float = float(score)
                    bar = "█" * int(score_float * 20)
                except (TypeError, ValueError):
                    score_float = 0.0
                    bar = ""
                lines.append(f"{name:<18} {bar} {int(round(score_float * 100))}%")

            self.feature_text.setText("\n".join(lines))
        else:
            self.feature_text.setText(
                "AI importance data not available yet.\n"
                "Run policy training to generate this view."
            )

    def _set_offline(self):
        self.current_mode.setText("Current system mode: OFFLINE")
        self.ml_mode.setText("AI recommendation: --")
        self.rl_action.setText("Decision source: --")
        self.confidence_label.setText("Confidence: --")
        self.top_features_label.setText("Main factors: --")
        self.reason_label.setText("Why this mode was chosen:\n• System offline")
        self.recommendation_label.setText("What you should do now:\nWait for telemetry to reconnect")
