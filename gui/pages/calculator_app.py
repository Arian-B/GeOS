import math

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QScroller,
    QVBoxLayout,
    QWidget,
)

from gui import theme


SAFE_FUNCTIONS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sqrt": math.sqrt,
    "log": math.log10,
    "ln": math.log,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "pi": math.pi,
    "e": math.e,
}


class CalculatorAppPage(QWidget):
    def __init__(self):
        super().__init__()
        self.expression = ""
        self._scientific_visible = False
        self._scientific_animation = None

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
                border-radius: 8px;
                padding: 12px 14px;
            }}
            QPushButton:hover {{
                background-color: {theme.BUTTON_HOVER};
                border: 2px solid {theme.TEXT_SECONDARY};
            }}
            QPushButton:pressed {{
                background-color: {theme.BUTTON_ACTIVE};
                border: 2px solid {theme.TEXT_PRIMARY};
                padding-top: 14px;
                padding-bottom: 10px;
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
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("CALCULATOR")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        subtitle = QLabel("Quick farm math with a normal calculator and an expandable scientific panel.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.mode_button = QPushButton("Open Scientific Panel")
        self.mode_button.setStyleSheet(self.mode_button.styleSheet() + "font-size: 17px; font-weight: bold;")
        self.mode_button.clicked.connect(self.toggle_mode)
        layout.addWidget(self.mode_button)

        display_frame = QFrame()
        display_frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border: 2px solid {theme.SHELL_BORDER};
                border-radius: 12px;
            }}
            """
        )
        display_layout = QVBoxLayout(display_frame)
        display_layout.setContentsMargins(18, 16, 18, 16)
        display_layout.setSpacing(8)

        self.mode_label = QLabel("NORMAL CALCULATOR")
        self.mode_label.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme.TEXT_SECONDARY};")
        self.expression_label = QLabel("0")
        self.expression_label.setWordWrap(True)
        self.expression_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.expression_label.setStyleSheet("font-size: 20px; color: #B9DED0;")
        self.result_label = QLabel("0")
        self.result_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.result_label.setStyleSheet("font-size: 38px; font-weight: bold;")
        display_layout.addWidget(self.mode_label)
        display_layout.addWidget(self.expression_label)
        display_layout.addWidget(self.result_label)
        layout.addWidget(display_frame)

        normal_frame = QFrame()
        normal_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        normal_grid = QGridLayout(normal_frame)
        normal_grid.setContentsMargins(0, 0, 0, 0)
        normal_grid.setHorizontalSpacing(10)
        normal_grid.setVerticalSpacing(10)

        buttons = [
            ("C", self.clear_expression),
            ("⌫", self.backspace),
            ("(", lambda: self.append_token("(")),
            (")", lambda: self.append_token(")")),
            ("7", lambda: self.append_token("7")),
            ("8", lambda: self.append_token("8")),
            ("9", lambda: self.append_token("9")),
            ("÷", lambda: self.append_token("/")),
            ("4", lambda: self.append_token("4")),
            ("5", lambda: self.append_token("5")),
            ("6", lambda: self.append_token("6")),
            ("×", lambda: self.append_token("*")),
            ("1", lambda: self.append_token("1")),
            ("2", lambda: self.append_token("2")),
            ("3", lambda: self.append_token("3")),
            ("-", lambda: self.append_token("-")),
            ("0", lambda: self.append_token("0")),
            (".", lambda: self.append_token(".")),
            ("=", self.evaluate_expression),
            ("+", lambda: self.append_token("+")),
        ]

        for index, (label, handler) in enumerate(buttons):
            button = self._make_key_button(label, height=66)
            button.clicked.connect(handler)
            normal_grid.addWidget(button, index // 4, index % 4)
        layout.addWidget(normal_frame)

        self.scientific_panel = QFrame()
        self.scientific_panel.setMaximumHeight(0)
        self.scientific_panel.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.SHELL_PANEL_ALT};
                border: 2px solid {theme.SHELL_BORDER};
                border-radius: 12px;
            }}
            """
        )
        scientific_layout = QVBoxLayout(self.scientific_panel)
        scientific_layout.setContentsMargins(16, 14, 16, 16)
        scientific_layout.setSpacing(10)

        info = QLabel("Scientific tools")
        info.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {theme.TEXT_SECONDARY};")
        hint = QLabel("Functions, constants, and exponent controls for more detailed calculations.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_MUTED};")
        scientific_layout.addWidget(info)
        scientific_layout.addWidget(hint)

        scientific_grid = QGridLayout()
        scientific_grid.setHorizontalSpacing(10)
        scientific_grid.setVerticalSpacing(10)
        scientific_layout.addLayout(scientific_grid)

        scientific_buttons = [
            ("sin", lambda: self.append_token("sin(")),
            ("cos", lambda: self.append_token("cos(")),
            ("tan", lambda: self.append_token("tan(")),
            ("sqrt", lambda: self.append_token("sqrt(")),
            ("log", lambda: self.append_token("log(")),
            ("ln", lambda: self.append_token("ln(")),
            ("pi", lambda: self.append_token("pi")),
            ("e", lambda: self.append_token("e")),
            ("x²", lambda: self.append_token("**2")),
            ("^", lambda: self.append_token("^")),
            ("abs", lambda: self.append_token("abs(")),
            ("exp", lambda: self.append_token("exp(")),
        ]

        for index, (label, handler) in enumerate(scientific_buttons):
            button = self._make_key_button(label, height=58)
            button.clicked.connect(handler)
            scientific_grid.addWidget(button, index // 4, index % 4)

        layout.addWidget(self.scientific_panel)
        layout.addStretch()

        self._refresh_display()

    def _make_key_button(self, label, height):
        button = QPushButton(label)
        button.setMinimumHeight(height)
        button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {theme.BUTTON_BG};
                color: {theme.TEXT_PRIMARY};
                border: 2px solid {theme.SHELL_BORDER};
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 24px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme.BUTTON_HOVER};
                border: 2px solid {theme.TEXT_SECONDARY};
            }}
            QPushButton:pressed {{
                background-color: {theme.BUTTON_ACTIVE};
                border: 2px solid {theme.TEXT_PRIMARY};
                padding-top: 12px;
                padding-bottom: 8px;
            }}
            """
        )
        return button

    def toggle_mode(self):
        self._scientific_visible = not self._scientific_visible
        target_height = self.scientific_panel.sizeHint().height() if self._scientific_visible else 0

        animation = QPropertyAnimation(self.scientific_panel, b"maximumHeight", self)
        animation.setDuration(200)
        animation.setStartValue(self.scientific_panel.maximumHeight())
        animation.setEndValue(target_height)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        self._scientific_animation = animation
        self._scientific_animation.start()

        self.mode_label.setText("SCIENTIFIC CALCULATOR" if self._scientific_visible else "NORMAL CALCULATOR")
        self.mode_button.setText("Close Scientific Panel" if self._scientific_visible else "Open Scientific Panel")

    def append_token(self, token):
        if self.expression == "Error":
            self.expression = ""
        self.expression += token
        self._refresh_display()

    def clear_expression(self):
        self.expression = ""
        self._refresh_display()

    def backspace(self):
        self.expression = self.expression[:-1]
        self._refresh_display()

    def evaluate_expression(self):
        if not self.expression.strip():
            return
        prepared = self.expression.replace("^", "**").replace("÷", "/").replace("×", "*")
        try:
            result = eval(prepared, {"__builtins__": {}}, SAFE_FUNCTIONS)
        except Exception:
            self.expression = "Error"
            self.expression_label.setText("Invalid expression")
            self.result_label.setText("Error")
            return

        if isinstance(result, float):
            result_text = f"{result:.8f}".rstrip("0").rstrip(".")
        else:
            result_text = str(result)
        self.expression = result_text
        self._refresh_display()

    def _refresh_display(self):
        value = self.expression or "0"
        self.expression_label.setText(value)
        self.result_label.setText(value)
