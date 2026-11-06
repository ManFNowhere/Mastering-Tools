import sys
import os
import platform


def _user_data_dir():
    """OS-appropriate directory for user-writable app data (settings.json)."""
    if platform.system() == "Darwin":
        return os.path.expanduser("~/Library/Application Support/SS-Mastering")
    elif platform.system() == "Windows":
        return os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")), "SS-Mastering"
        )
    else:
        return os.path.expanduser("~/.config/SS-Mastering")


if getattr(sys, "frozen", False):
    # Bundled: read-only data files (lang.json, assets) live in sys._MEIPASS
    os.chdir(sys._MEIPASS)
    # User-writable data (settings.json) → OS user data directory
    _ud = _user_data_dir()
    os.makedirs(_ud, exist_ok=True)
    os.environ["SS_USERDATA"] = _ud
else:
    # Development: everything lives next to main.py
    os.environ.setdefault("SS_USERDATA", os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from ui_main import MasteringApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Helvetica Neue", 13))
    window = MasteringApp()
    window.show()
    sys.exit(app.exec())