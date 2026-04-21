# gui/main_window.py

import datetime
import json
import os
import subprocess

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QStackedWidget,
    QGraphicsOpacityEffect,
    QLabel,
    QFrame,
    QToolButton,
    QMenu,
    QMessageBox,
    QApplication,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QPoint, QEasingCurve, QTimer, QParallelAnimationGroup

from gui.nav_bar import NavBar
from gui.pages.home import HomePage
from gui.pages.sensors import SensorsPage
from gui.pages.control import ControlPage
from gui.pages.ai import AIPage
from gui.pages.alerts import AlertsPage
from gui.pages.settings import SettingsPage
from gui.pages.task_monitor import TaskMonitorPage
from gui.pages.water_manager import WaterManagerPage
from gui.pages.power_center import PowerCenterPage
from gui.pages.updates_page import UpdatesPage
from gui.pages.maintenance_page import MaintenancePage
from gui.pages.clock_app import ClockAppPage
from gui.pages.calculator_app import CalculatorAppPage
from gui.pages.notes_app import NotesAppPage
from gui.pages.weather_app import WeatherAppPage
from gui.pages.calendar_app import CalendarAppPage
from gui.pages.reports_app import ReportsAppPage
from gui.pages.help_app import HelpAppPage
from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")
SYSTEMD_MANAGED_ENV = "GEOS_MANAGED_BY_SYSTEMD"


