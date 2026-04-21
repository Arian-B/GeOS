import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QScrollArea, QScroller, QVBoxLayout, QWidget

from control.os_control import read_control, write_control
from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAFE_MODE_FLAG = os.path.join(BASE_DIR, "control", "SAFE_MODE")
BOOT_SUCCESS_FILE = os.path.join(BASE_DIR, "state", "boot_success.flag")


class MaintenanceCard(QFrame):
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


class MaintenancePage(QWidget):
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
        QScroller.grabGesture(self.scroll.viewport(), QScroller.TouchGesture)
        outer.addWidget(self.scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.scroll.setWidget(content)

        self.layout = QVBoxLayout(content)
        self.layout.setSpacing(16)
        self.layout.setContentsMargins(24, 24, 24, 24)

        self.title = QLabel("MAINTENANCE")
        self.title.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.layout.addWidget(self.title)

        self.subtitle = QLabel("Safe mode, recovery readiness, and service-control preparation.")
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        self.layout.addWidget(self.subtitle)

        self.summary = QLabel("Checking maintenance state...")
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

        self.safe_card = MaintenanceCard("Safe Mode")
        self.maint_card = MaintenanceCard("Maintenance Mode")
        self.boot_card = MaintenanceCard("Boot Recovery")
        for card in (self.safe_card, self.maint_card, self.boot_card):
            self.layout.addWidget(card)

        self.safe_btn = QPushButton("Toggle Safe Mode")
        self.maint_btn = QPushButton("Toggle Maintenance Mode")
        self.safe_btn.clicked.connect(self.toggle_safe_mode)
        self.maint_btn.clicked.connect(self.toggle_maintenance)
        self.layout.addWidget(self.safe_btn)
        self.layout.addWidget(self.maint_btn)
        self.layout.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1500)
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
        control = read_control()
        control["safe_mode"] = enable
        write_control(control)
        self.refresh()

    def toggle_maintenance(self):
        control = read_control()
        control["maintenance"] = not bool(control.get("maintenance", False))
        write_control(control)
        self.refresh()

    def refresh(self):
        control = read_control()
        safe_mode = bool(control.get("safe_mode", False)) or os.path.exists(SAFE_MODE_FLAG)
        maintenance = bool(control.get("maintenance", False))
        boot_ready = os.path.exists(BOOT_SUCCESS_FILE)

        self.safe_card.value.setText("Enabled" if safe_mode else "Disabled")
        self.safe_card.detail.setText(
            "GeOS is limiting workloads for recovery." if safe_mode else "Recovery restrictions are currently off."
        )

        self.maint_card.value.setText("Enabled" if maintenance else "Disabled")
        self.maint_card.detail.setText(
            "Maintenance mode is holding the system in a protected state."
            if maintenance
            else "Maintenance mode is not currently active."
        )

        self.boot_card.value.setText("Ready" if boot_ready else "Unknown")
        self.boot_card.detail.setText(
            "A recent boot-success marker is present." if boot_ready else "No current boot-success marker found."
        )

        self.summary.setText(
            f"Maintenance state: safe mode {'on' if safe_mode else 'off'} | maintenance {'on' if maintenance else 'off'}"
        )
        self.safe_btn.setText("Disable Safe Mode" if safe_mode else "Enable Safe Mode")
        self.maint_btn.setText("Disable Maintenance Mode" if maintenance else "Enable Maintenance Mode")
