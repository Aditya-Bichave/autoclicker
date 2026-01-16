from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit, QDialogButtonBox

class PointEditorDialog(QDialog):
    def __init__(self, point_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Point")
        self.data = point_data.copy()

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.inp_x = QDoubleSpinBox()
        self.inp_x.setRange(0, 99999)
        self.inp_x.setDecimals(4)
        self.inp_x.setValue(float(self.data.get("x", 0)))

        self.inp_y = QDoubleSpinBox()
        self.inp_y.setRange(0, 99999)
        self.inp_y.setDecimals(4)
        self.inp_y.setValue(float(self.data.get("y", 0)))

        self.inp_type = QComboBox()
        self.inp_type.addItems(["left", "right"])
        self.inp_type.setCurrentText(self.data.get("type", "left"))

        self.inp_delay = QSpinBox()
        self.inp_delay.setRange(0, 60000)
        self.inp_delay.setValue(int(self.data.get("delay", 0)))
        self.inp_delay.setSuffix(" ms")

        self.inp_group = QSpinBox()
        self.inp_group.setRange(0, 9)
        self.inp_group.setValue(int(self.data.get("group", 0)))

        self.inp_label = QLineEdit(self.data.get("label", ""))

        form.addRow("X:", self.inp_x)
        form.addRow("Y:", self.inp_y)
        form.addRow("Type:", self.inp_type)
        form.addRow("Delay:", self.inp_delay)
        form.addRow("Group:", self.inp_group)
        form.addRow("Label:", self.inp_label)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_data(self):
        return {
            "x": self.inp_x.value(),
            "y": self.inp_y.value(),
            "type": self.inp_type.currentText(),
            "delay": self.inp_delay.value(),
            "group": self.inp_group.value(),
            "label": self.inp_label.text()
        }
