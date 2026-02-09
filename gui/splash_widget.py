# gui/splash_widget.py

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtCore import Qt, QTimer, Signal
from gui import theme


class SplashWidget(QWidget):
    boot_finished = Signal()   # 🔑 signal

    def __init__(self):
        super().__init__()

        self.setStyleSheet(f"background-color: {theme.BACKGROUND};")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        logo = QLabel("GeOS")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("""
            font-size: 64px;
            font-weight: 900;
            color: #C7F9CC;
            letter-spacing: 3px;
        """)

        subtitle = QLabel("prototype version 1.0")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 16px;
            color: #A8DADC;
        """)

        self.status = QLabel("Initializing system modules...")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("""
            font-size: 14px;
            color: #A8DADC;
        """)

        bar_layout = QHBoxLayout()
        bar_layout.setSpacing(6)

        self.blocks = []
        for _ in range(12):
            block = QFrame()
            block.setFixedSize(22, 14)
            block.setStyleSheet("background-color: #1B4332; border-radius: 2px;")
            self.blocks.append(block)
            bar_layout.addWidget(block)

        layout.addStretch()
        layout.addWidget(logo)
        layout.addWidget(subtitle)
        layout.addSpacing(30)
        layout.addLayout(bar_layout)
        layout.addWidget(self.status)
        layout.addStretch()

        self.step = 0
        self.messages = [
            "Initializing system modules...",
            "Loading telemetry engine...",
            "Starting ML policy controller...",
            "Configuring control interfaces...",
            "Launching user environment..."
        ]

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.timer.start(500)

    def advance(self):
        if self.step < len(self.blocks):
            self.blocks[self.step].setStyleSheet(
                "background-color: #74C69D; border-radius: 2px;"
            )

        if self.step < len(self.messages):
            self.status.setText(self.messages[self.step])

        self.step += 1

        # 🔑 BOOT COMPLETE
        if self.step >= len(self.blocks):
            self.timer.stop()
            QTimer.singleShot(400, self.boot_finished.emit)
