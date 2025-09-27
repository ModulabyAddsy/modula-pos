# src/ui/views/dashboard_view.py

from PySide6.QtWidgets import QWidget, QHBoxLayout, QSplitter
from PySide6.QtCore import Qt
from src.ui.views.widgets.navigation_sidebar import NavigationSidebar
from src.ui.views.widgets.workspace_view import WorkspaceView

class DashboardView(QWidget):
    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.setObjectName("ModulaProDashboard")
        self.app_controller = app_controller
        
        # --- LÍNEA CLAVE RE-AÑADIDA ---
        # Fuerza al widget a que SIEMPRE pinte el fondo definido en la hoja de estilos.
        self.setAutoFillBackground(True)
        # --------------------------------

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        self.nav_sidebar = NavigationSidebar()
        self.workspace = WorkspaceView()
        splitter.addWidget(self.nav_sidebar)
        splitter.addWidget(self.workspace)

        # Conectamos las dos señales para la nueva lógica de clic/doble clic
        self.nav_sidebar.modulo_click_sencillo.connect(self._handle_single_click)
        self.nav_sidebar.modulo_doble_click.connect(self._handle_double_click)
        
        # Configuración del tamaño y comportamiento del splitter
        splitter.setSizes([240, 840]) 
        self.nav_sidebar.setMinimumWidth(200)
        self.workspace.setMinimumWidth(300)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
        
        # --- NUEVAS FUNCIONES MANEJADORAS ---
    def _handle_single_click(self, manifest: dict):
        """
        Manejador para el clic sencillo. Carga el widget y se lo pasa
        a la función de reemplazo de pestaña del workspace.
        """
        # Usamos el ModuleManager (a través del app_controller) para cargar el widget
        widget = self.app_controller.module_manager.load_module_widget(manifest)
        if widget:
            self.workspace.reemplazar_pestaña_actual(manifest['nombre'], widget)

    def _handle_double_click(self, manifest: dict):
        """
        Manejador para el doble clic. Carga el widget y se lo pasa
        a la función de abrir nueva pestaña del workspace.
        """
        # Usamos el ModuleManager para cargar el widget
        widget = self.app_controller.module_manager.load_module_widget(manifest)
        if widget:
            self.workspace.abrir_nuevo_modulo(manifest['nombre'], widget)