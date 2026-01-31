# gui/main_window.py

from PySide6.QtWidgets import QWidget, QHBoxLayout, QStackedWidget
from PySide6.QtCore import QTimer

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

        # Pages
        self.pages = {
            "home": HomePage(),
            "sensors": SensorsPage(),
            "control": ControlPage(),
            "ai": AIPage(),
            "settings": SettingsPage()
        }

        # Splash
        self.splash = SplashWidget()
        self.stack.addWidget(self.splash)

        for page in self.pages.values():
            self.stack.addWidget(page)

        self.nav.page_selected.connect(self.switch_page)

        layout.addWidget(self.nav)
        layout.addWidget(self.stack)

        # Boot state
        self.nav.hide()
        self.stack.setCurrentWidget(self.splash)

        # End splash after 3 seconds
        QTimer.singleShot(3000, self.finish_boot)

    def finish_boot(self):
        self.nav.show()
        self.switch_page("home")

    def switch_page(self, page_name):
        self.stack.setCurrentWidget(self.pages[page_name])
