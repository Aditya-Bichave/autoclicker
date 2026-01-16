import json
from pathlib import Path
from logging_setup import logging

log = logging.getLogger("config")

PROFILE_DIR = Path("profiles")
PROFILE_DIR.mkdir(exist_ok=True)

DEFAULT_PROFILE = {
    "version": 1,
    "name": "default",
    "delay_ms": 5,
    "click_type": "left",
    "click_mode": "simultaneous",
    "toggle_key": "f6",
    "kill_key": "esc",
    "points": []
}

def _atomic_write(path, data):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        f.flush()
    tmp.replace(path)
    log.debug(f"Profile written: {path.name}")

def normalize(name, data):
    merged = {**DEFAULT_PROFILE, **data}
    merged["name"] = name
    return merged

def load_profile(name):
    path = PROFILE_DIR / f"{name}.json"
    log.info(f"Loading profile: {name}")

    try:
        if not path.exists():
            profile = normalize(name, {})
            _atomic_write(path, profile)
            return profile

        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            raise ValueError("Empty profile")

        data = json.loads(raw)
        profile = normalize(name, data)
        _atomic_write(path, profile)
        return profile

    except Exception:
        log.exception("Profile load failed, recovering")
        profile = normalize(name, {})
        _atomic_write(path, profile)
        return profile

def save_profile(name, data):
    log.info(f"Saving profile: {name}")
    profile = normalize(name, data)
    _atomic_write(PROFILE_DIR / f"{name}.json", profile)

def list_profiles():
    return sorted(p.stem for p in PROFILE_DIR.glob("*.json"))
