# ui/main_window.py
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, Signal, QTime
from ui.picker import PointPicker
from ui.point_model import PointModel
from ui.overlay import Overlay
from ui.styles import DARK_STYLE, LIGHT_STYLE
from core.logging_setup import get_logger
from core.screen_utils import get_virtual_screen_rect
from ui.point_editor import PointEditorDialog
from core.global_config import GlobalConfig
from PySide6.QtGui import QShortcut, QKeySequence

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
    play_macro_requested = Signal(str, float, bool)
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

        self.global_config = GlobalConfig()

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
        self.lbl_sched_info = QLabel("")
        self.lbl_cps = QLabel("CPS: 0")
        self.status_bar_layout.addWidget(self.lbl_sched_info)
        self.status_bar_layout.addStretch()
        self.status_bar_layout.addWidget(self.lbl_cps)
        layout.addLayout(self.status_bar_layout)

        # Shortcuts
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self._save)

        self.shortcut_save_as = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self.shortcut_save_as.activated.connect(self._save_as)

        self._picker = None

        # Apply Global Config
        self.theme_combo.setCurrentText(self.global_config.get("theme", "Dark"))
        if self.global_config.get("compact_mode", False):
            self.chk_compact.setChecked(True)

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

        self.hold_time = QSpinBox()
        self.hold_time.setRange(0, 5000)
        self.hold_time.setSuffix(" ms")
        self.hold_time.valueChanged.connect(self._on_config_changed)
        self.hold_time.setToolTip("Duration to hold mouse button down")

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
        l.addWidget(QLabel("Hold Time (ms)"))
        l.addWidget(self.hold_time)
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
        duplicate = menu.addAction("Duplicate")
        edit = menu.addAction("Edit...")
        delete = menu.addAction("Delete")
        set_group = menu.addAction("Set Group...")

        action = menu.exec(self.points_view.mapToGlobal(pos))

        if not action: return

        if action == delete:
            self._delete_selected_points()
        elif action == duplicate:
            self._duplicate_selected_points()
        elif action == edit:
            self._edit_selected_point()
        elif action == set_group:
            self._set_group_selected_points()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
             if self.points_view.hasFocus():
                  self._delete_selected_points()
        super().keyPressEvent(event)

    def _delete_selected_points(self):
        indexes = self.points_view.selectedIndexes()
        rows = sorted(set(i.row() for i in indexes), reverse=True)
        for r in rows:
            self.point_model.remove_at(r)

    def _duplicate_selected_points(self):
        indexes = self.points_view.selectedIndexes()
        if not indexes: return

        rows = sorted([i.row() for i in indexes])
        new_points = []
        current_points = self.point_model.get_points()

        for r in rows:
            if 0 <= r < len(current_points):
                p = current_points[r].copy()
                # Offset slightly? If float, 0.01? If int, 10?
                if isinstance(p["x"], float):
                    p["x"] += 0.01
                    p["y"] += 0.01
                else:
                    p["x"] += 10
                    p["y"] += 10
                new_points.append(p)

        # Append new points
        all_points = current_points + new_points
        self.point_model.set_points(all_points)

    def _edit_selected_point(self):
        indexes = self.points_view.selectedIndexes()
        if not indexes: return
        # Edit the first selected point
        row = indexes[0].row()
        current_points = self.point_model.get_points()
        if 0 <= row < len(current_points):
            p = current_points[row]
            dlg = PointEditorDialog(p, self)
            if dlg.exec():
                new_data = dlg.get_data()
                self.point_model.update_point(row, new_data)

    def _set_group_selected_points(self):
        indexes = self.points_view.selectedIndexes()
        if not indexes: return

        group, ok = QInputDialog.getInt(self, "Set Group", "Group ID (0-9):", 0, 0, 9)
        if ok:
            for i in indexes:
                self.point_model.set_group(i.row(), group)

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

        self.chk_failsafe = QCheckBox("Enable Failsafe Timeout")
        self.chk_failsafe.toggled.connect(self._on_config_changed)

        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(1, 3600)
        self.spin_timeout.setSuffix(" s")
        self.spin_timeout.valueChanged.connect(self._on_config_changed)

        for w in [
            QLabel("Toggle Key"), self.toggle_key,
            QLabel("Kill Key"), self.kill_key,
            QLabel("Theme"), self.theme_combo,
            self.chk_compact,
            self.chk_failsafe,
            QLabel("Timeout (s)"), self.spin_timeout,
            save, save_as
        ]:
            l.addWidget(w)

    def _toggle_compact_mode(self, checked):
        self.global_config.set("compact_mode", checked)
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
        self.global_config.set("theme", text)
        app = QApplication.instance()
        if text == "Light":
            app.setStyleSheet(LIGHT_STYLE)
        else:
            app.setStyleSheet(DARK_STYLE)

    # ---------------- TUNING TAB ----------------

    def _build_tuning_tab(self):
        l = QVBoxLayout(self.tuning_tab)

        presets = QHBoxLayout()
        btn_safe = QPushButton("Game-Safe")
        btn_safe.clicked.connect(self._apply_preset_safe)
        btn_balanced = QPushButton("Balanced")
        btn_balanced.clicked.connect(self._apply_preset_balanced)
        btn_max = QPushButton("Max Perf")
        btn_max.clicked.connect(self._apply_preset_max)
        presets.addWidget(btn_safe)
        presets.addWidget(btn_balanced)
        presets.addWidget(btn_max)

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

        self.cps_cap = QSpinBox()
        self.cps_cap.setRange(0, 1000)
        self.cps_cap.setSuffix(" CPS")
        self.cps_cap.setToolTip("0 = Unlimited")
        self.cps_cap.valueChanged.connect(self._on_config_changed)

        self.thread_priority = QComboBox()
        self.thread_priority.addItems(["idle", "lowest", "below_normal", "normal", "above_normal", "highest", "time_critical"])
        self.thread_priority.currentTextChanged.connect(self._on_config_changed)

        self.busy_wait = QSpinBox()
        self.busy_wait.setRange(0, 100000)
        self.busy_wait.setSuffix(" us")
        self.busy_wait.valueChanged.connect(self._on_config_changed)

        self.batch_size = QSpinBox()
        self.batch_size.setRange(1, 100)
        self.batch_size.valueChanged.connect(self._on_config_changed)

        self.retry_count = QSpinBox()
        self.retry_count.setRange(0, 10)
        self.retry_count.valueChanged.connect(self._on_config_changed)

        self.overload_thresh = QSpinBox()
        self.overload_thresh.setRange(1, 1000)
        self.overload_thresh.valueChanged.connect(self._on_config_changed)

        l.addLayout(presets)
        l.addWidget(self.chk_game_safe)

        g1 = QGridLayout()
        g1.addWidget(QLabel("Jitter Radius:"), 0, 0)
        g1.addWidget(self.jitter_px, 0, 1)
        g1.addWidget(QLabel("Jitter Delay:"), 1, 0)
        g1.addWidget(self.jitter_pct, 1, 1)
        g1.addWidget(QLabel("CPS Cap:"), 2, 0)
        g1.addWidget(self.cps_cap, 2, 1)
        l.addLayout(g1)

        l.addWidget(QLabel("<b>Advanced Tuning</b>"))
        g2 = QGridLayout()
        g2.addWidget(QLabel("Priority:"), 0, 0)
        g2.addWidget(self.thread_priority, 0, 1)
        g2.addWidget(QLabel("Busy Wait:"), 1, 0)
        g2.addWidget(self.busy_wait, 1, 1)
        g2.addWidget(QLabel("Batch Size:"), 2, 0)
        g2.addWidget(self.batch_size, 2, 1)
        g2.addWidget(QLabel("Retry Count:"), 3, 0)
        g2.addWidget(self.retry_count, 3, 1)
        g2.addWidget(QLabel("Overload Thresh:"), 4, 0)
        g2.addWidget(self.overload_thresh, 4, 1)
        l.addLayout(g2)

        l.addStretch()

    def _apply_preset_safe(self):
        self.chk_game_safe.setChecked(True)
        self.thread_priority.setCurrentText("normal")
        self.busy_wait.setValue(0)
        self.batch_size.setValue(1)
        self.jitter_px.setValue(max(self.jitter_px.value(), 2))
        self.jitter_pct.setValue(max(self.jitter_pct.value(), 10))
        self.cps_cap.setValue(20)

    def _apply_preset_balanced(self):
        self.chk_game_safe.setChecked(False)
        self.thread_priority.setCurrentText("above_normal")
        self.busy_wait.setValue(500)
        self.batch_size.setValue(1)
        self.cps_cap.setValue(0)

    def _apply_preset_max(self):
        self.chk_game_safe.setChecked(False)
        self.thread_priority.setCurrentText("highest")
        self.busy_wait.setValue(2000)
        self.batch_size.setValue(5)
        self.cps_cap.setValue(0)

    # ---------------- SCHEDULE TAB ----------------

    def _build_schedule_tab(self):
        l = QVBoxLayout(self.schedule_tab)

        self.chk_sched = QCheckBox("Enable Schedule")
        self.chk_sched.toggled.connect(self._on_config_changed)

        self.time_sched = QTimeEdit()
        self.time_sched.setDisplayFormat("HH:mm")
        self.time_sched.timeChanged.connect(self._on_config_changed)

        self.chk_repeat = QCheckBox("Repeat Daily")
        self.chk_repeat.toggled.connect(self._on_config_changed)

        type_layout = QHBoxLayout()
        self.radio_profile = QRadioButton("Run Profile")
        self.radio_macro = QRadioButton("Run Macro")
        self.radio_profile.setChecked(True)
        self.bg_type = QButtonGroup(self)
        self.bg_type.addButton(self.radio_profile)
        self.bg_type.addButton(self.radio_macro)
        self.radio_profile.toggled.connect(self._on_config_changed)
        self.radio_macro.toggled.connect(self._on_config_changed)
        type_layout.addWidget(self.radio_profile)
        type_layout.addWidget(self.radio_macro)

        self.combo_macro = QComboBox()
        self.combo_macro.addItems(self.macro_manager.list_macros())
        self.combo_macro.currentTextChanged.connect(self._on_config_changed)

        self.lbl_sched_status = QLabel("Next Run: -")

        l.addWidget(self.chk_sched)
        l.addWidget(QLabel("Start Time:"))
        l.addWidget(self.time_sched)
        l.addWidget(self.chk_repeat)
        l.addLayout(type_layout)
        l.addWidget(QLabel("Macro (if selected):"))
        l.addWidget(self.combo_macro)
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

        self.chk_instant = QCheckBox("Instant Playback")

        l.addWidget(self.macro_list)
        l.addLayout(btns)
        l.addWidget(QLabel("Playback Speed"))
        l.addWidget(self.speed_slider)
        l.addWidget(self.chk_instant)

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
            instant = self.chk_instant.isChecked()
            self.play_macro_requested.emit(item.text(), speed, instant)

    def _on_delete_macro_clicked(self):
        item = self.macro_list.currentItem()
        if item:
            self.delete_macro_requested.emit(item.text())

    def refresh_macro_list(self):
        macros = self.macro_manager.list_macros()
        self.macro_list.clear()
        self.macro_list.addItems(macros)
        current = self.combo_macro.currentText()
        self.combo_macro.clear()
        self.combo_macro.addItems(macros)
        self.combo_macro.setCurrentText(current)

    def load_profile_data(self, p):
        self.profile_name = p["name"]

        inputs = [
            self.profile_combo, self.delay, self.hold_time, self.click_type, self.mode,
            self.toggle_key, self.kill_key, self.point_model,
            self.jitter_px, self.jitter_pct, self.cps_cap,
            self.thread_priority, self.busy_wait, self.batch_size, self.retry_count, self.overload_thresh,
            self.chk_limit, self.limit_count,
            self.chk_burst, self.burst_size, self.burst_interval,
            self.chk_sched, self.time_sched, self.chk_repeat, self.radio_profile, self.radio_macro, self.combo_macro,
            self.chk_failsafe, self.spin_timeout,
            self.chk_game_safe
        ]
        for w in inputs: w.blockSignals(True)

        self.profile_combo.clear()
        self.profile_combo.addItems(self.profile_manager.list_profiles())
        self.profile_combo.setCurrentText(p["name"])

        self.delay.setValue(p["delay_ms"])
        self.hold_time.setValue(p.get("hold_time_ms", 0))
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
        self.cps_cap.setValue(t.get("cps_cap", 0))
        self.thread_priority.setCurrentText(t.get("thread_priority", "normal"))
        self.busy_wait.setValue(t.get("busy_wait_us", 500))
        self.batch_size.setValue(t.get("batch_size", 1))
        self.retry_count.setValue(t.get("retry_count", 3))
        self.overload_thresh.setValue(t.get("overload_threshold", 10))

        sch = p.get("schedule", {})
        self.chk_sched.setChecked(sch.get("enabled", False))
        time_str = sch.get("time", "12:00")
        self.time_sched.setTime(QTime.fromString(time_str, "HH:mm"))
        self.chk_repeat.setChecked(sch.get("repeat", False))

        fs = p.get("failsafe", {})
        self.chk_failsafe.setChecked(fs.get("enabled", False))
        self.spin_timeout.setValue(fs.get("timeout", 60))

        if sch.get("type") == "macro":
            self.radio_macro.setChecked(True)
        else:
            self.radio_profile.setChecked(True)

        self.combo_macro.setCurrentText(sch.get("macro_name", ""))

        if sch.get("enabled"):
             self.lbl_sched_status.setText(f"Scheduled for {time_str}")
        else:
             self.lbl_sched_status.setText("Next Run: -")

        for w in inputs: w.blockSignals(False)
        self.set_unsaved_indicator(False)

    # ---------------- POINT PICKER ----------------

    def _start_picker(self):
        log.info("Starting point picker")
        self.status.setText("Click anywhere to pick a point…")
        self.pick_btn.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CrossCursor)

        self._picker = PointPicker()
        self._picker.point_picked.connect(self._on_point_picked)
        self._picker.finished.connect(self._picker_finished)
        self._picker.start()

    def _on_point_picked(self, x, y):
        vx, vy, vw, vh = get_virtual_screen_rect()
        nx = (x - vx) / vw
        ny = (y - vy) / vh
        # Clamp 0.0-1.0
        nx = max(0.0, min(1.0, nx))
        ny = max(0.0, min(1.0, ny))
        self.point_model.add_point(nx, ny)

    def _picker_finished(self):
        log.info("Point picker finished")
        self.pick_btn.setEnabled(True)
        QApplication.restoreOverrideCursor()
        self.set_running(False)

    # ---------------- PROFILE ----------------

    def _save(self):
        self.profile_manager.save(self.profile_name, self.get_config())

    def _save_as(self):
        name, ok = QInputDialog.getText(self, "Save Profile As", "Profile name:")
        if ok and name:
            if name in self.profile_manager.list_profiles():
                ret = QMessageBox.question(self, "Overwrite?", f"Profile '{name}' exists. Overwrite?", QMessageBox.Yes | QMessageBox.No)
                if ret != QMessageBox.Yes:
                    return

            self.profile_name = name
            self.profile_manager.save(name, self.get_config())

    def get_config(self):
        return {
            "name": self.profile_name,
            "delay_ms": self.delay.value(),
            "hold_time_ms": self.hold_time.value(),
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
                },
                "cps_cap": self.cps_cap.value(),
                "thread_priority": self.thread_priority.currentText(),
                "busy_wait_us": self.busy_wait.value(),
                "batch_size": self.batch_size.value(),
                "retry_count": self.retry_count.value(),
                "overload_threshold": self.overload_thresh.value()
            },
            "schedule": {
                "enabled": self.chk_sched.isChecked(),
                "time": self.time_sched.time().toString("HH:mm"),
                "repeat": self.chk_repeat.isChecked(),
                "type": "macro" if self.radio_macro.isChecked() else "profile",
                "macro_name": self.combo_macro.currentText()
            },
            "failsafe": {
                "enabled": self.chk_failsafe.isChecked(),
                "timeout": self.spin_timeout.value()
            }
        }

    # ---------------- UI STATE ----------------

    def set_running(self, running):
        self.status.setText("RUNNING" if running else "STOPPED")
        self.start.setText("STOP" if running else "START")

        self.tabs.setEnabled(not running)
        self.profile_combo.setEnabled(not running)
        self.btn_new.setEnabled(not running)
        self.btn_rename.setEnabled(not running)
        self.btn_delete.setEnabled(not running)
        self.btn_preview.setEnabled(not running)

    def show_error(self, msg):
        log.error(msg)
        QMessageBox.critical(self, "Error", msg)

    def closeEvent(self, event):
        if self.overlay:
            self.overlay.close()
        event.accept()
