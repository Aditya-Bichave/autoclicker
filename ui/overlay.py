from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QColor, QBrush

class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        # In multi-monitor setup, showFullScreen usually covers one screen.
        # Ideally we cover virtual geometry.
        # For simple v2, start with FullScreen on primary or current.
        self.showFullScreen()

        self.points = []

    def update_points(self, points):
        self.points = points
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        for p in self.points:
            x, y = p["x"], p["y"]
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

            painter.drawEllipse(x - 10, y - 10, 20, 20)
