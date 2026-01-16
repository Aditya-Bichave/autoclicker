import json
from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, QMimeData

class PointModel(QAbstractListModel):
    def __init__(self, points=None):
        super().__init__()
        self._points = points or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._points)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._points)):
            return None

        point = self._points[index.row()]
        # Safeguard against corrupted data
        if not isinstance(point, dict):
            return str(point)

        if role == Qt.DisplayRole:
            label = point.get("label", "")
            if label:
                return f"{point.get('x',0)}, {point.get('y',0)} - {label}"
            return f"{point.get('x',0)}, {point.get('y',0)} ({point.get('type','left')})"

        elif role == Qt.EditRole:
            return f"{point.get('x',0)},{point.get('y',0)}"

        elif role == Qt.UserRole:
            return point

        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False

        try:
            # Simple parsing of "x,y"
            parts = value.split(',')
            if len(parts) >= 2:
                x = int(parts[0].strip())
                y = int(parts[1].strip())

                self._points[index.row()]['x'] = x
                self._points[index.row()]['y'] = y

                self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole, Qt.UserRole])
                return True
        except ValueError:
            pass
        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsDropEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsDragEnabled

    def supportedDropActions(self):
        return Qt.MoveAction

    def mimeTypes(self):
        return ['application/x-point-list']

    def mimeData(self, indexes):
        mime = QMimeData()
        data = []
        for idx in indexes:
             data.append(self._points[idx.row()])
        mime.setData('application/x-point-list', json.dumps(data).encode('utf-8'))
        return mime

    def dropMimeData(self, data, action, row, column, parent):
        if action == Qt.IgnoreAction: return True
        if not data.hasFormat('application/x-point-list'): return False

        if row == -1:
            row = len(self._points)

        encoded = data.data('application/x-point-list')
        points = json.loads(encoded.data().decode('utf-8'))

        self.beginInsertRows(QModelIndex(), row, row + len(points) - 1)
        for p in points:
            self._points.insert(row, p)
            row += 1
        self.endInsertRows()
        return True

    def removeRows(self, row, count, parent=QModelIndex()):
        self.beginRemoveRows(parent, row, row + count - 1)
        for _ in range(count):
            del self._points[row]
        self.endRemoveRows()
        return True

    # Helper methods
    def set_points(self, points):
        self.beginResetModel()
        self._points = points
        self.endResetModel()

    def get_points(self):
        return self._points

    def add_point(self, x, y):
        self.beginInsertRows(QModelIndex(), len(self._points), len(self._points))
        self._points.append({
             "x": x, "y": y, "type": "left", "delay": 0, "label": "", "group": 0
        })
        self.endInsertRows()

    def remove_at(self, row):
        self.removeRows(row, 1)

    def set_group(self, row, group_id):
        if 0 <= row < len(self._points):
            self._points[row]['group'] = group_id
            idx = self.index(row)
            self.dataChanged.emit(idx, idx, [Qt.DisplayRole, Qt.UserRole])
