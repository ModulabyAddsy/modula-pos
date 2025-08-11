# src/ui/views/loading_view.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt

class LoadingView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LoadingView")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)

        self.title_label = QLabel("Iniciando Modula POS", self)
        self.title_label.setObjectName("loadingTitle")
        self.title_label.setAlignment(Qt.AlignCenter)

        # ✅ NUEVO: Etiqueta para mostrar el estado actual
        self.status_label = QLabel("Preparando...", self)
        self.status_label.setObjectName("loadingSubtitle")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMinimumWidth(400) # Para evitar que la ventana cambie de tamaño

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100) # Ahora es una barra de progreso determinada
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumWidth(300)

        layout.addWidget(self.title_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)
    
    def update_status(self, message: str, progress: int):
        """Actualiza el mensaje de estado y el valor de la barra de progreso."""
        self.status_label.setText(message)
        self.progress_bar.setValue(progress)