# src/ui/dialogs.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                               QDialogButtonBox, QMessageBox, QRadioButton, QComboBox, QSizePolicy, QSpacerItem, QPushButton,
                               QHBoxLayout, QTextEdit, QCheckBox)
from PySide6.QtGui import QIcon, QFont
from PySide6.QtCore import Qt
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

class CrearSucursalDialog(QDialog):
    def __init__(self, ciudad, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Registrar Nueva Sucursal")
        
        self.layout = QVBoxLayout(self)
        
        self.label = QLabel(f"Detectamos una nueva ubicación en <b>{ciudad}</b> que no está registrada.\n"
                            "Ingresa un nombre para registrarla como una nueva sucursal:")
        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText("Ej: Sucursal Contry")
        
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.nombre_input)
        self.layout.addWidget(self.buttonBox)

    def get_nombre(self):
        """Devuelve el nombre ingresado, sin espacios extra."""
        return self.nombre_input.text().strip()

def mostrar_dialogo_migracion(nombre_sucursal_destino) -> bool:
    """Muestra un diálogo simple preguntando al usuario si desea migrar."""
    respuesta = QMessageBox.question(None, "Detección de Ubicación",
        f"Hemos detectado que esta terminal podría estar en la sucursal:\n\n"
        f"<b>{nombre_sucursal_destino}</b>\n\n"
        f"¿Deseas mover esta terminal a esta sucursal?",
        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
    return respuesta == QMessageBox.Yes

class ResolverUbicacionDialog(QDialog):
    def __init__(self, sucursales_existentes, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resolver Conflicto de Ubicación")
        self.setMinimumWidth(400)

        # --- Layout y Widgets ---
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Detectamos que esta terminal está en una ubicación no registrada.\n¿Qué deseas hacer?")
        self.label.setWordWrap(True)

        self.opcion_crear = QRadioButton("Crear una nueva sucursal en esta ubicación (Se añadirá un cargo de $99 MXN/mes a tu plan)")
        self.nombre_sucursal_input = QLineEdit()
        self.nombre_sucursal_input.setPlaceholderText("Ej: Sucursal Cumbres")

        self.opcion_asignar = QRadioButton("Asignar esta terminal a una sucursal existente")
        self.sucursales_combo = QComboBox()
        for suc in sucursales_existentes:
            self.sucursales_combo.addItem(suc["nombre"], suc["id"])
        
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        # --- Añadir al Layout ---
        self.layout.addWidget(self.label)
        self.layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        self.layout.addWidget(self.opcion_crear)
        self.layout.addWidget(self.nombre_sucursal_input)
        self.layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        self.layout.addWidget(self.opcion_asignar)
        self.layout.addWidget(self.sucursales_combo)
        self.layout.addWidget(self.buttonBox)

        # --- Lógica interna ---
        self.opcion_crear.toggled.connect(self.actualizar_estado_inputs)
        self.opcion_crear.setChecked(True) # Iniciar con "crear" seleccionado

        # --- Conexiones ---
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def actualizar_estado_inputs(self):
        self.nombre_sucursal_input.setEnabled(self.opcion_crear.isChecked())
        self.sucursales_combo.setEnabled(not self.opcion_crear.isChecked())

    def get_resultado(self):
        if self.opcion_crear.isChecked():
            return ("crear", {"nombre": self.nombre_sucursal_input.text().strip()})
        else:
            id_sucursal = self.sucursales_combo.currentData()
            return ("asignar", {"id_sucursal": id_sucursal})
        
class SeleccionarSucursalDialog(QDialog):
    def __init__(self, sucursales, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Asignar Terminal a Sucursal")
        
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Por favor, selecciona la sucursal a la que pertenece esta nueva terminal:")
        self.combo_sucursales = QComboBox()
        for suc in sucursales:
            self.combo_sucursales.addItem(suc["nombre"], suc["id"])
            
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.combo_sucursales)
        self.layout.addWidget(self.buttonBox)

    def get_selected_sucursal_id(self):
        return self.combo_sucursales.currentData()
    
class RecuperarContrasenaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recuperar Contraseña")
        self.setObjectName("CustomDialog") # Para aplicar estilos
        self.setMinimumWidth(400)

        # --- Layout Principal ---
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # --- Título del Diálogo ---
        title_label = QLabel("Recuperar contraseña")
        title_label.setObjectName("DialogTitle")

        # --- Texto Descriptivo ---
        info_label = QLabel("Ingresa tu correo para recibir las instrucciones de recuperación.")
        info_label.setObjectName("DialogInfoText")
        info_label.setWordWrap(True)

        # --- Campo de Email ---
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("tu-correo@ejemplo.com")
        
        # --- Layout para los Botones (Cancel, Send) ---
        button_layout = QHBoxLayout()
        button_layout.addStretch() # Empuja los botones a la derecha

        self.cancel_button = QPushButton("Cancelar")
        self.send_button = QPushButton("Enviar")
        self.send_button.setObjectName("LoginButton") # Reutilizamos el estilo del botón primario

        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.send_button)

        # --- Añadir todos los widgets al layout principal ---
        main_layout.addWidget(title_label)
        main_layout.addWidget(info_label)
        main_layout.addWidget(self.email_input)
        main_layout.addStretch() # Espacio flexible
        main_layout.addLayout(button_layout)

        # --- Conexiones ---
        self.send_button.clicked.connect(self.accept) # 'accept' cierra el diálogo con resultado "Ok"
        self.cancel_button.clicked.connect(self.reject) # 'reject' cierra el diálogo con resultado "Cancel"

    def get_email(self):
        """Esta función se mantiene igual y es la que usa el app_controller."""
        return self.email_input.text().strip()

class NewTerminalDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # --- CONFIGURACIÓN DE LA VENTANA ---
        self.setWindowTitle("Registro de Nueva Terminal")

        # <<-- CAMBIO: Construimos la ruta absoluta al ícono y la usamos
        icon_path = str(PROJECT_ROOT / "src" / "assets" / "images" / "logo_modula.ico")
        self.setWindowIcon(QIcon(icon_path)) # Usamos la ruta correcta y segura
        
        self.setMinimumSize(450, 400)
        self.setObjectName("NewTerminalDialog")
        self.setModal(True)

        # --- WIDGETS ---
        # (El resto del código de la clase no necesita cambios y permanece igual)
        # Título principal
        self.title_label = QLabel("Detectamos un nuevo equipo")
        self.title_label.setObjectName("titleLabel")

        # Subtítulo explicativo
        self.subtitle_label = QLabel(
            "Para continuar, es necesario registrar este dispositivo como una "
            "nueva terminal asociada a tu cuenta de Modula."
        )
        self.subtitle_label.setObjectName("subtitleLabel")
        self.subtitle_label.setWordWrap(True)

        # Recuadro con Términos y Condiciones
        self.terms_text_edit = QTextEdit()
        self.terms_text_edit.setReadOnly(True)
        self.terms_text_edit.setObjectName("termsTextEdit")
        self.terms_text_edit.setHtml(
            """
            <h4 style="margin-bottom: 5px;">Términos y Condiciones por Terminal Adicional</h4>
            <p>Al aceptar y registrar esta nueva terminal, usted comprende y está de acuerdo con las siguientes condiciones:</p>
            <ul>
                <li><b>Cargo Adicional:</b> Se aplicará un cargo recurrente de <b>$50.00 MXN + IVA</b> a su suscripción mensual por cada terminal adicional registrada. Este monto se verá reflejado en su próximo estado de cuenta.</li>
                <li><b>Activación:</b> La terminal se activará de forma inmediata tras la confirmación, permitiendo el acceso completo a las funciones de Modula Punto de Venta.</li>
                <li><b>Facturación:</b> El cobro es recurrente y se mantendrá activo mientras la terminal no sea dada de baja desde su panel de administración de cuenta en el portal de Addsy.</li>
                <li><b>Gestión:</b> Puede administrar, desactivar o eliminar sus terminales en cualquier momento desde la sección "Mi Suscripción" > "Administrar Terminales" en su cuenta.</li>
            </ul>
            """
        )

        # Checkbox de aceptación
        self.accept_checkbox = QCheckBox("He leído y acepto los Términos y Condiciones para añadir una nueva terminal.")
        self.accept_checkbox.setObjectName("acceptCheckbox")

        # Botones de Acción
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setObjectName("cancelButton")
        
        self.accept_button = QPushButton("Aceptar y Registrar")
        self.accept_button.setObjectName("acceptButton")
        self.accept_button.setEnabled(False) # Deshabilitado por defecto

        # --- LAYOUTS ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)

        buttons_layout = QHBoxLayout()
        buttons_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.accept_button)

        main_layout.addWidget(self.title_label)
        main_layout.addWidget(self.subtitle_label)
        main_layout.addWidget(self.terms_text_edit)
        main_layout.addWidget(self.accept_checkbox)
        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        main_layout.addLayout(buttons_layout)
        
        # --- SEÑALES Y SLOTS (Lógica) ---
        self.accept_checkbox.stateChanged.connect(self.toggle_accept_button)
        self.accept_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def toggle_accept_button(self, state):
        """Habilita o deshabilita el botón de aceptar según el estado del checkbox."""
        if state == Qt.CheckState.Checked.value:
            self.accept_button.setEnabled(True)
        else:
            self.accept_button.setEnabled(False)