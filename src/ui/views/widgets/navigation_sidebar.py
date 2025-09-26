# src/ui/views/widgets/navigation_sidebar.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QGraphicsDropShadowEffect
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QSize
from src.core.utils import resource_path 

class NavigationSidebar(QWidget):
    """
    Panel de navegación principal a la izquierda.
    Contiene la lista de módulos y una barra de búsqueda.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NavigationSidebar")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # AÑADIDO: Barra de búsqueda de módulos
        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("ModuleSearchBar")
        self.search_bar.setPlaceholderText("Buscar módulo...")
        self.search_bar.textChanged.connect(self._filter_modules)

        # --- NUEVO: Limitar el ancho máximo de la barra de búsqueda ---
        self.search_bar.setMaximumWidth(300)

        # Lista de Módulos
        self.module_list = QListWidget()
        self.module_list.setObjectName("ModuleListWidget")
        self.module_list.setSpacing(10) # Aumentamos un poco el espaciado

        # --- NUEVO: Configuración para el layout de cuadrícula (Grid/Flow Layout) ---
        self.module_list.setViewMode(QListWidget.ViewMode.IconMode) # Vista de íconos
        self.module_list.setResizeMode(QListWidget.ResizeMode.Adjust) # Se reajusta con el tamaño
        self.module_list.setMovement(QListWidget.Movement.Static) # Evita que se muevan los ítems
        self.module_list.setWrapping(True) # Permite que los ítems "bajen" a la siguiente fila
        self.module_list.setUniformItemSizes(True) # Optimización para ítems de tamaño similar
        self.module_list.setIconSize(QSize(32, 32)) # Iconos un poco más grandes
        
        # Añadimos los widgets al layout
        layout.addWidget(self.search_bar, 0, Qt.AlignmentFlag.AlignHCenter) # Centramos la barra
        layout.addWidget(self.module_list)
        
                # --- AÑADIR SOMBRA ---
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor("#d1d5db")
        shadow.setOffset(0, 2) # Sombra ligera hacia abajo
        self.search_bar.setGraphicsEffect(shadow)
        
        self._add_dummy_modules()

    def _add_dummy_modules(self):
        """Carga módulos de ejemplo en la lista."""
        modules = [
            {"name": "Punto de Venta", "icon": "assets/icons/shopping-cart.svg"},
            {"name": "Inventario", "icon": "assets/icons/archive.svg"},
            {"name": "Clientes", "icon": "assets/icons/users.svg"},
            {"name": "Reportes", "icon": "assets/icons/bar-chart-2.svg"},
            {"name": "Configuración", "icon": "assets/icons/settings.svg"}
        ]

        for module in modules:
            item = QListWidgetItem(module["name"])
            icon_path = resource_path(module["icon"])
            item.setIcon(QIcon(icon_path))
            
            # --- NUEVO: Centrar el texto debajo del ícono ---
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self.module_list.addItem(item)
            
        self.module_list.setCurrentRow(0)

    def _filter_modules(self, text):
        """Filtra los módulos en la lista según el texto de búsqueda."""
        search_text = text.lower()
        for i in range(self.module_list.count()):
            item = self.module_list.item(i)
            item_text = item.text().lower()
            # Oculta el item si no contiene el texto de búsqueda
            item.setHidden(search_text not in item_text)