# gui/pages/control.py

from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QFrame
from PySide6.QtCore import QTimer
import json
import os
import psutil
from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONTROL_FILE = os.path.join(BASE_DIR, "control", "control.json")
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")

# -----------------------------
# WORKLOAD → ACTUATOR MAP
# -----------------------------
WORKLOAD_MAP = {
    "sensor_workload.py": "Sensor Network",
    "irrigation_workload.py": "Irrigation System",
    "camera_workload.py": "Farm Surveillance",
    "analytics_workload.py": "Analytics Engine"
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


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# -----------------------------
# WORKLOAD DETECTION
# -----------------------------
def running_workloads():
    """
    Detect running workload scripts by inspecting process command lines.
    Returns: set of workload filenames currently active.
    """
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

    return active


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
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(8)

        self.title = QLabel(title)
        self.title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {theme.TEXT_PRIMARY};
        """)

        self.status = QLabel("STATUS: --")
        self.status.setStyleSheet(f"""
            font-size: 15px;
            color: {theme.TEXT_SECONDARY};
        """)

        layout.addWidget(self.title)
        layout.addWidget(self.status)


# -----------------------------
# CONTROL PAGE
# -----------------------------
class ControlPage(QWidget):
    def __init__(self):
        super().__init__()

        main = QVBoxLayout(self)
        main.setSpacing(20)
        main.setContentsMargins(30, 30, 30, 30)

        # CONTROL MODE LABEL
        self.mode_label = QLabel("CONTROL MODE: --")
        self.mode_label.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {theme.TEXT_PRIMARY};
        """)

        # TOGGLE BUTTON
        self.toggle_btn = QPushButton("SWITCH MODE")
        self.toggle_btn.setFixedHeight(44)
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.BUTTON_ACTIVE};
                color: {theme.TEXT_PRIMARY};
                font-size: 15px;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {theme.BUTTON_ACTIVE};
            }}
        """)
        self.toggle_btn.clicked.connect(self.toggle_mode)

        main.addWidget(self.mode_label)
        main.addWidget(self.toggle_btn)

        # ACTUATOR CARDS
        self.cards = {}
        for wf, title in WORKLOAD_MAP.items():
            card = ActuatorCard(title)
            self.cards[wf] = card
            main.addWidget(card)

        main.addStretch()

        # REFRESH TIMER
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1500)

        self.refresh()

    # -----------------------------
    # ACTIONS
    # -----------------------------
    def toggle_mode(self):
        control = read_json(CONTROL_FILE)
        if not control:
            return

        control["mode"] = "MANUAL" if control.get("mode") == "AUTO" else "AUTO"
        write_json(CONTROL_FILE, control)
        self.refresh()

    def refresh(self):
        control = read_json(CONTROL_FILE)
        state = read_json(STATE_FILE)

        if not control or not state:
            return

        # MODE DISPLAY
        mode = control.get("mode", "AUTO")
        mode_color = (
            theme.MODE_COLORS["PERFORMANCE"]
            if mode == "AUTO"
            else "#FFD166"
        )

        self.mode_label.setText(f"CONTROL MODE: {mode}")
        self.mode_label.setStyleSheet(
            f"font-size: 22px; font-weight: bold; color: {mode_color};"
        )

        active = running_workloads()

        for wf, card in self.cards.items():
            self.update_card(card, wf in active)

    def update_card(self, card, is_on):
        if is_on:
            text = "STATUS: ACTIVE"
            color = theme.MODE_COLORS["PERFORMANCE"]
        else:
            text = "STATUS: INACTIVE"
            color = theme.TEXT_SECONDARY

        card.status.setText(text)
        card.status.setStyleSheet(f"""
            font-size: 15px;
            color: {color};
        """)
