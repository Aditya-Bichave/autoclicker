from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QPen, QColor, QBrush
from core.screen_utils import get_virtual_screen_rect

class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # In multi-monitor setup, use virtual geometry
        vx, vy, vw, vh = get_virtual_screen_rect()
        self.setGeometry(vx, vy, vw, vh)

        self.points = []

    def update_points(self, points):
        self.points = points
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        vx, vy, vw, vh = get_virtual_screen_rect()

        for p in self.points:
            x, y = p["x"], p["y"]

            if isinstance(x, float):
                abs_x = int(vx + x * vw)
                abs_y = int(vy + y * vh)
            else:
                abs_x, abs_y = int(x), int(y)

            # Map global to local
            local_p = self.mapFromGlobal(QPoint(abs_x, abs_y))
            lx, ly = local_p.x(), local_p.y()

            group = p.get("group", 0)

            # Simple color coding based on group
            if group == 0:
                color = QColor(0, 255, 0, 200) # Green
            elif group == 1:
                color = QColor(0, 0, 255, 200) # Blue
            elif group == 2:
                color = QColor(255, 0, 0, 200) # Red
            else:
                color = QColor(255, 255, 0, 200) # Yellow

            pen = QPen(color)
            pen.setWidth(2)
            painter.setPen(pen)
            color.setAlpha(50)
            painter.setBrush(QBrush(color))

            painter.drawEllipse(lx - 10, ly - 10, 20, 20)
