import json
from pathlib import Path
from core.logging_setup import get_logger

log = get_logger("macro_manager")

class MacroManager:
    def __init__(self, macro_dir="macros"):
        import sys
        if getattr(sys, 'frozen', False):
            base = Path(sys.executable).parent
        else:
            base = Path(sys.argv[0]).parent

        self.macro_dir = base / macro_dir
        self.macro_dir.mkdir(exist_ok=True)

    def list_macros(self):
        return sorted(p.stem for p in self.macro_dir.glob("*.json"))

    def save(self, name, events):
        path = self.macro_dir / f"{name}.json"
        data = {
            "version": 1,
            "name": name,
            "events": events
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        log.info(f"Saved macro: {name}")

    def load(self, name):
        path = self.macro_dir / f"{name}.json"
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("events", [])

    def delete(self, name):
        path = self.macro_dir / f"{name}.json"
        if path.exists():
            path.unlink()
            log.info(f"Deleted macro: {name}")
