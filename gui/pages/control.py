# gui/pages/control.py

from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QScrollArea, QScroller, QMessageBox
from PySide6.QtCore import QTimer, Qt
import json
import os
import glob
import psutil
import datetime
from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONTROL_FILE = os.path.join(BASE_DIR, "control", "control.json")
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")
WORKLOAD_STATE_FILE = os.path.join(BASE_DIR, "workloads", "workload_state.json")
BOOT_STATE_FILE = os.path.join(BASE_DIR, "state", "boot_state.json")
SYSTEM_DIR = os.path.join(BASE_DIR, "system")
SLOT_CURRENT_FILE = os.path.join(SYSTEM_DIR, "slot_current")
SLOT_PENDING_FILE = os.path.join(SYSTEM_DIR, "slot_pending.json")
UPDATE_POLICY_FILE = os.path.join(BASE_DIR, "state", "update_policy.json")
SAFE_MODE_FLAG = os.path.join(BASE_DIR, "control", "SAFE_MODE")
UPDATES_INCOMING_DIR = os.path.join(BASE_DIR, "updates", "incoming")
UPDATE_INCOMING_STATE_FILE = os.path.join(BASE_DIR, "state", "update_incoming.json")

DEFAULT_CONTROL = {
    "mode": "AUTO",
    "manual_override_mode": None,
    "emergency_shutdown": False,
    "irrigation": False,
    "ventilation": False,
    "forced_mode": None,
    "workloads": {
        "sensor": True,
        "irrigation": True,
        "camera": True,
        "analytics": True
    },
    "maintenance": False
}

# -----------------------------
# WORKLOAD → ACTUATOR MAP
# -----------------------------
WORKLOAD_MAP = {
    "sensor_workload.py": "Sensor Network",
    "irrigation_workload.py": "Irrigation System",
    "camera_workload.py": "Farm Surveillance",
    "analytics_workload.py": "Analytics Engine"
}

WORKLOAD_KEY_MAP = {
    "sensor": "sensor_workload.py",
    "irrigation": "irrigation_workload.py",
    "camera": "camera_workload.py",
    "analytics": "analytics_workload.py"
}

WORKLOAD_LABELS = {
    "sensor": "Sensor Network",
    "irrigation": "Irrigation System",
    "camera": "Farm Surveillance",
    "analytics": "Analytics Engine"
}

# -----------------------------
# FILE HELPERS
# -----------------------------

def read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def read_text(path):
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def ensure_control_schema(control):
    if not isinstance(control, dict):
        control = {}
    for k, v in DEFAULT_CONTROL.items():
        if k not in control:
            control[k] = v
    if control.get("manual_override_mode") is None and control.get("forced_mode") is not None:
        control["manual_override_mode"] = control.get("forced_mode")
    if control.get("forced_mode") is None and control.get("manual_override_mode") is not None:
        control["forced_mode"] = control.get("manual_override_mode")
    if "workloads" not in control or not isinstance(control["workloads"], dict):
        control["workloads"] = DEFAULT_CONTROL["workloads"].copy()
    else:
        for k, v in DEFAULT_CONTROL["workloads"].items():
            if k not in control["workloads"]:
                control["workloads"][k] = v
    return control


def read_update_info():
    current = read_text(SLOT_CURRENT_FILE) or "--"
    pending = "--"
    data = read_json(SLOT_PENDING_FILE)
    if isinstance(data, dict):
        pending = data.get("slot") or "--"
    return current, pending


def read_update_policy():
    data = read_json(UPDATE_POLICY_FILE)
    return data if isinstance(data, dict) else {}


def read_boot_state():
    data = read_json(BOOT_STATE_FILE)
    return data if isinstance(data, dict) else {}


# -----------------------------
# WORKLOAD DETECTION
# -----------------------------

