# src/ui/views/widgets/navigation_sidebar.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QSize, Signal
from pathlib import Path

class NavigationSidebar(QWidget):
    # --- MODIFICADO: Las señales ahora emiten un diccionario (el manifest) ---
    modulo_click_sencillo = Signal(dict)
    modulo_doble_click = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NavigationSidebar")
        # ... (el resto de la configuración inicial no cambia) ...
        layout = QVBoxLayout(self)
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
        
        self.module_list.itemClicked.connect(self._on_module_single_clicked)
        self.module_list.itemDoubleClicked.connect(self._on_module_double_clicked)
        
        layout.addWidget(self.search_bar)
        layout.addWidget(self.module_list)

    def _on_module_single_clicked(self, item):
        """Emite el manifest completo del módulo con un solo clic."""
        manifest = item.data(Qt.UserRole)
        if manifest:
            self.modulo_click_sencillo.emit(manifest)

    def _on_module_double_clicked(self, item):
        """Emite el manifest completo del módulo con un doble clic."""
        manifest = item.data(Qt.UserRole)
        if manifest:
            self.modulo_doble_click.emit(manifest)
        
    def populate_modules(self, modules_list: list, modules_dir: Path):
        """
        NUEVA FUNCIÓN: Limpia la lista y la llena con los módulos instalados.
        """
        self.module_list.clear()
        for manifest in modules_list:
            item = QListWidgetItem(manifest['nombre'])
            # Guardamos el manifest completo en el item para usarlo después
            item.setData(Qt.UserRole, manifest)
            
            icon_path = modules_dir / manifest['id'] / manifest['icono']
            if icon_path.exists():
                item.setIcon(QIcon(str(icon_path)))
                
            self.module_list.addItem(item)


    def _filter_modules(self, text):
        """Filtra los módulos en la lista según el texto de búsqueda."""
        search_text = text.lower()
        for i in range(self.module_list.count()):
            item = self.module_list.item(i)
            item_text = item.text().lower()
            item.setHidden(search_text not in item_text)