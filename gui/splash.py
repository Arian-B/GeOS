from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame
)
from PySide6.QtCore import Qt, QTimer
from gui import theme


class SplashScreen(QWidget):
    def __init__(self, on_finish_callback):
        super().__init__()

        self.setWindowTitle("GeOS")
        self.on_finish = on_finish_callback
        self.setFixedSize(1024, 600)
        self.setStyleSheet(f"background-color: {theme.BACKGROUND};")

        # === MAIN LAYOUT ===
        main = QVBoxLayout(self)
        main.setAlignment(Qt.AlignCenter)
        main.setSpacing(20)

        # === LOGO ===
        self.logo = QLabel("GeOS")
        self.logo.setAlignment(Qt.AlignCenter)
        self.logo.setStyleSheet("""
            font-size: 64px;
            font-weight: 900;
            color: #C7F9CC;
            letter-spacing: 3px;
        """)

        self.subtitle = QLabel("prototype version 1.0")
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setStyleSheet("""
            font-size: 16px;
            color: #A8DADC;
        """)

        # === LOADING TEXT ===
        self.status = QLabel("Initializing system modules...")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("""
            font-size: 14px;
            color: #A8DADC;
        """)

        # === BLOCK LOADING BAR ===
        self.bar_container = QHBoxLayout()
        self.bar_container.setSpacing(6)
        self.blocks = []

        for _ in range(12):
            block = QFrame()
            block.setFixedSize(22, 14)
            block.setStyleSheet("""
                background-color: #1B4332;
                border-radius: 2px;
            """)
            self.blocks.append(block)
            self.bar_container.addWidget(block)

        # === ASSEMBLE ===
        main.addStretch()
        main.addWidget(self.logo)
        main.addWidget(self.subtitle)
        main.addSpacing(30)
        main.addLayout(self.bar_container)
        main.addWidget(self.status)
        main.addStretch()

        # === TIMER ===
        self.step = 0
        self.messages = [
            "Initializing system modules...",
            "Loading telemetry engine...",
            "Starting ML policy controller...",
            "Configuring control interfaces...",
            "Launching user environment..."
        ]

        self.timer = QTimer()
        self.timer.timeout.connect(self.advance)
        self.timer.start(500)

    def advance(self):
        if self.step < len(self.blocks):
            self.blocks[self.step].setStyleSheet("""
                background-color: #74C69D;
                border-radius: 2px;
            """)
        if self.step < len(self.messages):
            self.status.setText(self.messages[self.step])

        self.step += 1

        if self.step >= len(self.blocks):
            self.timer.stop()
            QTimer.singleShot(600, self.finish)

    def finish(self):
        geometry = self.geometry()
        self.close()
        self.on_finish(geometry)
