import ctypes
ctypes.windll.user32.SetProcessDPIAware()

import sys
from PySide6.QtWidgets import QApplication
from styles import DARK_STYLE
from config import load_profile
from gui import MainWindow
from controller import Controller
from logging_setup import get_logger

log = get_logger("main")
log.info("Application starting")

profile = load_profile("default")

app = QApplication(sys.argv)
app.setStyleSheet(DARK_STYLE)

window = MainWindow(profile)
controller = Controller(window, profile)

window.start.clicked.connect(controller.toggle)
window.show()

log.info("UI shown")
sys.exit(app.exec())
