# src/ui/views/widgets/navigation_sidebar.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, 
                               QTreeWidget, QTreeWidgetItem) # <-- CAMBIO: QTreeWidget
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QSize, Signal
from pathlib import Path
import collections # <-- NUEVO: Para agrupar fácilmente

class NavigationSidebar(QWidget):
    modulo_click_sencillo = Signal(dict)
    modulo_doble_click = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NavigationSidebar")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10) # Ajuste de márgenes para estética
        layout.setSpacing(15)

        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("ModuleSearchBar")
        self.search_bar.setPlaceholderText("Buscar módulo...")
        self.search_bar.textChanged.connect(self._filter_modules)
        
        # --- CAMBIO CLAVE: Usamos QTreeWidget en lugar de QListWidget ---
        self.module_tree = QTreeWidget()
        self.module_tree.setObjectName("ModuleTreeWidget")
        self.module_tree.setHeaderHidden(True) # No queremos ver la cabecera de la tabla
        self.module_tree.setIconSize(QSize(20, 20))
        
        self.module_tree.itemClicked.connect(self._on_module_single_clicked)
        self.module_tree.itemDoubleClicked.connect(self._on_module_double_clicked)
        
        layout.addWidget(self.search_bar)
        layout.addWidget(self.module_tree)
        
        self.setLayout(layout)

    def _on_module_single_clicked(self, item, column):
        """Emite el manifest si el item es un módulo (tiene un manifest asociado)."""
        manifest = item.data(0, Qt.UserRole)
        # Solo emitimos la señal si el item es un módulo hijo, no una categoría padre
        if manifest:
            self.modulo_click_sencillo.emit(manifest)

    def _on_module_double_clicked(self, item, column):
        """Emite el manifest si el item es un módulo."""
        manifest = item.data(0, Qt.UserRole)
        if manifest:
            self.modulo_doble_click.emit(manifest)
        
    def populate_modules(self, modules_list: list, modules_dir: Path):
        """
        MODIFICADO: Llena el árbol, agrupando los módulos por categoría.
        """
        self.module_tree.clear()
        
        # 1. Agrupar módulos por categoría
        modules_by_category = collections.defaultdict(list)
        for manifest in modules_list:
            # Si un módulo no tiene categoría, lo ponemos en "General"
            category = manifest.get('category', 'General')
            modules_by_category[category].append(manifest)

        # 2. Poblar el QTreeWidget
        for category_name, manifests in sorted(modules_by_category.items()):
            # Creamos el item de la categoría (padre)
            category_item = QTreeWidgetItem(self.module_tree, [category_name])
            category_item.setFlags(category_item.flags() & ~Qt.ItemIsSelectable) # La categoría no es seleccionable
            
            # Agregamos los módulos como hijos de la categoría
            for manifest in manifests:
                module_item = QTreeWidgetItem(category_item, [manifest['nombre']])
                # Guardamos el manifest completo en el item para usarlo después
                module_item.setData(0, Qt.UserRole, manifest)
                
                icon_path = modules_dir / manifest['id'] / manifest['icono']
                if icon_path.exists():
                    module_item.setIcon(0, QIcon(str(icon_path)))
            
            # Expandimos todas las categorías por defecto
            category_item.setExpanded(True)

    def _filter_modules(self, text):
        """Filtra los módulos en el árbol según el texto de búsqueda."""
        search_text = text.lower()
        
        # Iteramos sobre las categorías (items de nivel superior)
        for i in range(self.module_tree.topLevelItemCount()):
            category_item = self.module_tree.topLevelItem(i)
            category_has_visible_child = False
            
            # Iteramos sobre los módulos (hijos de la categoría)
            for j in range(category_item.childCount()):
                module_item = category_item.child(j)
                manifest = module_item.data(0, Qt.UserRole)
                
                # Buscamos en el nombre y en los tags
                item_text = manifest.get('nombre', '').lower()
                tags = " ".join(manifest.get('tags', [])).lower()
                
                is_match = search_text in item_text or search_text in tags
                module_item.setHidden(not is_match)
                
                if is_match:
                    category_has_visible_child = True
            
            # Ocultamos la categoría si ninguno de sus módulos coincide con la búsqueda
            category_item.setHidden(not category_has_visible_child)