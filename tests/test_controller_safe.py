import unittest
import sys
from unittest.mock import MagicMock, patch

# Mock pynput BEFORE import
mock_pynput = MagicMock()
sys.modules["pynput"] = mock_pynput
sys.modules["pynput.mouse"] = MagicMock()
sys.modules["pynput.keyboard"] = MagicMock()

# Now import
from core.controller import Controller

class TestControllerSafe(unittest.TestCase):
    def setUp(self):
        self.ui = MagicMock()
        self.app_state = MagicMock()
        self.pm = MagicMock()
        self.mm = MagicMock()

        self.app_state.active_profile = {
            "name": "default",
            "toggle_key": "F6",
            "kill_key": "Esc"
        }

        self.ctrl = Controller(self.ui, self.app_state, self.pm, self.mm)

    def test_init(self):
        self.assertIsNotNone(self.ctrl)

    def test_toggle(self):
        self.ui.tabs.currentIndex.return_value = 0
        self.ctrl.engine.running = False
        self.ui.get_config.return_value = {"points": []}

        with patch.object(self.ctrl.engine, "start") as mock_start:
            self.ctrl.toggle()
            mock_start.assert_called()

    def test_emergency_stop(self):
        with patch.object(self.ctrl.engine, "stop") as s1, \
             patch.object(self.ctrl.recorder, "stop") as s2, \
             patch.object(self.ctrl.player, "stop") as s3:

            self.ctrl.engine.running = True
            self.ctrl.recorder.running = True
            self.ctrl.player.running = True

            self.ctrl.emergency_stop()

            s1.assert_called()
            s2.assert_called()
            s3.assert_called()

if __name__ == "__main__":
    unittest.main()
