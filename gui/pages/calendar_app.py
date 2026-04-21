import datetime
import json
import os

from PySide6.QtCore import QDate, QEvent, QTime, QTimer, Qt
from PySide6.QtGui import QAction, QActionGroup, QColor, QTextCharFormat, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QScroller,
    QSizePolicy,
    QTableView,
    QTimeEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QPlainTextEdit,
    QMenu,
    QSpinBox,
)

from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVENTS_FILE = os.path.join(BASE_DIR, "state", "calendar_events.json")
CHEVRON_ICON = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons", "chevron_down.svg")

NOTIFY_OPTIONS = [
    ("At event time", 0),
    ("5 minutes before", 5),
    ("15 minutes before", 15),
    ("30 minutes before", 30),
    ("1 hour before", 60),
    ("1 day before", 1440),
]


def load_events():
    try:
        with open(EVENTS_FILE, "r") as handle:
            data = json.load(handle)
        if isinstance(data, list):
            normalized = []
            for item in data:
                if isinstance(item, dict):
                    normalized.append(
                        {
                            "title": str(item.get("title") or "Untitled event"),
                            "description": str(item.get("description") or ""),
                            "date": str(item.get("date") or ""),
                            "time": str(item.get("time") or "09:00"),
                            "notify_minutes": int(item.get("notify_minutes") or 0),
                            "notified_key": str(item.get("notified_key") or ""),
                        }
                    )
            return normalized
    except Exception:
        pass
    return []


def save_events(events):
    os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)
    with open(EVENTS_FILE, "w") as handle:
        json.dump(events, handle, indent=2)


class GeosOptionPicker(QWidget):
    def __init__(self, options, min_width=0):
        super().__init__()
        self._options = list(options)
        self._current_index = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.button = QToolButton()
        self.button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.button.setPopupMode(QToolButton.InstantPopup)
        if min_width > 0:
            self.button.setMinimumWidth(min_width)
        self.button.setStyleSheet(
            f"""
            QToolButton {{
                background-color: {theme.SHELL_PANEL_ALT};
                color: {theme.TEXT_PRIMARY};
                border: 2px solid {theme.SHELL_BORDER};
                border-radius: 8px;
                padding: 8px 34px 8px 10px;
                text-align: left;
                font-family: {theme.MONO_FONT};
                font-size: 13px;
            }}
            QToolButton:hover {{
                border: 2px solid {theme.TEXT_SECONDARY};
                background-color: {theme.SHELL_PANEL_ALT};
            }}
            QToolButton:pressed {{
                background-color: {theme.BUTTON_ACTIVE};
                border: 2px solid {theme.TEXT_PRIMARY};
            }}
            QToolButton::menu-indicator {{
                image: url("{CHEVRON_ICON}");
                subcontrol-origin: padding;
                subcontrol-position: right center;
                right: 10px;
            }}
            """
        )

        self.menu = QMenu(self.button)
        self.menu.setStyleSheet(
            f"""
            QMenu {{
                background-color: {theme.SHELL_PANEL_ALT};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.SHELL_BORDER};
            }}
            QMenu::item {{
                background-color: transparent;
                color: {theme.TEXT_PRIMARY};
                padding: 6px 12px;
            }}
            QMenu::item:selected {{
                background-color: {theme.BUTTON_ACTIVE};
                color: {theme.TEXT_PRIMARY};
            }}
            QMenu::item:hover {{
                background-color: {theme.BUTTON_ACTIVE};
                color: {theme.TEXT_PRIMARY};
            }}
            """
        )
        self.action_group = QActionGroup(self)
        self.action_group.setExclusive(True)

        for index, (label, data) in enumerate(self._options):
            action = QAction(label, self.action_group)
            action.setCheckable(True)
            action.setData(data)
            action.triggered.connect(lambda checked=False, idx=index: self.setCurrentIndex(idx))
            self.menu.addAction(action)

        self.button.setMenu(self.menu)
        layout.addWidget(self.button)
        self.setCurrentIndex(0)

    def currentData(self):
        return self._options[self._current_index][1]

    def currentText(self):
        return self._options[self._current_index][0]

    def setCurrentIndex(self, index):
        if not 0 <= index < len(self._options):
            return
        self._current_index = index
        label, _ = self._options[index]
        self.button.setText(label)
        actions = self.action_group.actions()
        if 0 <= index < len(actions):
            actions[index].setChecked(True)


