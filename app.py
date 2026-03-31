"""
PhoneFlash PC — application object.
Handles resource paths for both .py and .exe modes.
"""
import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from core.settings_manager import SettingsManager
from ui.main_window import MainWindow
from ui.theme import apply_theme

IS_FROZEN = getattr(sys, "frozen", False)


def resource_path(relative: str) -> str:
    """
    Returns absolute path to a resource.
    Works in both dev (.py) and packaged (.exe) modes.

    In .exe mode (PyInstaller onedir):
      sys._MEIPASS = temp extraction dir (contains resources/)
      sys.executable dir = where PhoneFlash.exe lives
    """
    if IS_FROZEN:
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative)


def exe_dir() -> str:
    """Directory where the .exe lives (for writable files like settings.json)."""
    if IS_FROZEN:
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


class PhoneFlashApp:
    def __init__(self, argv):
        self._app = QApplication(argv)
        self._app.setApplicationName("PhoneFlash")
        self._app.setOrganizationName("PhoneFlash")

        # Icon
        icon_path = resource_path(os.path.join("resources", "PhoneFlash.ico"))
        if os.path.isfile(icon_path):
            self._app.setWindowIcon(QIcon(icon_path))

        # Settings — writable, so stored next to .exe (not inside _MEIPASS)
        settings_path = os.path.join(exe_dir(), "settings.json")
        self.settings = SettingsManager(settings_path)

        # Theme
        theme_name = self.settings.get("theme", "dark")
        apply_theme(self._app, theme_name)

        # Main window
        self._window = MainWindow(self._app, self.settings)

    def run(self) -> int:
        self._window.show()
        return self._app.exec()