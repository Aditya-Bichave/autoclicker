# ui/main_window.py
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, Signal, QTime
from ui.picker import PointPicker
from ui.point_model import PointModel
from ui.overlay import Overlay
from ui.styles import DARK_STYLE, LIGHT_STYLE
from core.logging_setup import get_logger

log = get_logger("ui")

class MainWindow(QWidget):
    # Signals for Controller
    profile_switched = Signal(str)
    create_profile_requested = Signal()
    rename_profile_requested = Signal()
    delete_profile_requested = Signal()
    config_changed = Signal()

    # Macro Signals
    record_macro_requested = Signal()
    stop_recording_requested = Signal()
    play_macro_requested = Signal(str, float)
    stop_macro_requested = Signal()
    delete_macro_requested = Signal(str)

    def __init__(self, profile, profile_manager, macro_manager):
        super().__init__()
        self.profile_manager = profile_manager
        self.macro_manager = macro_manager
        self.setWindowTitle("Multi Clicker")
        self.setFixedSize(420, 680)
        self.profile_name = profile["name"]

        self.overlay = None

        # Point Model
        self.point_model = PointModel()
        self.point_model.dataChanged.connect(self._on_config_changed)
        self.point_model.rowsInserted.connect(self._on_config_changed)
        self.point_model.rowsRemoved.connect(self._on_config_changed)
        self.point_model.rowsMoved.connect(self._on_config_changed)
        self.point_model.modelReset.connect(self._on_config_changed)

        self.tabs = QTabWidget(self)
        self.click_tab = QWidget()
        self.settings_tab = QWidget()
        self.tuning_tab = QWidget()
        self.macro_tab = QWidget()
        self.schedule_tab = QWidget()

        self.tabs.addTab(self.click_tab, "Clicking")
        self.tabs.addTab(self.settings_tab, "Settings")
        self.tabs.addTab(self.tuning_tab, "Tuning")
        self.tabs.addTab(self.macro_tab, "Macro")
        self.tabs.addTab(self.schedule_tab, "Schedule")

        self._build_top_bar(profile)
        self._build_click_tab()
        self._build_settings_tab()
        self._build_tuning_tab()
        self._build_macro_tab()
        self._build_schedule_tab()
        self.load_profile_data(profile)

        layout = QVBoxLayout(self)
        layout.addLayout(self.top_bar_layout)
        layout.addWidget(self.tabs)

        self.status_bar_layout = QHBoxLayout()
        self.lbl_cps = QLabel("CPS: 0")
        self.status_bar_layout.addStretch()
        self.status_bar_layout.addWidget(self.lbl_cps)
        layout.addLayout(self.status_bar_layout)

        self._picker = None

    def _build_top_bar(self, p):
        self.top_bar_layout = QHBoxLayout()

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(self.profile_manager.list_profiles())
        self.profile_combo.setCurrentText(p["name"])
        self.profile_combo.currentTextChanged.connect(self._on_profile_combo_changed)
        self.profile_combo.setToolTip("Select active profile")

        self.btn_new = QPushButton("New")
        self.btn_new.clicked.connect(self.create_profile_requested.emit)
        self.btn_new.setToolTip("Create new profile")

        self.btn_rename = QPushButton("Ren")
        self.btn_rename.clicked.connect(self.rename_profile_requested.emit)
        self.btn_rename.setToolTip("Rename current profile")

        self.btn_delete = QPushButton("Del")
        self.btn_delete.clicked.connect(self.delete_profile_requested.emit)
        self.btn_delete.setToolTip("Delete current profile")

        self.btn_preview = QPushButton("👁")
        self.btn_preview.setCheckable(True)
        self.btn_preview.clicked.connect(self._toggle_overlay)
        self.btn_preview.setToolTip("Toggle click overlay preview")

        self.lbl_unsaved = QLabel("")
        self.lbl_unsaved.setStyleSheet("color: orange; font-weight: bold;")

        self.top_bar_layout.addWidget(self.profile_combo, 1)
        self.top_bar_layout.addWidget(self.lbl_unsaved)
        self.top_bar_layout.addWidget(self.btn_new)
        self.top_bar_layout.addWidget(self.btn_rename)
        self.top_bar_layout.addWidget(self.btn_delete)
        self.top_bar_layout.addWidget(self.btn_preview)

    def _toggle_overlay(self, checked):
        if checked:
            if not self.overlay:
                self.overlay = Overlay()
            self.overlay.update_points(self.point_model.get_points())
            self.overlay.show()
        else:
            if self.overlay:
                self.overlay.hide()

    def _on_profile_combo_changed(self, text):
        if text:
            self.profile_switched.emit(text)

    def _on_config_changed(self, *args):
        self.config_changed.emit()
        if self.overlay and self.overlay.isVisible():
            self.overlay.update_points(self.point_model.get_points())

    def set_unsaved_indicator(self, unsaved):
        self.lbl_unsaved.setText("(*)" if unsaved else "")

    def update_cps(self, cps):
        state = "RUNNING" if self.start.text() == "STOP" else "STOPPED"
        self.lbl_cps.setText(f"Profile: {self.profile_name} | State: {state} | CPS: {cps}")

    # ---------------- CLICK TAB ----------------

    def _build_click_tab(self):
        l = QVBoxLayout(self.click_tab)

        self.status = QLabel("STOPPED", alignment=Qt.AlignCenter)

        self.delay = QSpinBox()
        self.delay.setRange(2, 1000)
        self.delay.valueChanged.connect(self._on_config_changed)
        self.delay.setToolTip("Delay between clicks in milliseconds")

        self.click_type = QComboBox()
        self.click_type.addItems(["left", "right"])
        self.click_type.currentTextChanged.connect(self._on_config_changed)
        self.click_type.setToolTip("Mouse button to click")

        self.mode = QComboBox()
        self.mode.addItems(["simultaneous", "sequential", "grouped"])
        self.mode.currentTextChanged.connect(self._on_config_changed)
        self.mode.setToolTip("Clicking strategy:\nSimultaneous: All points at once\nSequential: One by one\nGrouped: Split into two groups")

        # Click Limit
        self.chk_limit = QCheckBox("Limit Clicks")
        self.chk_limit.toggled.connect(self._on_config_changed)
        self.limit_count = QSpinBox()
        self.limit_count.setRange(1, 9999999)
        self.limit_count.setValue(1000)
        self.limit_count.valueChanged.connect(self._on_config_changed)

        limit_layout = QHBoxLayout()
        limit_layout.addWidget(self.chk_limit)
        limit_layout.addWidget(self.limit_count)

        # Burst Mode
        self.chk_burst = QCheckBox("Burst Mode")
        self.chk_burst.toggled.connect(self._on_config_changed)

        self.burst_size = QSpinBox()
        self.burst_size.setRange(1, 1000)
        self.burst_size.setValue(10)
        self.burst_size.valueChanged.connect(self._on_config_changed)

        self.burst_interval = QSpinBox()
        self.burst_interval.setRange(0, 10000)
        self.burst_interval.setValue(500)
        self.burst_interval.setSuffix(" ms")
        self.burst_interval.valueChanged.connect(self._on_config_changed)

        burst_layout = QHBoxLayout()
        burst_layout.addWidget(self.chk_burst)
        burst_layout.addWidget(QLabel("Size:"))
        burst_layout.addWidget(self.burst_size)
        burst_layout.addWidget(QLabel("Int:"))
        burst_layout.addWidget(self.burst_interval)

        self.points_view = QListView()
        self.points_view.setModel(self.point_model)
        self.points_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.points_view.setDragDropMode(QAbstractItemView.InternalMove)
        self.points_view.setDragEnabled(True)
        self.points_view.setAcceptDrops(True)
        self.points_view.setDropIndicatorShown(True)
        self.points_view.setDefaultDropAction(Qt.MoveAction)

        self.points_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.points_view.customContextMenuRequested.connect(self._point_menu)

        self.points_view.setToolTip("List of coordinates (Drag to reorder, Right-click to delete)")

        self.pick_btn = QPushButton("➕ Pick Point")
        self.pick_btn.clicked.connect(self._start_picker)
        self.pick_btn.setToolTip("Pick a point on screen")

        clear = QPushButton("🧹 Clear Points")
        clear.clicked.connect(lambda: self.point_model.set_points([]))
        clear.setToolTip("Remove all points")

        self.start = QPushButton("START")
        self.start.setToolTip("Start/Stop clicking (Hotkey: F6)")

        l.addWidget(self.status)
        l.addWidget(QLabel("Delay (ms)"))
        l.addWidget(self.delay)
        l.addWidget(QLabel("Click Type"))
        l.addWidget(self.click_type)
        l.addWidget(QLabel("Click Mode"))
        l.addWidget(self.mode)
        l.addLayout(limit_layout)
        l.addLayout(burst_layout)
        l.addWidget(QLabel("Points"))
        l.addWidget(self.points_view)
        l.addWidget(self.pick_btn)
        l.addWidget(clear)
        l.addWidget(self.start)

    def _point_menu(self, pos):
        idx = self.points_view.indexAt(pos)
        if not idx.isValid():
            return

        menu = QMenu(self)
        delete = menu.addAction("Delete")
        set_group = menu.addAction("Set Group...")

        action = menu.exec(self.points_view.mapToGlobal(pos))

        if action == delete:
            indexes = self.points_view.selectedIndexes()
            rows = sorted(set(i.row() for i in indexes), reverse=True)
            for r in rows:
                self.point_model.remove_at(r)

        elif action == set_group:
            indexes = self.points_view.selectedIndexes()
            if not indexes: return

            group, ok = QInputDialog.getInt(self, "Set Group", "Group ID (0-9):", 0, 0, 9)
            if ok:
                for i in indexes:
                    self.point_model.set_group(i.row(), group)

        elif action == duplicate:
            indexes = self.points_view.selectedIndexes()
            if not indexes: return

            # Sort by row to keep order
            rows = sorted([i.row() for i in indexes])
            new_points = []

            # Get data for selected points
            current_points = self.point_model.get_points()
            for r in rows:
                if 0 <= r < len(current_points):
                    # Deep copy the dict to avoid ref issues
                    p = current_points[r].copy()
                    # Offset slightly so user sees it
                    p["x"] += 10
                    p["y"] += 10
                    new_points.append(p)

            # Insert them
            # Access underlying list directly to copy full properties
            # This relies on internal implementation of PointModel but is safe given we just read it.
            # To be 100% proper we would add 'add_point_dict' to model, but we are updating main_window now.
            # We can use set_points to refresh everything or just append.
            all_points = self.point_model.get_points()
            all_points.extend(new_points)
            self.point_model.set_points(all_points)

    # ---------------- SETTINGS TAB ----------------

    def _build_settings_tab(self):
        l = QVBoxLayout(self.settings_tab)

        self.toggle_key = QComboBox()
        self.toggle_key.addItems(["f6", "f7", "f8"])
        self.toggle_key.currentTextChanged.connect(self._on_config_changed)

        self.kill_key = QComboBox()
        self.kill_key.addItems(["esc"])
        self.kill_key.currentTextChanged.connect(self._on_config_changed)

        # Theme Toggle
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)

        save = QPushButton("💾 Save")
        save.clicked.connect(self._save)

        save_as = QPushButton("💾 Save As…")
        save_as.clicked.connect(self._save_as)

        # Compact Mode Toggle
        self.chk_compact = QCheckBox("Compact Mode")
        self.chk_compact.toggled.connect(self._toggle_compact_mode)

        for w in [
            QLabel("Toggle Key"), self.toggle_key,
            QLabel("Kill Key"), self.kill_key,
            QLabel("Theme"), self.theme_combo,
            self.chk_compact,
            save, save_as
        ]:
            l.addWidget(w)

    def _toggle_compact_mode(self, checked):
        if checked:
            self.tabs.hide()
            self.setFixedSize(420, 150)

            # Move Start Button
            self.start.setParent(self)
            self.layout().insertWidget(1, self.start)
            self.start.show()

            # Move Delay SpinBox (Requirement: "Compact: only start/stop, delay, profile")
            # We need to find where delay is currently (click_tab layout)
            self.delay.setParent(self)
            self.layout().insertWidget(1, self.delay) # Insert above start button
            self.delay.show()

            # Context menu for exiting compact mode
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self._compact_context_menu)
        else:
            # Restore
            self.setFixedSize(420, 680)
            self.tabs.show()

            # Restore start button
            self.click_tab.layout().addWidget(self.start)

            # Restore delay spinbox. It was at index 2 (Label "Delay", Widget Delay)
            # We assume label is separate. We just put delay back.
            # Layout order in build_click_tab: status, label, delay...
            # We can just append and let user re-adjust or insert at specific index if strict.
            # build_click_tab order: status, label_delay, delay, ...
            # Inserting at index 2 matches original build order approximately.
            self.click_tab.layout().insertWidget(2, self.delay)

            # Disable context menu for main window
            self.setContextMenuPolicy(Qt.NoContextMenu)
            try:
                self.customContextMenuRequested.disconnect(self._compact_context_menu)
            except: pass

    def _compact_context_menu(self, pos):
        if not self.chk_compact.isChecked(): return
        menu = QMenu(self)
        restore = menu.addAction("Exit Compact Mode")
        if menu.exec(self.mapToGlobal(pos)) == restore:
            self.chk_compact.setChecked(False)

    def _on_theme_changed(self, text):
        app = QApplication.instance()
        if text == "Light":
            app.setStyleSheet(LIGHT_STYLE)
        else:
            app.setStyleSheet(DARK_STYLE)

    # ---------------- TUNING TAB ----------------

    def _build_tuning_tab(self):
        l = QVBoxLayout(self.tuning_tab)

        self.chk_game_safe = QCheckBox("Game-Safe Mode")
        self.chk_game_safe.setToolTip("Enforces safe limits: Max 20 CPS, Min Jitter 2px/10%")
        self.chk_game_safe.toggled.connect(self._on_config_changed)

        self.jitter_px = QSpinBox()
        self.jitter_px.setRange(0, 500)
        self.jitter_px.setSuffix(" px")
        self.jitter_px.valueChanged.connect(self._on_config_changed)

        self.jitter_pct = QSpinBox()
        self.jitter_pct.setRange(0, 100)
        self.jitter_pct.setSuffix(" %")
        self.jitter_pct.valueChanged.connect(self._on_config_changed)

        l.addWidget(self.chk_game_safe)
        l.addWidget(QLabel("Jitter Radius (Pixels)"))
        l.addWidget(self.jitter_px)
        l.addWidget(QLabel("Jitter Delay (Percent)"))
        l.addWidget(self.jitter_pct)
        l.addStretch()

    # ---------------- SCHEDULE TAB ----------------

    def _build_schedule_tab(self):
        l = QVBoxLayout(self.schedule_tab)

        self.chk_sched = QCheckBox("Enable Schedule")
        self.chk_sched.toggled.connect(self._on_config_changed)

        self.time_sched = QTimeEdit()
        self.time_sched.setDisplayFormat("HH:mm")
        self.time_sched.timeChanged.connect(self._on_config_changed)

        self.lbl_sched_status = QLabel("Next Run: -")

        l.addWidget(self.chk_sched)
        l.addWidget(QLabel("Start Time:"))
        l.addWidget(self.time_sched)
        l.addWidget(self.lbl_sched_status)
        l.addStretch()

    # ---------------- MACRO TAB ----------------

    def _build_macro_tab(self):
        l = QVBoxLayout(self.macro_tab)

        self.macro_list = QListWidget()
        self.macro_list.addItems(self.macro_manager.list_macros())

        btns = QHBoxLayout()
        self.btn_record = QPushButton("Record")
        self.btn_record.setCheckable(True)
        self.btn_record.clicked.connect(self._on_record_toggled)

        self.btn_play = QPushButton("Play")
        self.btn_play.clicked.connect(self._on_play_clicked)

        self.btn_stop_macro = QPushButton("Stop")
        self.btn_stop_macro.clicked.connect(self.stop_macro_requested.emit)

        self.btn_del_macro = QPushButton("Delete")
        self.btn_del_macro.clicked.connect(self._on_delete_macro_clicked)

        btns.addWidget(self.btn_record)
        btns.addWidget(self.btn_play)
        btns.addWidget(self.btn_stop_macro)
        btns.addWidget(self.btn_del_macro)

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(10, 500)
        self.speed_slider.setValue(100)

        l.addWidget(self.macro_list)
        l.addLayout(btns)
        l.addWidget(QLabel("Playback Speed"))
        l.addWidget(self.speed_slider)

    def _on_record_toggled(self, checked):
        if checked:
            self.record_macro_requested.emit()
            self.btn_record.setText("Stop Recording")
        else:
            self.stop_recording_requested.emit()
            self.btn_record.setText("Record")

    def _on_play_clicked(self):
        item = self.macro_list.currentItem()
        if item:
            speed = self.speed_slider.value() / 100.0
            self.play_macro_requested.emit(item.text(), speed)

    def _on_delete_macro_clicked(self):
        item = self.macro_list.currentItem()
        if item:
            self.delete_macro_requested.emit(item.text())

    def refresh_macro_list(self):
        self.macro_list.clear()
        self.macro_list.addItems(self.macro_manager.list_macros())

    def load_profile_data(self, p):
        self.profile_name = p["name"]

        inputs = [
            self.profile_combo, self.delay, self.click_type, self.mode,
            self.toggle_key, self.kill_key, self.point_model,
            self.jitter_px, self.jitter_pct,
            self.chk_limit, self.limit_count,
            self.chk_burst, self.burst_size, self.burst_interval,
            self.chk_sched, self.time_sched, self.chk_game_safe
        ]
        for w in inputs: w.blockSignals(True)

        self.profile_combo.clear()
        self.profile_combo.addItems(self.profile_manager.list_profiles())
        self.profile_combo.setCurrentText(p["name"])

        self.delay.setValue(p["delay_ms"])
        self.click_type.setCurrentText(p["click_type"])
        self.mode.setCurrentText(p["click_mode"])

        cl = p.get("click_limit", {})
        self.chk_limit.setChecked(cl.get("enabled", False))
        self.limit_count.setValue(cl.get("count", 1000))

        bm = p.get("burst", {})
        self.chk_burst.setChecked(bm.get("enabled", False))
        self.burst_size.setValue(bm.get("size", 10))
        self.burst_interval.setValue(bm.get("interval_ms", 500))

        self.point_model.set_points(p["points"])

        self.toggle_key.setCurrentText(p["toggle_key"])
        self.kill_key.setCurrentText(p["kill_key"])

        t = p.get("tuning", {})
        self.chk_game_safe.setChecked(t.get("game_safe", False))
        j = t.get("jitter", {})
        self.jitter_px.setValue(j.get("px", 0))
        self.jitter_pct.setValue(j.get("percent", 0))

        sch = p.get("schedule", {})
        self.chk_sched.setChecked(sch.get("enabled", False))
        time_str = sch.get("time", "12:00")
        self.time_sched.setTime(QTime.fromString(time_str, "HH:mm"))

        for w in inputs: w.blockSignals(False)
        self.set_unsaved_indicator(False)

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
        self.point_model.add_point(x, y)

    def _picker_finished(self):
        log.info("Point picker finished")
        self.pick_btn.setEnabled(True)
        self.set_running(False)

    # ---------------- PROFILE ----------------

    def _save(self):
        self.profile_manager.save(self.profile_name, self.get_config())

    def _save_as(self):
        name, ok = QInputDialog.getText(self, "Save Profile As", "Profile name:")
        if ok and name:
            self.profile_name = name
            self.profile_manager.save(name, self.get_config())

    def get_config(self):
        return {
            "name": self.profile_name,
            "delay_ms": self.delay.value(),
            "click_type": self.click_type.currentText(),
            "click_mode": self.mode.currentText(),
            "toggle_key": self.toggle_key.currentText(),
            "kill_key": self.kill_key.currentText(),
            "points": self.point_model.get_points(),
            "click_limit": {
                "enabled": self.chk_limit.isChecked(),
                "count": self.limit_count.value()
            },
            "burst": {
                "enabled": self.chk_burst.isChecked(),
                "size": self.burst_size.value(),
                "interval_ms": self.burst_interval.value()
            },
            "tuning": {
                "game_safe": self.chk_game_safe.isChecked(),
                "jitter": {
                    "px": self.jitter_px.value(),
                    "percent": self.jitter_pct.value()
                }
            },
            "schedule": {
                "enabled": self.chk_sched.isChecked(),
                "time": self.time_sched.time().toString("HH:mm")
            }
        }

    # ---------------- UI STATE ----------------

    def set_running(self, running):
        self.status.setText("RUNNING" if running else "STOPPED")
        self.start.setText("STOP" if running else "START")

    def show_error(self, msg):
        log.error(msg)
        QMessageBox.critical(self, "Error", msg)

    def closeEvent(self, event):
        if self.overlay:
            self.overlay.close()
        event.accept()
