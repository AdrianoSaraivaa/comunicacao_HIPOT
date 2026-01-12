import sys
from PySide6.QtWidgets import QApplication
from gui import HipotWindow


def main():
    app = QApplication(sys.argv)
    window = HipotWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
