import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PCReader")
    
    window = MainWindow()
    window.resize(920, 700)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
