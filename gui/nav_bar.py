# gui/nav_bar.py

from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFontMetrics
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFrame, QScrollArea, QScroller

from gui import theme

ICON_SIZE = QSize(32, 32)
NAV_WIDTH = 220


class NavBar(QWidget):
    page_selected = Signal(str)

    def __init__(self, app_registry):
        super().__init__()
        self._buttons = {}
        self._group_buttons = {}
        self._group_layouts = {}
        self._group_hints = {}
        self._app_registry = list(app_registry)
        self._app_meta = {item["key"]: item for item in self._app_registry}
        self._expanded_groups = {"System": True, "Apps": True}

        self.setFixedWidth(NAV_WIDTH)
        self.setStyleSheet(
            f"""
            background-color: {theme.SIDEBAR_BG};
            border-right: 1px solid {theme.SHELL_BORDER};
            """
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(14, 20, 14, 20)

        brand = QLabel("GeOS")
        brand.setStyleSheet(
            f"""
            color: {theme.TEXT_PRIMARY};
            font-size: 28px;
            font-weight: bold;
            letter-spacing: 2px;
            """
        )
        layout.addWidget(brand)

        tagline = QLabel("field operating shell")
        tagline.setWordWrap(True)
        tagline.setStyleSheet(
            f"""
            color: {theme.TEXT_MUTED};
            font-size: 12px;
            padding-bottom: 8px;
            """
        )
        layout.addWidget(tagline)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {theme.SHELL_BORDER};")
        layout.addWidget(divider)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(
            f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 4px 0 4px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {theme.SHELL_BORDER};
                border-radius: 5px;
                min-height: 28px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {theme.TEXT_SECONDARY};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
                height: 0px;
            }}
            """
        )
        QScroller.grabGesture(self.scroll.viewport(), QScroller.TouchGesture)
        layout.addWidget(self.scroll, 1)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.scroll.setWidget(scroll_content)

        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(0, 0, 12, 0)

        groups = OrderedDict()
        for item in self._app_registry:
            group_name = item.get("group", "System")
            groups.setdefault(group_name, []).append(item)

        for group_name, items in groups.items():
            header = QPushButton(f"▾  {group_name}")
            header.setCursor(Qt.PointingHandCursor)
            header.setStyleSheet(self._group_style())
            header.clicked.connect(lambda _, name=group_name: self.toggle_group(name))
            scroll_layout.addWidget(header)
            self._group_buttons[group_name] = header

            group_frame = QFrame()
            group_frame.setStyleSheet("background: transparent; border: none;")
            group_layout = QVBoxLayout(group_frame)
            group_layout.setSpacing(-4 if group_name == "System" else 4)
            group_layout.setContentsMargins(8, 0, 2, 0)
            scroll_layout.addWidget(group_frame)
            self._group_layouts[group_name] = group_frame

            for item in items:
                key = item["key"]
                filename = item["icon"]
                label = item["label"]
                subtitle = item["subtitle"]
                group = item.get("group", "System")

                btn = QPushButton()
                btn.setFixedHeight(68 if group == "System" else 44)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setCheckable(True)
                btn.setIcon(self.render_svg_icon(filename, theme.TEXT_PRIMARY))
                btn.setIconSize(ICON_SIZE)
                btn.setToolTip(f"{label}: {subtitle}" if subtitle else label)
                btn.setStyleSheet(self._button_style(active=False, group=group))
                btn.setProperty("nav_label", label)
                btn.setProperty("nav_subtitle", subtitle)
                btn.setProperty("nav_group", group)
                btn.clicked.connect(lambda _, k=key: self.page_selected.emit(k))
                if group == "System":
                    btn.setContentsMargins(0, 0, 0, 0)

                group_layout.addWidget(btn)
                self._buttons[key] = btn
                self._update_button_text(btn)

            if group_name == "Apps":
                hint = QLabel("More built-in apps will appear here.")
                hint.setWordWrap(True)
                hint.setStyleSheet(
                    f"""
                    color: {theme.TEXT_MUTED};
                    font-size: 11px;
                    padding: 6px 8px 0 8px;
                    """
                )
                group_layout.addWidget(hint)
                self._group_hints[group_name] = hint

        utility = QLabel("Core farm and device software")
        utility.setWordWrap(True)
        utility.setStyleSheet(
            f"""
            color: {theme.TEXT_MUTED};
            font-size: 11px;
            padding-top: 6px;
            """
        )
        layout.addWidget(utility)

    def _group_style(self):
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {theme.TEXT_SECONDARY};
                border: none;
                text-align: left;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 2px 2px 2px;
            }}
            QPushButton:hover {{
                color: {theme.TEXT_PRIMARY};
            }}
        """

    def _button_style(self, active, group):
        bg = theme.BUTTON_ACTIVE if active else theme.BUTTON_BG
        border = theme.TEXT_SECONDARY if active else theme.SHELL_BORDER
        shadow = "#051f1c"
        padding = "10px 12px" if group == "System" else "8px 10px"
        font_size = "15px" if group == "System" else "14px"
        radius = "10px" if group == "System" else "8px"
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {theme.TEXT_PRIMARY};
                border: 2px solid {border};
                border-bottom: 4px solid {shadow};
                border-radius: {radius};
                padding: {padding};
                text-align: left;
                font-size: {font_size};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme.BUTTON_ACTIVE};
                border: 2px solid {theme.TEXT_SECONDARY};
                border-bottom: 4px solid {shadow};
            }}
            QPushButton:pressed {{
                background-color: {theme.BUTTON_HOVER};
                border: 2px solid {theme.TEXT_PRIMARY};
                border-bottom: 2px solid {shadow};
                padding-top: 12px;
                padding-bottom: 8px;
            }}
        """

    def _available_text_width(self, button, group):
        reserve = 92 if group == "System" else 66
        width = button.width() if button.width() > 0 else NAV_WIDTH - 36
        return max(48, width - reserve)

    def _elide(self, button, text, width):
        metrics = QFontMetrics(button.font())
        return metrics.elidedText(text, Qt.ElideRight, width)

    def _update_button_text(self, button):
        group = button.property("nav_group") or "System"
        label = button.property("nav_label") or ""
        subtitle = button.property("nav_subtitle") or ""
        text_width = self._available_text_width(button, group)

        if group == "System":
            display_label = self._elide(button, label, text_width)
            display_subtitle = self._elide(button, subtitle, text_width)
            button.setText(f"{display_label}\n{display_subtitle}")
        else:
            button.setText(self._elide(button, label, text_width))

    def _update_button_texts(self):
        for button in self._buttons.values():
            self._update_button_text(button)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_button_texts()

    def toggle_group(self, group_name):
        expanded = not self._expanded_groups.get(group_name, True)
        self._expanded_groups[group_name] = expanded
        frame = self._group_layouts.get(group_name)
        if frame is not None:
            frame.setVisible(expanded)
        button = self._group_buttons.get(group_name)
        if button is not None:
            prefix = "▾" if expanded else "▸"
            button.setText(f"{prefix}  {group_name}")

    def set_active(self, key):
        for item_key, btn in self._buttons.items():
            is_active = item_key == key
            group = self._app_meta.get(item_key, {}).get("group", "System")
            btn.blockSignals(True)
            btn.setChecked(is_active)
            btn.blockSignals(False)
            btn.setStyleSheet(self._button_style(active=is_active, group=group))
            self._update_button_text(btn)

        for item in self._app_registry:
            if item["key"] == key:
                group_name = item.get("group", "System")
                if not self._expanded_groups.get(group_name, True):
                    self.toggle_group(group_name)
                break

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
