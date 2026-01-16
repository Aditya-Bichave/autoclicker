from engine import ClickEngine
from hotkeys import Hotkeys
from logging_setup import get_logger

log = get_logger("controller")

class Controller:
    def __init__(self, ui, profile):
        self.ui = ui
        self.engine = ClickEngine()

        self.engine.started.connect(self._on_start)
        self.engine.stopped.connect(self._on_stop)
        self.engine.error.connect(self.ui.show_error)

        self.hotkeys = Hotkeys(
            profile["toggle_key"],
            profile["kill_key"],
            self.toggle,
            self.kill
        )
        self.hotkeys.start()

    def toggle(self):
        log.debug("Toggle requested")
        self.ui.start.setEnabled(False)
        if self.engine.running:
            self.engine.stop()
        else:
            self.engine.start(self.ui.get_config())

    def kill(self):
        log.warning("Kill switch triggered")
        self.hotkeys.stop()
        self.engine.stop()
        self.ui.close()

    def _on_start(self):
        log.info("Engine started")
        self.ui.set_running(True)
        self.ui.start.setEnabled(True)

    def _on_stop(self):
        log.info("Engine stopped")
        self.ui.set_running(False)
        self.ui.start.setEnabled(True)
