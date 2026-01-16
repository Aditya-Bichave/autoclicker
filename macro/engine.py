import time
import threading
import json
import ctypes
import platform
from pynput import mouse, keyboard
from PySide6.QtCore import QObject, Signal
from core.logging_setup import get_logger
from core.screen_utils import get_virtual_screen_rect

log = get_logger("macro_engine")

class MacroRecorder(QObject):
    finished = Signal(list)
    MAX_DURATION = 3600 # 1 hour

    def __init__(self):
        super().__init__()
        self.events = []
        self.start_time = 0
        self.running = False
        self._m_listener = None
        self._k_listener = None
        self.rect = (0, 0, 1920, 1080)

    def start(self):
        self.events = []
        self.start_time = time.perf_counter()
        self.running = True
        self.rect = get_virtual_screen_rect()

        self._m_listener = mouse.Listener(
            on_click=self._on_click,
            on_scroll=self._on_scroll)
        self._k_listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release)

        self._m_listener.start()
        self._k_listener.start()
        log.info("Macro recording started")

    def stop(self):
        if not self.running: return
        self.running = False
        if self._m_listener:
            self._m_listener.stop()
            self._m_listener = None
        if self._k_listener:
            self._k_listener.stop()
            self._k_listener = None

        log.info(f"Macro recording stopped. {len(self.events)} events.")
        self.finished.emit(self.events)

    def _record(self, type_, data):
        if not self.running: return
        dt = time.perf_counter() - self.start_time
        if dt > self.MAX_DURATION:
            log.warning("Macro recording reached max duration")
            self.stop()
            return
        self.events.append({"t": dt, "type": type_, "data": data})

    def _on_click(self, x, y, button, pressed):
        vx, vy, vw, vh = self.rect
        nx = (x - vx) / vw
        ny = (y - vy) / vh
        self._record("mouse_click", {"x": nx, "y": ny, "button": str(button), "pressed": pressed})

    def _on_scroll(self, x, y, dx, dy):
        vx, vy, vw, vh = self.rect
        nx = (x - vx) / vw
        ny = (y - vy) / vh
        self._record("mouse_scroll", {"x": nx, "y": ny, "dx": dx, "dy": dy})

    def _on_press(self, key):
        try: k = key.char
        except: k = str(key)
        self._record("key_press", {"key": k})

    def _on_release(self, key):
        try: k = key.char
        except: k = str(key)
        self._record("key_release", {"key": k})

class MacroPlayer(QObject):
    finished = Signal()

    def __init__(self):
        super().__init__()
        self.running = False
        self.mouse_ctl = mouse.Controller()
        self.key_ctl = keyboard.Controller()

    def play(self, events, speed=1.0, instant=False):
        if self.running: return
        self.running = True
        log.info(f"Macro playback started. Speed: {speed}x, Instant: {instant}")
        threading.Thread(target=self._play_loop, args=(events, speed, instant), daemon=True).start()

    def stop(self):
        if self.running:
            self.running = False
            log.info("Macro playback stopped")

    def _play_loop(self, events, speed, instant):
        start_time = time.perf_counter()
        try:
            for event in events:
                if not self.running: break

                if not instant:
                    target_time = event["t"] / speed
                    while time.perf_counter() - start_time < target_time:
                        if not self.running: break
                        time.sleep(0.001)
                else:
                    # Minimum safety delay even for instant
                    time.sleep(0.001)

                if not self.running: break
                self._execute_event(event)
        except Exception as e:
            log.error(f"Macro playback error: {e}")

        self.running = False
        self.finished.emit()

    def _execute_event(self, event):
        t = event["type"]
        d = event["data"]
        vx, vy, vw, vh = get_virtual_screen_rect()

        if t == "mouse_click":
            abs_x = int(vx + d["x"] * vw)
            abs_y = int(vy + d["y"] * vh)
            self.mouse_ctl.position = (abs_x, abs_y)
            btn = getattr(mouse.Button, d["button"].split('.')[-1], mouse.Button.left)
            if d["pressed"]:
                self.mouse_ctl.press(btn)
            else:
                self.mouse_ctl.release(btn)

        elif t == "mouse_scroll":
            abs_x = int(vx + d["x"] * vw)
            abs_y = int(vy + d["y"] * vh)
            self.mouse_ctl.position = (abs_x, abs_y)
            self.mouse_ctl.scroll(d["dx"], d["dy"])

        elif t == "key_press":
            k = self._parse_key(d["key"])
            self.key_ctl.press(k)

        elif t == "key_release":
            k = self._parse_key(d["key"])
            self.key_ctl.release(k)

    def _parse_key(self, k_str):
        # Basic parsing
        if len(k_str) == 1:
            return k_str
        # Key.space -> keyboard.Key.space
        if k_str.startswith("Key."):
            attr = k_str.split('.')[1]
            return getattr(keyboard.Key, attr, k_str)
        return k_str
