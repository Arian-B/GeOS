import datetime
import os

from PySide6.QtCore import QTime, QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QScroller,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from gui import theme


class ClockSection(QFrame):
    def __init__(self, title, subtitle):
        super().__init__()
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border: none;
                border-radius: 12px;
            }}
            """
        )
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 16, 18, 16)
        self.layout.setSpacing(8)

        heading = QLabel(title)
        heading.setStyleSheet(f"font-size: 19px; font-weight: bold; color: {theme.TEXT_PRIMARY};")
        sub = QLabel(subtitle)
        sub.setWordWrap(True)
        sub.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED};")

        self.layout.addWidget(heading)
        self.layout.addWidget(sub)


class ClockAppPage(QWidget):
    def __init__(self):
        super().__init__()
        self._stopwatch_elapsed_ms = 0
        self._stopwatch_running = False
        self._alarm_fired_key = None
        self._use_24_hour = False
        self._clock_active = False

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
            QTimeEdit {{
                background-color: {theme.SHELL_PANEL_ALT};
                color: {theme.TEXT_PRIMARY};
                border: none;
                border-radius: 8px;
                padding: 8px 10px;
            }}
            QCheckBox {{
                color: {theme.TEXT_PRIMARY};
                spacing: 8px;
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

        title = QLabel("CLOCK")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        subtitle = QLabel("Time tools for daily work, reminders, and quick field timing.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        digital_section = ClockSection("Digital Clock", "Current local date and time for the running device.")
        format_row = QHBoxLayout()
        self.use_24_hour = QCheckBox("Use 24-hour format")
        self.use_24_hour.setChecked(False)
        format_row.addWidget(self.use_24_hour)
        format_row.addStretch()
        digital_section.layout.addLayout(format_row)
        self.digital_time = QLabel("--:--:--")
        self.digital_time.setStyleSheet(f"font-size: 30px; font-weight: bold; color: {theme.TEXT_PRIMARY};")
        self.digital_date = QLabel("--")
        self.digital_date.setStyleSheet(f"font-size: 14px; color: {theme.TEXT_MUTED};")
        digital_section.layout.addWidget(self.digital_time)
        digital_section.layout.addWidget(self.digital_date)
        layout.addWidget(digital_section)

        stopwatch_section = ClockSection("Stopwatch", "Track irrigation, inspection, or maintenance time quickly.")
        self.stopwatch_display = QLabel("00:00:00.0")
        self.stopwatch_display.setStyleSheet("font-size: 26px; font-weight: bold;")
        stopwatch_section.layout.addWidget(self.stopwatch_display)

        stopwatch_actions = QGridLayout()
        self.start_stopwatch_button = self._make_clock_button("Start")
        self.pause_stopwatch_button = self._make_clock_button("Pause")
        self.reset_stopwatch_button = self._make_clock_button("Reset")
        stopwatch_actions.addWidget(self.start_stopwatch_button, 0, 0)
        stopwatch_actions.addWidget(self.pause_stopwatch_button, 0, 1)
        stopwatch_actions.addWidget(self.reset_stopwatch_button, 1, 0, 1, 2)
        stopwatch_section.layout.addLayout(stopwatch_actions)
        layout.addWidget(stopwatch_section)

        alarm_section = ClockSection("Alarm", "Set a simple reminder alarm. GeOS will use the default system beep.")
        alarm_row = QVBoxLayout()
        self.alarm_time = QTimeEdit()
        self.alarm_time.setDisplayFormat("HH:mm")
        self.alarm_time.setTime(QTime.currentTime().addSecs(300))
        self.alarm_enabled = QCheckBox("Enable alarm")
        self.alarm_status = QLabel("Alarm inactive")
        self.alarm_status.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        alarm_row.addWidget(self.alarm_time)
        alarm_row.addWidget(self.alarm_enabled)
        alarm_section.layout.addLayout(alarm_row)
        alarm_section.layout.addWidget(self.alarm_status)
        layout.addWidget(alarm_section)

        layout.addStretch()

        self.start_stopwatch_button.clicked.connect(self.start_stopwatch)
        self.pause_stopwatch_button.clicked.connect(self.pause_stopwatch)
        self.reset_stopwatch_button.clicked.connect(self.reset_stopwatch)
        self.alarm_enabled.toggled.connect(self.update_alarm_status)
        self.use_24_hour.toggled.connect(self.update_time_format)

        self.stopwatch_timer = QTimer(self)
        self.stopwatch_timer.timeout.connect(self.update_stopwatch_display)

        self.refresh()
        self.on_page_deactivated()

    def start_stopwatch(self):
        self._stopwatch_running = True
        if self._clock_active and not self.stopwatch_timer.isActive():
            self.stopwatch_timer.start(100)

    def pause_stopwatch(self):
        self._stopwatch_running = False
        self.stopwatch_timer.stop()

    def reset_stopwatch(self):
        self._stopwatch_running = False
        self._stopwatch_elapsed_ms = 0
        self.stopwatch_timer.stop()
        self.stopwatch_display.setText("00:00:00.0")

    def update_time_format(self):
        self._use_24_hour = self.use_24_hour.isChecked()
        self.alarm_time.setDisplayFormat("HH:mm" if self._use_24_hour else "hh:mm AP")
        self.update_alarm_status()
        self.refresh()

    def update_alarm_status(self):
        if self.alarm_enabled.isChecked():
            self.alarm_status.setText(f"Alarm armed for {self._format_qtime(self.alarm_time.time())}")
            self._alarm_fired_key = None
        else:
            self.alarm_status.setText("Alarm inactive")
            self._alarm_fired_key = None

    def refresh(self):
        now = datetime.datetime.now()
        self.digital_time.setText(self._format_datetime(now, include_seconds=True))
        self.digital_date.setText(now.strftime("%A, %d %B %Y"))

        self._check_alarm(now)

    def _schedule_clock_tick(self):
        if not self._clock_active:
            return
        next_delay_ms = 1000 - datetime.datetime.now().microsecond // 1000
        QTimer.singleShot(next_delay_ms, self._on_clock_tick)

    def _on_clock_tick(self):
        if not self._clock_active:
            return
        self.refresh()
        self._schedule_clock_tick()

    def update_stopwatch_display(self):
        if self._stopwatch_running:
            self._stopwatch_elapsed_ms += 100
        self.stopwatch_display.setText(self._format_elapsed(self._stopwatch_elapsed_ms))

    def _make_clock_button(self, label):
        button = QPushButton(label)
        button.setMinimumHeight(48)
        button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {theme.BUTTON_BG};
                color: {theme.TEXT_PRIMARY};
                border: 2px solid {theme.SHELL_BORDER};
                border-bottom: 4px solid #051f1c;
                border-radius: 8px;
                padding: 8px 10px;
                font-size: 16px;
                font-weight: bold;
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
                padding-top: 10px;
                padding-bottom: 6px;
            }}
            """
        )
        return button

    def _check_alarm(self, now):
        if not self.alarm_enabled.isChecked():
            return

        target = self.alarm_time.time()
        fire_key = now.strftime("%Y-%m-%d %H:%M")
        if now.hour == target.hour() and now.minute == target.minute() and now.second == 0:
            if self._alarm_fired_key != fire_key:
                self._alarm_fired_key = fire_key
                for _ in range(3):
                    QApplication.beep()
                self.alarm_status.setText(f"Alarm fired at {self._format_datetime(now, include_seconds=False)}")

    def _format_elapsed(self, elapsed_ms):
        total_tenths = elapsed_ms // 100
        seconds = total_tenths // 10
        tenths = total_tenths % 10
        minutes = seconds // 60
        hours = minutes // 60
        return f"{hours:02d}:{minutes % 60:02d}:{seconds % 60:02d}.{tenths}"

    def _format_datetime(self, dt_value, include_seconds):
        fmt = "%H:%M:%S" if include_seconds else "%H:%M"
        if not self._use_24_hour:
            fmt = "%I:%M:%S %p" if include_seconds else "%I:%M %p"
            return dt_value.strftime(fmt).lstrip("0")
        return dt_value.strftime(fmt)

    def _format_qtime(self, time_value):
        return time_value.toString("HH:mm" if self._use_24_hour else "hh:mm AP")

    def on_page_activated(self):
        if self._clock_active:
            return
        self._clock_active = True
        self.refresh()
        if self._stopwatch_running and not self.stopwatch_timer.isActive():
            self.stopwatch_timer.start(100)
        self._schedule_clock_tick()

    def on_page_deactivated(self):
        self._clock_active = False
        self.stopwatch_timer.stop()
