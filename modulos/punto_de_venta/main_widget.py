# Importamos nuestra nueva clase base
from src.core.module_base import ModulaModuleBase
from PySide6.QtWidgets import QLabel, QVBoxLayout

# La clase del módulo AHORA HEREDA de ModulaModuleBase
class PuntoDeVentaWidget(ModulaModuleBase):
    def __init__(self, app_controller=None, parent=None):
        # Es crucial llamar al __init__ de la clase padre
        super().__init__(app_controller, parent)
        
        # A partir de aquí, el código es específico del módulo
        self.setWindowTitle("Punto de Venta")
        
        layout = QVBoxLayout(self)
        label = QLabel(f"Interfaz del Punto de Venta (Versión del manifest)")
        layout.addWidget(label)
        
        print("¡Módulo Punto de Venta cargado!")

    def on_module_loaded(self):
        print("El módulo Punto de Venta ahora es visible en una pestaña.")
        # Aquí podrías, por ejemplo, cargar la lista de productos
        # usando self.app_controller.api_client.get_products()

    def on_module_closed(self):
        print("El módulo Punto de Venta se está cerrando.")
        # Aquí podrías guardar el estado del carrito de compras, si es necesario