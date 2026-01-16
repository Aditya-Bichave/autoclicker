import threading
import time
import datetime
from PySide6.QtCore import QObject, Signal
from core.logging_setup import get_logger

log = get_logger("scheduler")

class Scheduler(QObject):
    job_triggered = Signal(dict)

    def __init__(self):
        super().__init__()
        self.running = False
        self.jobs = []
        self._thread = None
        self._stop_event = threading.Event()

    def start(self):
        if self.running: return
        self.running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("Scheduler started")

    def stop(self):
        self.running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        log.info("Scheduler stopped")

    def update_job(self, profile_name, schedule_data):
        # Remove existing job for this profile
        self.jobs = [j for j in self.jobs if j["profile"] != profile_name]

        if schedule_data.get("enabled"):
            self.jobs.append({
                "profile": profile_name,
                "time": schedule_data.get("time"),
                "executed_today": False
            })
            log.info(f"Scheduled {profile_name} at {schedule_data.get('time')}")

    def _loop(self):
        while self.running:
            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M")

            # Reset executed flags at midnight
            if now.hour == 0 and now.minute == 0 and now.second < 2:
                for j in self.jobs: j["executed_today"] = False

            for job in self.jobs:
                if not job["executed_today"] and job["time"] == current_time:
                    log.info(f"Triggering scheduled job: {job['profile']}")
                    self.job_triggered.emit(job)
                    job["executed_today"] = True

            if self._stop_event.wait(1):
                break
