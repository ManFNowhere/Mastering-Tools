import sys
import os

# When bundled with PyInstaller (--onedir), set CWD to the executable's
# directory so relative paths (lang.json, settings.json) resolve correctly.
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from ui_main import MasteringApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Helvetica Neue", 13))
    window = MasteringApp()
    window.show()
    sys.exit(app.exec())