import unittest
import shutil
from pathlib import Path
from core.app_state import AppState
from core.global_config import GlobalConfig

class TestAppState(unittest.TestCase):
    def test_defaults(self):
        state = AppState()
        self.assertFalse(state.engine_running)
        self.assertFalse(state.unsaved_changes)
        self.assertIsNone(state.active_profile)

class TestGlobalConfig(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_config")
        self.test_dir.mkdir(exist_ok=True)
        self.cfg_path = self.test_dir / "config.json"

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_load_save(self):
        cfg = GlobalConfig("test_config/config.json")
        # Override path because init uses argv
        cfg.path = self.cfg_path

        cfg.set("theme", "Light")
        self.assertEqual(cfg.get("theme"), "Light")

        # Verify file
        import json
        with open(self.cfg_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["theme"], "Light")

    def test_defaults(self):
        cfg = GlobalConfig("test_config/missing.json")
        cfg.path = self.test_dir / "missing.json"
        self.assertEqual(cfg.get("theme"), "Dark")

if __name__ == "__main__":
    unittest.main()
