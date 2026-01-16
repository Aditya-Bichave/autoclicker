import unittest
import shutil
from pathlib import Path
from macro.manager import MacroManager

class TestMacroManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_macros")
        self.test_dir.mkdir(exist_ok=True)
        self.mgr = MacroManager("test_macros")
        # Override internal dir because init resolves relative to argv[0]
        self.mgr.macro_dir = self.test_dir

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_save_load(self):
        events = [{"t": 0, "type": "click"}]
        self.mgr.save("test_macro", events)

        loaded = self.mgr.load("test_macro")
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["type"], "click")

    def test_list_delete(self):
        self.mgr.save("m1", [])
        self.mgr.save("m2", [])

        macros = self.mgr.list_macros()
        self.assertEqual(len(macros), 2)
        self.assertIn("m1", macros)

        self.mgr.delete("m1")
        macros = self.mgr.list_macros()
        self.assertEqual(len(macros), 1)
        self.assertNotIn("m1", macros)

if __name__ == "__main__":
    unittest.main()
