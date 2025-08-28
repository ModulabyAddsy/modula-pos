# src/ui/views/auth_view.py
from PySide6.QtCore import Signal, Qt, QDate
from PySide6.QtGui import QPixmap, QColor, QCursor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                               QPushButton, QFrame, QStackedWidget, QDateEdit, 
                               QCheckBox, QGraphicsDropShadowEffect, QFormLayout)
from pathlib import Path
from src.core.utils import resource_path
import re

# Se calcula la ruta raíz para poder encontrar los assets de forma fiable
PROJECT_ROOT = Path(__file__).resolve().parents[3]

class IconLineEdit(QFrame):
    """
    Un widget de QFrame personalizado que contiene un ícono y un QLineEdit,
    estilizado para parecer un único campo de texto.
    """
    def __init__(self, icon_path: str, placeholder_text: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("IconLineEdit")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        icon_label = QLabel()
        pixmap = QPixmap(icon_path)
        icon_label.setPixmap(pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(placeholder_text)
        self.line_edit.setObjectName("TransparentLineEdit")
        
        layout.addWidget(icon_label)
        layout.addWidget(self.line_edit)

    def text(self) -> str:
        return self.line_edit.text()

    def setEchoMode(self, mode):
        self.line_edit.setEchoMode(mode)

class LoginForm(QWidget):
    """Formulario específico para el inicio de sesión, rediseñado visualmente."""
    login_solicitado = Signal(str, str)
    recuperacion_solicitada = Signal()
    ir_a_registro = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0)
        
        icon_email_path = resource_path("assets/images/icon_email.png")
        icon_lock_path = resource_path("assets/images/icon_lock.png")
        
        self.email_input = IconLineEdit(icon_email_path, "tu@empresa.com")
        self.password_input = IconLineEdit(icon_lock_path, "••••••••••")
        self.password_input.setEchoMode(QLineEdit.Password)
        
        # --- CORREGIDO: Layout vertical para las opciones ---
        options_layout = QVBoxLayout()
        options_layout.setSpacing(5)
        self.show_password_checkbox = QCheckBox("Ver contraseña")
        self.show_password_checkbox.setCursor(QCursor(Qt.PointingHandCursor)) 
        self.forgot_password_button = QPushButton("¿Olvidaste tu contraseña?")
        self.forgot_password_button.setObjectName("SecondaryLinkRed")
        self.forgot_password_button.setCursor(QCursor(Qt.PointingHandCursor))
        options_layout.addWidget(self.show_password_checkbox, alignment=Qt.AlignLeft)
        options_layout.addWidget(self.forgot_password_button, alignment=Qt.AlignLeft)
        
        self.login_button = QPushButton("Iniciar sesion")
        self.login_button.setObjectName("LoginButton")
        self.login_button.setCursor(QCursor(Qt.PointingHandCursor))
        
        self.create_account_button = QPushButton("Crear cuenta")
        self.create_account_button.setObjectName("SecondaryLink")
        self.create_account_button.setCursor(QCursor(Qt.PointingHandCursor))

        layout.addWidget(QLabel("Correo electrónico"))
        layout.addWidget(self.email_input)
        layout.addSpacing(10)
        layout.addWidget(QLabel("Contraseña"))
        layout.addWidget(self.password_input)
        layout.addLayout(options_layout)
        layout.addSpacing(20)
        layout.addWidget(self.login_button)
        layout.addWidget(self.create_account_button, alignment=Qt.AlignCenter)
        
        self.login_button.clicked.connect(self.submit)
        self.forgot_password_button.clicked.connect(self.recuperacion_solicitada.emit)
        self.create_account_button.clicked.connect(self.ir_a_registro.emit)
        self.show_password_checkbox.toggled.connect(self._toggle_password_visibility)

    def submit(self):
        email = self.email_input.text()
        password = self.password_input.text()
        self.login_solicitado.emit(email, password)

    def _toggle_password_visibility(self, checked):
        if checked:
            self.password_input.setEchoMode(QLineEdit.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.Password)

class RegisterForm(QWidget):
    """Formulario de registro con validación y un layout profesional."""
    registro_solicitado = Signal(dict)
    ir_a_login = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(1) # Reducimos el espaciado general
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Creación de Widgets de Entrada (sin cambios) ---
        self.nombre_completo = QLineEdit()
        self.correo = QLineEdit()
        self.contrasena = QLineEdit()
        self.contrasena.setEchoMode(QLineEdit.Password)
        self.telefono = QLineEdit()
        self.fecha_nacimiento = QDateEdit()
        self.fecha_nacimiento.setCalendarPopup(True)
        self.fecha_nacimiento.setDisplayFormat("yyyy-MM-dd")
        self.fecha_nacimiento.setDate(QDate(2000, 1, 1))
        self.nombre_empresa = QLineEdit()
        self.rfc = QLineEdit()

        # --- Creación de Etiquetas de Error (sin cambios) ---
        self.error_nombre_completo = QLabel()
        self.error_correo = QLabel()
        self.error_contrasena = QLabel()
        self.error_telefono = QLabel()
        self.error_nombre_empresa = QLabel()
        
        for label in [self.error_nombre_completo, self.error_correo, self.error_contrasena, self.error_telefono, self.error_nombre_empresa]:
            label.setObjectName("ValidationErrorLabel")
            label.setVisible(False)
            label.setAlignment(Qt.AlignLeft)

        # --- AÑADIMOS WIDGETS AL LAYOUT CON LA ESTRUCTURA VERTICAL ---
        main_layout.addWidget(QLabel("Nombre Completo:"))
        main_layout.addWidget(self.nombre_completo)
        main_layout.addWidget(self.error_nombre_completo)
        
        main_layout.addWidget(QLabel("Correo Electrónico:"))
        main_layout.addWidget(self.correo)
        main_layout.addWidget(self.error_correo)

        main_layout.addWidget(QLabel("Contraseña (mínimo 6 caracteres):"))
        main_layout.addWidget(self.contrasena)
        main_layout.addWidget(self.error_contrasena)

        main_layout.addWidget(QLabel("Teléfono:"))
        main_layout.addWidget(self.telefono)
        main_layout.addWidget(self.error_telefono)
        
        main_layout.addWidget(QLabel("Fecha de Nacimiento:"))
        main_layout.addWidget(self.fecha_nacimiento)
        
        main_layout.addWidget(QLabel("Nombre de la Empresa:"))
        main_layout.addWidget(self.nombre_empresa)
        main_layout.addWidget(self.error_nombre_empresa)
        
        main_layout.addWidget(QLabel("RFC (Opcional):"))
        main_layout.addWidget(self.rfc)
        
        # --- LÓGICA DE BOTONES CORREGIDA ---
        self.submit_button = QPushButton("Registrar y Proceder al Pago")
        self.submit_button.setObjectName("LoginButton")
        self.submit_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.submit_button.setEnabled(False)

        back_to_login_button = QPushButton("¿Ya tienes cuenta? Inicia sesión")
        back_to_login_button.setObjectName("SecondaryLink")
        back_to_login_button.setCursor(QCursor(Qt.PointingHandCursor))

        main_layout.addStretch(1) # Empuja el formulario hacia arriba y los botones hacia abajo

        # Creamos un layout dedicado solo para los botones
        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addWidget(self.submit_button)
        button_layout.addWidget(back_to_login_button, alignment=Qt.AlignCenter)
        
        # Añadimos el layout de botones al layout principal
        main_layout.addLayout(button_layout)
        
        # --- Conexión de Señales (sin cambios) ---
        self.submit_button.clicked.connect(self.submit)
        back_to_login_button.clicked.connect(self.ir_a_login.emit)
        
        self.nombre_completo.textChanged.connect(self._validate_form)
        self.correo.textChanged.connect(self._validate_form)
        self.contrasena.textChanged.connect(self._validate_form)
        self.telefono.textChanged.connect(self._validate_form)
        self.nombre_empresa.textChanged.connect(self._validate_form)

    # --- NUEVAS FUNCIONES DE VALIDACIÓN ---

    def _validate_field(self, line_edit, error_label, min_length=1, message="Este campo es obligatorio", validator=None, validator_message="Formato no válido"):
        """Función genérica para validar un campo."""
        text = line_edit.text().strip()
        if len(text) < min_length:
            error_label.setText(message)
            error_label.setVisible(True)
            return False
        if validator and not validator(text):
            error_label.setText(validator_message)
            error_label.setVisible(True)
            return False
        
        error_label.setVisible(False)
        return True

    def _validate_correo(self, text):
        """Valida que el texto tenga un formato de correo simple."""
        return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", text)

    def _validate_form(self):
        """Orquesta la validación de todo el formulario y activa/desactiva el botón."""
        is_nombre_valid = self._validate_field(self.nombre_completo, self.error_nombre_completo, 3, "Debe tener al menos 3 caracteres")
        is_correo_valid = self._validate_field(self.correo, self.error_correo, validator=self._validate_correo, validator_message="Correo no válido")
        is_contrasena_valid = self._validate_field(self.contrasena, self.error_contrasena, 6, "Debe tener al menos 6 caracteres")
        is_telefono_valid = self._validate_field(self.telefono, self.error_telefono, 10, "Debe tener 10 dígitos")
        is_empresa_valid = self._validate_field(self.nombre_empresa, self.error_nombre_empresa)

        # <-- Habilitamos el botón solo si todos los campos requeridos son válidos
        is_form_valid = all([is_nombre_valid, is_correo_valid, is_contrasena_valid, is_telefono_valid, is_empresa_valid])
        self.submit_button.setEnabled(is_form_valid)


    def submit(self):
        # La lógica de submit no cambia
        data = {
            "nombre_completo": self.nombre_completo.text().strip(),
            "correo": self.correo.text().strip(),
            "contrasena": self.contrasena.text(),
            "telefono": self.telefono.text().strip(),
            "fecha_nacimiento": self.fecha_nacimiento.date().toString("yyyy-MM-dd"),
            "nombre_empresa": self.nombre_empresa.text().strip(),
            "rfc": self.rfc.text().strip(),
        }
        self.registro_solicitado.emit(data)


class AuthView(QWidget):
    """Vista principal de autenticación que implementa el nuevo diseño de dos paneles."""
    login_solicitado = Signal(str, str)
    registro_solicitado = Signal(dict)
    recuperacion_solicitada = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AuthView")
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        logo_modula_path = resource_path("assets/images/logo_modula.png")
        logo_addsy_path = resource_path("assets/images/logo_addsy_powered.png")

        # === Panel Izquierdo (Branding) ===
        left_panel = QFrame()
        left_panel.setObjectName("AuthLeftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignCenter)
        left_layout.setSpacing(20)

        logo_icon_label = QLabel()
        logo_icon_label.setPixmap(QPixmap(logo_modula_path).scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        logo_text_label = QLabel("MODULA")
        logo_text_label.setObjectName("AuthBrandText")

        tagline_label = QLabel("Tu negocio, modular.")
        tagline_label.setObjectName("AuthTagline")
        
        left_layout.addStretch()
        left_layout.addWidget(logo_icon_label, alignment=Qt.AlignCenter)
        left_layout.addWidget(logo_text_label, alignment=Qt.AlignCenter)
        left_layout.addWidget(tagline_label, alignment=Qt.AlignCenter)
        left_layout.addStretch()

        # === Panel Derecho (Formulario) ===
        right_panel = QFrame()
        right_panel.setObjectName("AuthRightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setAlignment(Qt.AlignCenter)

        form_card = QFrame()
        form_card.setObjectName("AuthFormCard")
        form_card.setMaximumWidth(380)
        form_card.setMinimumHeight(500)
        
        card_layout = QVBoxLayout(form_card)
        card_layout.setContentsMargins(40, 30, 40, 30)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 5)
        form_card.setGraphicsEffect(shadow)
        
        self.title_label = QLabel("Bienvenido a Modula")
        self.title_label.setObjectName("AuthTitle")

        self.error_label = QLabel("")
        self.error_label.setObjectName("AuthErrorLabel")
        self.error_label.setVisible(False)
        self.error_label.setWordWrap(True)
        
        self.stacked_widget = QStackedWidget()
        self.login_form = LoginForm()
        self.register_form = RegisterForm()
        self.stacked_widget.addWidget(self.login_form)
        self.stacked_widget.addWidget(self.register_form)
        
        version_label = QLabel("V1.0")
        version_label.setObjectName("VersionLabel")

        card_layout.addWidget(self.title_label, alignment=Qt.AlignCenter)
        card_layout.addWidget(self.error_label, alignment=Qt.AlignCenter)
        card_layout.addWidget(self.stacked_widget)
        
        right_layout.addWidget(form_card)
        right_layout.addWidget(version_label, 0, Qt.AlignRight | Qt.AlignBottom)

        main_layout.addWidget(left_panel, 40)
        main_layout.addWidget(right_panel, 60)
        
        # Conexiones de Señales
        self.login_form.login_solicitado.connect(self.login_solicitado)
        self.login_form.recuperacion_solicitada.connect(self.recuperacion_solicitada)
        self.register_form.registro_solicitado.connect(self.registro_solicitado)
        
        self.login_form.ir_a_registro.connect(self.show_register_form)
        self.register_form.ir_a_login.connect(self.show_login_form)

    def show_login_form(self):
        self.stacked_widget.setCurrentWidget(self.login_form)
        self.title_label.setText("Bienvenido a Modula")
        self.error_label.setVisible(False)

    def show_register_form(self):
        self.stacked_widget.setCurrentWidget(self.register_form)
        self.title_label.setText("Crear Nueva Cuenta")
        self.error_label.setVisible(False)
        
    def show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def clear_inputs(self):
        """Limpia todos los campos de entrada en ambos formularios."""
        # Limpiar formulario de login
        if hasattr(self, 'login_form'):
            self.login_form.email_input.line_edit.clear()
            self.login_form.password_input.line_edit.clear()
            self.login_form.show_password_checkbox.setChecked(False)

        # Limpiar formulario de registro
        if hasattr(self, 'register_form'):
            self.register_form.nombre_completo.clear()
            self.register_form.correo.clear()
            self.register_form.contrasena.clear()
            self.register_form.telefono.clear()
            self.register_form.fecha_nacimiento.setDate(QDate(2000, 1, 1))
            self.register_form.nombre_empresa.clear()
            self.register_form.rfc.clear()
        
        # Ocultar cualquier mensaje de error
        self.error_label.setVisible(False)