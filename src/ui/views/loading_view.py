# src/ui/views/loading_view.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve # <-- 1. IMPORTAMOS las clases de animación
from pathlib import Path

# Bloque para calcular la ruta absoluta a la raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parents[3]

class LoadingView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LoadingView")

        logo_modula_path = str(PROJECT_ROOT / "src" / "assets" / "images" / "logo_modula.png")
        logo_addsy_path = str(PROJECT_ROOT / "src" / "assets" / "images" / "logo_addsy_powered.png")

        # 1. Widgets de la Interfaz
        self.logo_label = QLabel()
        pixmap_modula = QPixmap(logo_modula_path)
        self.logo_label.setPixmap(pixmap_modula.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo_label.setAlignment(Qt.AlignCenter)
        
        self.title_label = QLabel("<b>MODULA</b> POS")
        self.title_label.setObjectName("LoadingTitle")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.status_label = QLabel("Iniciando Modula POS...")
        self.status_label.setObjectName("LoadingStatus")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        
        # --- 2. CREAMOS Y CONFIGURAMOS EL OBJETO DE ANIMACIÓN ---
        # Lo guardamos como un atributo de la clase para poder usarlo después
        self.progress_animation = QPropertyAnimation(self.progress_bar, b"value") # b"value" es la propiedad que animaremos
        self.progress_animation.setDuration(200) # Duración de la animación en milisegundos
        self.progress_animation.setEasingCurve(QEasingCurve.InOutQuad) # Un efecto de aceleración suave
        # --------------------------------------------------------
        
        # Contenedor y layout para el footer
        footer_container = QWidget()
        footer_layout = QHBoxLayout(footer_container)
        footer_layout.setContentsMargins(0,0,0,0)
        footer_layout.setSpacing(6)

        footer_text_label = QLabel("Powered by:")
        footer_text_label.setObjectName("LoadingFooterText")

        self.footer_logo_label = QLabel()
        pixmap_addsy = QPixmap(logo_addsy_path)
        self.footer_logo_label.setPixmap(pixmap_addsy.scaledToHeight(80, Qt.SmoothTransformation))
        
        footer_layout.addStretch()
        footer_layout.addWidget(footer_text_label)
        footer_layout.addWidget(self.footer_logo_label)
        footer_layout.addStretch()

        # 2. Layout Vertical Principal
        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self.logo_label)
        layout.addWidget(self.title_label)
        layout.addSpacing(20)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addStretch()
        layout.addWidget(footer_container)
        layout.setContentsMargins(50, 20, 50, 20)
        
        self.setLayout(layout)

    # --- 3. REEMPLAZAMOS EL MÉTODO update_status ---
    def update_status(self, message: str, percentage: int):
        """
        Método público para ser llamado desde el app_controller.
        Ahora, en lugar de saltar, anima la barra de progreso.
        """
        self.status_label.setText(message)
        
        # Detenemos cualquier animación anterior para evitar conflictos
        self.progress_animation.stop() 
        
        # Definimos el punto de inicio (el valor actual) y el final (el nuevo porcentaje)
        self.progress_animation.setStartValue(self.progress_bar.value())
        self.progress_animation.setEndValue(percentage)
        
        # ¡Iniciamos la animación!
        self.progress_animation.start()
    # ---------------------------------------------