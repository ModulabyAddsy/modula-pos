# src/ui/views/auth_view.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, 
                               QPushButton, QFormLayout, QTabWidget,
                               QSpacerItem, QSizePolicy, QDateEdit)
from PySide6.QtCore import Signal, Qt, QDate
import uuid

class LoginForm(QWidget):
    login_solicitado = Signal(str, str)
    recuperacion_solicitada = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 20, 0, 0)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Correo Electrónico")
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Contraseña")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.recover_button = QPushButton("¿Olvidaste tu contraseña?")
        self.recover_button.setObjectName("link-style-button")
        self.recover_button.clicked.connect(self.recuperacion_solicitada.emit)

        self.submit_button = QPushButton("Entrar")
        self.submit_button.setObjectName("primary")
        self.submit_button.clicked.connect(self.submit)

        layout.addRow(self.email_input)
        layout.addRow(self.password_input)
        layout.addWidget(self.recover_button) # Botón de recuperar va antes del de entrar
        layout.addRow(self.submit_button)
        
    def submit(self):
        email = self.email_input.text()
        password = self.password_input.text()
        self.login_solicitado.emit(email, password)

class RegisterForm(QWidget):
    registro_solicitado = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 20, 0, 0)
        main_layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.nombre_completo = QLineEdit()
        self.correo = QLineEdit()
        self.contrasena = QLineEdit()
        self.contrasena.setEchoMode(QLineEdit.EchoMode.Password)
        self.telefono = QLineEdit()
        
        self.fecha_nacimiento = QDateEdit()
        self.fecha_nacimiento.setCalendarPopup(True)
        self.fecha_nacimiento.setDisplayFormat("yyyy-MM-dd")
        self.fecha_nacimiento.setDate(QDate(2000, 1, 1))

        self.nombre_empresa = QLineEdit()
        self.rfc = QLineEdit()

        form_layout.addRow(QLabel("Nombre Completo:"), self.nombre_completo)
        form_layout.addRow(QLabel("Correo Electrónico:"), self.correo)
        form_layout.addRow(QLabel("Contraseña:"), self.contrasena)
        form_layout.addRow(QLabel("Teléfono:"), self.telefono)
        form_layout.addRow(QLabel("Fecha de Nacimiento:"), self.fecha_nacimiento)
        form_layout.addRow(QLabel("Nombre de la Empresa:"), self.nombre_empresa)
        form_layout.addRow(QLabel("RFC (Opcional):"), self.rfc)

        self.submit_button = QPushButton("Registrar y Proceder al Pago")
        self.submit_button.setObjectName("primary")
        self.submit_button.clicked.connect(self.submit)
        
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.submit_button)

    def submit(self):
        data = {
            "nombre_completo": self.nombre_completo.text(),
            "correo": self.correo.text(),
            "contrasena": self.contrasena.text(),
            "telefono": self.telefono.text(),
            "fecha_nacimiento": self.fecha_nacimiento.date().toString("yyyy-MM-dd"),
            "nombre_empresa": self.nombre_empresa.text(),
            "rfc": self.rfc.text(),
            "id_terminal": str(uuid.uuid4())
        }
        self.registro_solicitado.emit(data)


class AuthView(QWidget):
    login_solicitado = Signal(str, str)
    registro_solicitado = Signal(dict)
    # ✅ CORRECCIÓN: Añadir la señal que faltaba aquí
    recuperacion_solicitada = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AuthView")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        title = QLabel("Modula POS")
        title.setObjectName("h1")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("Punto de Venta Inteligente")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.tabs = QTabWidget()
        self.login_form = LoginForm()
        self.register_form = RegisterForm()
        
        self.tabs.addTab(self.login_form, "Iniciar Sesión")
        self.tabs.addTab(self.register_form, "Crear Cuenta")
        
        # Conectamos las señales de los formularios internos a las señales de esta vista
        self.login_form.login_solicitado.connect(self.login_solicitado)
        self.login_form.recuperacion_solicitada.connect(self.recuperacion_solicitada)
        self.register_form.registro_solicitado.connect(self.registro_solicitado)
        
        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        main_layout.addWidget(self.tabs)
        main_layout.addStretch()