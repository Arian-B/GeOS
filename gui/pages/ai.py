# gui/pages/ai.py

import datetime
import json
import os

import joblib
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QScroller, QVBoxLayout, QWidget

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


class InfoCard(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 10px;
                border: none;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        self.title = QLabel(title)
        self.title.setStyleSheet(f"font-size: 14px; color: {theme.TEXT_MUTED}; font-weight: bold;")
        self.value = QLabel("--")
        self.value.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.detail = QLabel("--")
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_PRIMARY};")

        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.detail)


class AIPage(QWidget):
    _cached_importance = None
    _cached_top_features = None

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
        QScroller.grabGesture(self.scroll.viewport(), QScroller.LeftMouseButtonGesture)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll)

        self.layout = QVBoxLayout(content)
        self.layout.setSpacing(16)
        self.layout.setContentsMargins(24, 24, 24, 24)

        self.header = QLabel("ADVISOR")
        self.header.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.layout.addWidget(self.header)

        self.subtitle = QLabel("Farmer-readable guidance from GeOS, with deeper model details below.")
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        self.layout.addWidget(self.subtitle)

        self.primary_card = InfoCard("What GeOS Suggests")
        self.reason_card = InfoCard("Why It Chose This")
        self.action_card = InfoCard("What You Should Do")
        self.detail_card = InfoCard("Model Details")
        self.factors_card = InfoCard("Main Factors")
        self.history_card = InfoCard("Decision Timing")

        for card in (
            self.primary_card,
            self.reason_card,
            self.action_card,
            self.detail_card,
            self.factors_card,
            self.history_card,
        ):
            self.layout.addWidget(card)

        self._load_feature_importance_once()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def _load_feature_importance_once(self):
        if AIPage._cached_importance is not None:
            return

        items = []
        importance = read_json(FEATURE_IMPORTANCE_FILE)
        if isinstance(importance, list):
            for entry in importance:
                if isinstance(entry, dict) and entry.get("feature") is not None and entry.get("importance") is not None:
                    items.append((entry.get("feature"), entry.get("importance")))
        elif isinstance(importance, dict):
            items = list(importance.items())

        if not items:
            try:
                model = joblib.load(MODEL_FILE)
                if hasattr(model, "feature_importances_"):
                    importances = list(model.feature_importances_)
                    names = list(getattr(model, "feature_names_in_", []))
                    if not names or len(names) != len(importances):
                        names = [f"feature_{i}" for i in range(len(importances))]
                    items = list(zip(names, importances))
            except Exception:
                items = []

        items = sorted(items, key=lambda x: x[1], reverse=True)
        AIPage._cached_importance = items
        AIPage._cached_top_features = items[:3]

    def _friendly_feature_name(self, name):
        return FEATURE_FRIENDLY_NAMES.get(name, str(name).replace("_", " ").title())

    def _format_local_feature(self, entry):
        if not isinstance(entry, dict):
            return None
        name = self._friendly_feature_name(entry.get("feature"))
        contribution = entry.get("contribution")
        direction = entry.get("direction")
        if isinstance(contribution, (int, float)):
            direction_text = "supporting" if direction != "opposes_prediction" else "pushing against"
            return f"{name} ({direction_text}, {contribution:+.2f})"
        importance = entry.get("importance")
        if isinstance(importance, (int, float)):
            return f"{name} ({int(round(importance * 100))}%)"
        return name

    def refresh(self):
        state = read_json(STATE_FILE)
        if is_offline(state):
            self.primary_card.value.setText("Offline")
            self.primary_card.detail.setText("No recent controller state.")
            self.reason_card.value.setText("--")
            self.reason_card.detail.setText("Reasoning unavailable while telemetry is offline.")
            self.action_card.value.setText("--")
            self.action_card.detail.setText("Wait for GeOS to reconnect.")
            self.detail_card.value.setText("--")
            self.detail_card.detail.setText("Model details unavailable.")
            self.factors_card.value.setText("--")
            self.factors_card.detail.setText("No factor data available.")
            self.history_card.value.setText("--")
            self.history_card.detail.setText("No action timestamp available.")
            return

        current = state.get("current_mode", "UNKNOWN")
        suggested = state.get("ml_suggested_mode", "UNKNOWN")
        policy_source = state.get("policy_source", "UNKNOWN")
        sensors = state.get("sensors", {})
        control = read_json(CONTROL_FILE) or {}
        meta = read_json(MODEL_META_FILE) or {}
        safe_mode = bool(control.get("safe_mode")) or os.path.exists(SAFE_MODE_FLAG)
        maintenance = bool(control.get("maintenance", False))
        soil = sensors.get("soil_moisture")
        battery = sensors.get("battery")
        temp = sensors.get("temperature")
        cpu = sensors.get("cpu_percent", 0)

        self.primary_card.value.setText(suggested if suggested != "UNKNOWN" else current)
        self.primary_card.detail.setText(
            f"Current mode: {current} | policy source: {str(policy_source).replace('_', ' ').title()}"
        )

        reasons = []
        for code in state.get("ml_reason_codes", []):
            if code == "manual_override":
                reasons.append("manual control is active")
            elif code == "safety_override":
                reasons.append("safety rules overrode the learned policy")
            elif code == "lightgbm_policy":
                reasons.append("the LightGBM policy selected the mode")
            elif code == "emergency_shutdown":
                reasons.append("emergency shutdown is active")
            elif code == "maintenance_mode":
                reasons.append("maintenance mode is active")

        if soil is not None and soil < 30:
            reasons.append("soil moisture is low")
        if temp is not None and temp > 35:
            reasons.append("temperature is above the preferred range")
        if battery is not None and battery < 20:
            reasons.append("battery reserve is low")
        if cpu > 60:
            reasons.append("system load is high")
        if safe_mode:
            reasons.append("safe mode is limiting workloads")
        if maintenance:
            reasons.append("maintenance mode is enabled")
        if not reasons:
            reasons.append("conditions are stable")

        self.reason_card.value.setText("Explained")
        self.reason_card.detail.setText("; ".join(reasons))

        recommendation = "Continue normal operation."
        if safe_mode:
            recommendation = "Keep safe mode enabled until readings settle."
        elif battery is not None and battery < 20:
            recommendation = "Protect uptime and reduce heavy workloads."
        elif soil is not None and soil < 30:
            recommendation = "Prioritize irrigation and watch soil recovery."
        elif cpu > 60:
            recommendation = "Reduce system load until utilization drops."
        elif soil is None or temp is None or battery is None:
            recommendation = "Check missing sensor inputs so GeOS can make stronger decisions."

        self.action_card.value.setText("Recommended")
        self.action_card.detail.setText(recommendation)

        confidence = state.get("ml_confidence")
        raw_confidence = state.get("ml_raw_confidence")
        confidence_source = state.get("ml_confidence_source")
        if isinstance(confidence, (int, float)):
            confidence_percent = int(round(max(0.0, min(1.0, confidence)) * 100))
        else:
            confidence_percent = 0
        model_type = meta.get("model_type", "UNKNOWN")
        trained_at = meta.get("trained_at", "--")
        self.detail_card.value.setText(f"{confidence_percent}%")
        detail_text = f"{model_type} | trained {trained_at}"
        if confidence_source:
            detail_text += f" | {str(confidence_source).replace('_', ' ').title()}"
        if isinstance(raw_confidence, (int, float)):
            detail_text += f" | raw {int(round(max(0.0, min(1.0, raw_confidence)) * 100))}%"
        self.detail_card.detail.setText(detail_text)

        factor_lines = []
        state_top_features = state.get("ml_top_features")
        if isinstance(state_top_features, list) and state_top_features:
            for entry in state_top_features[:3]:
                formatted = self._format_local_feature(entry)
                if formatted:
                    factor_lines.append(formatted)
        if not factor_lines:
            for name, score in AIPage._cached_top_features or []:
                factor_lines.append(f"{self._friendly_feature_name(name)} ({int(round(float(score) * 100))}%)")

        self.factors_card.value.setText("Top Drivers")
        self.factors_card.detail.setText("; ".join(factor_lines) if factor_lines else "No factor data available.")

        last_time = state.get("last_ai_action_time", "--")
        self.history_card.value.setText("Last Update")
        self.history_card.detail.setText(f"{last_time} | thresholds ready: {'yes' if state.get('ml_thresholds') else 'no'}")
