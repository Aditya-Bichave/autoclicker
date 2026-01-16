import json
from pathlib import Path
from core.logging_setup import get_logger

log = get_logger("profile_manager")

class ProfileManager:
    DEFAULT_PROFILE = {
        "version": 2,
        "name": "default",
        "delay_ms": 5,
        "click_type": "left",
        "click_mode": "simultaneous",
        "toggle_key": "f6",
        "kill_key": "esc",
        "points": [],
        "resolution": [1920, 1080],
        "tuning": {
             "min_delay_ms": 2,
             "busy_wait_us": 500,
             "batch_size": 1,
             "jitter": {"px": 0, "percent": 0},
             "cps_cap": 0
        },
        "schedule": {"enabled": False, "time": "12:00", "repeat": False},
        "failsafe": {"enabled": False, "timeout": 60}
    }

    def __init__(self, profile_dir="profiles"):
        import sys
        if getattr(sys, 'frozen', False):
            base = Path(sys.executable).parent
        else:
            base = Path(sys.argv[0]).parent

        self.profile_dir = base / profile_dir
        self.profile_dir.mkdir(exist_ok=True)

    def _atomic_write(self, path, data):
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            f.flush()
        tmp.replace(path)
        log.debug(f"Profile written: {path.name}")

    def migrate_profile(self, data):
        version = data.get("version", 1)

        # Always check and fix points structure, regardless of version
        if "points" in data:
             new_points = []
             changed = False
             for p in data["points"]:
                 if isinstance(p, (list, tuple)):
                     new_points.append({
                         "x": int(p[0]),
                         "y": int(p[1]),
                         "type": data.get("click_type", "left"),
                         "delay": 0,
                         "label": "",
                         "group": 0
                     })
                     changed = True
                 elif isinstance(p, dict):
                     # Ensure required fields
                     if "x" not in p or "y" not in p:
                         continue # Skip invalid
                     new_points.append(p)
                 else:
                     # Invalid format, skip
                     continue

             if changed or len(new_points) != len(data["points"]):
                 data["points"] = new_points

        if version < 2:
            log.info(f"Migrating profile {data.get('name', 'unknown')} v{version} -> v2")
            data["version"] = 2
            if "resolution" not in data:
                data["resolution"] = self.DEFAULT_PROFILE["resolution"]
            if "tuning" not in data:
                data["tuning"] = self.DEFAULT_PROFILE["tuning"].copy()
            if "schedule" not in data:
                data["schedule"] = self.DEFAULT_PROFILE["schedule"].copy()
            if "failsafe" not in data:
                data["failsafe"] = self.DEFAULT_PROFILE["failsafe"].copy()

        return data

    def normalize(self, name, data):
        data = self.migrate_profile(data)
        merged = {**self.DEFAULT_PROFILE, **data}
        merged["name"] = name
        return merged

    def load(self, name):
        path = self.profile_dir / f"{name}.json"
        log.info(f"Loading profile: {name}")

        try:
            if not path.exists():
                profile = self.normalize(name, {})
                self._atomic_write(path, profile)
                return profile

            raw = path.read_text(encoding="utf-8").strip()
            if not raw:
                raise ValueError("Empty profile")

            data = json.loads(raw)
            profile = self.normalize(name, data)
            self._atomic_write(path, profile)
            return profile

        except Exception:
            log.exception("Profile load failed, recovering")
            profile = self.normalize(name, {})
            self._atomic_write(path, profile)
            return profile

    def save(self, name, data):
        log.info(f"Saving profile: {name}")
        profile = self.normalize(name, data)
        self._atomic_write(self.profile_dir / f"{name}.json", profile)

    def list_profiles(self):
        return sorted(p.stem for p in self.profile_dir.glob("*.json"))

    def delete(self, name):
        path = self.profile_dir / f"{name}.json"
        if path.exists():
            path.unlink()
            log.info(f"Deleted profile: {name}")
        else:
            log.warning(f"Delete failed: profile {name} not found")
