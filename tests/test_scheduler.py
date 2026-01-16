import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scheduler.scheduler import Scheduler

class TestScheduler(unittest.TestCase):
    def test_update_job(self):
        s = Scheduler()

        # Add job
        s.update_job("p1", {"enabled": True, "time": "12:00"})
        self.assertEqual(len(s.jobs), 1)
        self.assertEqual(s.jobs[0]["profile"], "p1")
        self.assertEqual(s.jobs[0]["time"], "12:00")

        # Update job (same profile)
        s.update_job("p1", {"enabled": True, "time": "13:00"})
        self.assertEqual(len(s.jobs), 1)
        self.assertEqual(s.jobs[0]["time"], "13:00")

        # Disable job
        s.update_job("p1", {"enabled": False})
        self.assertEqual(len(s.jobs), 0)

if __name__ == "__main__":
    unittest.main()
