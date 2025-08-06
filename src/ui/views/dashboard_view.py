# src/ui/views/dashboard_view.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class DashboardView(QWidget):
    """
    Placeholder para la pantalla principal de la aplicación después del login.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DashboardView")

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # Mensaje de bienvenida
        self.welcome_label = QLabel("¡Bienvenido a Modula POS!", self)
        
        # Agrandar la fuente para que sea más visible
        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        self.welcome_label.setFont(font)
        self.welcome_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.welcome_label)
        self.setLayout(layout)