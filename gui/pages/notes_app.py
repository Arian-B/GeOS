import json
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextOption
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QScroller,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NOTES_FILE = os.path.join(BASE_DIR, "state", "notes.json")


def load_notes():
    try:
        with open(NOTES_FILE, "r") as handle:
            data = json.load(handle)
        if isinstance(data, list) and data:
            normalized = []
            for item in data:
                if isinstance(item, dict):
                    normalized.append(
                        {
                            "title": str(item.get("title") or "Note"),
                            "content": str(item.get("content") or ""),
                        }
                    )
            if normalized:
                return normalized
    except Exception:
        pass
    return [{"title": "Note 1", "content": ""}]


def save_notes(notes):
    os.makedirs(os.path.dirname(NOTES_FILE), exist_ok=True)
    with open(NOTES_FILE, "w") as handle:
        json.dump(notes, handle, indent=2)


class NotesEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.NoFrame)
        self.setPlaceholderText("Write notes here...")
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.setStyleSheet(
            f"""
            QPlainTextEdit {{
                background-color: {theme.SHELL_BG};
                color: {theme.TEXT_PRIMARY};
                border: none;
                padding: 14px 16px;
                font-family: {theme.MONO_FONT};
                font-size: 16px;
            }}
            """
        )


class NotesAppPage(QWidget):
    def __init__(self):
        super().__init__()
        self._notes = load_notes()
        self._editors = []

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
            QTabBar::tab {{
                background-color: {theme.BUTTON_BG};
                color: {theme.TEXT_PRIMARY};
                border: 2px solid {theme.SHELL_BORDER};
                border-bottom: 4px solid #051f1c;
                border-radius: 8px;
                padding: 8px 14px;
                margin-right: 6px;
                min-width: 100px;
            }}
            QTabBar::tab:selected {{
                background-color: {theme.BUTTON_ACTIVE};
                border: 2px solid {theme.TEXT_SECONDARY};
                border-bottom: 4px solid #051f1c;
            }}
            QTabWidget::pane {{
                border: none;
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

        title_row = QHBoxLayout()
        title = QLabel("NOTES")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.delete_button = QPushButton("Delete Note")
        self.delete_button.clicked.connect(self.delete_current_note)
        self.add_button = QPushButton("+")
        self.add_button.setFixedWidth(52)
        self.add_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {theme.BUTTON_ACTIVE};
                color: {theme.TEXT_PRIMARY};
                border: 2px solid {theme.TEXT_SECONDARY};
                border-bottom: 4px solid #051f1c;
                border-radius: 8px;
                font-size: 24px;
                font-weight: bold;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background-color: {theme.BUTTON_HOVER};
                border: 2px solid {theme.TEXT_PRIMARY};
                border-bottom: 4px solid #051f1c;
            }}
            QPushButton:pressed {{
                background-color: {theme.BUTTON_HOVER};
                border: 2px solid {theme.TEXT_PRIMARY};
                border-bottom: 2px solid #051f1c;
                padding-top: 6px;
                padding-bottom: 2px;
            }}
            """
        )
        self.add_button.clicked.connect(self.add_note)
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self.delete_button)
        title_row.addWidget(self.add_button)
        layout.addLayout(title_row)

        subtitle = QLabel("Field notes, reminders, and quick observations. Add as many notes as you need.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        layout.addWidget(subtitle)

        self.note_frame = QFrame()
        self.note_frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.SHELL_BG};
                border: 2px solid {theme.TEXT_SECONDARY};
                border-radius: 12px;
            }}
            """
        )
        frame_layout = QVBoxLayout(self.note_frame)
        frame_layout.setContentsMargins(10, 10, 10, 10)
        frame_layout.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.South)
        self.tabs.setDocumentMode(True)
        self.tabs.currentChanged.connect(self.sync_titles)
        frame_layout.addWidget(self.tabs)
        layout.addWidget(self.note_frame)
        layout.addStretch()

        for note in self._notes:
            self._create_note_tab(note["title"], note["content"])

    def _create_note_tab(self, title, content):
        editor = NotesEditor()
        editor.setPlainText(content)
        editor.textChanged.connect(self.persist_notes)
        self._editors.append(editor)
        self.tabs.addTab(editor, title)

    def add_note(self):
        note_number = self.tabs.count() + 1
        title = f"Note {note_number}"
        self._notes.append({"title": title, "content": ""})
        self._create_note_tab(title, "")
        self.tabs.setCurrentIndex(self.tabs.count() - 1)
        self.persist_notes()

    def delete_current_note(self):
        if self.tabs.count() <= 1:
            return
        index = self.tabs.currentIndex()
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        if widget is not None:
            widget.deleteLater()
        del self._notes[index]
        self.persist_notes()

    def sync_titles(self):
        for index in range(self.tabs.count()):
            self.tabs.setTabText(index, self._notes[index]["title"])

    def persist_notes(self):
        notes = []
        for index in range(self.tabs.count()):
            editor = self.tabs.widget(index)
            notes.append(
                {
                    "title": self.tabs.tabText(index),
                    "content": editor.toPlainText() if isinstance(editor, QPlainTextEdit) else "",
                }
            )
        self._notes = notes
        save_notes(self._notes)
