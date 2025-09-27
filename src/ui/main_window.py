# src/ui/main_window.py

from PySide6.QtWidgets import QMainWindow, QStackedWidget, QApplication, QLabel
from PySide6.QtGui import QScreen, QIcon
from PySide6.QtCore import Qt
from src.ui.views.auth_view import AuthView
from src.ui.views.dashboard_view import DashboardView
from src.ui.views.loading_view import LoadingView
from src.ui.views.login_view import LoginView

class MainWindow(QMainWindow):
    def __init__(self, app_controller):
        super().__init__()
        self.dashboard_view = DashboardView(app_controller)
        self.setWindowTitle("Modula POS")
        self.setObjectName("MainWindow")
        icon = QIcon(":/images/logo_modula.ico")
        self.setWindowIcon(icon)

        self._create_menu_bar()
        self._create_status_bar()
        
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.loading_view = LoadingView()
        self.auth_view = AuthView()
        self.dashboard_view = DashboardView()
        self.login_view = LoginView()

        self.stacked_widget.addWidget(self.loading_view)
        self.stacked_widget.addWidget(self.auth_view)
        self.stacked_widget.addWidget(self.dashboard_view)
        self.stacked_widget.addWidget(self.login_view)
        
        self.center()

    def _create_menu_bar(self):
        self.main_menu_bar = self.menuBar()
        file_menu = self.main_menu_bar.addMenu("Archivo")
        options_menu = self.main_menu_bar.addMenu("Opciones")
        devices_menu = self.main_menu_bar.addMenu("Dispositivos")
        help_menu = self.main_menu_bar.addMenu("Acerca de")
        exit_action = file_menu.addAction("Salir")
        exit_action.triggered.connect(self.close)

    def _create_status_bar(self):
        self.main_status_bar = self.statusBar()
        user_info_label = QLabel("Juan Gonzalez | Administrador")
        self.main_status_bar.addPermanentWidget(user_info_label)

    def center(self):
        center_point = QScreen.availableGeometry(QApplication.primaryScreen()).center()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
        
    def mostrar_vista_login_local(self):
        self.main_menu_bar.hide()
        self.main_status_bar.hide()
        # --- LÓGICA UNIFICADA Y CORRECTA ---
        flags = Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinimizeButtonHint
        self.setWindowFlags(flags)
        self.setFixedSize(500, 550) 
        self.center()
        self.show()
        self.stacked_widget.setCurrentWidget(self.login_view)

    def mostrar_vista_carga(self):
        self.main_menu_bar.hide()
        self.main_status_bar.hide()
        # --- LÓGICA UNIFICADA Y CORRECTA ---
        flags = Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinimizeButtonHint
        self.setWindowFlags(flags)
        self.setFixedSize(550, 600)
        self.center()
        self.show()
        self.stacked_widget.setCurrentWidget(self.loading_view)

    def mostrar_vista_auth(self):
        self.main_menu_bar.hide()
        self.main_status_bar.hide()
        # --- LÓGICA UNIFICADA Y CORRECTA ---
        flags = Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinimizeButtonHint
        self.setWindowFlags(flags)
        self.setFixedSize(960, 640)
        self.center()
        self.show()
        self.stacked_widget.setCurrentWidget(self.auth_view)
    
    def mostrar_vista_dashboard(self):
        self.main_menu_bar.show()
        self.main_status_bar.show()

        # Activa el botón de maximizar
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        # --- Elimina la restricción de tamaño fijo ---
        self.setMaximumSize(16777215, 16777215)  # "infinito" en Qt
        self.setMinimumSize(1280, 720)

        self.show()
        self.showNormal()
        self.center()
        
        self.stacked_widget.setCurrentWidget(self.dashboard_view)