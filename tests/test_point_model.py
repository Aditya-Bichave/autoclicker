import unittest
from PySide6.QtCore import Qt
from ui.point_model import PointModel

class TestPointModel(unittest.TestCase):
    def test_init(self):
        model = PointModel()
        self.assertEqual(model.rowCount(), 0)

        points = [{"x": 10, "y": 20}]
        model = PointModel(points)
        self.assertEqual(model.rowCount(), 1)

    def test_add_remove(self):
        model = PointModel()
        model.add_point(100, 200)
        self.assertEqual(model.rowCount(), 1)
        p = model.get_points()[0]
        self.assertEqual(p["x"], 100)
        self.assertEqual(p["y"], 200)

        model.remove_at(0)
        self.assertEqual(model.rowCount(), 0)

    def test_set_data(self):
        model = PointModel([{"x": 0, "y": 0}])
        idx = model.index(0)

        # Test valid string
        model.setData(idx, "50, 60", Qt.EditRole)
        p = model.get_points()[0]
        self.assertEqual(p["x"], 50)
        self.assertEqual(p["y"], 60)

        # Test float string
        model.setData(idx, "0.5, 0.5", Qt.EditRole)
        p = model.get_points()[0]
        self.assertAlmostEqual(p["x"], 0.5)

    def test_grouping(self):
        model = PointModel([{"x": 0, "y": 0}])
        model.set_group(0, 2)
        p = model.get_points()[0]
        self.assertEqual(p["group"], 2)

    def test_roles(self):
        model = PointModel([{"x": 10, "y": 20, "label": "Test"}])
        idx = model.index(0)

        display = model.data(idx, Qt.DisplayRole)
        self.assertIn("10", display)
        self.assertIn("Test", display)

        edit = model.data(idx, Qt.EditRole)
        self.assertEqual(edit, "10,20")

if __name__ == "__main__":
    unittest.main()
