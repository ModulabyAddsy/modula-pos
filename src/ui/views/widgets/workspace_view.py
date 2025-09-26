# src/ui/views/widgets/workspace_view.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PySide6.QtCore import Qt

class WorkspaceView(QWidget):
    """
    Panel central y dinámico. Su contenido cambiará según el módulo
    seleccionado. Ahora es un área con scroll automático.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WorkspaceView")
        
        # 1. Layout principal que contendrá únicamente el QScrollArea
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 2. Creamos el QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True) # ¡Muy importante! Permite que el widget interior se redimensione
        scroll_area.setObjectName("WorkspaceScrollArea")
        
        # 3. Creamos un widget contenedor que irá DENTRO del scroll area
        # Todo el contenido de tus módulos se añadirá a este widget
        self.scroll_content_widget = QWidget()
        self.scroll_content_widget.setObjectName("WorkspaceContent")
        
        # 4. Creamos el layout para el widget contenedor
        content_layout = QVBoxLayout(self.scroll_content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop) # Alinea el contenido arriba
        content_layout.setContentsMargins(20, 20, 20, 20) # Añade un poco de padding
        content_layout.setSpacing(15)

        # --- PRUEBA DE CONCEPTO: Añadimos contenido para forzar el scroll ---
        # Puedes borrar este bloque 'for' cuando empieces a cargar módulos reales.
        label_titulo = QLabel("Workspace Principal (con Scroll)")
        label_titulo.setStyleSheet("font-size: 24px; font-weight: bold;")
        content_layout.addWidget(label_titulo)
        
        for i in range(30):
            content_layout.addWidget(QLabel(f"Contenido de ejemplo línea {i+1} para demostrar el scroll vertical."))

        # Este widget grande forzará el scroll horizontal
        widget_ancho = QLabel("Este texto es muy, muy, muy, muy, muy, muy, muy, muy, muy, muy, muy, muy, muy, muy largo para forzar la aparición del scroll horizontal.")
        widget_ancho.setMinimumWidth(2000)
        content_layout.addWidget(widget_ancho)
        # --- FIN DE LA PRUEBA ---
        
        # 5. Asignamos el widget contenedor al QScrollArea
        scroll_area.setWidget(self.scroll_content_widget)
        
        # 6. Añadimos el QScrollArea al layout principal de la vista
        main_layout.addWidget(scroll_area)
