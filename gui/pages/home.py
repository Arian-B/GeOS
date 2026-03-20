import datetime
import json
import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QScroller, QVBoxLayout, QWidget

from control.os_control import read_control, write_control
from core_os.notifications import get_latest_alert
from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")
WORKLOAD_STATE_FILE = os.path.join(BASE_DIR, "workloads", "workload_state.json")
BOOT_STATE_FILE = os.path.join(BASE_DIR, "state", "boot_state.json")
DEVICE_FILE = os.path.join(BASE_DIR, "state", "device.json")
SYSTEM_DIR = os.path.join(BASE_DIR, "system")
SLOT_CURRENT_FILE = os.path.join(SYSTEM_DIR, "slot_current")
SLOT_PENDING_FILE = os.path.join(SYSTEM_DIR, "slot_pending.json")
SAFE_MODE_FLAG = os.path.join(BASE_DIR, "control", "SAFE_MODE")


def read_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None


def read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def read_workload_state():
    data = read_json(WORKLOAD_STATE_FILE)
    return data if isinstance(data, dict) else {}


def read_boot_state():
    data = read_json(BOOT_STATE_FILE)
    return data if isinstance(data, dict) else {}


def read_device_info():
    data = read_json(DEVICE_FILE)
    return data if isinstance(data, dict) else {}


def read_update_info():
    current = "--"
    pending = "--"
    try:
        with open(SLOT_CURRENT_FILE, "r") as f:
            current = f.read().strip() or "--"
    except Exception:
        pass
    pending_data = read_json(SLOT_PENDING_FILE)
    if isinstance(pending_data, dict):
        pending = pending_data.get("slot") or "--"
    return current, pending


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


def level_color(level):
    if level == "CRITICAL":
        return theme.ACCENT_DANGER
    if level == "WARN":
        return theme.ACCENT_WARN
    return theme.TEXT_SECONDARY


class SummaryCard(QFrame):
    def __init__(self, title, tone="normal"):
        super().__init__()
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 12px;
                border: none;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        self.title = QLabel(title)
        self.title.setStyleSheet(f"font-size: 14px; color: {theme.TEXT_MUTED}; font-weight: bold;")
        self.value = QLabel("--")
        self.value.setStyleSheet("font-size: 26px; font-weight: bold;")
        self.detail = QLabel("--")
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_PRIMARY};")

        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.detail)