def running_workloads():
    """
    Detect running workload scripts by inspecting process command lines.
    Returns: set of workload filenames currently active.
    """
    state = read_json(WORKLOAD_STATE_FILE)
    if isinstance(state, dict):
        active = set()
        for key, filename in WORKLOAD_KEY_MAP.items():
            if state.get(key):
                active.add(filename)
        if active:
            return active

    active = set()

    for proc in psutil.process_iter(attrs=["cmdline"]):
        try:
            cmdline = proc.info["cmdline"]
            if not cmdline:
                continue

            cmd = " ".join(cmdline)
            for wf in WORKLOAD_MAP:
                if wf in cmd:
                    active.add(wf)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if active:
        return active

    # If state exists but shows no active workloads, fall back to empty set.
    return active


def find_workload_pids():
    """
    Best-effort PID lookup by matching workload filenames in command lines.
    Returns: dict of workload filename -> list of PIDs
    """
    pids = {wf: [] for wf in WORKLOAD_MAP}

    for proc in psutil.process_iter(attrs=["pid", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline")
            if not cmdline:
                continue
            cmd = " ".join(cmdline)
            for wf in WORKLOAD_MAP:
                if wf in cmd:
                    pids[wf].append(proc.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return pids

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


def button_css(bg_color, font_size):
    return f"""
        QPushButton {{
            background-color: {bg_color};
            color: {theme.TEXT_PRIMARY};
            font-size: {font_size}px;
            border: 2px solid {theme.SHELL_BORDER};
            border-bottom: 4px solid #051f1c;
            border-radius: 6px;
            font-family: {theme.MONO_FONT};
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
            padding-top: 2px;
            padding-bottom: 0px;
        }}
    """


# -----------------------------
# UI COMPONENTS
# -----------------------------
class ActuatorCard(QFrame):
    def __init__(self, title):
        super().__init__()

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 10px;
                border: none;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(6)

        self.title = QLabel(title)
        self.title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.MONO_FONT};
        """)

        self.badge = QLabel("[IDLE]")
        self.badge.setStyleSheet(f"""
            font-size: 12px;
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.MONO_FONT};
        """)

        self.status = QLabel("STATUS: --")
        self.status.setStyleSheet(f"""
            font-size: 15px;
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.MONO_FONT};
        """)

        self.pid_label = QLabel("PID: --")
        self.pid_label.setStyleSheet(f"""
            font-size: 12px;
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.MONO_FONT};
        """)

        layout.addWidget(self.title)
        layout.addWidget(self.badge)
        layout.addWidget(self.status)
        layout.addWidget(self.pid_label)


# -----------------------------
# CONTROL PAGE
# -----------------------------
class ControlPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.BACKGROUND};
                font-family: {theme.MONO_FONT};
            }}
            QLabel {{
                color: {theme.TEXT_PRIMARY};
                border: none;
                background: transparent;
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

        main = QVBoxLayout(content)
        main.setSpacing(20)
        main.setContentsMargins(30, 30, 30, 30)

        # CONTROL MODE LABEL
        self.mode_label = QLabel("CONTROL MODE: --")
        self.mode_label.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.MONO_FONT};
        """)

        # OVERRIDE / EMERGENCY LABEL
        self.override_label = QLabel("OVERRIDE: --")
        self.override_label.setStyleSheet(f"""
            font-size: 14px;
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.MONO_FONT};
        """)

        # SAFE MODE / MAINTENANCE LABELS
        self.safe_mode_label = QLabel("SAFE MODE: --")
        self.safe_mode_label.setStyleSheet(f"""
            font-size: 13px;
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.MONO_FONT};
        """)

        self.maintenance_label = QLabel("MAINTENANCE: --")
        self.maintenance_label.setStyleSheet(f"""
            font-size: 13px;
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.MONO_FONT};
        """)

        # TOGGLE BUTTON
        self.toggle_btn = QPushButton("SWITCH MODE")
        self.toggle_btn.setFixedHeight(44)
        self.toggle_btn.setStyleSheet(button_css(theme.BUTTON_ACTIVE, 15))
        self.toggle_btn.clicked.connect(self.toggle_mode)

        main.addWidget(self.mode_label)
        main.addWidget(self.override_label)
        main.addWidget(self.safe_mode_label)
        main.addWidget(self.maintenance_label)
        main.addWidget(self.toggle_btn)

        # MANUAL OVERRIDE / EMERGENCY BUTTONS
        self.force_energy_btn = QPushButton("FORCE ENERGY SAVER")
        self.force_energy_btn.setFixedHeight(44)
        self.force_energy_btn.setStyleSheet(button_css(theme.BUTTON_BG, 14))
        self.force_energy_btn.clicked.connect(
            lambda: self.set_manual_override("ENERGY_SAVER")
        )

        self.force_perf_btn = QPushButton("FORCE PERFORMANCE")
        self.force_perf_btn.setFixedHeight(44)
        self.force_perf_btn.setStyleSheet(button_css(theme.BUTTON_BG, 14))
        self.force_perf_btn.clicked.connect(
            lambda: self.set_manual_override("PERFORMANCE")
        )

        self.emergency_btn = QPushButton("EMERGENCY MODE")
        self.emergency_btn.setFixedHeight(44)
        self.emergency_btn.setStyleSheet(button_css(theme.BUTTON_ACTIVE, 14))
        self.emergency_btn.clicked.connect(self.toggle_emergency)

        main.addWidget(self.force_energy_btn)
        main.addWidget(self.force_perf_btn)
        main.addWidget(self.emergency_btn)

        # SAFE MODE / MAINTENANCE BUTTONS
        self.safe_mode_btn = QPushButton("TOGGLE SAFE MODE")
        self.safe_mode_btn.setFixedHeight(40)
        self.safe_mode_btn.setStyleSheet(button_css(theme.BUTTON_BG, 13))
        self.safe_mode_btn.clicked.connect(self.toggle_safe_mode)

        self.maintenance_btn = QPushButton("TOGGLE MAINTENANCE")
        self.maintenance_btn.setFixedHeight(40)
        self.maintenance_btn.setStyleSheet(button_css(theme.BUTTON_BG, 13))
        self.maintenance_btn.clicked.connect(self.toggle_maintenance)

        main.addWidget(self.safe_mode_btn)
        main.addWidget(self.maintenance_btn)

        # UPDATE STATUS SECTION
        self.update_section_label = QLabel("UPDATE STATUS")
        self.update_section_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.MONO_FONT};
        """)
        main.addWidget(self.update_section_label)

        self.update_frame = QFrame()
        self.update_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 8px;
                border: none;
            }}
        """)
        update_layout = QVBoxLayout(self.update_frame)
        update_layout.setContentsMargins(20, 15, 20, 15)
        update_layout.setSpacing(6)

        self.update_current_label = QLabel("Current Slot: --")
        self.update_pending_label = QLabel("Pending Slot: --")
        self.update_policy_label = QLabel("Policy: --")

        for lbl in (self.update_current_label, self.update_pending_label, self.update_policy_label):
            lbl.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_SECONDARY}; font-family: {theme.MONO_FONT};")
            update_layout.addWidget(lbl)

        self.clear_pending_btn = QPushButton("CLEAR PENDING UPDATE")
        self.clear_pending_btn.setFixedHeight(36)
        self.clear_pending_btn.setStyleSheet(button_css(theme.BUTTON_BG, 12))
        self.clear_pending_btn.clicked.connect(self.clear_pending_update)
        update_layout.addWidget(self.clear_pending_btn)

        main.addWidget(self.update_frame)

        # Workload section header
        self.workload_section_label = QLabel("WORKLOAD CONTROLS")
        self.workload_section_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.MONO_FONT};
        """)
        main.addWidget(self.workload_section_label)

        # ACTUATOR CARDS
        self.cards = {}
        self.workload_buttons = {}
        self.workload_status_badges = {}
        for wf, title in WORKLOAD_MAP.items():
            card = ActuatorCard(title)
            self.cards[wf] = card
            main.addWidget(card)

        # PER-WORKLOAD TOGGLES
        for key, label in WORKLOAD_LABELS.items():
            row = QFrame()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)

            btn = QPushButton(f"TOGGLE {label.upper()}")
            btn.setFixedHeight(40)
            btn.setStyleSheet(button_css(theme.BUTTON_BG, 13))
            btn.clicked.connect(lambda _, k=key: self.toggle_workload(k))
            self.workload_buttons[key] = btn

            status = QLabel("STATUS: --")
            status.setStyleSheet(f"""
                font-size: 12px;
                color: {theme.TEXT_SECONDARY};
                font-family: {theme.MONO_FONT};
            """)
            self.workload_status_badges[key] = status

            row_layout.addWidget(btn)
            row_layout.addWidget(status)
            row_layout.addStretch()
            main.addWidget(row)

        main.addStretch()

        # REFRESH TIMER
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(500)

        self.refresh()

    # -----------------------------
    # ACTIONS
    # -----------------------------
    def toggle_mode(self):
        control = ensure_control_schema(read_json(CONTROL_FILE))

        # If emergency is active, toggling mode clears it first.
        if control.get("emergency_shutdown"):
            control["emergency_shutdown"] = False

        if control.get("mode") == "AUTO":
            control["mode"] = "MANUAL"
        else:
            control["mode"] = "AUTO"
            control["manual_override_mode"] = None
            control["forced_mode"] = None
        write_json(CONTROL_FILE, control)
        self.refresh()

    def set_manual_override(self, mode_name):
        control = ensure_control_schema(read_json(CONTROL_FILE))
        control["mode"] = "MANUAL"
        control["manual_override_mode"] = mode_name
        control["forced_mode"] = mode_name  # backward compatibility
        write_json(CONTROL_FILE, control)
        self.refresh()

    def toggle_emergency(self):
        control = ensure_control_schema(read_json(CONTROL_FILE))
        control["emergency_shutdown"] = not control.get("emergency_shutdown", False)
        write_json(CONTROL_FILE, control)
        self.refresh()

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
        control = ensure_control_schema(read_json(CONTROL_FILE))
        control["safe_mode"] = enable
        write_json(CONTROL_FILE, control)
        self.refresh()

    def toggle_maintenance(self):
        control = ensure_control_schema(read_json(CONTROL_FILE))
        control["maintenance"] = not control.get("maintenance", False)
        write_json(CONTROL_FILE, control)
        self.refresh()

    def clear_pending_update(self):
        removed_any = False
        try:
            os.remove(SLOT_PENDING_FILE)
            removed_any = True
        except FileNotFoundError:
            pass

        for pattern in ("*.zip", "*.sig", "*.sig.json", "*.sha256"):
            for path in glob.glob(os.path.join(UPDATES_INCOMING_DIR, pattern)):
                try:
                    os.remove(path)
                    removed_any = True
                except FileNotFoundError:
                    pass

        try:
            os.remove(UPDATE_INCOMING_STATE_FILE)
            removed_any = True
        except FileNotFoundError:
            pass

        if removed_any:
            QMessageBox.information(self, "Updates", "Pending/staged update files were cleared.")
        else:
            QMessageBox.information(self, "Updates", "No pending update files found.")
        self.refresh()

    def toggle_workload(self, key):
        control = ensure_control_schema(read_json(CONTROL_FILE))
        if control.get("emergency_shutdown"):
            # Block toggles during emergency to avoid conflicting actions.
            return
        workloads = control.get("workloads", {})
        current = workloads.get(key, True)
        if current:
            label = WORKLOAD_LABELS.get(key, key).title()
            confirm = QMessageBox.question(
                self,
                "Confirm Stop",
                f"Stop {label}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return
        workloads[key] = not current
        control["workloads"] = workloads
        write_json(CONTROL_FILE, control)
        self.refresh()

    def refresh(self):
        control = ensure_control_schema(read_json(CONTROL_FILE))
        state = read_json(STATE_FILE)

        if not control or is_offline(state):
            self.mode_label.setText("CONTROL MODE: OFFLINE")
            self.mode_label.setStyleSheet(
                f"font-size: 22px; font-weight: bold; color: {theme.TEXT_SECONDARY}; font-family: {theme.MONO_FONT};"
            )
            self.override_label.setText("OVERRIDE: --")
            self.override_label.setStyleSheet(
                f"font-size: 14px; color: {theme.TEXT_SECONDARY}; font-family: {theme.MONO_FONT};"
            )
            self.safe_mode_label.setText("SAFE MODE: --")
            self.maintenance_label.setText("MAINTENANCE: --")
            self.update_current_label.setText("Current Slot: --")
            self.update_pending_label.setText("Pending Slot: --")
            self.update_policy_label.setText("Policy: --")
            self.clear_pending_btn.setEnabled(False)
            for wf, card in self.cards.items():
                self.update_card(card, False, None)
            for btn in self.workload_buttons.values():
                btn.setEnabled(False)
            for badge in self.workload_status_badges.values():
                badge.setText("STATUS: OFFLINE")
                badge.setStyleSheet(
                    f"font-size: 12px; color: {theme.TEXT_SECONDARY}; font-family: {theme.MONO_FONT};"
                )
            # Keep core control actions available so the operator can recover without telemetry.
            self.toggle_btn.setEnabled(True)
            self.force_energy_btn.setEnabled(True)
            self.force_perf_btn.setEnabled(True)
            self.emergency_btn.setEnabled(True)
            self.safe_mode_btn.setEnabled(True)
            self.maintenance_btn.setEnabled(True)
            return

        # MODE DISPLAY
        mode = control.get("mode", "AUTO")
        emergency = control.get("emergency_shutdown", False)
        safe_mode = bool(control.get("safe_mode")) or os.path.exists(SAFE_MODE_FLAG)
        maintenance = bool(control.get("maintenance", False))
        manual_override = control.get("manual_override_mode")
        if manual_override is None:
            manual_override = control.get("forced_mode")

        mode_color = (
            theme.MODE_COLORS["PERFORMANCE"]
            if mode == "AUTO"
            else theme.MODE_COLORS["ENERGY_SAVER"]
        )

        if emergency:
            self.mode_label.setText("CONTROL MODE: EMERGENCY")
            mode_color = theme.MODE_COLORS["ENERGY_SAVER"]
            self.override_label.setText("OVERRIDE: EMERGENCY SHUTDOWN")
            self.override_label.setStyleSheet(
                f"font-size: 14px; color: {theme.MODE_COLORS['ENERGY_SAVER']}; font-family: {theme.MONO_FONT};"
            )
        elif mode == "MANUAL" and manual_override:
            self.mode_label.setText(f"CONTROL MODE: MANUAL ({manual_override})")
            manual_color = theme.MODE_COLORS.get(manual_override, theme.TEXT_PRIMARY)
            mode_color = manual_color
            self.override_label.setText("OVERRIDE: MANUAL MODE")
            self.override_label.setStyleSheet(
                f"font-size: 14px; color: {manual_color}; font-family: {theme.MONO_FONT};"
            )
        else:
            self.mode_label.setText(f"CONTROL MODE: {mode}")
            self.override_label.setText("OVERRIDE: NONE")
            self.override_label.setStyleSheet(
                f"font-size: 14px; color: {theme.TEXT_SECONDARY}; font-family: {theme.MONO_FONT};"
            )
        self.mode_label.setStyleSheet(
            f"font-size: 22px; font-weight: bold; color: {mode_color}; font-family: {theme.MONO_FONT};"
        )

        safe_color = theme.TEXT_PRIMARY if safe_mode else theme.TEXT_SECONDARY
        maint_color = theme.TEXT_PRIMARY if maintenance else theme.TEXT_SECONDARY
        self.safe_mode_label.setText(f"SAFE MODE: {'ON' if safe_mode else 'OFF'}")
        self.safe_mode_label.setStyleSheet(
            f"font-size: 13px; color: {safe_color}; font-family: {theme.MONO_FONT};"
        )
        self.maintenance_label.setText(f"MAINTENANCE: {'ON' if maintenance else 'OFF'}")
        self.maintenance_label.setStyleSheet(
            f"font-size: 13px; color: {maint_color}; font-family: {theme.MONO_FONT};"
        )

        current_slot, pending_slot = read_update_info()
        policy = read_update_policy()
        sig = "ON" if policy.get("require_signature") else "OFF"
        sha = "ON" if policy.get("require_sha256") else "OFF"
        auto_stage = "ON" if policy.get("auto_stage_updates", True) else "OFF"
        self.update_current_label.setText(f"Current Slot: {current_slot}")
        self.update_pending_label.setText(f"Pending Slot: {pending_slot}")
        self.update_policy_label.setText(f"Policy: sig={sig} sha={sha} auto={auto_stage}")
        self.clear_pending_btn.setEnabled(pending_slot not in (None, "", "--"))

        active = running_workloads()
        pids = find_workload_pids()

        for wf, card in self.cards.items():
            self.update_card(card, wf in active, pids.get(wf))

        # Update per-workload toggle labels based on desired state.
        workloads = control.get("workloads", {})
        for key, btn in self.workload_buttons.items():
            desired = workloads.get(key, True)
            label = WORKLOAD_LABELS.get(key, key)
            btn.setText(
                f"STOP {label.upper()}" if desired else f"START {label.upper()}"
            )
            badge = self.workload_status_badges.get(key)
            if badge:
                if desired:
                    badge.setText("STATUS: ENABLED")
                    badge.setStyleSheet(
                        f"font-size: 12px; color: {theme.TEXT_SECONDARY}; font-family: {theme.MONO_FONT};"
                    )
                else:
                    badge.setText("STATUS: DISABLED")
                    badge.setStyleSheet(
                        f"font-size: 12px; color: {theme.TEXT_PRIMARY}; font-family: {theme.MONO_FONT};"
                    )

        # If emergency is active, visually disable workload controls.
        if emergency or safe_mode:
            for btn in self.workload_buttons.values():
                btn.setEnabled(False)
            for badge in self.workload_status_badges.values():
                badge.setText("STATUS: LOCKED")
                badge.setStyleSheet(
                    f"font-size: 12px; color: {theme.TEXT_SECONDARY}; font-family: {theme.MONO_FONT};"
                )
        else:
            for btn in self.workload_buttons.values():
                btn.setEnabled(True)

        self.safe_mode_btn.setEnabled(True)
        self.maintenance_btn.setEnabled(True)

    def update_card(self, card, is_on, pid_list):
        if is_on:
            text = "STATUS: ACTIVE"
            color = theme.TEXT_PRIMARY
            badge_text = "[RUNNING]"
            badge_color = theme.TEXT_PRIMARY
        else:
            text = "STATUS: INACTIVE"
            color = theme.TEXT_SECONDARY
            badge_text = "[IDLE]"
            badge_color = theme.TEXT_SECONDARY

        card.status.setText(text)
        card.status.setStyleSheet(f"""
            font-size: 15px;
            color: {color};
            font-family: {theme.MONO_FONT};
        """)

        card.badge.setText(badge_text)
        card.badge.setStyleSheet(f"""
            font-size: 12px;
            color: {badge_color};
            font-family: {theme.MONO_FONT};
        """)

        if pid_list:
            pid_text = ", ".join(str(p) for p in pid_list)
            card.pid_label.setText(f"PID: {pid_text}")
        else:
            card.pid_label.setText("PID: --")
