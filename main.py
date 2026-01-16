import platform
if platform.system() == "Windows":
    import ctypes
    ctypes.windll.user32.SetProcessDPIAware()
    # High resolution timer
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
    except:
        pass

import sys
from PySide6.QtWidgets import QApplication
from ui.styles import DARK_STYLE
from core.profile_manager import ProfileManager
from macro.manager import MacroManager
from ui.main_window import MainWindow
from core.controller import Controller
from core.logging_setup import get_logger
from core.app_state import AppState

log = get_logger("main")
log.info("Application starting")

app = QApplication(sys.argv)
app.setStyleSheet(DARK_STYLE)

profile_manager = ProfileManager()
macro_manager = MacroManager()
profile = profile_manager.load("default")

app_state = AppState()
app_state.active_profile = profile

window = MainWindow(profile, profile_manager, macro_manager)
controller = Controller(window, app_state, profile_manager, macro_manager)

window.start.clicked.connect(controller.toggle)
window.show()

log.info("UI shown")
sys.exit(app.exec())
