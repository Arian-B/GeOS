# gui/nav_bar.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
from pathlib import Path
from gui import theme

ICON_SIZE = QSize(32, 32)

class NavBar(QWidget):
    page_selected = Signal(str)

    def __init__(self):
        super().__init__()

        self.setFixedWidth(120)
        self.setStyleSheet(f"background-color: {theme.SIDEBAR_BG};")

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(10, 20, 10, 20)

        self.icon_map = {
            "home": "home.svg",
            "sensors": "plant.svg",
            "control": "droplet.svg",
            "ai": "brain.svg",
            "settings": "settings.svg",
        }

        for key, filename in self.icon_map.items():
            btn = QPushButton()
            btn.setFixedSize(80, 60)
            btn.setCursor(Qt.PointingHandCursor)

            icon = self.render_svg_icon(
                filename,
                theme.TEXT_PRIMARY
            )
            btn.setIcon(icon)
            btn.setIconSize(ICON_SIZE)

            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme.BUTTON_BG};
                    border: none;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {theme.BUTTON_ACTIVE};
                }}
            """)

            btn.clicked.connect(lambda _, k=key: self.page_selected.emit(k))
            layout.addWidget(btn)

        layout.addStretch()

    def render_svg_icon(self, filename, color_hex):
        """Render SVG as colored QIcon (Qt-safe)"""
        icon_path = Path(__file__).parent.joinpath("icons", filename)
        pixmap = QPixmap(ICON_SIZE)
        pixmap.fill(Qt.transparent)

        if not icon_path.exists():
            print(f"[NavBar] Missing icon: {icon_path}")
            return QIcon()

        renderer = QSvgRenderer(str(icon_path))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor(color_hex))
        painter.setBrush(QColor(color_hex))
        renderer.render(painter)
        painter.end()

        return QIcon(pixmap)
