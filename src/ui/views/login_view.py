# Archivo: src/ui/views/login_view.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from src.core.utils import resource_path # Asegúrate de que esta importación sea correcta

class LoginView(QWidget):
    """
    Vista de inicio de sesión para el software Modula POS, adaptada con
    el estilo visual de la marca.
    """
    # Señales para comunicar con el controlador principal
    login_solicitado = Signal(str, str)
    recuperacion_solicitada = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AuthView") # Asigna un ID al widget principal para el fondo
        self.setup_ui()

    def setup_ui(self):
        # Layout principal que centrará la tarjeta del formulario
        main_layout = QHBoxLayout(self)
        main_layout.addStretch()

        # Contenedor central tipo "card"
        form_container = QWidget()
        form_container.setObjectName("AuthFormCard") # Para aplicar estilos a la tarjeta
        form_container.setFixedWidth(350)

        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(30, 30, 30, 30)
        form_layout.setSpacing(15)

        # --- Widgets del Formulario ---

        # 1. Logo de Modula
        logo_path = resource_path("assets/images/logo_modula.png")
        logo_pixmap = QPixmap(logo_path)
        logo_label = QLabel()
        logo_label.setPixmap(logo_pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)

        # 2. Títulos
        title_label = QLabel("Bienvenido a Modula")
        title_label.setObjectName("h1") # Estilo de título principal
        title_label.setAlignment(Qt.AlignCenter)

        subtitle_label = QLabel("Inicia sesión para continuar")
        subtitle_label.setAlignment(Qt.AlignCenter)

        # 3. Campos de entrada
        self.empleado_input = QLineEdit()
        self.empleado_input.setPlaceholderText("Número de empleado")

        self.contrasena_input = QLineEdit()
        self.contrasena_input.setPlaceholderText("Contraseña")
        self.contrasena_input.setEchoMode(QLineEdit.Password)

        # 4. Etiqueta de error (reemplaza a QMessageBox)
        self.error_label = QLabel()
        self.error_label.setObjectName("AuthErrorLabel") # Estilo para errores
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.hide() # Oculta por defecto

        # 5. Botones
        self.login_button = QPushButton("Iniciar Sesión")
        self.login_button.setObjectName("primary") # Estilo de botón principal
        self.login_button.setCursor(Qt.PointingHandCursor)

        self.recuperar_button = QPushButton("Recuperar contraseña")
        self.recuperar_button.setObjectName("link-style-button") # Estilo de enlace
        self.recuperar_button.setCursor(Qt.PointingHandCursor)

        # --- Ensamblado del Layout ---
        form_layout.addWidget(logo_label)
        form_layout.addSpacing(10)
        form_layout.addWidget(title_label)
        form_layout.addWidget(subtitle_label)
        form_layout.addSpacing(20)
        form_layout.addWidget(self.empleado_input)
        form_layout.addWidget(self.contrasena_input)
        form_layout.addWidget(self.error_label)
        form_layout.addWidget(self.login_button)
        form_layout.addWidget(self.recuperar_button)
        form_layout.addStretch()

        main_layout.addWidget(form_container)
        main_layout.addStretch()

        # --- Conexión de señales ---
        self.login_button.clicked.connect(self.emit_login_request)
        self.recuperar_button.clicked.connect(self.emit_recuperacion_request)
        # Permite presionar Enter para iniciar sesión
        self.empleado_input.returnPressed.connect(self.emit_login_request)
        self.contrasena_input.returnPressed.connect(self.emit_login_request)

    def emit_login_request(self):
        self.clear_error() # Limpia errores previos
        empleado = self.empleado_input.text().strip()
        contrasena = self.contrasena_input.text()

        if not empleado or not contrasena:
            self.show_error("Por favor, ingresa tu número de empleado y contraseña.")
            return

        self.login_solicitado.emit(empleado, contrasena)

    def emit_recuperacion_request(self):
        self.clear_error() # Limpia errores previos
        empleado = self.empleado_input.text().strip()

        if not empleado:
            self.show_error("Ingresa tu número de empleado para recuperar la contraseña.")
            return

        self.recuperacion_solicitada.emit(empleado)

    def show_error(self, message: str):
        """Muestra un mensaje de error en la interfaz."""
        self.error_label.setText(message)
        self.error_label.show()

    def clear_error(self):
        """Oculta el mensaje de error."""
        self.error_label.hide()

    def clear_inputs(self):
        """Limpia todos los campos de entrada."""
        self.empleado_input.clear()
        self.contrasena_input.clear()
        self.clear_error()
        self.empleado_input.setFocus()