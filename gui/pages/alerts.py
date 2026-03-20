import datetime

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QScroller, QVBoxLayout, QWidget

from core_os.notifications import get_active_alerts
from gui import theme


def level_color(level):
    if level == "CRITICAL":
        return theme.ACCENT_DANGER
    if level == "WARN":
        return theme.ACCENT_WARN
    return theme.TEXT_SECONDARY


class AlertCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 10px;
                border: none;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        self.level = QLabel("LEVEL")
        self.level.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.time = QLabel("--")
        self.time.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED};")
        self.message = QLabel("--")
        self.message.setWordWrap(True)
        self.message.setStyleSheet(f"font-size: 17px; color: {theme.TEXT_PRIMARY};")

        layout.addWidget(self.level)
        layout.addWidget(self.time)
        layout.addWidget(self.message)

    def bind(self, alert):
        level = str(alert.get("level", "INFO")).upper()
        color = level_color(level)
        self.level.setText(level)
        self.level.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {color};")

        timestamp = alert.get("time")
        if timestamp:
            try:
                parsed = datetime.datetime.fromisoformat(timestamp)
                timestamp = parsed.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
        self.time.setText(f"Time: {timestamp or '--'}")
        self.message.setText(alert.get("message", "--"))


class AlertsPage(QWidget):
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
        self.layout.setSpacing(14)
        self.layout.setContentsMargins(24, 24, 24, 24)

        self.title = QLabel("ALERT CENTER")
        self.title.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.layout.addWidget(self.title)

        self.subtitle = QLabel("Live system warnings and critical farm events.")
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        self.layout.addWidget(self.subtitle)

        self.summary = QLabel("Checking alerts...")
        self.summary.setStyleSheet(f"font-size: 14px; color: {theme.TEXT_SECONDARY};")
        self.layout.addWidget(self.summary)

        self.cards_layout = QVBoxLayout()
        self.cards_layout.setSpacing(12)
        self.layout.addLayout(self.cards_layout)
        self.layout.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1500)
        self.refresh()

    def _clear_cards(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def refresh(self):
        alerts = get_active_alerts(limit=25)
        self._clear_cards()

        if not alerts:
            empty = AlertCard()
            empty.bind(
                {
                    "level": "INFO",
                    "time": datetime.datetime.now().isoformat(timespec="seconds"),
                    "message": "No active alerts in the current event log.",
                }
            )
            self.cards_layout.addWidget(empty)
            self.summary.setText("System calm: no recent warnings or critical alerts.")
            return

        critical = sum(1 for alert in alerts if str(alert.get("level", "")).upper() == "CRITICAL")
        warn = sum(1 for alert in alerts if str(alert.get("level", "")).upper() == "WARN")
        self.summary.setText(
            f"Recent alerts: {len(alerts)} total | {critical} critical | {warn} warnings"
        )

        for alert in alerts:
            card = AlertCard()
            card.bind(alert)
            self.cards_layout.addWidget(card)
