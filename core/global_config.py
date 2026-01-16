import json
from pathlib import Path
from core.logging_setup import get_logger

log = get_logger("config")

class GlobalConfig:
    def __init__(self, filename="config.json"):
        import sys
        if getattr(sys, 'frozen', False):
            base = Path(sys.executable).parent
        else:
            base = Path(sys.argv[0]).parent

        self.path = base / filename
        self.data = {
            "theme": "Dark",
            "compact_mode": False
        }
        self.load()

    def load(self):
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data.update(json.load(f))
            except Exception as e:
                log.error(f"Failed to load config: {e}")

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            log.error(f"Failed to save config: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()
