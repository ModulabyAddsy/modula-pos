# src/ui/views/widgets/navigation_sidebar.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QSize,  Signal
from src.core.utils import resource_path

class NavigationSidebar(QWidget):
    """
    Panel de navegación que ahora distingue entre un solo clic y un doble clic.
    """
    modulo_click_sencillo = Signal(str)
    modulo_doble_click = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NavigationSidebar")

        layout = QVBoxLayout(self)
        # --- CORRECCIÓN sutil en márgenes para consistencia ---
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("ModuleSearchBar")
        self.search_bar.setPlaceholderText("Buscar módulo...")
        self.search_bar.textChanged.connect(self._filter_modules)
        
        self.module_list = QListWidget()
        self.module_list.setObjectName("ModuleListWidget")
        self.module_list.setSpacing(5)
        self.module_list.setIconSize(QSize(20, 20))
        
        # Conectamos las señales a las funciones que AHORA SÍ existen
        self.module_list.itemClicked.connect(self._on_module_single_clicked)
        self.module_list.itemDoubleClicked.connect(self._on_module_double_clicked)
        
        layout.addWidget(self.search_bar)
        layout.addWidget(self.module_list)
        
        self._add_dummy_modules()

    
    def _on_module_single_clicked(self, item):
        """Emite la señal para un solo clic."""
        self.modulo_click_sencillo.emit(item.text())

    # --- FUNCIÓN AÑADIDA ---
    def _on_module_double_clicked(self, item):
        """Emite la señal para un doble clic."""
        self.modulo_doble_click.emit(item.text())
        
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
            
            # --- MODIFICADO: Eliminamos el centrado de texto ---
            # El alineamiento por defecto (izquierda) es el que queremos
            
            self.module_list.addItem(item)
            
        self.module_list.setCurrentRow(0)

    def _filter_modules(self, text):
        """Filtra los módulos en la lista según el texto de búsqueda."""
        search_text = text.lower()
        for i in range(self.module_list.count()):
            item = self.module_list.item(i)
            item_text = item.text().lower()
            item.setHidden(search_text not in item_text)