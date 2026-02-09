# gui/main_window.py

from PySide6.QtWidgets import QWidget, QHBoxLayout, QStackedWidget
from PySide6.QtCore import Qt, QPropertyAnimation, QPoint, QEasingCurve

from gui.nav_bar import NavBar
from gui.pages.home import HomePage
from gui.pages.sensors import SensorsPage
from gui.pages.control import ControlPage
from gui.pages.ai import AIPage
from gui.pages.settings import SettingsPage
from gui.splash_widget import SplashWidget
from gui import theme


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("GeOS")
        self.setFixedSize(1024, 600)
        self.setStyleSheet(f"background-color: {theme.BACKGROUND};")

        layout = QHBoxLayout(self)

        self.nav = NavBar()
        self.stack = QStackedWidget()

        # Splash screen (boot phase)
        self.splash = SplashWidget()
        self.splash.boot_finished.connect(self.finish_boot)
        self.stack.addWidget(self.splash)

        # Main pages
        self.pages = {
            "home": HomePage(),
            "sensors": SensorsPage(),
            "control": ControlPage(),
            "ai": AIPage(),
            "settings": SettingsPage()
        }

        for page in self.pages.values():
            self.stack.addWidget(page)

        self.nav.page_selected.connect(self.switch_page)

        layout.addWidget(self.nav)
        layout.addWidget(self.stack)

        # Initial boot state
        self.nav.hide()
        self.stack.setCurrentWidget(self.splash)

    def animate_page(self, widget):
        start_pos = widget.pos()
        widget.move(start_pos.x() + 40, start_pos.y())

        self.anim = QPropertyAnimation(widget, b"pos")
        self.anim.setDuration(220)
        self.anim.setStartValue(QPoint(start_pos.x() + 40, start_pos.y()))
        self.anim.setEndValue(start_pos)
        self.anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.anim.start()

    def finish_boot(self):
        self.nav.show()
        self.switch_page("home")

    def switch_page(self, page_name):
        page = self.pages[page_name]
        self.stack.setCurrentWidget(page)
        self.animate_page(page)
