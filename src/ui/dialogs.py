# src/ui/dialogs.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                               QDialogButtonBox, QMessageBox, QRadioButton, QComboBox, QSizePolicy, QSpacerItem)


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
        
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Ingresa el correo electrónico asociado a tu cuenta Addsy para recibir un enlace de recuperación.")
        self.label.setWordWrap(True)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("tu-correo@ejemplo.com")
        
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.email_input)
        self.layout.addWidget(self.buttonBox)

    def get_email(self):
        return self.email_input.text().strip()