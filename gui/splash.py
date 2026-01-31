# gui/splash.py

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer
from gui import theme


class SplashScreen(QWidget):
    def __init__(self, on_finish_callback):
        super().__init__()

        self.on_finish_callback = on_finish_callback

        self.setWindowTitle("GeOS Boot")
        self.setFixedSize(1024, 600)   # 🔒 SAME SIZE AS MAIN WINDOW
        self.setStyleSheet(f"""
            background-color: {theme.BACKGROUND};
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        logo = QLabel("GeOS")
        logo.setStyleSheet(f"""
            font-size: 64px;
            font-weight: bold;
            color: {theme.TEXT_PRIMARY};
        """)

        subtitle = QLabel("Prototype Version 1.0")
        subtitle.setStyleSheet(f"""
            font-size: 16px;
            color: {theme.TEXT_SECONDARY};
        """)

        layout.addWidget(logo)
        layout.addWidget(subtitle)

        # Auto-close after 3 seconds
        QTimer.singleShot(3000, self.finish)

    def finish(self):
        self.close()
        self.on_finish_callback()
