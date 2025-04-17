import sys
from PySide6.QtWidgets import QApplication
from ui_main import MasteringApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MasteringApp()
    window.show()
    sys.exit(app.exec())