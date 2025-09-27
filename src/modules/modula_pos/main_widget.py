from src.core.module_base import ModulaModuleBase
from PySide6.QtWidgets import QLabel, QVBoxLayout
from PySide6.QtCore import Qt

class PuntoDeVentaWidget(ModulaModuleBase):
    def __init__(self, app_controller=None, parent=None):
        super().__init__(app_controller, parent)

        # --- LÍNEA CLAVE AÑADIDA ---
        self.setObjectName("WorkspaceContent")
        # ---------------------------

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel("Contenido del Módulo: Punto de Venta v1.0.0")
        label.setStyleSheet("font-size: 24px;")

        layout.addWidget(label)