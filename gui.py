# gui.py
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt
from config import save_profile
from picker import PointPicker
from logging_setup import get_logger

log = get_logger("gui")

class MainWindow(QWidget):
    def __init__(self, profile):
        super().__init__()
        self.setWindowTitle("Multi Clicker")
        self.setFixedSize(420, 620)
        self.profile_name = profile["name"]

        self.tabs = QTabWidget(self)
        self.click_tab = QWidget()
        self.settings_tab = QWidget()

        self.tabs.addTab(self.click_tab, "Clicking")
        self.tabs.addTab(self.settings_tab, "Settings")

        self._build_click_tab(profile)
        self._build_settings_tab(profile)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)

        self._picker = None  # keep reference

    # ---------------- CLICK TAB ----------------

    def _build_click_tab(self, p):
        l = QVBoxLayout(self.click_tab)

        self.status = QLabel("STOPPED", alignment=Qt.AlignCenter)

        self.delay = QSpinBox()
        self.delay.setRange(2, 1000)
        self.delay.setValue(p["delay_ms"])

        self.click_type = QComboBox()
        self.click_type.addItems(["left", "right"])
        self.click_type.setCurrentText(p["click_type"])

        self.mode = QComboBox()
        self.mode.addItems(["simultaneous", "sequential", "grouped"])
        self.mode.setCurrentText(p["click_mode"])

        self.points = QListWidget()
        self.points.setContextMenuPolicy(Qt.CustomContextMenu)
        self.points.customContextMenuRequested.connect(self._point_menu)

        for x, y in p["points"]:
            self._add_point(x, y)

        self.pick_btn = QPushButton("➕ Pick Point")
        self.pick_btn.clicked.connect(self._start_picker)

        clear = QPushButton("🧹 Clear Points")
        clear.clicked.connect(self.points.clear)

        self.start = QPushButton("START")

        for w in [
            self.status,
            QLabel("Delay (ms)"), self.delay,
            QLabel("Click Type"), self.click_type,
            QLabel("Click Mode"), self.mode,
            QLabel("Points"), self.points,
            self.pick_btn, clear, self.start
        ]:
            l.addWidget(w)

    # ---------------- SETTINGS TAB ----------------

    def _build_settings_tab(self, p):
        l = QVBoxLayout(self.settings_tab)

        self.toggle_key = QComboBox()
        self.toggle_key.addItems(["f6", "f7", "f8"])
        self.toggle_key.setCurrentText(p["toggle_key"])

        self.kill_key = QComboBox()
        self.kill_key.addItems(["esc"])
        self.kill_key.setCurrentText(p["kill_key"])

        save = QPushButton("💾 Save")
        save.clicked.connect(self._save)

        save_as = QPushButton("💾 Save As…")
        save_as.clicked.connect(self._save_as)

        for w in [
            QLabel("Toggle Key"), self.toggle_key,
            QLabel("Kill Key"), self.kill_key,
            save, save_as
        ]:
            l.addWidget(w)

    # ---------------- POINT PICKER ----------------

    def _start_picker(self):
        log.info("Starting point picker")
        self.status.setText("Click anywhere to pick a point…")
        self.pick_btn.setEnabled(False)

        self._picker = PointPicker()
        self._picker.point_picked.connect(self._on_point_picked)
        self._picker.finished.connect(self._picker_finished)
        self._picker.start()

    def _on_point_picked(self, x, y):
        self._add_point(x, y)

    def _picker_finished(self):
        log.info("Point picker finished")
        self.pick_btn.setEnabled(True)
        self.set_running(False)

    def _add_point(self, x, y):
        item = QListWidgetItem(f"{x},{y}")
        item.setData(Qt.UserRole, (x, y))
        self.points.addItem(item)

    def _point_menu(self, pos):
        item = self.points.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        delete = menu.addAction("Delete")
        if menu.exec(self.points.mapToGlobal(pos)) == delete:
            self.points.takeItem(self.points.row(item))

    # ---------------- PROFILE ----------------

    def _save(self):
        save_profile(self.profile_name, self.get_config())

    def _save_as(self):
        name, ok = QInputDialog.getText(self, "Save Profile As", "Profile name:")
        if ok and name:
            self.profile_name = name
            save_profile(name, self.get_config())

    def get_config(self):
        pts = [self.points.item(i).data(Qt.UserRole)
               for i in range(self.points.count())]

        return {
            "name": self.profile_name,
            "delay_ms": self.delay.value(),
            "click_type": self.click_type.currentText(),
            "click_mode": self.mode.currentText(),
            "toggle_key": self.toggle_key.currentText(),
            "kill_key": self.kill_key.currentText(),
            "points": pts
        }

    # ---------------- UI STATE ----------------

    def set_running(self, running):
        self.status.setText("RUNNING" if running else "STOPPED")
        self.start.setText("STOP" if running else "START")

    def show_error(self, msg):
        log.error(msg)
        QMessageBox.critical(self, "Error", msg)
