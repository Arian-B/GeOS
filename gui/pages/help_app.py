from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QScroller, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

from gui import theme


class HelpSection(QFrame):
    def __init__(self, title, body):
        super().__init__()
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border: 2px solid {theme.SHELL_BORDER};
                border-bottom: 4px solid #051f1c;
                border-radius: 12px;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        heading = QLabel(title)
        heading.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {theme.TEXT_SECONDARY};")
        text = QLabel(body)
        text.setWordWrap(True)
        text.setStyleSheet("font-size: 14px;")
        layout.addWidget(heading)
        layout.addWidget(text)


class HelpAppPage(QWidget):
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

        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("HELP")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        subtitle = QLabel("On-device quick guide for farmers and operators using GeOS.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        sections = [
            (
                "Overview",
                "Use Overview to see the overall state of the farm system, the current GeOS mode, power status, and any immediate recommendation.",
            ),
            (
                "Field Monitor",
                "Field Monitor shows soil moisture, temperature, humidity, battery reserve, and connectivity. If values look abnormal, check Alerts next.",
            ),
            (
                "Water Manager",
                "Water Manager helps you review irrigation state and manually enable or disable irrigation when needed. Use it carefully when soil conditions are changing.",
            ),
            (
                "Power Center",
                "Power Center lets you view battery state and choose a power strategy. ENERGY_SAVER reduces load, BALANCED is general use, and PERFORMANCE favors speed.",
            ),
            (
                "Alerts",
                "Alerts shows warnings and critical events. Critical alerts should be handled first. Warnings should be reviewed before conditions worsen.",
            ),
            (
                "Device and Maintenance",
                "Device shows hardware and OS details. Maintenance and Updates are for service checks, safe mode, and staged update review.",
            ),
            (
                "Apps",
                "Apps are utility tools. Clock handles time tools, Notes stores field observations, Weather shows live local weather, Calendar schedules events, and Reports summarizes local GeOS data.",
            ),
            (
                "Operator Guidance",
                "If GeOS enters recovery or safe mode, review Alerts, Device, and Task Monitor first. Avoid forcing modes unless you understand the reason for the system state.",
            ),
        ]

        for heading, body in sections:
            layout.addWidget(HelpSection(heading, body))

        layout.addStretch()

