import time
import threading
import ctypes
import platform
import random
from ctypes import wintypes
from PySide6.QtCore import QObject, Signal
from core.logging_setup import get_logger

log = get_logger("engine")

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
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

    # Pre-create inputs to avoid ctypes overhead in loop
    _INPUT_MOUSE_MOVE = INPUT(INPUT_MOUSE, MOUSEINPUT(0, 0, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, 0))
    _INPUT_LEFT_DOWN = INPUT(INPUT_MOUSE, MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, 0))
    _INPUT_LEFT_UP = INPUT(INPUT_MOUSE, MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, 0))
    _INPUT_RIGHT_DOWN = INPUT(INPUT_MOUSE, MOUSEINPUT(0, 0, 0, MOUSEEVENTF_RIGHTDOWN, 0, 0))
    _INPUT_RIGHT_UP = INPUT(INPUT_MOUSE, MOUSEINPUT(0, 0, 0, MOUSEEVENTF_RIGHTUP, 0, 0))

    def get_click_inputs(x, y, click_type):
        x = max(VX, min(x, VX + VW - 1))
        y = max(VY, min(y, VY + VH - 1))

        abs_x = int((x - VX) * 65535 / VW)
        abs_y = int((y - VY) * 65535 / VH)

        # Update move input
        move = INPUT(INPUT_MOUSE, MOUSEINPUT(abs_x, abs_y, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, 0))

        if click_type == "left":
            return [move, _INPUT_LEFT_DOWN, _INPUT_LEFT_UP]
        else:
            return [move, _INPUT_RIGHT_DOWN, _INPUT_RIGHT_UP]

    def send_inputs(inputs_list):
        n = len(inputs_list)
        if n == 0: return
        arr = (INPUT * n)(*inputs_list)
        try:
            if user32.SendInput(n, ctypes.byref(arr), ctypes.sizeof(INPUT)) == 0:
                # Log but don't crash thread?
                # raise ctypes.WinError(ctypes.get_last_error())
                log.error(f"SendInput failed: {ctypes.WinError(ctypes.get_last_error())}")
        except OSError as e:
            log.error(f"SendInput OS error: {e}")

else:
    def get_click_inputs(x, y, click_type):
        # Return dummy inputs to simulate 3 events per click (move, down, up)
        return [1, 2, 3]

    def send_inputs(inputs_list):
        pass

class ClickEngine(QObject):
    started = Signal()
    stopped = Signal()
    error = Signal(str)
    cps_updated = Signal(int)

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
            points = cfg["points"]
            mode = cfg["click_mode"]
            click_type = cfg["click_type"]
            tuning = cfg.get("tuning", {})
            game_safe = tuning.get("game_safe", False)

            min_delay = tuning.get("min_delay_ms", 2) / 1000
            jitter_px = tuning.get("jitter", {}).get("px", 0)
            jitter_pct = tuning.get("jitter", {}).get("percent", 0) / 100
            batch_size = tuning.get("batch_size", 1)

            if game_safe:
                # Enforce safe limits
                min_delay = max(min_delay, 0.050) # 50ms (20 CPS max)
                jitter_px = max(jitter_px, 2)
                jitter_pct = max(jitter_pct, 0.10) # 10%

            base_delay = max(cfg["delay_ms"], min_delay * 1000) / 1000
            if game_safe:
                base_delay = max(base_delay, 0.050)

            # Limits & Burst
            click_limit = cfg.get("click_limit", {})
            limit_enabled = click_limit.get("enabled", False)
            limit_count = click_limit.get("count", 0)
            total_clicks = 0

            burst = cfg.get("burst", {})
            burst_enabled = burst.get("enabled", False)
            burst_size = burst.get("size", 10)
            burst_interval = burst.get("interval_ms", 500) / 1000.0
            burst_counter = 0

            next_tick = time.perf_counter()
            clicks_this_sec = 0
            last_cps_time = time.perf_counter()

            while not self._stop.is_set():
                now = time.perf_counter()

                # CPS
                if now - last_cps_time >= 1.0:
                    self.cps_updated.emit(clicks_this_sec)
                    clicks_this_sec = 0
                    last_cps_time = now

                # Jitter Delay
                current_delay = base_delay
                if jitter_pct > 0:
                    current_delay += base_delay * random.uniform(-jitter_pct, jitter_pct)

                next_tick += max(current_delay, 0.001)

                def get_jp(p):
                    jx, jy = 0, 0
                    if jitter_px > 0:
                        jx = random.randint(-jitter_px, jitter_px)
                        jy = random.randint(-jitter_px, jitter_px)
                    return (int(p.get("x",0)) + jx, int(p.get("y",0)) + jy)

                input_buffer = []

                def flush_buffer():
                    nonlocal input_buffer, clicks_this_sec, total_clicks, burst_counter
                    if input_buffer:
                        count = len(input_buffer) // 3 # 3 inputs per click
                        send_inputs(input_buffer)
                        clicks_this_sec += count
                        total_clicks += count
                        burst_counter += count
                        input_buffer = []

                if mode == "simultaneous":
                    for p in points:
                        jx, jy = get_jp(p)
                        ctype = p.get("type", click_type)
                        input_buffer.extend(get_click_inputs(jx, jy, ctype))

                    flush_buffer()

                elif mode == "sequential":
                    for p in points:
                        if self._stop.is_set(): return
                        jx, jy = get_jp(p)
                        ctype = p.get("type", click_type)
                        input_buffer.extend(get_click_inputs(jx, jy, ctype))

                        # Flush immediately for sequential unless batching > 1
                        # If batching > 1, we might group sequential clicks?
                        # Usually sequential implies distinct events.
                        # I'll flush immediately to respect sequential nature.
                        flush_buffer()

                elif mode == "grouped":
                    # Simple implementation for grouped: split in two
                    mid = max(1, len(points)//2)
                    groups = [points[:mid], points[mid:]]
                    for group in groups:
                        for p in group:
                            jx, jy = get_jp(p)
                            input_buffer.extend(get_click_inputs(jx, jy, p.get("type", click_type)))
                        flush_buffer()
                        time.sleep(0.001)

                # Check limits
                if limit_enabled and total_clicks >= limit_count:
                    log.info(f"Click limit reached: {total_clicks}")
                    return

                # Check burst
                if burst_enabled and burst_counter >= burst_size:
                    burst_counter = 0
                    end_wait = time.perf_counter() + burst_interval
                    while time.perf_counter() < end_wait:
                        if self._stop.is_set(): return
                        time.sleep(0.001)
                    # Reset timing to avoid catch-up speed burst
                    next_tick = time.perf_counter()

                # Wait for next tick
                now = time.perf_counter()
                wait = next_tick - now
                if wait > 0:
                    if wait > 0.002:
                        time.sleep(wait - 0.0015)
                    # Busy wait
                    while time.perf_counter() < next_tick:
                        if self._stop.is_set(): return
                else:
                    # Lagging
                    next_tick = time.perf_counter()

        except Exception as e:
            log.critical("Engine crashed", exc_info=True)
            self.error.emit(str(e))
        finally:
            log.info("Engine loop finished")
            with self._lock:
                was_running = self.running
                self.running = False

            if was_running:
                self.stopped.emit()
