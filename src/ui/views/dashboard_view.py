# src/ui/views/dashboard_view.py

from PySide6.QtWidgets import QWidget, QHBoxLayout, QSplitter
from PySide6.QtCore import Qt

# Importamos los widgets que SÍ estamos usando
from src.ui.views.widgets.navigation_sidebar import NavigationSidebar
from src.ui.views.widgets.workspace_view import WorkspaceView

class DashboardView(QWidget):
    """
    Implementa la vista principal 'Modula Pro' con una estructura de 2 paneles
    redimensionables gracias a QSplitter.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ModulaProDashboard")
        
        # Usaremos un QHBoxLayout solo para contener el QSplitter y que ocupe todo el espacio.
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Creamos el QSplitter con orientación horizontal
        splitter = QSplitter(Qt.Horizontal)

        # 2. Instanciamos los paneles que irán dentro del splitter
        self.nav_sidebar = NavigationSidebar()
        self.workspace = WorkspaceView()

        # 3. Añadimos los dos paneles directamente al splitter
        splitter.addWidget(self.nav_sidebar)
        splitter.addWidget(self.workspace)

        # 4. (Opcional pero recomendado) Configuramos el tamaño inicial de los paneles.
        # Esto le da al sidebar 240px y al workspace el resto del espacio disponible.
        splitter.setSizes([240, 840]) 
        
        # Reforzamos el tamaño mínimo de ambos paneles
        self.nav_sidebar.setMinimumWidth(200)
        self.workspace.setMinimumWidth(300)

        # --- NUEVO: Evitar que los paneles se colapsen por completo ---
        # El índice 0 corresponde al primer widget añadido (nav_sidebar)
        # El índice 1 corresponde al segundo widget añadido (workspace)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)