class MainWindow(QWidget):
    APP_REGISTRY = [
        {
            "key": "home",
            "label": "Overview",
            "subtitle": "Farm status and live summary",
            "icon": "home.svg",
            "group": "System",
        },
        {
            "key": "sensors",
            "label": "Field Monitor",
            "subtitle": "Sensors and environment",
            "icon": "plant.svg",
            "group": "System",
        },
        {
            "key": "control",
            "label": "Control Center",
            "subtitle": "Manual operations and workloads",
            "icon": "droplet.svg",
            "group": "System",
        },
        {
            "key": "ai",
            "label": "Advisor",
            "subtitle": "GeOS guidance and reasoning",
            "icon": "brain.svg",
            "group": "System",
        },
        {
            "key": "updates_page",
            "label": "Updates",
            "subtitle": "Slots and staged packages",
            "icon": "update.svg",
            "group": "System",
        },
        {
            "key": "maintenance_page",
            "label": "Maintenance",
            "subtitle": "Safe mode and recovery",
            "icon": "maintenance.svg",
            "group": "System",
        },
        {
            "key": "power_center",
            "label": "Power Center",
            "subtitle": "Energy mode and battery reserve",
            "icon": "brain.svg",
            "group": "System",
        },
        {
            "key": "water_manager",
            "label": "Water Manager",
            "subtitle": "Irrigation and moisture recovery",
            "icon": "droplet.svg",
            "group": "System",
        },
        {
            "key": "alerts",
            "label": "Alerts",
            "subtitle": "Warnings and critical events",
            "icon": "alert.svg",
            "group": "System",
        },
        {
            "key": "task_monitor",
            "label": "Task Monitor",
            "subtitle": "Services, workloads, and load",
            "icon": "task.svg",
            "group": "System",
        },
        {
            "key": "settings",
            "label": "Device",
            "subtitle": "Hardware, OS, and network",
            "icon": "settings.svg",
            "group": "System",
        },
        {
            "key": "clock",
            "label": "Clock",
            "subtitle": "Time, world clocks, stopwatch, alarm",
            "icon": "clock.svg",
            "group": "Apps",
        },
        {
            "key": "calculator",
            "label": "Calculator",
            "subtitle": "Normal and scientific calculator",
            "icon": "calculator.svg",
            "group": "Apps",
        },
        {
            "key": "notes",
            "label": "Notes",
            "subtitle": "Multiple field notes and reminders",
            "icon": "notes.svg",
            "group": "Apps",
        },
        {
            "key": "weather",
            "label": "Weather",
            "subtitle": "Live local weather and animated conditions",
            "icon": "weather.svg",
            "group": "Apps",
        },
        {
            "key": "calendar",
            "label": "Calendar",
            "subtitle": "Events, reminders, and Gregorian dates",
            "icon": "calendar.svg",
            "group": "Apps",
        },
        {
            "key": "reports",
            "label": "Reports",
            "subtitle": "Local summaries and operating snapshots",
            "icon": "reports.svg",
            "group": "Apps",
        },
        {
            "key": "help",
            "label": "Help",
            "subtitle": "On-device guidance and quick reference",
            "icon": "help.svg",
            "group": "Apps",
        },
    ]

    def __init__(self):
        super().__init__()
        self._page_animation = None
        self._current_page_key = None

        self.setWindowTitle("GeOS")
        self.resize(1240, 720)
        self.setMinimumSize(920, 620)
        self.setStyleSheet(f"background-color: {theme.SHELL_BG};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.nav = NavBar(self.APP_REGISTRY)
        layout.addWidget(self.nav)

        shell = QFrame()
        shell.setStyleSheet(f"background-color: {theme.SHELL_BG};")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(22, 18, 22, 18)
        shell_layout.setSpacing(16)

        header = QFrame()
        header.setStyleSheet(
            f"""
            background-color: {theme.SHELL_PANEL};
            border: 1px solid {theme.SHELL_BORDER};
            border-radius: 14px;
            """
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(12)

        title_column = QVBoxLayout()
        title_column.setSpacing(4)
        self.shell_title = QLabel("Overview")
        self.shell_title.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: 28px; font-weight: bold;"
        )
        self.shell_subtitle = QLabel("Farm status and live summary")
        self.shell_subtitle.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: 13px;"
        )
        title_column.addWidget(self.shell_title)
        title_column.addWidget(self.shell_subtitle)
        header_layout.addLayout(title_column, 2)

        self.mode_pill = QLabel("MODE --")
        self.mode_pill.setAlignment(Qt.AlignCenter)
        self.mode_pill.setMinimumWidth(160)
        self.mode_pill.setStyleSheet(self._pill_style(theme.SHELL_PANEL_ALT, theme.TEXT_PRIMARY))

        self.status_pill = QLabel("SYSTEM OFFLINE")
        self.status_pill.setAlignment(Qt.AlignCenter)
        self.status_pill.setMinimumWidth(180)
        self.status_pill.setStyleSheet(self._pill_style(theme.BUTTON_BG, theme.TEXT_SECONDARY))

        self.power_button = QToolButton()
        self.power_button.setText("POWER")
        self.power_button.setCursor(Qt.PointingHandCursor)
        self.power_button.setPopupMode(QToolButton.InstantPopup)
        self.power_button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.power_button.setStyleSheet(self._power_button_style())
        self.power_button.setMenu(self._build_power_menu())

        self.clock_label = QLabel("--:--")
        self.clock_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.clock_label.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: 20px; font-weight: bold;"
        )

        header_layout.addWidget(self.mode_pill)
        header_layout.addWidget(self.status_pill)
        header_layout.addWidget(self.power_button)
        header_layout.addStretch()
        header_layout.addWidget(self.clock_label)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet(
            f"""
            QStackedWidget {{
                background-color: {theme.SHELL_BG};
                border: none;
            }}
            """
        )

        # Main pages
        self.pages = {
            "home": HomePage(),
            "sensors": SensorsPage(),
            "control": ControlPage(),
            "ai": AIPage(),
            "updates_page": UpdatesPage(),
            "maintenance_page": MaintenancePage(),
            "power_center": PowerCenterPage(),
            "water_manager": WaterManagerPage(),
            "alerts": AlertsPage(),
            "task_monitor": TaskMonitorPage(),
            "settings": SettingsPage(),
            "clock": ClockAppPage(),
            "calculator": CalculatorAppPage(),
            "notes": NotesAppPage(),
            "weather": WeatherAppPage(),
            "calendar": CalendarAppPage(),
            "reports": ReportsAppPage(),
            "help": HelpAppPage(),
        }

        for page in self.pages.values():
            self.stack.addWidget(page)
            self._set_page_active(page, False)

        self.nav.page_selected.connect(self.switch_page)

        shell_layout.addWidget(header)
        shell_layout.addWidget(self.stack, 1)
        layout.addWidget(shell, 1)

        self.header_timer = QTimer(self)
        self.header_timer.timeout.connect(self.refresh_shell_state)
        self.header_timer.start(1000)

        self.switch_page("home")
        self.refresh_shell_state()

    def _pill_style(self, bg, fg):
        return (
            f"background-color: {bg};"
            f"color: {fg};"
            f"border: 1px solid {theme.SHELL_BORDER};"
            "border-radius: 18px;"
            "padding: 8px 14px;"
            "font-size: 12px;"
            "font-weight: bold;"
        )

    def _power_button_style(self):
        return (
            f"QToolButton {{"
            f"background-color: {theme.SHELL_PANEL_ALT};"
            f"color: {theme.TEXT_PRIMARY};"
            f"border: 1px solid {theme.SHELL_BORDER};"
            "border-radius: 18px;"
            "padding: 8px 18px;"
            "font-size: 12px;"
            "font-weight: bold;"
            "min-width: 104px;"
            "}"
            f"QToolButton:hover {{ background-color: {theme.BUTTON_ACTIVE}; }}"
            f"QToolButton:pressed {{ background-color: {theme.BUTTON_BG}; }}"
            f"QToolButton::menu-indicator {{ image: none; width: 0px; }}"
        )

    def _power_menu_style(self):
        return (
            f"QMenu {{"
            f"background-color: {theme.SHELL_PANEL};"
            f"color: {theme.TEXT_PRIMARY};"
            f"border: 1px solid {theme.SHELL_BORDER};"
            "padding: 8px;"
            "}"
            f"QMenu::item {{"
            "padding: 10px 24px 10px 14px;"
            "border-radius: 10px;"
            "margin: 2px 0px;"
            "}"
            f"QMenu::item:selected {{"
            f"background-color: {theme.BUTTON_ACTIVE};"
            f"color: {theme.TEXT_PRIMARY};"
            "}"
            f"QMenu::separator {{"
            f"height: 1px;"
            f"background-color: {theme.SHELL_BORDER};"
            "margin: 6px 8px;"
            "}"
        )

    def _build_power_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(self._power_menu_style())

        sleep_action = QAction("Sleep", self)
        sleep_action.triggered.connect(lambda: self._run_power_command("systemctl suspend", "Sleep"))
        menu.addAction(sleep_action)

        restart_action = QAction("Restart", self)
        restart_action.triggered.connect(lambda: self._run_power_command("systemctl reboot", "Restart"))
        menu.addAction(restart_action)

        shutdown_action = QAction("Shut Down", self)
        shutdown_action.triggered.connect(lambda: self._run_power_command("systemctl poweroff", "Shut Down"))
        menu.addAction(shutdown_action)

        if not self._is_systemd_managed():
            menu.addSeparator()
            exit_action = QAction("Exit GeOS", self)
            exit_action.triggered.connect(self.close)
            menu.addAction(exit_action)

        return menu

    def _is_systemd_managed(self):
        return str(os.environ.get(SYSTEMD_MANAGED_ENV, "")).strip().lower() in ("1", "true", "yes", "on")

    def _run_power_command(self, command, label):
        confirm = QMessageBox(self)
        confirm.setWindowTitle(label)
        confirm.setText(f"{label} this device?")
        confirm.setInformativeText("GeOS will hand control to the operating system power manager.")
        confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm.setDefaultButton(QMessageBox.No)
        confirm.setStyleSheet(
            f"QMessageBox {{ background-color: {theme.SHELL_PANEL}; color: {theme.TEXT_PRIMARY}; }}"
            f"QLabel {{ color: {theme.TEXT_PRIMARY}; }}"
            f"QPushButton {{"
            f"background-color: {theme.BUTTON_BG};"
            f"color: {theme.TEXT_PRIMARY};"
            f"border: 1px solid {theme.SHELL_BORDER};"
            "border-radius: 10px;"
            "padding: 8px 16px;"
            "min-width: 92px;"
            "}"
            f"QPushButton:hover {{ background-color: {theme.BUTTON_ACTIVE}; }}"
        )
        if confirm.exec() != QMessageBox.Yes:
            return

        try:
            subprocess.Popen(command.split(), close_fds=True)
        except Exception as exc:
            QMessageBox.critical(
                self,
                f"{label} Failed",
                f"GeOS could not run the power command.\n\n{exc}",
            )

    def show_shell(self):
        screen = self.screen() or QApplication.primaryScreen()
        if screen is not None:
            geometry = screen.geometry()
            self.setGeometry(geometry)
        self.showFullScreen()

    def _read_state(self):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _app_meta(self, key):
        for item in self.APP_REGISTRY:
            if item["key"] == key:
                return item
        return {"label": key.title(), "subtitle": ""}

    def animate_page(self, widget):
        start_pos = widget.pos()
        widget.move(start_pos.x() + 40, start_pos.y())

        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        effect.setOpacity(0.0)

        pos_anim = QPropertyAnimation(widget, b"pos")
        pos_anim.setDuration(260)
        pos_anim.setStartValue(QPoint(start_pos.x() + 40, start_pos.y()))
        pos_anim.setEndValue(start_pos)
        pos_anim.setEasingCurve(QEasingCurve.OutCubic)

        fade_anim = QPropertyAnimation(effect, b"opacity")
        fade_anim.setDuration(260)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.setEasingCurve(QEasingCurve.InOutCubic)

        self._page_animation = QParallelAnimationGroup(self)
        self._page_animation.addAnimation(pos_anim)
        self._page_animation.addAnimation(fade_anim)
        self._page_animation.start()

    def refresh_shell_state(self):
        state = self._read_state()
        self.clock_label.setText(datetime.datetime.now().strftime("%H:%M"))

        mode = state.get("current_mode") or "--"
        mode_color = theme.MODE_COLORS.get(mode, theme.TEXT_PRIMARY)
        self.mode_pill.setText(f"MODE {mode}")
        self.mode_pill.setStyleSheet(self._pill_style(theme.SHELL_PANEL_ALT, mode_color))

        sensors = state.get("sensors", {}) if isinstance(state.get("sensors"), dict) else {}
        network = sensors.get("network", "OFFLINE")
        if state:
            status_text = "FIELD ONLINE" if network == "ONLINE" else "FIELD OFFLINE"
            status_color = theme.TEXT_SECONDARY if network == "ONLINE" else theme.ACCENT_WARN
        else:
            status_text = "SYSTEM OFFLINE"
            status_color = theme.ACCENT_WARN
        self.status_pill.setText(status_text)
        self.status_pill.setStyleSheet(self._pill_style(theme.BUTTON_BG, status_color))

    def switch_page(self, page_name):
        previous_key = self._current_page_key
        if previous_key in self.pages:
            self._set_page_active(self.pages[previous_key], False)

        meta = self._app_meta(page_name)
        page = self.pages[page_name]
        self.shell_title.setText(meta["label"])
        self.shell_subtitle.setText(meta["subtitle"])
        self.nav.set_active(page_name)
        self.stack.setCurrentWidget(page)
        self._current_page_key = page_name
        self._set_page_active(page, True)
        self.animate_page(page)

    def _set_page_active(self, page, active):
        hook_name = "on_page_activated" if active else "on_page_deactivated"
        hook = getattr(page, hook_name, None)
        if callable(hook):
            hook()

        timer_names = ("timer", "notification_timer", "animation_timer", "refresh_timer")
        managed = getattr(page, "_managed_timers", None)
        if managed is None:
            managed = {}
            setattr(page, "_managed_timers", managed)

        for name in timer_names:
            timer = getattr(page, name, None)
            if not isinstance(timer, QTimer):
                continue

            if active:
                state = managed.get(name)
                if state and state.get("was_active"):
                    timer.start(state["interval"])
                elif state is None and timer.interval() > 0:
                    timer.start(timer.interval())
            else:
                managed[name] = {
                    "interval": timer.interval(),
                    "was_active": timer.isActive(),
                }
                timer.stop()


    def closeEvent(self, event):
        if self.header_timer.isActive():
            self.header_timer.stop()

        for page in self.pages.values():
            self._set_page_active(page, False)
            cleanup = getattr(page, "on_app_closing", None)
            if callable(cleanup):
                cleanup()

        super().closeEvent(event)
