# gui/splash_widget.py

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from gui import theme


class SplashWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.setStyleSheet(f"""
            background-color: {theme.BACKGROUND};
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        logo = QLabel("GeOS")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(f"""
            font-size: 72px;
            font-weight: bold;
            color: {theme.TEXT_PRIMARY};
        """)

        subtitle = QLabel("Prototype Version 1.0")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"""
            font-size: 16px;
            color: {theme.TEXT_SECONDARY};
        """)

        layout.addWidget(logo)
        layout.addSpacing(10)
        layout.addWidget(subtitle)
