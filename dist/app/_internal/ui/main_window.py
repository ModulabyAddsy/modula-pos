# src/ui/main_window.py
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QApplication
from PySide6.QtGui import QScreen, QIcon
from PySide6.QtCore import Qt
from src.ui.views.auth_view import AuthView
from src.ui.views.dashboard_view import DashboardView
from src.ui.views.loading_view import LoadingView

class MainWindow(QMainWindow):
    """La ventana principal que actúa como un contenedor para las vistas."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modula POS")
        self.setObjectName("MainWindow")
        
        # --- 2. ESTABLECEMOS EL ÍCONO DE LA APLICACIÓN ---
        # Usamos la ruta de recursos que acabamos de añadir
        icon = QIcon(":/images/logo_modula.ico")
        self.setWindowIcon(icon)
        # ---------------------------------------------------

        # --- CORRECCIÓN: Definimos explícitamente los botones que queremos ---
        # Habilitamos minimizar y cerrar, pero deshabilitamos maximizar.
        flags = Qt.WindowFlags()
        flags |= Qt.WindowMinimizeButtonHint
        flags |= Qt.WindowCloseButtonHint
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint | flags)
        
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.loading_view = LoadingView()
        self.auth_view = AuthView()
        self.dashboard_view = DashboardView()

        self.stacked_widget.addWidget(self.loading_view)
        self.stacked_widget.addWidget(self.auth_view)
        self.stacked_widget.addWidget(self.dashboard_view)
        
        self.center()

    def center(self):
        """Centra la ventana en la pantalla activa."""
        center_point = QScreen.availableGeometry(QApplication.primaryScreen()).center()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def mostrar_vista_carga(self):
        self.setFixedSize(550, 600)
        self.center()
        self.stacked_widget.setCurrentWidget(self.loading_view)

    def mostrar_vista_auth(self):
        self.setFixedSize(960, 640)
        self.center()
        self.stacked_widget.setCurrentWidget(self.auth_view)
    
    def mostrar_vista_dashboard(self):
        # Habilitamos de nuevo el botón de maximizar para el dashboard
        flags = self.windowFlags()
        flags |= Qt.WindowMaximizeButtonHint
        self.setWindowFlags(flags)
        
        self.setMinimumSize(1200, 800) # Usamos tamaño mínimo en lugar de fijo
        self.showMaximized() # Mostramos el dashboard maximizado por defecto
        self.center()
        self.stacked_widget.setCurrentWidget(self.dashboard_view)
