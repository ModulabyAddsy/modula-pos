# src/core/utils.py
import sys
import os

def resource_path(relative_path):
    """ Obtiene la ruta absoluta al recurso, funciona para desarrollo y para PyInstaller """
    try:
        # PyInstaller crea una carpeta temporal y guarda la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # En desarrollo, la base es la raíz del proyecto, pero los assets están en 'src'
        base_path = os.path.abspath("./src")

    return os.path.join(base_path, relative_path)