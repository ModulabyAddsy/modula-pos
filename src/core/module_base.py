from PySide6.QtWidgets import QWidget

class ModulaModuleBase(QWidget):
    """
    La clase base 'contrato' de la que todos los módulos de Modula deben heredar.

    Asegura que cada módulo tenga una estructura y una interfaz predecibles
    para que el software principal pueda cargarlo e interactuar con él.
    """
    def __init__(self, app_controller=None, parent=None):
        """
        El constructor de un módulo siempre recibirá una referencia al 
        controlador principal de la aplicación.

        Args:
            app_controller: Una instancia de AppController para acceder a
                            funciones globales como el cliente API, etc.
            parent: El widget padre, gestionado por Qt.
        """
        super().__init__(parent)
        
        # Guardamos una referencia al controlador para que el módulo pueda
        # interactuar con el resto de la aplicación (ej. hacer llamadas a la API).
        self.app_controller = app_controller

    def on_module_loaded(self):
        """
        Este método será llamado por el sistema principal justo después de que
        el módulo sea cargado en una pestaña. Útil para iniciar tareas.
        """
        pass # Los módulos pueden sobreescribir este método si lo necesitan.

    def on_module_closed(self):
        """
        Este método será llamado por el sistema principal justo antes de que
        la pestaña del módulo se cierre. Útil para guardar estados o limpiar.
        """
        pass # Los módulos pueden sobreescribir este método si lo necesitan.