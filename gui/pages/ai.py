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
MODEL_META_FILE = os.path.join(BASE_DIR, "ml_engine", "policy_model.meta.json")
CONTROL_FILE = os.path.join(BASE_DIR, "control", "control.json")
SAFE_MODE_FLAG = os.path.join(BASE_DIR, "control", "SAFE_MODE")
FEATURE_FRIENDLY_NAMES = {
    "battery": "Battery level",
    "battery_avg": "Battery average",
    "battery_delta": "Battery change",
    "battery_low_streak": "Low-battery streak",
    "soil_moisture": "Soil moisture",
    "soil_moisture_avg": "Soil moisture average",
    "soil_moisture_delta": "Soil moisture change",
    "soil_dry_streak": "Dry-soil streak",
    "temperature": "Temperature",
    "temperature_avg": "Temperature average",
    "temperature_delta": "Temperature change",
    "temp_high_streak": "High-temperature streak",
    "humidity": "Air humidity",
    "humidity_avg": "Air humidity average",
    "humidity_delta": "Air humidity change",
    "cpu_percent": "CPU usage",
    "cpu_percent_avg": "Average CPU usage",
    "cpu_percent_delta": "CPU usage change",
    "memory_percent": "Memory usage",
    "memory_percent_avg": "Average memory usage",
    "memory_percent_delta": "Memory usage change",
    "load_avg": "System load",
    "load_avg_avg": "Average system load",
    "load_avg_delta": "System load change",
    "hour": "Time of day",
    "control_manual": "Manual control mode",
    "control_auto": "Automatic control mode",
    "workload_active_count_avg": "Average active workloads",
    "workload_enabled_count_avg": "Average enabled workloads",
    "network_online": "Network online state",
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
        self.policy_source_label = QLabel("Policy source: --")
        self.confidence_label = QLabel("Confidence: --")
        self.top_features_label = QLabel("Main factors: --")
        self.model_summary = QLabel("Model: --")

        for lbl in (self.current_mode, self.ml_mode, self.policy_source_label, self.confidence_label, self.top_features_label, self.model_summary):
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
        layout.addWidget(self.policy_source_label)
        layout.addWidget(self.confidence_label)
        layout.addWidget(self.top_features_label)
        layout.addWidget(self.model_summary)
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

    def _friendly_feature_name(self, name):
        return FEATURE_FRIENDLY_NAMES.get(name, str(name).replace("_", " ").title())

    def _format_local_feature(self, entry):
        if not isinstance(entry, dict):
            return None
        name = self._friendly_feature_name(entry.get("feature"))
        contribution = entry.get("contribution")
        direction = entry.get("direction")
        if isinstance(contribution, (int, float)):
            direction_text = "supports" if direction != "opposes_prediction" else "pushes against"
            return f"{name} ({direction_text}, {contribution:+.2f})"
        importance = entry.get("importance")
        if isinstance(importance, (int, float)):
            return f"{name} ({int(round(importance * 100))}%)"
        return name

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
        policy_source = state.get("policy_source", "UNKNOWN")
        sensors = state.get("sensors", {})
        control = read_json(CONTROL_FILE) or {}
        meta = read_json(MODEL_META_FILE) or {}
        safe_mode = bool(control.get("safe_mode")) or os.path.exists(SAFE_MODE_FLAG)
        maintenance = bool(control.get("maintenance", False))

        self.current_mode.setText(f"Current system mode: {current}")
        self.ml_mode.setText(f"AI recommendation: {suggested}")
        self.policy_source_label.setText(f"Policy source: {policy_source}")

        confidence = state.get("ml_confidence")
        raw_confidence = state.get("ml_raw_confidence")
        confidence_source = state.get("ml_confidence_source")
        if isinstance(confidence, (int, float)):
            confidence = int(round(max(0.0, min(1.0, confidence)) * 100))
        else:
            confidence = 80 if current == suggested else 55
        confidence_text = f"Confidence: {self._confidence_bar(confidence)}"
        if confidence_source == "CALIBRATED" and isinstance(raw_confidence, (int, float)):
            raw_percent = int(round(max(0.0, min(1.0, raw_confidence)) * 100))
            confidence_text += f" | raw {raw_percent}%"
        elif confidence_source:
            confidence_text += f" | {str(confidence_source).replace('_', ' ').title()}"
        self.confidence_label.setText(confidence_text)

        state_top_features = state.get("ml_top_features")
        if isinstance(state_top_features, list) and state_top_features:
            top_items = []
            for entry in state_top_features[:3]:
                if not isinstance(entry, dict):
                    continue
                top_items.append((entry.get("feature"), entry.get("importance", 0.0)))
        else:
            top_items = AIPage._cached_top_features or []

        if top_items:
            top_parts = []
            for entry in state_top_features[:3] if isinstance(state_top_features, list) and state_top_features else []:
                formatted = self._format_local_feature(entry)
                if formatted:
                    top_parts.append(formatted)
            if not top_parts:
                for name, score in top_items:
                    friendly = self._friendly_feature_name(name)
                    top_parts.append(f"{friendly} ({int(round(score * 100))}%)")
            self.top_features_label.setText("Main factors: " + ", ".join(top_parts))
        else:
            self.top_features_label.setText("Main factors: --")

        model_type = meta.get("model_type", "UNKNOWN")
        trained_at = meta.get("trained_at", "--")
        self.model_summary.setText(f"Model: {model_type} | Trained: {trained_at}")

        last_time = state.get("last_ai_action_time")

        # =============================
        # DECISION REASONING
        # =============================
        soil = sensors.get("soil_moisture")
        battery = sensors.get("battery")
        temp = sensors.get("temperature")
        cpu = sensors.get("cpu_percent", 0)

        reasons = []
        for code in state.get("ml_reason_codes", []):
            if code == "manual_override":
                reasons.append("Manual control override is active")
            elif code == "safety_override":
                reasons.append("Safety policy overrode the learned policy")
            elif code == "lightgbm_policy":
                reasons.append("Mode selected by the LightGBM policy model")
            elif code == "emergency_shutdown":
                reasons.append("Emergency shutdown mode is active")
            elif code == "maintenance_mode":
                reasons.append("Maintenance mode is active")

        local_explanations = []
        for entry in state.get("ml_top_features", [])[:3]:
            formatted = self._format_local_feature(entry)
            if formatted:
                local_explanations.append(formatted)
        if local_explanations:
            reasons.append("LightGBM evidence: " + "; ".join(local_explanations))

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
                name = self._friendly_feature_name(feature)
                try:
                    score_float = float(score)
                    bar = "█" * int(score_float * 20)
                except (TypeError, ValueError):
                    score_float = 0.0
                    bar = ""
                lines.append(f"{name:<18} {bar} {int(round(score_float * 100))}%")

            self.feature_text.setText("\n".join(lines))
        else:
            meta = read_json(MODEL_META_FILE) or {}
            model_name = meta.get("model_type", "LightGBM")
            self.feature_text.setText(
                f"{model_name} policy model configured.\n"
                "Feature importance data not available yet.\n"
                "Run policy training to generate this view."
            )

    def _set_offline(self):
        self.current_mode.setText("Current system mode: OFFLINE")
        self.ml_mode.setText("AI recommendation: --")
        self.policy_source_label.setText("Policy source: --")
        self.confidence_label.setText("Confidence: --")
        self.top_features_label.setText("Main factors: --")
        self.model_summary.setText("Model: --")
        self.reason_label.setText("Why this mode was chosen:\n• System offline")
        self.recommendation_label.setText("What you should do now:\nWait for telemetry to reconnect")
