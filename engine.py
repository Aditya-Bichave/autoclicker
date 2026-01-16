import time
import threading
import ctypes
from ctypes import wintypes
from PySide6.QtCore import QObject, Signal
from logging_setup import get_logger

log = get_logger("engine")
user32 = ctypes.WinDLL("user32", use_last_error=True)

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

INPUT_MOUSE = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_MOVE = 0x0001

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

VX = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
VY = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
VW = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
VH = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("mi", MOUSEINPUT)]

def send_click(x, y, click_type):
    x = max(VX, min(x, VX + VW - 1))
    y = max(VY, min(y, VY + VH - 1))

    abs_x = int((x - VX) * 65535 / VW)
    abs_y = int((y - VY) * 65535 / VH)

    down = MOUSEEVENTF_LEFTDOWN if click_type == "left" else MOUSEEVENTF_RIGHTDOWN
    up   = MOUSEEVENTF_LEFTUP   if click_type == "left" else MOUSEEVENTF_RIGHTUP

    inputs = (INPUT * 3)(
        INPUT(INPUT_MOUSE, MOUSEINPUT(abs_x, abs_y, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, 0)),
        INPUT(INPUT_MOUSE, MOUSEINPUT(0, 0, 0, down, 0, 0)),
        INPUT(INPUT_MOUSE, MOUSEINPUT(0, 0, 0, up, 0, 0)),
    )

    if user32.SendInput(3, ctypes.byref(inputs), ctypes.sizeof(INPUT)) == 0:
        raise ctypes.WinError(ctypes.get_last_error())

class ClickEngine(QObject):
    started = Signal()
    stopped = Signal()
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self.running = False
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.Lock()

    def start(self, cfg):
        with self._lock:
            if self.running:
                log.debug("Start ignored: already running")
                return
            if not cfg.get("points"):
                self.error.emit("No click points defined")
                return

            self.running = True
            self._stop.clear()

            self._thread = threading.Thread(
                target=self._loop,
                args=(cfg,),
                daemon=True,
                name="ClickEngineThread"
            )
            log.info("Engine thread starting")
            self._thread.start()
            self.started.emit()

    def stop(self):
        with self._lock:
            if not self.running:
                log.debug("Stop ignored: not running")
                return
            log.info("Stopping engine")
            self.running = False
            self._stop.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

        self.stopped.emit()

    def _loop(self, cfg):
        try:
            delay = max(cfg["delay_ms"], 2) / 1000
            points = cfg["points"]
            mode = cfg["click_mode"]
            click = cfg["click_type"]

            next_tick = time.perf_counter()

            while not self._stop.is_set():
                next_tick += delay

                if mode == "simultaneous":
                    for p in points:
                        send_click(*p, click)

                elif mode == "sequential":
                    for p in points:
                        if self._stop.is_set():
                            return
                        send_click(*p, click)

                elif mode == "grouped":
                    mid = max(1, len(points)//2)
                    for group in (points[:mid], points[mid:]):
                        for p in group:
                            send_click(*p, click)
                        time.sleep(0.001)

                while time.perf_counter() < next_tick:
                    if self._stop.is_set():
                        return
                    time.sleep(0.0005)

        except Exception as e:
            log.critical("Engine crashed", exc_info=True)
            self.error.emit(str(e))
            self.running = False
            self.stopped.emit()
