# app_main.py (Modificado)
import sys
from PySide6.QtWidgets import QApplication
from dotenv import load_dotenv
from src.core.utils import resource_path
from src.core.app_controller import AppController

# --- Función de arranque de la aplicación principal ---
def start_modula_app(app_instance):
    """
    Inicializa y ejecuta la lógica principal de la aplicación Modula.
    Esta función es llamada por el launcher después de las verificaciones.
    """
    # Cargar las variables de entorno
    load_dotenv()

    # Cargar la hoja de estilos
    try:
        stylesheet_path = resource_path("assets/qss/style.qss")
        with open(stylesheet_path, "r", encoding="utf-8") as f:
            app_instance.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Advertencia: No se encontró el archivo de estilos 'style.qss'.")

    # Iniciar el controlador principal de la aplicación
    # NOTA: El controlador necesitará ser un objeto persistente para que no sea eliminado por el recolector de basura.
    # Lo asignaremos a una propiedad de la instancia de la app.
    app_instance.controller = AppController(app_instance)
    app_instance.controller.run()

# --- Bloque de prueba (Opcional) ---
# Este bloque solo se ejecutará si corres app_main.py directamente
# para propósitos de desarrollo y depuración.
if __name__ == '__main__':
    app = QApplication(sys.argv)
    start_modula_app(app)
    sys.exit(app.exec())