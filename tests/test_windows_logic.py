import unittest
import sys
from unittest.mock import MagicMock, patch
import ctypes

class TestWindowsLogic(unittest.TestCase):
    def setUp(self):
        # Remove engine.click_engine from sys.modules to force reload
        if 'engine.click_engine' in sys.modules:
            del sys.modules['engine.click_engine']

        # Inject WinDLL/get_last_error if missing (Linux)
        self.injected = []

        if not hasattr(ctypes, 'WinDLL'):
            self.windll_mock = MagicMock()
            setattr(ctypes, 'WinDLL', self.windll_mock)
            self.injected.append('WinDLL')
        else:
            self.windll_mock = None

        if not hasattr(ctypes, 'get_last_error'):
            setattr(ctypes, 'get_last_error', MagicMock(return_value=0))
            self.injected.append('get_last_error')

        if not hasattr(ctypes, 'WinError'):
            setattr(ctypes, 'WinError', MagicMock(side_effect=lambda x: f"Error {x}"))
            self.injected.append('WinError')

    def tearDown(self):
        for attr in self.injected:
            if hasattr(ctypes, attr):
                delattr(ctypes, attr)

    def test_windows_flow(self):
        with patch('platform.system', return_value='Windows'):
            mock_user32 = MagicMock()
            mock_kernel32 = MagicMock()

            def side_effect(name, **kwargs):
                if 'user32' in name: return mock_user32
                if 'kernel32' in name: return mock_kernel32
                return MagicMock()

            if self.windll_mock:
                self.windll_mock.side_effect = side_effect

            with patch('ctypes.WinDLL', side_effect=side_effect) as mock_dll:
                mock_user32.GetSystemMetrics.return_value = 1000

                import engine.click_engine as ce

                # Check metrics
                self.assertEqual(ce.VX, 1000)

                # Inputs
                inputs = ce.get_click_inputs(10, 10, 'left')
                self.assertEqual(len(inputs), 3)

                # Retry
                mock_user32.SendInput.return_value = 0
                ce.send_inputs(inputs, retry_count=2)
                self.assertEqual(mock_user32.SendInput.call_count, 3)

if __name__ == "__main__":
    unittest.main()
