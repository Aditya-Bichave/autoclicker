import unittest
import shutil
from pathlib import Path
import sys
import os

# Add root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.profile_manager import ProfileManager
from core.screen_utils import get_virtual_screen_rect

class TestProfileManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_profiles")
        self.test_dir.mkdir(exist_ok=True)
        # Mock sys.argv for ProfileManager path resolution if needed
        # But ProfileManager uses sys.argv[0].parent.
        # In test, sys.argv[0] is this script. parent is tests/.
        # So it will create test_profiles inside tests/ or relative to it.
        # We pass profile_dir relative.
        self.pm = ProfileManager(profile_dir="test_profiles")
        # Fix pm path to be absolute or relative to CWD if needed?
        # ProfileManager init logic:
        # base = Path(sys.argv[0]).parent
        # self.profile_dir = base / profile_dir
        # If running from root via python -m unittest, sys.argv[0] might be runner.
        # Let's override self.pm.profile_dir to ensure it points to our temp dir
        self.pm.profile_dir = self.test_dir

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_default_profile(self):
        p = self.pm.load("new_profile")
        self.assertEqual(p["version"], 2)
        self.assertIn("tuning", p)
        self.assertIn("schedule", p)
        self.assertEqual(p["schedule"]["type"], "profile")

    def test_migration_v1(self):
        # Create v1 profile
        data = {
            "version": 1,
            "points": [[100, 200], [300, 400]]
        }
        name = "v1_prof"
        path = self.test_dir / f"{name}.json"
        import json
        with open(path, "w") as f:
            json.dump(data, f)

        # Load and verify migration
        p = self.pm.load(name)
        self.assertEqual(p["version"], 2)
        self.assertEqual(len(p["points"]), 2)
        self.assertEqual(p["points"][0]["x"], 100)
        self.assertIn("failsafe", p)

class TestCoordinates(unittest.TestCase):
    def test_normalization(self):
        vx, vy, vw, vh = get_virtual_screen_rect()
        # In headless/linux without X, this returns 0,0,1920,1080 (fallback)

        # Simulate pick
        x_abs = vx + vw / 2
        y_abs = vy + vh / 2

        nx = (x_abs - vx) / vw
        ny = (y_abs - vy) / vh

        self.assertAlmostEqual(nx, 0.5)
        self.assertAlmostEqual(ny, 0.5)

if __name__ == "__main__":
    unittest.main()
