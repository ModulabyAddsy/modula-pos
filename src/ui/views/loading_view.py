#src\ui\views\loading_view.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt

class LoadingView(QWidget):
    """
    Una vista simple que muestra un mensaje de "Cargando..." y una barra de progreso.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LoadingView")

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        # Etiqueta de texto
        self.label = QLabel("Verificando sesión...", self)
        font = self.label.font()
        font.setPointSize(16)
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignCenter)

        # Barra de progreso indeterminada (estilo "marcha")
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0) # Esto la hace indeterminada
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumWidth(300)

        # Añadir widgets al layout
        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)
    
    def set_message(self, title, subtitle=""):
        self.label.setText(title)
        # Puedes añadir un segundo label para el subtítulo si quieres
        
    def update_log_message(self, message: str):
        """Actualiza la etiqueta de estado con mensajes del proceso de carga."""
        self.label.setText(message)