from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame, QPushButton, QHBoxLayout, QScrollArea, QScroller
from PySide6.QtCore import QTimer, Qt
from control.os_control import read_control, write_control
import json
import os
import datetime
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
    try:
        with open(WORKLOAD_STATE_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


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


class HomePage(QWidget):
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

        self.main_layout = QVBoxLayout(content)
        self.main_layout.setSpacing(14)
        self.main_layout.setContentsMargins(30, 30, 30, 30)

        # === HEADER ROW ===
        self.mode_label = QLabel("MODE: --")
        self.mode_label.setStyleSheet("font-size: 26px; font-weight: bold;")

        self.cursor_label = QLabel("_")
        self.cursor_label.setStyleSheet(
            f"font-size: 26px; font-weight: bold; color: {theme.RETRO_CURSOR_COLOR};"
        )

        self.clock_label = QLabel("00:00:00")
        self.clock_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.clock_label.setStyleSheet("font-size: 18px;")

        header_row = QHBoxLayout()
        header_row.addWidget(self.mode_label)
        header_row.addWidget(self.cursor_label)
        header_row.addStretch()
        header_row.addWidget(self.clock_label)

        # === SYSTEM OVERVIEW ===
        status_frame = QFrame()
        status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 8px;
                border: none;
            }}
        """)
        status_layout = QVBoxLayout(status_frame)

        self.boot_label = QLabel("Boot: --")
        self.control_state_label = QLabel("Control: --")
        self.safe_label = QLabel("Safe Mode: --")
        self.update_label = QLabel("Update Slot: --")
        self.device_label = QLabel("Device: --")

        for lbl in (self.boot_label, self.control_state_label, self.safe_label, self.update_label, self.device_label):
            lbl.setStyleSheet("font-size: 14px;")
            status_layout.addWidget(lbl)

        # === QUICK ACTIONS ===
        self.force_save = QPushButton("Force Energy Saver")
        self.force_perf = QPushButton("Force Performance")
        self.resume_ai = QPushButton("Resume AI Control")
        self.safe_mode_btn = QPushButton("Toggle Safe Mode")

        for b in (self.force_save, self.force_perf, self.resume_ai, self.safe_mode_btn):
            b.setFixedHeight(36)
            b.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme.BUTTON_BG};
                    color: {theme.TEXT_PRIMARY};
                    border: none;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {theme.BUTTON_HOVER};
                }}
            """)

        self.force_save.clicked.connect(lambda: self.set_mode("ENERGY_SAVER"))
        self.force_perf.clicked.connect(lambda: self.set_mode("PERFORMANCE"))
        self.resume_ai.clicked.connect(lambda: self.set_mode(None))
        self.safe_mode_btn.clicked.connect(self.toggle_safe_mode)

        # === SYSTEM METRICS ===
        system_frame = QFrame()
        system_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 8px;
                border: none;
            }}
        """)
        system_layout = QVBoxLayout(system_frame)

        self.cpu_label = QLabel("CPU: --")
        self.mem_label = QLabel("MEM: --")
        self.load_label = QLabel("LOAD: --")

        system_layout.addWidget(self.cpu_label)
        system_layout.addWidget(self.mem_label)
        system_layout.addWidget(self.load_label)

        # === POWER SECTION ===
        power_frame = QFrame()
        power_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 8px;
                border: none;
            }}
        """)
        power_layout = QVBoxLayout(power_frame)

        self.power_label = QLabel("Power: --")
        self.backup_label = QLabel("Backup: --")
        self.health_label = QLabel("Battery Health: --")

        power_layout.addWidget(self.power_label)
        power_layout.addWidget(self.backup_label)
        power_layout.addWidget(self.health_label)

        # === NETWORK STATUS ===
        self.network_label = QLabel("Network: --")
        self.network_label.setStyleSheet("font-size: 16px;")

        # === WORKLOAD STATUS ===
        self.workload_dot = QLabel("●")
        self.workload_dot.setStyleSheet(
            f"font-size: 14px; color: {theme.TEXT_SECONDARY};"
        )
        self.workload_label = QLabel("WORKLOAD: --")
        self.workload_label.setStyleSheet("font-size: 14px;")

        workload_row = QHBoxLayout()
        workload_row.addWidget(self.workload_dot)
        workload_row.addWidget(self.workload_label)
        workload_row.addStretch()

        # === ALERT BANNER ===
        self.alert_label = QLabel("")
        self.alert_label.setStyleSheet(
            "font-size: 14px; font-weight: bold;"
        )

        # === SENSOR SNAPSHOT ===
        sensor_frame = QFrame()
        sensor_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 8px;
                border: none;
            }}
        """)
        sensor_layout = QVBoxLayout(sensor_frame)

        self.soil_label = QLabel("Soil Moisture: --")
        self.temp_label = QLabel("Temperature: --")
        self.humidity_label = QLabel("Humidity: --")

        sensor_layout.addWidget(self.soil_label)
        sensor_layout.addWidget(self.temp_label)
        sensor_layout.addWidget(self.humidity_label)

        # === ADD TO MAIN LAYOUT ===
        self.main_layout.addLayout(header_row)
        self.main_layout.addWidget(status_frame)
        for b in (self.force_save, self.force_perf, self.resume_ai, self.safe_mode_btn):
            self.main_layout.addWidget(b)
        self.main_layout.addWidget(self._divider())
        self.main_layout.addWidget(system_frame)
        self.main_layout.addWidget(self._divider())
        self.main_layout.addWidget(power_frame)
        self.main_layout.addWidget(self.network_label)
        self.main_layout.addLayout(workload_row)
        self.main_layout.addWidget(self.alert_label)
        self.main_layout.addWidget(self._divider())
        self.main_layout.addWidget(sensor_frame)
        self.main_layout.addStretch()

        # === REFRESH TIMER ===
        self.cursor_on = True
        self.dot_on = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(500)

        self.refresh()

    def _divider(self):
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {theme.RETRO_GRID_LINE};")
        return line

    def refresh(self):
        # CLOCK
        self.clock_label.setText(datetime.datetime.now().strftime("%H:%M:%S"))

        # BLINKING CURSOR
        self.cursor_on = not self.cursor_on
        self.cursor_label.setVisible(self.cursor_on)

        state = read_state()
        if is_offline(state):
            self._set_offline()
            return

        for b in (self.force_save, self.force_perf, self.resume_ai, self.safe_mode_btn):
            b.setEnabled(True)

        actual_mode = state.get("current_mode", "UNKNOWN")
        sensors = state.get("sensors", {})

        # BOOT STATUS
        boot_state = read_boot_state()
        boot_phase = boot_state.get("phase") or state.get("boot_phase") or "UNKNOWN"
        boot_message = boot_state.get("message") or state.get("boot_message")
        boot_text = f"Boot: {boot_phase}"
        if boot_message:
            boot_text += f" ({boot_message})"
        self.boot_label.setText(boot_text)

        # CONTROL STATE (read from control plane for accuracy)
        control = read_control()
        safe_mode = bool(control.get("safe_mode")) or os.path.exists(SAFE_MODE_FLAG)
        manual_override = control.get("manual_override_mode") or control.get("forced_mode")
        display_mode = actual_mode
        if control.get("emergency_shutdown"):
            display_mode = "ENERGY_SAVER"
        elif safe_mode or control.get("maintenance"):
            display_mode = "ENERGY_SAVER"
        elif control.get("mode") == "MANUAL" and manual_override:
            display_mode = manual_override

        if control.get("emergency_shutdown"):
            control_state = "EMERGENCY"
        elif control.get("mode") == "MANUAL":
            override = manual_override
            control_state = f"MANUAL ({override})" if override else "MANUAL"
        else:
            control_state = "AUTO"
        self.control_state_label.setText(f"Control: {control_state}")
        self.safe_label.setText(f"Safe Mode: {'ON' if safe_mode else 'OFF'}")
        self.safe_mode_btn.setText("Disable Safe Mode" if safe_mode else "Enable Safe Mode")

        # Show the intended target mode immediately for responsive UI feedback.
        mode_color = theme.MODE_COLORS.get(display_mode, theme.TEXT_PRIMARY)
        self.mode_label.setText(f"MODE: {display_mode}")
        self.mode_label.setStyleSheet(
            f"font-size: 26px; font-weight: bold; color: {mode_color};"
        )

        current_slot, pending_slot = read_update_info()
        pending_text = pending_slot if pending_slot and pending_slot != "--" else "None"
        self.update_label.setText(f"Update Slot: {current_slot} (pending: {pending_text})")

        device = read_device_info()
        device_id = device.get("device_id", "--")
        label = device.get("label")
        if label:
            self.device_label.setText(f"Device: {label} ({device_id})")
        else:
            self.device_label.setText(f"Device: {device_id}")

        # SYSTEM METRICS
        cpu = sensors.get("cpu_percent", "--")
        mem = sensors.get("memory_percent", "--")
        load = sensors.get("load_avg", "--")

        self.cpu_label.setText(f"CPU: {cpu}%")
        self.mem_label.setText(f"MEM: {mem}%")
        self.load_label.setText(f"LOAD: {load}")

        # POWER
        battery = sensors.get("battery")
        battery_health = sensors.get("battery_health")
        if battery is None:
            self.power_label.setText("Power: External (No Battery)")
            self.backup_label.setText("Backup Level: N/A")
            self.health_label.setText("Battery Health: N/A")
        else:
            if battery > 20:
                self.power_label.setText("Power: External (OK)")
            else:
                self.power_label.setText("Power: Backup")
            self.backup_label.setText(f"Backup Level: {battery}%")
            if battery_health is None:
                self.health_label.setText("Battery Health: N/A")
            else:
                self.health_label.setText(f"Battery Health: {battery_health}%")

        # NETWORK STATUS
        network = sensors.get("network", "UNKNOWN")
        if network == "ONLINE":
            self.network_label.setText("Network: Connected")
            self.network_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
        else:
            self.network_label.setText("Network: Offline")
            self.network_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")

        # WORKLOAD STATUS
        workloads = read_workload_state()
        active = any(workloads.values()) if workloads else False
        if active:
            self.workload_label.setText("WORKLOAD: ACTIVE")
            self.dot_on = not self.dot_on
            dot_color = theme.TEXT_PRIMARY if self.dot_on else theme.TEXT_SECONDARY
        else:
            self.workload_label.setText("WORKLOAD: IDLE")
            dot_color = theme.TEXT_SECONDARY

        self.workload_dot.setStyleSheet(
            f"font-size: 14px; color: {dot_color};"
        )

        # ALERTS
        alert = get_latest_alert()
        if alert:
            level = alert.get("level", "INFO")
            if level == "WARN":
                color = theme.TEXT_SECONDARY
            else:
                color = theme.TEXT_PRIMARY
            self.alert_label.setStyleSheet(
                f"font-size: 14px; font-weight: bold; color: {color};"
            )
            self.alert_label.setText(f"[{alert['level']}] {alert['message']}")
        else:
            self.alert_label.setText("")

        # SENSOR SNAPSHOT
        soil = sensors.get("soil_moisture")
        temp = sensors.get("temperature")
        humidity = sensors.get("humidity")

        self.soil_label.setText(
            f"Soil Moisture: {soil}%" if soil is not None else "Soil Moisture: N/A"
        )
        self.temp_label.setText(
            f"Temperature: {temp} °C" if temp is not None else "Temperature: N/A"
        )
        self.humidity_label.setText(
            f"Humidity: {humidity}%" if humidity is not None else "Humidity: N/A"
        )

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

    def _set_offline(self):
        self.mode_label.setText("MODE: SYSTEM OFFLINE")
        self.mode_label.setStyleSheet(
            f"font-size: 26px; font-weight: bold; color: {theme.TEXT_SECONDARY};"
        )
        self.boot_label.setText("Boot: OFFLINE")
        self.control_state_label.setText("Control: OFFLINE")
        self.safe_label.setText("Safe Mode: --")
        self.update_label.setText("Update Slot: --")
        self.device_label.setText("Device: --")

        self.cpu_label.setText("CPU: --")
        self.mem_label.setText("MEM: --")
        self.load_label.setText("LOAD: --")

        self.power_label.setText("Power: --")
        self.backup_label.setText("Backup Level: --")
        self.health_label.setText("Battery Health: --")

        self.network_label.setText("Network: Offline")
        self.network_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")

        self.workload_label.setText("WORKLOAD: IDLE")
        self.workload_dot.setStyleSheet(
            f"font-size: 14px; color: {theme.TEXT_SECONDARY};"
        )

        self.alert_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {theme.TEXT_SECONDARY};"
        )
        self.alert_label.setText("SYSTEM OFFLINE")

        self.soil_label.setText("Soil Moisture: --")
        self.temp_label.setText("Temperature: --")
        self.humidity_label.setText("Humidity: --")

        for b in (self.force_save, self.force_perf, self.resume_ai, self.safe_mode_btn):
            b.setEnabled(True)

    def set_mode(self, mode):
        control = read_control()
        control["forced_mode"] = mode
        control["manual_override_mode"] = mode
        control["mode"] = "AUTO" if mode is None else "MANUAL"
        write_control(control)
