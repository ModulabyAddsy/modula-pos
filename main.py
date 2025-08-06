# main.py
import sys
from PySide6.QtWidgets import QApplication
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

from src.core.app_controller import AppController

if __name__ == '__main__':
    app = QApplication(sys.argv)
    try:
        with open("src/assets/qss/style.qss", "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Advertencia: No se encontró el archivo de estilos 'style.qss'.")

    controller = AppController(app)
    controller.run()
    sys.exit(app.exec())