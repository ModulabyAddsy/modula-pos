# src/ui/views/loading_view.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from src.core.utils import resource_path

class LoadingView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LoadingView")
        
        logo_modula_path = resource_path("assets/images/logo_modula.png")
        logo_addsy_path = resource_path("assets/images/logo_addsy_powered.png")   

        # Widgets de la Interfaz
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
        
        # --- NUEVO: Etiqueta para el subtítulo ---
        self.subtitle_label = QLabel("")
        self.subtitle_label.setObjectName("LoadingSubtitle") # Para futuros estilos
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setWordWrap(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        
        self.progress_animation = QPropertyAnimation(self.progress_bar, b"value")
        self.progress_animation.setDuration(200)
        self.progress_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Footer
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

        # Layout Vertical Principal
        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self.logo_label)
        layout.addWidget(self.title_label)
        layout.addSpacing(20)
        layout.addWidget(self.status_label)
        layout.addWidget(self.subtitle_label) # <-- AÑADIDO
        layout.addWidget(self.progress_bar)
        layout.addStretch()
        layout.addWidget(footer_container)
        layout.setContentsMargins(50, 20, 50, 20)
        
        self.setLayout(layout)

    def update_status(self, message: str, percentage: int):
        """Método para la carga inicial con progreso medible."""
        self.progress_bar.setRange(0, 100) # Aseguramos modo normal
        self.status_label.setText(message)
        self.subtitle_label.setText("") # Limpiamos el subtítulo
        
        self.progress_animation.stop() 
        self.progress_animation.setStartValue(self.progress_bar.value())
        self.progress_animation.setEndValue(percentage)
        self.progress_animation.start()
    
    # --- NUEVO: La función que faltaba ---
    def set_message(self, title: str, subtitle: str = "", indeterminate: bool = False):
        """
        Método para mostrar un estado de carga sin progreso medible.
        """
        self.status_label.setText(title)
        self.subtitle_label.setText(subtitle)
        
        if indeterminate:
            # Modo "gusanito"
            self.progress_bar.setRange(0, 0)
        else:
            # Modo normal, barra vacía
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)