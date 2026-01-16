import time
import threading
import json
import ctypes
import platform
from pynput import mouse, keyboard
from PySide6.QtCore import QObject, Signal
from core.logging_setup import get_logger

log = get_logger("macro_engine")

def get_screen_rect():
    if platform.system() == "Windows":
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            SM_XVIRTUALSCREEN = 76
            SM_YVIRTUALSCREEN = 77
            SM_CXVIRTUALSCREEN = 78
            SM_CYVIRTUALSCREEN = 79
            return (
                user32.GetSystemMetrics(SM_XVIRTUALSCREEN),
                user32.GetSystemMetrics(SM_YVIRTUALSCREEN),
                user32.GetSystemMetrics(SM_CXVIRTUALSCREEN),
                user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
            )
        except:
            return 0, 0, 1920, 1080
    else:
        return 0, 0, 1920, 1080

class MacroRecorder(QObject):
    finished = Signal(list)

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
        self.rect = get_screen_rect()

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

    def play(self, events, speed=1.0):
        if self.running: return
        self.running = True
        log.info(f"Macro playback started. Speed: {speed}x")
        threading.Thread(target=self._play_loop, args=(events, speed), daemon=True).start()

    def stop(self):
        if self.running:
            self.running = False
            log.info("Macro playback stopped")

    def _play_loop(self, events, speed):
        start_time = time.perf_counter()
        try:
            for event in events:
                if not self.running: break

                target_time = event["t"] / speed
                while time.perf_counter() - start_time < target_time:
                    if not self.running: break
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
        vx, vy, vw, vh = get_screen_rect()

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