class HomePage(QWidget):
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
            QPushButton {{
                background-color: {theme.BUTTON_BG};
                color: {theme.TEXT_PRIMARY};
                border: 2px solid {theme.SHELL_BORDER};
                border-bottom: 4px solid #051f1c;
                border-radius: 8px;
                padding: 10px 12px;
            }}
            QPushButton:hover {{
                background-color: {theme.BUTTON_HOVER};
                border: 2px solid {theme.TEXT_SECONDARY};
                border-bottom: 4px solid #051f1c;
            }}
            QPushButton:pressed {{
                background-color: {theme.BUTTON_ACTIVE};
                border: 2px solid {theme.TEXT_PRIMARY};
                border-bottom: 2px solid #051f1c;
                padding-top: 12px;
                padding-bottom: 8px;
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

        self.title = QLabel("OVERVIEW")
        self.title.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.layout.addWidget(self.title)

        self.subtitle = QLabel("Mission control for field health, power, watering, and live GeOS decisions.")
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        self.layout.addWidget(self.subtitle)

        self.alert_banner = QLabel("Checking system state...")
        self.alert_banner.setWordWrap(True)
        self.alert_banner.setStyleSheet(
            f"""
            font-size: 14px;
            font-weight: bold;
            background-color: {theme.BUTTON_BG};
            border: none;
            border-radius: 10px;
            padding: 10px 12px;
            """
        )
        self.layout.addWidget(self.alert_banner)

        self.health_card = SummaryCard("Farm Health")
        self.mode_card = SummaryCard("System Mode")
        self.water_card = SummaryCard("Watering")
        self.power_card = SummaryCard("Power")
        self.recommend_card = SummaryCard("GeOS Recommendation")
        self.device_card = SummaryCard("Device Status")

        for card in (
            self.health_card,
            self.mode_card,
            self.water_card,
            self.power_card,
            self.recommend_card,
            self.device_card,
        ):
            self.layout.addWidget(card)

        self.action_label = QLabel("Quick Actions")
        self.action_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(self.action_label)

        self.force_save = QPushButton("Protect Power")
        self.force_perf = QPushButton("Boost Performance")
        self.resume_ai = QPushButton("Return To Automatic")
        self.safe_mode_btn = QPushButton("Toggle Safe Mode")

        for button in (self.force_save, self.force_perf, self.resume_ai, self.safe_mode_btn):
            self.layout.addWidget(button)

        self.force_save.clicked.connect(lambda: self.set_mode("ENERGY_SAVER"))
        self.force_perf.clicked.connect(lambda: self.set_mode("PERFORMANCE"))
        self.resume_ai.clicked.connect(lambda: self.set_mode(None))
        self.safe_mode_btn.clicked.connect(self.toggle_safe_mode)

        self.layout.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def refresh(self):
        state = read_state()
        if is_offline(state):
            self._set_offline()
            return

        sensors = state.get("sensors", {}) if isinstance(state.get("sensors"), dict) else {}
        control = read_control()
        boot_state = read_boot_state()
        device = read_device_info()
        workloads = read_workload_state()
        current_slot, pending_slot = read_update_info()

        actual_mode = state.get("current_mode", "UNKNOWN")
        suggested_mode = state.get("ml_suggested_mode", "UNKNOWN")
        boot_phase = boot_state.get("phase") or state.get("boot_phase") or "UNKNOWN"
        safe_mode = bool(control.get("safe_mode")) or os.path.exists(SAFE_MODE_FLAG)
        manual_override = control.get("manual_override_mode") or control.get("forced_mode")

        display_mode = actual_mode
        if control.get("emergency_shutdown"):
            display_mode = "ENERGY_SAVER"
        elif safe_mode or control.get("maintenance"):
            display_mode = "ENERGY_SAVER"
        elif control.get("mode") == "MANUAL" and manual_override:
            display_mode = manual_override

        soil = sensors.get("soil_moisture")
        temp = sensors.get("temperature")
        humidity = sensors.get("humidity")
        battery = sensors.get("battery")
        battery_health = sensors.get("battery_health")
        network = sensors.get("network", "OFFLINE")

        active_workloads = [name for name, active in workloads.items() if active]
        latest_alert = get_latest_alert()

        if latest_alert:
            level = str(latest_alert.get("level", "INFO")).upper()
            self.alert_banner.setText(f"[{level}] {latest_alert.get('message', '--')}")
            self.alert_banner.setStyleSheet(
                f"""
                font-size: 14px;
                font-weight: bold;
                background-color: {theme.BUTTON_BG};
                border: 1px solid {level_color(level)};
                border-radius: 10px;
                padding: 10px 12px;
                color: {level_color(level)};
                """
            )
        else:
            self.alert_banner.setText("No urgent alerts. Field system is currently calm.")
            self.alert_banner.setStyleSheet(
                f"""
                font-size: 14px;
                font-weight: bold;
                background-color: {theme.BUTTON_BG};
                border: 1px solid {theme.SHELL_BORDER};
                border-radius: 10px;
                padding: 10px 12px;
                color: {theme.TEXT_SECONDARY};
                """
            )

        health = "Healthy"
        health_detail = []
        if soil is not None and soil < 30:
            health = "Needs attention"
            health_detail.append("soil moisture is low")
        if temp is not None and temp > 35:
            health = "Heat risk"
            health_detail.append("temperature is elevated")
        if battery is not None and battery < 20:
            health = "Power risk"
            health_detail.append("battery reserve is low")
        if safe_mode:
            health = "Safe mode active"
            health_detail.append("workloads are limited")
        if not health_detail:
            health_detail.append("all key readings are in a stable range")
        self.health_card.value.setText(health)
        self.health_card.detail.setText("; ".join(health_detail))

        self.mode_card.value.setText(display_mode)
        mode_detail = f"Boot {boot_phase} | control {control.get('mode', 'UNKNOWN')}"
        if pending_slot and pending_slot != "--":
            mode_detail += f" | update pending {pending_slot}"
        self.mode_card.detail.setText(mode_detail)

        if active_workloads:
            self.water_card.value.setText("Active")
            self.water_card.detail.setText(
                "Running modules: " + ", ".join(name.title() for name in active_workloads)
            )
        else:
            self.water_card.value.setText("Idle")
            self.water_card.detail.setText("No workload modules are marked active right now.")

        if battery is None:
            self.power_card.value.setText("External")
            self.power_card.detail.setText("No battery reported by the current platform.")
        else:
            source = "backup" if battery <= 20 else "stable"
            detail = f"Battery {battery}%"
            if battery_health is not None:
                detail += f" | health {battery_health}%"
            self.power_card.value.setText(source.title())
            self.power_card.detail.setText(detail)

        recommendation = "Continue automatic operation."
        if safe_mode:
            recommendation = "Keep safe mode enabled until the device stabilizes."
        elif battery is not None and battery < 20:
            recommendation = "Protect uptime and reduce heavy workloads."
        elif soil is not None and soil < 30:
            recommendation = "Prioritize irrigation and watch moisture recovery."
        elif temp is not None and temp > 35:
            recommendation = "Reduce load and monitor field temperature."
        elif suggested_mode and suggested_mode != "UNKNOWN":
            recommendation = f"GeOS suggests {suggested_mode.lower().replace('_', ' ')} mode."
        self.recommend_card.value.setText(suggested_mode if suggested_mode != "UNKNOWN" else display_mode)
        self.recommend_card.detail.setText(recommendation)

        device_name = device.get("label") or device.get("device_id", "--")
        self.device_card.value.setText("Connected" if network == "ONLINE" else "Offline")
        self.device_card.detail.setText(
            f"{device_name} | slot {current_slot} | network {network.lower()}"
        )

        self.safe_mode_btn.setText("Disable Safe Mode" if safe_mode else "Enable Safe Mode")

    def _set_offline(self):
        self.alert_banner.setText("System offline. Waiting for telemetry and controller state.")
        self.health_card.value.setText("Offline")
        self.health_card.detail.setText("No recent state update available.")
        self.mode_card.value.setText("--")
        self.mode_card.detail.setText("Mode data unavailable.")
        self.water_card.value.setText("--")
        self.water_card.detail.setText("Workload state unavailable.")
        self.power_card.value.setText("--")
        self.power_card.detail.setText("Power data unavailable.")
        self.recommend_card.value.setText("--")
        self.recommend_card.detail.setText("Advisory data unavailable.")
        self.device_card.value.setText("--")
        self.device_card.detail.setText("Device state unavailable.")

    def toggle_safe_mode(self):
        enable = not os.path.exists(SAFE_MODE_FLAG)
        if enable:
            with open(SAFE_MODE_FLAG, "w") as f:
                f.write("1")
        else:
            try:
                os.remove(SAFE_MODE_FLAG)
            except FileNotFoundError:
                pass
        control = read_control()
        control["safe_mode"] = enable
        write_control(control)

    def set_mode(self, mode):
        control = read_control()
        control["forced_mode"] = mode
        control["manual_override_mode"] = mode
        control["mode"] = "AUTO" if mode is None else "MANUAL"
        write_control(control)
