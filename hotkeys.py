from pynput import keyboard
from logging_setup import logging

log = logging.getLogger("hotkeys")

KEY_MAP = {
    "esc": keyboard.Key.esc,
    "f6": keyboard.Key.f6,
    "f7": keyboard.Key.f7,
    "f8": keyboard.Key.f8,
}

class Hotkeys:
    def __init__(self, toggle, kill, on_toggle, on_kill):
        self.toggle = toggle
        self.kill = kill
        self.on_toggle = on_toggle
        self.on_kill = on_kill
        self.listener = None

    def start(self):
        log.info("Hotkeys started")

        def on_press(key):
            if key == KEY_MAP.get(self.toggle):
                self.on_toggle()
            elif key == KEY_MAP.get(self.kill):
                self.on_kill()

        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.daemon = True
        self.listener.start()

    def stop(self):
        log.info("Hotkeys stopped")
        if self.listener:
            self.listener.stop()
