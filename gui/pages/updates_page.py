import glob
import json
import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QScrollArea, QScroller, QVBoxLayout, QWidget

from core_os import update_manager
from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYSTEM_DIR = os.path.join(BASE_DIR, "system")
STATE_DIR = os.path.join(BASE_DIR, "state")
INCOMING_DIR = os.path.join(BASE_DIR, "updates", "incoming")
PENDING_FILE = os.path.join(SYSTEM_DIR, "slot_pending.json")
CURRENT_FILE = os.path.join(SYSTEM_DIR, "slot_current")
UPDATE_INCOMING_STATE_FILE = os.path.join(STATE_DIR, "update_incoming.json")


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


class UpdateCard(QFrame):
    def __init__(self, title):
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
        layout.setSpacing(6)
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


class UpdatesPage(QWidget):
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
        outer.addWidget(self.scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.scroll.setWidget(content)

        self.layout = QVBoxLayout(content)
        self.layout.setSpacing(16)
        self.layout.setContentsMargins(24, 24, 24, 24)

        self.title = QLabel("UPDATES")
        self.title.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.layout.addWidget(self.title)

        self.subtitle = QLabel("System image slots, staged packages, and update policy.")
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        self.layout.addWidget(self.subtitle)

        self.summary = QLabel("Checking update state...")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet(
            f"""
            font-size: 14px;
            font-weight: bold;
            background-color: {theme.BUTTON_BG};
            border: none;
            border-radius: 10px;
            padding: 10px 12px;
            """
        )
        self.layout.addWidget(self.summary)

        self.slot_card = UpdateCard("Slot Status")
        self.pending_card = UpdateCard("Pending Update")
        self.policy_card = UpdateCard("Policy")
        self.incoming_card = UpdateCard("Incoming Packages")
        for card in (self.slot_card, self.pending_card, self.policy_card, self.incoming_card):
            self.layout.addWidget(card)

        self.clear_pending_btn = QPushButton("Clear Pending Update")
        self.clear_pending_btn.clicked.connect(self.clear_pending)
        self.layout.addWidget(self.clear_pending_btn)
        self.layout.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1500)
        self.refresh()

    def clear_pending(self):
        try:
            os.remove(PENDING_FILE)
        except FileNotFoundError:
            pass
        for pattern in ("*.zip", "*.sig", "*.sig.json", "*.sha256"):
            for path in glob.glob(os.path.join(INCOMING_DIR, pattern)):
                try:
                    os.remove(path)
                except FileNotFoundError:
                    pass
        try:
            os.remove(UPDATE_INCOMING_STATE_FILE)
        except FileNotFoundError:
            pass
        self.refresh()

    def refresh(self):
        current = read_text(CURRENT_FILE) or "--"
        pending = read_json(PENDING_FILE) or {}
        pending_slot = pending.get("slot", "--")
        package = pending.get("package", "--")
        staged_at = pending.get("staged_at", "--")
        policy = update_manager.read_policy()
        incoming = update_manager.list_incoming_updates()

        self.slot_card.value.setText(current)
        self.slot_card.detail.setText(f"Current active slot: {current}")

        if pending_slot and pending_slot != "--":
            self.pending_card.value.setText(pending_slot)
            self.pending_card.detail.setText(f"Package: {package} | staged at: {staged_at}")
        else:
            self.pending_card.value.setText("None")
            self.pending_card.detail.setText("No update is currently staged for the next boot.")

        self.policy_card.value.setText("Configured")
        self.policy_card.detail.setText(
            f"signature={policy.get('require_signature', False)} | sha256={policy.get('require_sha256', False)} | auto stage={policy.get('auto_stage_updates', True)} | auto apply={policy.get('auto_apply_updates', False)}"
        )

        self.incoming_card.value.setText(str(len(incoming)))
        if incoming:
            self.incoming_card.detail.setText("Packages waiting in incoming: " + ", ".join(incoming))
        else:
            self.incoming_card.detail.setText("No incoming update packages found.")

        self.summary.setText(
            f"Update status: current slot {current} | pending slot {pending_slot if pending_slot != '--' else 'none'}"
        )
        self.clear_pending_btn.setEnabled(bool(incoming) or (pending_slot not in ("", "--", None)))
