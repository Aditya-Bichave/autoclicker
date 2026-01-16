DARK_STYLE = """
QWidget {
    background: #121212;
    color: #E5E7EB;
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
}

QPushButton {
    background: #1E1E1E;
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 6px 12px;
}

QPushButton:hover {
    background: #2A2A2A;
    border-color: #444444;
}

QPushButton:pressed {
    background: #151515;
}

QPushButton:checked {
    background: #3A3A3A;
    border-color: #555555;
}

QListWidget, QListView, QComboBox, QSpinBox, QLineEdit {
    background: #1A1A1A;
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 4px;
    selection-background-color: #3A3A3A;
}

QTabWidget::pane {
    border: 1px solid #333333;
    background: #121212;
}

QTabBar::tab {
    background: #1E1E1E;
    padding: 8px 12px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background: #2A2A2A;
    border-bottom: 2px solid #007ACC;
}

QGroupBox {
    border: 1px solid #333333;
    border-radius: 6px;
    margin-top: 6px;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px;
}
"""

LIGHT_STYLE = """
QWidget {
    background: #F9FAFB;
    color: #1F2937;
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
}

QPushButton {
    background: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 6px 12px;
}

QPushButton:hover {
    background: #F3F4F6;
    border-color: #9CA3AF;
}

QPushButton:pressed {
    background: #E5E7EB;
}

QPushButton:checked {
    background: #E5E7EB;
    border-color: #6B7280;
}

QListWidget, QListView, QComboBox, QSpinBox, QLineEdit {
    background: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 4px;
    selection-background-color: #E5E7EB;
    selection-color: #000000;
}

QTabWidget::pane {
    border: 1px solid #E5E7EB;
    background: #F9FAFB;
}

QTabBar::tab {
    background: #F3F4F6;
    padding: 8px 12px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    border: 1px solid transparent;
}

QTabBar::tab:selected {
    background: #FFFFFF;
    border-bottom: 2px solid #3B82F6;
}

QGroupBox {
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    margin-top: 6px;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px;
}
"""
