from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QAction, QIcon

class Tray:
    def __init__(self, icon, on_toggle, on_exit):
        self.tray = QSystemTrayIcon(QIcon(icon))
        menu = QMenu()

        toggle = QAction("Start / Stop")
        toggle.triggered.connect(on_toggle)
        exit_ = QAction("Exit")
        exit_.triggered.connect(on_exit)

        menu.addAction(toggle)
        menu.addAction(exit_)
        self.tray.setContextMenu(menu)
        self.tray.show()

    def set_running(self, running):
        self.tray.setToolTip(
            "Multi Clicker – RUNNING 🟢" if running else "Multi Clicker – STOPPED 🔴"
        )
