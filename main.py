# main.py
import sys
from PySide6.QtWidgets import QApplication
from dotenv import load_dotenv
import src.resources_rc
from src.core.utils import resource_path

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# --- Importar el controlador principal ---
from src.core.app_controller import AppController

# --- Punto de entrada principal ---
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # --- Cargar hoja de estilos de forma segura ---
    try:
        # Ahora la ruta relativa NO lleva 'src' al principio
        stylesheet_path = resource_path("assets/qss/style.qss")
        with open(stylesheet_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Advertencia: No se encontró el archivo de estilos 'style.qss'.")

    # --- Iniciar la aplicación ---
    controller = AppController(app)
    controller.run()
    sys.exit(app.exec())