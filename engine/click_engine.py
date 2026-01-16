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
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

    INPUT_MOUSE = 0
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_ABSOLUTE = 0x8000
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_VIRTUALDESK = 0x4000

    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79

    VX = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    VY = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    VW = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    VH = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

    log.info(f"Screen Metrics: VX={VX}, VY={VY}, VW={VW}, VH={VH}")

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
        flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE

        if isinstance(x, float):
            # Normalized coordinates (0.0-1.0)
            abs_x = int(x * 65535)
            abs_y = int(y * 65535)
            flags |= MOUSEEVENTF_VIRTUALDESK
        else:
            # Absolute coordinates
            x = max(VX, min(x, VX + VW - 1))
            y = max(VY, min(y, VY + VH - 1))
            abs_x = int((x - VX) * 65535 / VW)
            abs_y = int((y - VY) * 65535 / VH)
            # Use Virtual Desk if we are mapping to virtual screen space explicitly?
            # Existing logic maps (x-VX) to 0..65535 over VW. This IS virtual desk mapping.
            # Without the flag, it maps to primary monitor.
            # We should probably enable it for absolute too if we want multi-monitor support.
            flags |= MOUSEEVENTF_VIRTUALDESK

        # Update move input
        move = INPUT(INPUT_MOUSE, MOUSEINPUT(abs_x, abs_y, 0, flags, 0, 0))

        if click_type == "left":
            return (move, _INPUT_LEFT_DOWN, _INPUT_LEFT_UP)
        else:
            return (move, _INPUT_RIGHT_DOWN, _INPUT_RIGHT_UP)

    def send_inputs(inputs_list, retry_count=3):
        n = len(inputs_list)
        if n == 0: return
        arr = (INPUT * n)(*inputs_list)

        for i in range(retry_count + 1):
            try:
                if user32.SendInput(n, ctypes.byref(arr), ctypes.sizeof(INPUT)) > 0:
                    return

                err = ctypes.get_last_error()
                log.warning(f"SendInput failed (attempt {i+1}): {ctypes.WinError(err)}")
                time.sleep(0.01)
            except OSError as e:
                log.error(f"SendInput OS error: {e}")
                break
        log.error("SendInput failed after retries")

else:
    def get_click_inputs(x, y, click_type):
        # Return dummy inputs to simulate 3 events per click (move, down, up)
        return [1, 2, 3]

    def send_inputs(inputs_list, retry_count=3):
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
            busy_wait_sec = tuning.get("busy_wait_us", 500) / 1_000_000.0
            retry_count = tuning.get("retry_count", 3)
            overload_threshold = tuning.get("overload_threshold", 10)

            if game_safe:
                # Enforce safe limits
                min_delay = max(min_delay, 0.050) # 50ms (20 CPS max)
                jitter_px = max(jitter_px, 2)
                jitter_pct = max(jitter_pct, 0.10) # 10%
                # Override priority to normal to avoid suspicious consistency
                tuning["thread_priority"] = "normal"

            # Thread Priority (Windows)
            if IS_WINDOWS:
                p_map = {
                    "idle": -15, "lowest": -2, "below_normal": -1, "normal": 0,
                    "above_normal": 1, "highest": 2, "time_critical": 15
                }
                p_str = tuning.get("thread_priority", "normal")
                if game_safe: p_str = "normal"

                p_val = p_map.get(p_str, 0)
                try:
                    kernel32.SetThreadPriority(kernel32.GetCurrentThread(), p_val)
                except Exception as e:
                    log.error(f"Failed to set thread priority: {e}")

            if game_safe:
                min_delay = max(min_delay, 0.050) # 50ms (20 CPS max)
                jitter_px = max(jitter_px, 2)
                jitter_pct = max(jitter_pct, 0.10) # 10%

            hold_time_ms = cfg.get("hold_time_ms", 0)
            cps_cap = tuning.get("cps_cap", 0)

            base_delay = max(cfg["delay_ms"], min_delay * 1000) / 1000
            if cps_cap > 0:
                base_delay = max(base_delay, 1.0 / cps_cap)

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

            consecutive_lag = 0
            last_lag_log = 0

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
                    x = p.get("x", 0)
                    y = p.get("y", 0)

                    jx, jy = 0, 0
                    if jitter_px > 0:
                        jx = random.randint(-jitter_px, jitter_px)
                        jy = random.randint(-jitter_px, jitter_px)

                    if isinstance(x, float):
                        # Convert pixel jitter to normalized jitter
                        return (x + (jx / VW), y + (jy / VH))
                    else:
                        return (int(x) + jx, int(y) + jy)

                input_buffer = []
                move_buffer = []
                down_buffer = []
                up_buffer = []

                def flush_buffer():
                    nonlocal input_buffer, move_buffer, down_buffer, up_buffer, clicks_this_sec, total_clicks, burst_counter

                    count = 0
                    if hold_time_ms > 0:
                        if down_buffer:
                            count = len(down_buffer)
                            send_inputs(move_buffer + down_buffer, retry_count)
                            time.sleep(hold_time_ms / 1000.0)
                            send_inputs(up_buffer, retry_count)
                            move_buffer = []
                            down_buffer = []
                            up_buffer = []
                    else:
                        if input_buffer:
                            count = len(input_buffer) // 3
                            send_inputs(input_buffer, retry_count)
                            input_buffer = []

                    if count > 0:
                        clicks_this_sec += count
                        total_clicks += count
                        burst_counter += count

                def add_click(m, d, u):
                    if hold_time_ms > 0:
                        move_buffer.append(m)
                        down_buffer.append(d)
                        up_buffer.append(u)
                    else:
                        input_buffer.extend([m, d, u])

                if mode == "simultaneous":
                    for p in points:
                        jx, jy = get_jp(p)
                        ctype = p.get("type", click_type)
                        add_click(*get_click_inputs(jx, jy, ctype))

                    flush_buffer()

                elif mode == "sequential":
                    batch_counter = 0
                    for p in points:
                        if self._stop.is_set(): return
                        jx, jy = get_jp(p)
                        ctype = p.get("type", click_type)
                        add_click(*get_click_inputs(jx, jy, ctype))

                        batch_counter += 1
                        if batch_counter >= batch_size:
                            flush_buffer()
                            batch_counter = 0
                    # Flush remaining
                    flush_buffer()

                elif mode == "grouped":
                    mid = max(1, len(points)//2)
                    groups = [points[:mid], points[mid:]]
                    for group in groups:
                        for p in group:
                            jx, jy = get_jp(p)
                            add_click(*get_click_inputs(jx, jy, p.get("type", click_type)))
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
                    if wait > busy_wait_sec:
                        time.sleep(wait - busy_wait_sec)
                    # Busy wait
                    while time.perf_counter() < next_tick:
                        if self._stop.is_set(): return
                    consecutive_lag = 0
                else:
                    # Lagging
                    consecutive_lag += 1
                    if consecutive_lag > overload_threshold and (time.time() - last_lag_log > 5):
                        log.warning(f"Engine overloaded/lagging. Behind by {consecutive_lag} ticks.")
                        last_lag_log = time.time()

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
