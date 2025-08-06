# src/ui/main_window.py
from PySide6.QtWidgets import QMainWindow, QStackedWidget
from src.ui.views.auth_view import AuthView
from src.ui.views.dashboard_view import DashboardView
from src.ui.views.loading_view import LoadingView

class MainWindow(QMainWindow):
    """La ventana principal que actúa como un contenedor para las vistas."""
    def __init__(self): # Ya no necesita recibir el api_client
        super().__init__()
        self.setWindowTitle("Modula POS")
        self.setObjectName("MainWindow")
        self.setFixedSize(550, 600)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.loading_view = LoadingView()
        self.auth_view = AuthView() # <-- CORRECCIÓN: No se pasa el api_client
        self.dashboard_view = DashboardView()

        self.stacked_widget.addWidget(self.loading_view)
        self.stacked_widget.addWidget(self.auth_view)
        self.stacked_widget.addWidget(self.dashboard_view)

        # La conexión de la señal de login exitoso se hará en el controlador
        # para mantener esta clase lo más simple posible.
        # self.auth_view.login_exitoso.connect(self.mostrar_vista_dashboard)

    def mostrar_vista_carga(self):
        self.setFixedSize(550, 600)
        self.stacked_widget.setCurrentWidget(self.loading_view)

    def mostrar_vista_auth(self):
        self.setFixedSize(550, 600)
        self.stacked_widget.setCurrentWidget(self.auth_view)
    
    def mostrar_vista_dashboard(self):
        self.setFixedSize(1200, 800)
        self.stacked_widget.setCurrentWidget(self.dashboard_view)