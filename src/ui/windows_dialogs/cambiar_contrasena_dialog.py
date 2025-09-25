# src/ui/dialogs/cambiar_contrasena_dialog.py

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                               QCheckBox, QDialogButtonBox, QMessageBox)

class CambiarContrasenaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cambio de Contraseña Requerido")
        self.setModal(True) # Impide interactuar con la ventana principal

        self.nueva_contrasena = ""

        # --- Creación de Widgets ---
        layout = QVBoxLayout(self)
        self.info_label = QLabel(
            "Por motivos de seguridad, es necesario que establezcas una nueva contraseña personal."
        )
        self.pass_label = QLabel("Nueva Contraseña:")
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.Password)

        self.confirm_label = QLabel("Confirmar Nueva Contraseña:")
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)

        self.show_pass_checkbox = QCheckBox("Mostrar contraseñas")

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        # --- Añadir Widgets al Layout ---
        layout.addWidget(self.info_label)
        layout.addWidget(self.pass_label)
        layout.addWidget(self.pass_input)
        layout.addWidget(self.confirm_label)
        layout.addWidget(self.confirm_input)
        layout.addWidget(self.show_pass_checkbox)
        layout.addWidget(self.button_box)

        # --- Conexiones de Señales ---
        self.show_pass_checkbox.toggled.connect(self.toggle_password_visibility)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def toggle_password_visibility(self, checked):
        if checked:
            self.pass_input.setEchoMode(QLineEdit.Normal)
            self.confirm_input.setEchoMode(QLineEdit.Normal)
        else:
            self.pass_input.setEchoMode(QLineEdit.Password)
            self.confirm_input.setEchoMode(QLineEdit.Password)

    def accept(self):
        """ Se ejecuta al presionar OK. Valida los datos antes de cerrar. """
        pass1 = self.pass_input.text()
        pass2 = self.confirm_input.text()

        if not pass1 or not pass2:
            QMessageBox.warning(self, "Error", "Ambos campos son obligatorios.")
            return

        if pass1 != pass2:
            QMessageBox.warning(self, "Error", "Las contraseñas no coinciden.")
            return
        
        # Validación de seguridad básica (puedes hacerla más compleja)
        if len(pass1) < 8:
            QMessageBox.warning(self, "Contraseña Débil", "La contraseña debe tener al menos 8 caracteres.")
            return

        self.nueva_contrasena = pass1
        super().accept() # Cierra el diálogo con resultado OK

    def get_nueva_contrasena(self) -> str:
        return self.nueva_contrasena