class GeosDatePicker(QWidget):
    def __init__(self):
        super().__init__()
        self._date = QDate.currentDate()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.button = QToolButton()
        self.button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.button.setStyleSheet(
            f"""
            QToolButton {{
                background-color: {theme.SHELL_PANEL_ALT};
                color: {theme.TEXT_PRIMARY};
                border: 2px solid {theme.SHELL_BORDER};
                border-radius: 8px;
                padding: 8px 34px 8px 10px;
                text-align: left;
                font-family: {theme.MONO_FONT};
                font-size: 13px;
            }}
            QToolButton:hover {{
                border: 2px solid {theme.TEXT_SECONDARY};
                background-color: {theme.SHELL_PANEL_ALT};
            }}
            QToolButton:pressed {{
                background-color: {theme.BUTTON_ACTIVE};
                border: 2px solid {theme.TEXT_PRIMARY};
            }}
            QToolButton::menu-indicator {{
                image: url("{CHEVRON_ICON}");
                subcontrol-origin: padding;
                subcontrol-position: right center;
                right: 10px;
            }}
            """
        )
        self.calendar = QCalendarWidget()
        self.popup = QFrame(None, Qt.Popup)
        self.popup.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.SHELL_PANEL_ALT};
                border: 1px solid {theme.SHELL_BORDER};
                border-radius: 10px;
            }}
            """
        )
        popup_layout = QVBoxLayout(self.popup)
        popup_layout.setContentsMargins(6, 6, 6, 6)
        popup_layout.addWidget(self.calendar)

        self.button.clicked.connect(self.toggle_popup)
        self.calendar.clicked.connect(self._on_date_chosen)
        self.calendar.activated.connect(self._on_date_chosen)

        layout.addWidget(self.button)
        self.setDate(self._date)

    def _sync_calendar(self):
        self.calendar.setSelectedDate(self._date)

    def toggle_popup(self):
        if self.popup.isVisible():
            self.popup.hide()
            return
        self._sync_calendar()
        popup_pos = self.button.mapToGlobal(self.button.rect().bottomLeft())
        self.popup.move(popup_pos)
        self.popup.show()
        self.popup.raise_()
        self.popup.activateWindow()

    def _on_date_chosen(self, selected_date):
        self.setDate(selected_date)
        QTimer.singleShot(0, self.popup.hide)

    def date(self):
        return self._date

    def setDate(self, date_value):
        if isinstance(date_value, QDate) and date_value.isValid():
            self._date = date_value
            self.calendar.setSelectedDate(date_value)
            self.button.setText(date_value.toString("dd MMM yyyy"))


class CalendarAppPage(QWidget):
    def __init__(self):
        super().__init__()
        self._events = load_events()
        self._selected_event_index = None
        self._calendar_scroll_targets = set()
        self._active_date = QDate.currentDate()
        self._highlighted_event_dates = set()

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
                padding-top: 12px;
                padding-bottom: 8px;
            }}
            QLineEdit, QTimeEdit, QComboBox, QPlainTextEdit {{
                background-color: {theme.SHELL_PANEL_ALT};
                color: {theme.TEXT_PRIMARY};
                border: 2px solid {theme.SHELL_BORDER};
                border-radius: 8px;
                padding: 8px 34px 8px 10px;
            }}
            QComboBox:hover, QTimeEdit:hover, QLineEdit:hover, QPlainTextEdit:hover {{
                border: 2px solid {theme.TEXT_SECONDARY};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border-left: 1px solid {theme.SHELL_BORDER};
                background-color: {theme.BUTTON_BG};
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
            QComboBox::down-arrow {{
                image: url("{CHEVRON_ICON}");
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme.SHELL_PANEL_ALT};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.SHELL_BORDER};
                selection-background-color: {theme.BUTTON_ACTIVE};
                selection-color: {theme.TEXT_PRIMARY};
                outline: 0;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {theme.BUTTON_ACTIVE};
                color: {theme.TEXT_PRIMARY};
            }}
            QListWidget {{
                background-color: {theme.SHELL_BG};
                color: {theme.TEXT_PRIMARY};
                border: 2px solid {theme.TEXT_SECONDARY};
                border-radius: 10px;
                padding: 6px;
            }}
            QListWidget::item {{
                border-bottom: 1px solid {theme.SHELL_BORDER};
                padding: 8px 6px;
            }}
            QListWidget::item:selected {{
                background-color: {theme.BUTTON_ACTIVE};
                color: {theme.TEXT_PRIMARY};
            }}
            QCalendarWidget QWidget {{
                alternate-background-color: {theme.SHELL_PANEL_ALT};
            }}
            QCalendarWidget QTableView {{
                background-color: {theme.SHELL_BG};
                color: {theme.TEXT_PRIMARY};
                selection-background-color: {theme.BUTTON_ACTIVE};
                selection-color: {theme.TEXT_PRIMARY};
                alternate-background-color: {theme.SHELL_PANEL_ALT};
                gridline-color: {theme.SHELL_BORDER};
                outline: 0;
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                color: {theme.TEXT_PRIMARY};
                background-color: {theme.SHELL_BG};
                selection-background-color: {theme.BUTTON_ACTIVE};
                selection-color: {theme.TEXT_PRIMARY};
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {theme.BUTTON_BG};
            }}
            QCalendarWidget QToolButton {{
                background-color: {theme.BUTTON_BG};
                color: {theme.TEXT_PRIMARY};
                border: 2px solid {theme.SHELL_BORDER};
                border-bottom: 4px solid #051f1c;
                border-radius: 8px;
                padding: 6px 8px;
                font-weight: bold;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: {theme.BUTTON_HOVER};
                border: 2px solid {theme.TEXT_SECONDARY};
                border-bottom: 4px solid #051f1c;
            }}
            QCalendarWidget QComboBox, QCalendarWidget QSpinBox {{
                background-color: {theme.SHELL_PANEL_ALT};
                color: {theme.TEXT_PRIMARY};
                border: 2px solid {theme.SHELL_BORDER};
                border-radius: 8px;
                padding: 6px 30px 6px 10px;
            }}
            QCalendarWidget QComboBox:hover, QCalendarWidget QSpinBox:hover {{
                border: 2px solid {theme.TEXT_SECONDARY};
            }}
            QCalendarWidget QComboBox::drop-down, QCalendarWidget QSpinBox::down-button {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border-left: 1px solid {theme.SHELL_BORDER};
                background-color: {theme.BUTTON_BG};
            }}
            QCalendarWidget QComboBox::down-arrow {{
                image: url("{CHEVRON_ICON}");
            }}
            QCalendarWidget QComboBox QAbstractItemView {{
                background-color: {theme.SHELL_PANEL_ALT};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.SHELL_BORDER};
                selection-background-color: {theme.BUTTON_ACTIVE};
                selection-color: {theme.TEXT_PRIMARY};
                outline: 0;
            }}
            QCalendarWidget QComboBox QAbstractItemView::item:hover {{
                background-color: {theme.BUTTON_ACTIVE};
                color: {theme.TEXT_PRIMARY};
            }}
            QCalendarWidget QMenu {{
                background-color: {theme.SHELL_PANEL_ALT};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.SHELL_BORDER};
            }}
            QCalendarWidget QMenu::item:selected {{
                background-color: {theme.BUTTON_ACTIVE};
                color: {theme.TEXT_PRIMARY};
            }}
            QCalendarWidget QMenu::item:hover {{
                background-color: {theme.BUTTON_ACTIVE};
                color: {theme.TEXT_PRIMARY};
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
        QScroller.grabGesture(self.scroll.viewport(), QScroller.TouchGesture)
        outer.addWidget(self.scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("CALENDAR")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        subtitle = QLabel("Gregorian calendar with events, descriptions, notification lead times, and local device-clock scheduling.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.status_label = QLabel("Using GeOS local system time for scheduling.")
        self.status_label.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_SECONDARY};")
        layout.addWidget(self.status_label)

        self.calendar_frame = QFrame()
        self.calendar_frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border: 2px solid {theme.TEXT_SECONDARY};
                border-radius: 12px;
            }}
            """
        )
        calendar_layout = QVBoxLayout(self.calendar_frame)
        calendar_layout.setContentsMargins(12, 12, 12, 12)
        calendar_layout.setSpacing(10)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.setSelectionMode(QCalendarWidget.NoSelection)
        self.calendar.clicked.connect(self._on_calendar_date_chosen)
        self.calendar.activated.connect(self._on_calendar_date_chosen)
        self.calendar.currentPageChanged.connect(self._on_calendar_page_changed)
        calendar_layout.addWidget(self.calendar)
        layout.addWidget(self.calendar_frame)

        self.form_frame = QFrame()
        self.form_frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border: 2px solid {theme.SHELL_BORDER};
                border-radius: 12px;
            }}
            """
        )
        form_layout = QVBoxLayout(self.form_frame)
        form_layout.setContentsMargins(14, 14, 14, 14)
        form_layout.setSpacing(10)

        form_title = QLabel("Event Editor")
        form_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {theme.TEXT_SECONDARY};")
        form_layout.addWidget(form_title)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Event title")
        self.description_input = QPlainTextEdit()
        self.description_input.setPlaceholderText("Event description")
        self.description_input.setFixedHeight(100)
        self.date_input = GeosDatePicker()
        self.date_input.setDate(QDate.currentDate())
        self.time_input = QTimeEdit()
        self.time_input.setDisplayFormat("hh:mm AP")
        self.time_input.setTime(QTime.currentTime())
        self.notify_input = GeosOptionPicker(NOTIFY_OPTIONS, min_width=220)

        form_layout.addWidget(self.title_input)
        form_layout.addWidget(self.description_input)

        dt_row = QHBoxLayout()
        dt_row.addWidget(self.date_input)
        dt_row.addWidget(self.time_input)
        form_layout.addLayout(dt_row)
        form_layout.addWidget(self.notify_input)

        action_row = QHBoxLayout()
        self.add_button = QPushButton("Add Event")
        self.update_button = QPushButton("Update Selected")
        self.delete_button = QPushButton("Delete Selected")
        self.add_button.clicked.connect(self.add_event)
        self.update_button.clicked.connect(self.update_selected_event)
        self.delete_button.clicked.connect(self.delete_selected_event)
        action_row.addWidget(self.add_button)
        action_row.addWidget(self.update_button)
        action_row.addWidget(self.delete_button)
        form_layout.addLayout(action_row)
        layout.addWidget(self.form_frame)

        events_title = QLabel("Scheduled Events")
        events_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {theme.TEXT_SECONDARY};")
        layout.addWidget(events_title)

        self.events_list = QListWidget()
        self.events_list.itemSelectionChanged.connect(self.populate_selected_event)
        layout.addWidget(self.events_list)

        layout.addStretch()

        self._configure_calendar_widgets()
        self._configure_popup_calendar(self.date_input.calendar)
        self._fit_main_calendar_height()
        QTimer.singleShot(0, self._fit_main_calendar_height)
        self.highlight_event_dates()
        self.refresh_event_list()

        self.notification_timer = QTimer(self)
        self.notification_timer.timeout.connect(self.check_notifications)
        self.notification_timer.start(30000)
        self.check_notifications()

    def _configure_calendar_widgets(self):
        nav_style = (
            f"background-color: {theme.BUTTON_BG};"
            f"color: {theme.TEXT_PRIMARY};"
            f"border: 2px solid {theme.SHELL_BORDER};"
            "border-bottom: 4px solid #051f1c;"
            "border-radius: 8px;"
            "padding: 4px 8px;"
            "font-weight: bold;"
        )

        prev_btn = self.calendar.findChild(QToolButton, "qt_calendar_prevmonth")
        next_btn = self.calendar.findChild(QToolButton, "qt_calendar_nextmonth")
        month_btn = self.calendar.findChild(QToolButton, "qt_calendar_monthbutton")
        year_btn = self.calendar.findChild(QToolButton, "qt_calendar_yearbutton")
        year_edit = self.calendar.findChild(QSpinBox, "qt_calendar_yearedit")
        table = self.calendar.findChild(QTableView)

        for btn, label in ((prev_btn, "<"), (next_btn, ">")):
            if btn is not None:
                btn.setArrowType(Qt.NoArrow)
                btn.setText(label)
                btn.setStyleSheet(nav_style + f"color: {theme.TEXT_SECONDARY};")

        for btn in (month_btn, year_btn):
            if btn is not None:
                btn.setStyleSheet(nav_style)
                menu = btn.menu()
                if menu is not None:
                    menu.setStyleSheet(
                        f"""
                        QMenu {{
                            background-color: {theme.SHELL_PANEL_ALT};
                            color: {theme.TEXT_PRIMARY};
                            border: 1px solid {theme.SHELL_BORDER};
                        }}
                        QMenu::item {{
                            background-color: transparent;
                            color: {theme.TEXT_PRIMARY};
                            padding: 6px 12px;
                        }}
                        QMenu::item:selected {{
                            background-color: {theme.BUTTON_ACTIVE};
                            color: {theme.TEXT_PRIMARY};
                        }}
                        """
                    )

        if year_edit is not None:
            year_edit.setStyleSheet(
                f"""
                QSpinBox {{
                    background-color: {theme.SHELL_PANEL_ALT};
                    color: {theme.TEXT_PRIMARY};
                    border: 2px solid {theme.SHELL_BORDER};
                    border-radius: 8px;
                    padding: 4px 8px;
                }}
                QSpinBox::up-button, QSpinBox::down-button {{
                    background-color: {theme.BUTTON_BG};
                    border-left: 1px solid {theme.SHELL_BORDER};
                    width: 18px;
                }}
                """
            )

        if table is not None:
            palette = table.palette()
            palette.setColor(QPalette.Base, QColor(theme.SHELL_BG))
            palette.setColor(QPalette.Text, QColor(theme.TEXT_PRIMARY))
            palette.setColor(QPalette.WindowText, QColor(theme.TEXT_PRIMARY))
            palette.setColor(QPalette.ButtonText, QColor(theme.TEXT_PRIMARY))
            palette.setColor(QPalette.Highlight, QColor(theme.BUTTON_ACTIVE))
            palette.setColor(QPalette.HighlightedText, QColor(theme.TEXT_PRIMARY))
            table.setPalette(palette)
            table.viewport().setAutoFillBackground(True)
            table.setStyleSheet(
                f"""
                QTableView {{
                    background-color: {theme.SHELL_BG};
                    color: {theme.TEXT_PRIMARY};
                    selection-background-color: {theme.BUTTON_ACTIVE};
                    selection-color: {theme.TEXT_PRIMARY};
                    gridline-color: {theme.SHELL_BORDER};
                    alternate-background-color: {theme.SHELL_PANEL_ALT};
                }}
                QHeaderView::section {{
                    background-color: {theme.BUTTON_BG};
                    color: {theme.TEXT_PRIMARY};
                    border: 1px solid {theme.SHELL_BORDER};
                    padding: 4px;
                }}
                """
            )

            self._install_calendar_scroll_redirect(table)

    def _configure_popup_calendar(self, popup_calendar):
        nav_style = (
            f"background-color: {theme.BUTTON_BG};"
            f"color: {theme.TEXT_PRIMARY};"
            f"border: 2px solid {theme.SHELL_BORDER};"
            "border-bottom: 4px solid #051f1c;"
            "border-radius: 8px;"
            "padding: 4px 8px;"
            "font-weight: bold;"
        )

        popup_calendar.setGridVisible(True)
        popup_calendar.setStyleSheet(
            f"""
            QCalendarWidget QWidget {{
                alternate-background-color: {theme.SHELL_PANEL_ALT};
            }}
            QCalendarWidget QTableView {{
                background-color: {theme.SHELL_BG};
                color: {theme.TEXT_PRIMARY};
                selection-background-color: {theme.BUTTON_ACTIVE};
                selection-color: {theme.TEXT_PRIMARY};
                alternate-background-color: {theme.SHELL_PANEL_ALT};
                gridline-color: {theme.SHELL_BORDER};
                outline: 0;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {theme.BUTTON_BG};
            }}
            """
        )

        prev_btn = popup_calendar.findChild(QToolButton, "qt_calendar_prevmonth")
        next_btn = popup_calendar.findChild(QToolButton, "qt_calendar_nextmonth")
        month_btn = popup_calendar.findChild(QToolButton, "qt_calendar_monthbutton")
        year_btn = popup_calendar.findChild(QToolButton, "qt_calendar_yearbutton")
        year_edit = popup_calendar.findChild(QSpinBox, "qt_calendar_yearedit")
        table = popup_calendar.findChild(QTableView)

        for btn, label in ((prev_btn, "<"), (next_btn, ">")):
            if btn is not None:
                btn.setArrowType(Qt.NoArrow)
                btn.setText(label)
                btn.setStyleSheet(nav_style + f"color: {theme.TEXT_SECONDARY};")

        for btn in (month_btn, year_btn):
            if btn is not None:
                btn.setStyleSheet(nav_style)
                menu = btn.menu()
                if menu is not None:
                    menu.setStyleSheet(
                        f"""
                        QMenu {{
                            background-color: {theme.SHELL_PANEL_ALT};
                            color: {theme.TEXT_PRIMARY};
                            border: 1px solid {theme.SHELL_BORDER};
                        }}
                        QMenu::item {{
                            background-color: transparent;
                            color: {theme.TEXT_PRIMARY};
                            padding: 6px 12px;
                        }}
                        QMenu::item:selected {{
                            background-color: {theme.BUTTON_ACTIVE};
                            color: {theme.TEXT_PRIMARY};
                        }}
                        QMenu::item:hover {{
                            background-color: {theme.BUTTON_ACTIVE};
                            color: {theme.TEXT_PRIMARY};
                        }}
                        """
                    )

        if year_edit is not None:
            year_edit.setStyleSheet(
                f"""
                QSpinBox {{
                    background-color: {theme.SHELL_PANEL_ALT};
                    color: {theme.TEXT_PRIMARY};
                    border: 2px solid {theme.SHELL_BORDER};
                    border-radius: 8px;
                    padding: 4px 8px;
                }}
                QSpinBox::up-button, QSpinBox::down-button {{
                    background-color: {theme.BUTTON_BG};
                    border-left: 1px solid {theme.SHELL_BORDER};
                    width: 18px;
                }}
                """
            )

        if table is not None:
            palette = table.palette()
            palette.setColor(QPalette.Base, QColor(theme.SHELL_BG))
            palette.setColor(QPalette.Text, QColor(theme.TEXT_PRIMARY))
            palette.setColor(QPalette.WindowText, QColor(theme.TEXT_PRIMARY))
            palette.setColor(QPalette.ButtonText, QColor(theme.TEXT_PRIMARY))
            palette.setColor(QPalette.Highlight, QColor(theme.BUTTON_ACTIVE))
            palette.setColor(QPalette.HighlightedText, QColor(theme.TEXT_PRIMARY))
            table.setPalette(palette)
            table.viewport().setAutoFillBackground(True)
            table.setStyleSheet(
                f"""
                QTableView {{
                    background-color: {theme.SHELL_BG};
                    color: {theme.TEXT_PRIMARY};
                    selection-background-color: {theme.BUTTON_ACTIVE};
                    selection-color: {theme.TEXT_PRIMARY};
                    gridline-color: {theme.SHELL_BORDER};
                    alternate-background-color: {theme.SHELL_PANEL_ALT};
                }}
                QHeaderView::section {{
                    background-color: {theme.BUTTON_BG};
                    color: {theme.TEXT_PRIMARY};
                    border: 1px solid {theme.SHELL_BORDER};
                    padding: 4px;
                }}
                """
            )

    def _install_calendar_scroll_redirect(self, table):
        targets = [self.calendar, table, table.viewport()]
        for target in targets:
            if target is None:
                continue
            if target in self._calendar_scroll_targets:
                continue
            target.installEventFilter(self)
            self._calendar_scroll_targets.add(target)

    def eventFilter(self, obj, event):
        if obj in self._calendar_scroll_targets and event.type() == QEvent.Wheel:
            bar = self.scroll.verticalScrollBar()
            if bar is not None:
                delta = event.angleDelta().y()
                if delta:
                    step = bar.singleStep() * 3
                    if step <= 0:
                        step = 60
                    direction = -1 if delta > 0 else 1
                    bar.setValue(bar.value() + (direction * step))
                    return True
        return super().eventFilter(obj, event)

    def _on_calendar_page_changed(self, _year, _month):
        QTimer.singleShot(0, self._fit_main_calendar_height)

    def _fit_main_calendar_height(self):
        table = self.calendar.findChild(QTableView)
        if table is None:
            return

        model = table.model()
        if model is None:
            return

        row_count = max(model.rowCount(), 6)
        if row_count <= 0:
            return

        rows_height = sum(table.rowHeight(row) for row in range(row_count))
        header = table.horizontalHeader()
        header_height = header.height() if header is not None else 0

        nav_bar = self.calendar.findChild(QWidget, "qt_calendar_navigationbar")
        nav_height = nav_bar.sizeHint().height() if nav_bar is not None else 0

        margins = self.calendar.contentsMargins()
        frame_height = 0

        required_height = (
            nav_height
            + header_height
            + rows_height
            + margins.top()
            + margins.bottom()
            + frame_height
            + 12
        )
        min_height = max(required_height, 360)

        self.calendar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.calendar.setMinimumHeight(min_height)
        self.calendar_frame.setMinimumHeight(min_height + 24)

    def _on_calendar_date_chosen(self, date_value):
        if isinstance(date_value, QDate) and date_value.isValid():
            self._active_date = date_value
            self.refresh_event_list()
            self.clear_form()

    def refresh_event_list(self):
        selected_date = self._active_date.toString("yyyy-MM-dd")
        self.events_list.clear()
        for index, event in enumerate(self._events):
            if event["date"] != selected_date:
                continue
            notify_text = next(label for label, minutes in NOTIFY_OPTIONS if minutes == event["notify_minutes"])
            item = QListWidgetItem(
                f"{event['time']} | {event['title']}\n{event['description'] or 'No description'}\nNotify: {notify_text}"
            )
            item.setData(Qt.UserRole, index)
            self.events_list.addItem(item)
        self._selected_event_index = None
        self.update_button.setEnabled(False)

    def add_event(self):
        title = self.title_input.text().strip()
        if not title:
            self.status_label.setText("Event title is required.")
            return
        event = {
            "title": title,
            "description": self.description_input.toPlainText().strip(),
            "date": self.date_input.date().toString("yyyy-MM-dd"),
            "time": self.time_input.time().toString("HH:mm"),
            "notify_minutes": int(self.notify_input.currentData()),
            "notified_key": "",
        }
        self._events.append(event)
        save_events(self._events)
        self.status_label.setText(f"Saved event: {title}")
        self._active_date = self.date_input.date()
        self.calendar.setCurrentPage(self._active_date.year(), self._active_date.month())
        self.highlight_event_dates()
        self.refresh_event_list()
        self.clear_form()

    def update_selected_event(self):
        if self._selected_event_index is None:
            self.status_label.setText("Select an event to update.")
            return
        title = self.title_input.text().strip()
        if not title:
            self.status_label.setText("Event title is required.")
            return
        event = self._events[self._selected_event_index]
        event["title"] = title
        event["description"] = self.description_input.toPlainText().strip()
        event["date"] = self.date_input.date().toString("yyyy-MM-dd")
        event["time"] = self.time_input.time().toString("HH:mm")
        event["notify_minutes"] = int(self.notify_input.currentData())
        event["notified_key"] = ""
        save_events(self._events)
        self.status_label.setText(f"Updated event: {title}")
        self._active_date = self.date_input.date()
        self.calendar.setCurrentPage(self._active_date.year(), self._active_date.month())
        self.highlight_event_dates()
        self.refresh_event_list()
        self.clear_form()

    def delete_selected_event(self):
        item = self.events_list.currentItem()
        if item is None:
            return
        index = item.data(Qt.UserRole)
        if index is None:
            return
        title = self._events[index]["title"]
        del self._events[index]
        save_events(self._events)
        self.status_label.setText(f"Deleted event: {title}")
        self.highlight_event_dates()
        self.refresh_event_list()
        self.clear_form()

    def populate_selected_event(self):
        item = self.events_list.currentItem()
        if item is None:
            self._selected_event_index = None
            self.update_button.setEnabled(False)
            return
        index = item.data(Qt.UserRole)
        if index is None:
            self._selected_event_index = None
            self.update_button.setEnabled(False)
            return
        self._selected_event_index = index
        self.update_button.setEnabled(True)
        event = self._events[index]
        self.title_input.setText(event["title"])
        self.description_input.setPlainText(event["description"])
        self.date_input.setDate(QDate.fromString(event["date"], "yyyy-MM-dd"))
        self.time_input.setTime(QTime.fromString(event["time"], "HH:mm"))
        notify_index = next(
            (idx for idx, (_, minutes) in enumerate(NOTIFY_OPTIONS) if minutes == event["notify_minutes"]),
            0,
        )
        self.notify_input.setCurrentIndex(notify_index)

    def highlight_event_dates(self):
        default_format = QTextCharFormat()
        for date in self._highlighted_event_dates:
            self.calendar.setDateTextFormat(date, default_format)

        event_dates = set()
        event_format = QTextCharFormat()
        event_format.setBackground(QColor(theme.BUTTON_ACTIVE))
        event_format.setForeground(QColor(theme.TEXT_PRIMARY))

        for event in self._events:
            date = QDate.fromString(event["date"], "yyyy-MM-dd")
            if date.isValid():
                event_dates.add(date)
                self.calendar.setDateTextFormat(date, event_format)

        today = QDate.currentDate()
        today_format = QTextCharFormat()
        today_format.setBackground(QColor(theme.TEXT_SECONDARY))
        today_format.setForeground(QColor(theme.SHELL_BG))
        today_format.setFontWeight(700)
        self.calendar.setDateTextFormat(today, today_format)

        self._highlighted_event_dates = event_dates

    def clear_form(self):
        self.title_input.clear()
        self.description_input.clear()
        self.date_input.setDate(self._active_date)
        self.time_input.setTime(QTime.currentTime())
        self.notify_input.setCurrentIndex(0)
        self._selected_event_index = None
        self.update_button.setEnabled(False)

    def check_notifications(self):
        now = datetime.datetime.now()
        for event in self._events:
            try:
                event_time = datetime.datetime.strptime(f"{event['date']} {event['time']}", "%Y-%m-%d %H:%M")
            except Exception:
                continue
            notify_time = event_time - datetime.timedelta(minutes=int(event.get("notify_minutes", 0)))
            notify_key = notify_time.strftime("%Y-%m-%d %H:%M")
            current_key = now.strftime("%Y-%m-%d %H:%M")
            if current_key == notify_key and event.get("notified_key") != notify_key:
                event["notified_key"] = notify_key
                save_events(self._events)
                self.status_label.setText(f"Reminder: {event['title']} at {event['time']}")
                QApplication.beep()
