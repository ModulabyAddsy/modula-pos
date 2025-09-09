# Archivo: src/ui/views/login_view.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt, Signal, QObject

class LoginView(QWidget):
    """
    Vista de inicio de sesión para el software Modula POS.
    Permite al usuario ingresar su número de empleado y contraseña.
    """
    
    # Señales para comunicar con el controlador principal
    login_solicitado = Signal(str, str) # Emite el número de empleado y la contraseña
    recuperacion_solicitada = Signal(str) # Emite el número de empleado para recuperación
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LoginView")
        
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        # Título de bienvenida
        welcome_label = QLabel("Bienvenido, por favor. Inicia sesión.")
        welcome_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(welcome_label)

        # Entrada para el número de empleado
        self.empleado_input = QLineEdit(self)
        self.empleado_input.setPlaceholderText("Número de empleado")
        main_layout.addWidget(self.empleado_input)

        # Entrada para la contraseña
        self.contrasena_input = QLineEdit(self)
        self.contrasena_input.setPlaceholderText("Contraseña")
        self.contrasena_input.setEchoMode(QLineEdit.Password)
        main_layout.addWidget(self.contrasena_input)

        # Layout para los botones
        button_layout = QHBoxLayout()
        self.login_button = QPushButton("Iniciar sesión")
        self.recuperar_button = QPushButton("Recuperar contraseña")
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.recuperar_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def connect_signals(self):
        self.login_button.clicked.connect(self.emit_login_request)
        self.recuperar_button.clicked.connect(self.emit_recuperacion_request)

    def emit_login_request(self):
        empleado = self.empleado_input.text().strip()
        contrasena = self.contrasena_input.text().strip()
        
        if not empleado or not contrasena:
            QMessageBox.warning(self, "Campos Requeridos", "Por favor, ingresa tu número de empleado y contraseña.")
            return

        self.login_solicitado.emit(empleado, contrasena)

    def emit_recuperacion_request(self):
        empleado = self.empleado_input.text().strip()
        
        if not empleado:
            QMessageBox.warning(self, "Campo Requerido", "Por favor, ingresa tu número de empleado para recuperar la contraseña.")
            return

        self.recuperacion_solicitada.emit(empleado)

    def clear_inputs(self):
        self.empleado_input.clear()
        self.contrasena_input.clear()