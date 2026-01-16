# core/controller.py
from PySide6.QtCore import QTimer, QObject, Signal, Qt
from PySide6.QtWidgets import QInputDialog, QMessageBox
from engine.click_engine import ClickEngine
from engine.macro_engine import MacroRecorder, MacroPlayer
from core.scheduler import Scheduler
from core.hotkeys import Hotkeys
from core.logging_setup import get_logger
import time

log = get_logger("controller")

class Controller(QObject):
    # Signals for thread-safe UI updates
    update_running_state_signal = Signal(bool)
    show_error_signal = Signal(str)
    close_app_signal = Signal()

    # Signal to handle hotkey trigger on main thread
    hotkey_triggered = Signal()

    def __init__(self, ui, app_state, profile_manager, macro_manager):
        super().__init__()
        self.ui = ui
        self.app_state = app_state
        self.profile_manager = profile_manager
        self.macro_manager = macro_manager
        self.engine = ClickEngine()

        self.recorder = MacroRecorder()
        self.player = MacroPlayer()

        self.scheduler = Scheduler()
        self.scheduler.job_triggered.connect(self._on_scheduled_job, Qt.QueuedConnection)
        self.scheduler.start()

        self.watchdog_timer = QTimer()
        self.watchdog_timer.timeout.connect(self._check_failsafe)
        self.start_time = 0

        self.engine.started.connect(self._on_start, Qt.QueuedConnection)
        self.engine.stopped.connect(self._on_stop, Qt.QueuedConnection)
        self.engine.error.connect(self.show_error_signal, Qt.QueuedConnection)
        self.engine.cps_updated.connect(self._on_cps_updated, Qt.QueuedConnection)

        self.recorder.finished.connect(self._on_recording_finished)
        self.player.finished.connect(self._on_playback_finished)

        profile = self.app_state.active_profile

        self.hotkeys = Hotkeys(
            profile["toggle_key"],
            profile["kill_key"],
            self._on_hotkey_toggle,
            self.kill
        )
        self.hotkeys.start()

        # Connect internal signal for thread safety
        self.hotkey_triggered.connect(self.toggle, Qt.QueuedConnection)

        # Connect UI update signals
        self.update_running_state_signal.connect(self._update_running_ui)
        self.show_error_signal.connect(self.ui.show_error)
        self.close_app_signal.connect(self._close_app)

        # Connect UI signals
        if hasattr(self.ui, "profile_switched"):
            self.ui.profile_switched.connect(self.load_profile)
        if hasattr(self.ui, "create_profile_requested"):
            self.ui.create_profile_requested.connect(self._handle_create_profile)
        if hasattr(self.ui, "rename_profile_requested"):
            self.ui.rename_profile_requested.connect(self._handle_rename_profile)
        if hasattr(self.ui, "delete_profile_requested"):
            self.ui.delete_profile_requested.connect(self._handle_delete_profile)
        if hasattr(self.ui, "config_changed"):
            self.ui.config_changed.connect(self._on_config_changed)

        # Macro signals
        if hasattr(self.ui, "record_macro_requested"):
            self.ui.record_macro_requested.connect(self.start_recording)
        if hasattr(self.ui, "stop_recording_requested"):
            self.ui.stop_recording_requested.connect(self.stop_recording)
        if hasattr(self.ui, "play_macro_requested"):
            self.ui.play_macro_requested.connect(self.play_macro)
        if hasattr(self.ui, "stop_macro_requested"):
            self.ui.stop_macro_requested.connect(self.stop_macro)
        if hasattr(self.ui, "delete_macro_requested"):
            self.ui.delete_macro_requested.connect(self.delete_macro)

    def _on_config_changed(self):
         if not self.app_state.unsaved_changes:
             self.app_state.unsaved_changes = True
             if hasattr(self.ui, "set_unsaved_indicator"):
                 self.ui.set_unsaved_indicator(True)

    def _on_cps_updated(self, cps):
        if hasattr(self.ui, "update_cps"):
            self.ui.update_cps(cps)

    def toggle(self):
        log.debug("Toggle requested")

        # Check active tab to decide what to toggle
        # 0: Click, 1: Settings, 2: Tuning, 3: Macro
        active_index = self.ui.tabs.currentIndex()

        if active_index == 3: # Macro Tab
            if self.player.running:
                self.stop_macro()
            elif self.recorder.running:
                self.stop_recording()
            else:
                # Start playing selected macro? Or record?
                # Usually hotkey plays the selected macro if ready, or we need a specific 'play' action.
                # Requirement: "use the similar key as the clicking to start and stop the macro as well"
                # If a macro is selected in the list, play it.
                item = self.ui.macro_list.currentItem()
                if item:
                    self.ui._on_play_clicked() # Re-use UI logic to get speed and emit signal
                else:
                    log.warning("No macro selected to play via hotkey")
        else:
            # Clicking Mode
            self.ui.start.setEnabled(False)
            if self.engine.running:
                self.engine.stop()
            else:
                self.engine.start(self.ui.get_config())

    def kill(self):
        log.warning("Kill switch triggered")
        # Emit signal to handle closing on main thread
        self.close_app_signal.emit()

    def _close_app(self):
        try:
            self.hotkeys.stop()
            self.engine.stop()
            self.recorder.stop()
            self.player.stop()
            self.scheduler.stop()
            if hasattr(self.ui, "overlay") and self.ui.overlay:
                self.ui.overlay.close()
            self.ui.close()
        except Exception as e:
            log.error(f"Error during close: {e}")

    def _on_hotkey_toggle(self):
        self.hotkey_triggered.emit()

    def _update_running_ui(self, running):
        self.ui.set_running(running)
        self.ui.start.setEnabled(True)

    def _on_start(self):
        log.info("Engine started")
        self.app_state.engine_running = True
        self.update_running_state_signal.emit(True)
        self.start_time = time.time()
        self.watchdog_timer.start(1000)

    def _on_stop(self):
        log.info("Engine stopped")
        self.app_state.engine_running = False
        self.update_running_state_signal.emit(False)
        self.watchdog_timer.stop()

    def _check_failsafe(self):
        failsafe = self.app_state.active_profile.get("failsafe", {})
        if failsafe.get("enabled"):
            timeout = failsafe.get("timeout", 60)
            if time.time() - self.start_time > timeout:
                log.warning("Failsafe timeout reached. Stopping.")
                self.kill() # Using kill to ensure everything stops

    def load_profile(self, name):
        log.info(f"Switching to profile: {name}")

        # Explicitly stop all engines to ensure clean state
        if self.engine.running:
            self.engine.stop()
        if self.recorder.running:
            self.recorder.stop()
        if self.player.running:
            self.player.stop()

        profile = self.profile_manager.load(name)
        self.app_state.active_profile = profile

        self.hotkeys.stop()
        self.hotkeys = Hotkeys(
            profile["toggle_key"],
            profile["kill_key"],
            self.toggle,
            self.kill
        )
        self.hotkeys.start()

        if hasattr(self.ui, "load_profile_data"):
             self.ui.load_profile_data(profile)
        self.app_state.unsaved_changes = False

        if self.scheduler:
            self.scheduler.update_job(name, profile.get("schedule", {}))

    def new_profile(self, name):
        profile = self.profile_manager.normalize(name, {})
        self.profile_manager.save(name, profile)
        self.load_profile(name)

    def save_profile(self):
        name = self.app_state.active_profile["name"]
        data = self.ui.get_config()
        self.profile_manager.save(name, data)
        self.app_state.active_profile = data
        self.app_state.unsaved_changes = False
        if hasattr(self.ui, "set_unsaved_indicator"):
             self.ui.set_unsaved_indicator(False)

        self.scheduler.update_job(name, data.get("schedule", {}))

    def save_profile_as(self, name):
        data = self.ui.get_config()
        self.profile_manager.save(name, data)
        self.load_profile(name)

    def rename_profile(self, new_name):
        old_name = self.app_state.active_profile["name"]
        data = self.ui.get_config()
        self.profile_manager.save(new_name, data)
        self.profile_manager.delete(old_name)
        self.load_profile(new_name)

    def delete_profile(self, name):
        self.profile_manager.delete(name)
        current = self.app_state.active_profile["name"]
        if current == name:
            self.load_profile("default")

    def _handle_create_profile(self):
        name, ok = QInputDialog.getText(self.ui, "New Profile", "Profile name:")
        if ok and name:
            if name in self.profile_manager.list_profiles():
                 QMessageBox.warning(self.ui, "Error", "Profile already exists")
                 return
            self.new_profile(name)

    def _handle_rename_profile(self):
        name, ok = QInputDialog.getText(self.ui, "Rename Profile", "New name:")
        if ok and name:
            if name in self.profile_manager.list_profiles():
                 QMessageBox.warning(self.ui, "Error", "Profile already exists")
                 return
            self.rename_profile(name)

    def _handle_delete_profile(self):
        current = self.app_state.active_profile["name"]
        if current == "default":
            QMessageBox.warning(self.ui, "Error", "Cannot delete default profile")
            return

        ret = QMessageBox.question(self.ui, "Delete Profile", f"Delete {current}?",
                                   QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            self.delete_profile(current)

    def _on_scheduled_job(self, job):
        log.info(f"Executing scheduled job: {job}")
        if self.engine.running:
            self.toggle()
            # Allow time for engine to stop via signals?
            # Toggle is async if engine running? No, engine.stop() waits for thread join.
            # So it is synchronous here.

        if job["profile"] != self.app_state.active_profile["name"]:
            self.load_profile(job["profile"])

        self.toggle()

    # Macro Methods

    def start_recording(self):
        if self.engine.running: self.toggle()
        if self.player.running: self.player.stop()
        self.recorder.start()

    def stop_recording(self):
        self.recorder.stop()

    def _on_recording_finished(self, events):
        name, ok = QInputDialog.getText(self.ui, "Save Macro", "Macro Name:")
        if ok and name:
            self.macro_manager.save(name, events)
            if hasattr(self.ui, "refresh_macro_list"):
                self.ui.refresh_macro_list()

    def play_macro(self, name, speed):
        if self.engine.running: self.toggle()
        if self.recorder.running: self.stop_recording()

        events = self.macro_manager.load(name)
        if events:
            self.player.play(events, speed)

    def stop_macro(self):
        self.player.stop()

    def _on_playback_finished(self):
        log.info("Playback finished")

    def delete_macro(self, name):
        ret = QMessageBox.question(self.ui, "Delete Macro", f"Delete {name}?",
                                   QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            self.macro_manager.delete(name)
            if hasattr(self.ui, "refresh_macro_list"):
                self.ui.refresh_macro_list()
