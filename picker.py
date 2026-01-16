# picker.py
import threading
from pynput import mouse
from PySide6.QtCore import QObject, Signal
from logging_setup import get_logger

log = get_logger("picker")

class PointPicker(QObject):
    point_picked = Signal(int, int)
    finished = Signal()

    def start(self):
        def worker():
            log.info("Point picker started")

            def on_click(x, y, button, pressed):
                if pressed:
                    log.info(f"Point picked at ({x}, {y})")
                    self.point_picked.emit(x, y)
                    self.finished.emit()
                    return False

            with mouse.Listener(on_click=on_click) as listener:
                listener.join()

        threading.Thread(target=worker, daemon=True).start()
