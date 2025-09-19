import sys
import os
import subprocess
import requests
import hashlib
import shutil
import zipfile
import winreg # Biblioteca para interactuar con el registro de Windows
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget, QLabel, QProgressBar, QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, QTimer, QCoreApplication, Signal
import ctypes
from datetime import datetime
from src.core.utils import resource_path 
# NUEVO: Importamos la función de arranque de nuestra aplicación principal
import app_main

# --- Configuración del Lanzador ---
APP_DIR_NAME = 'Modula POS'
# NOTA: APP_EXE ya no se usa para lanzar, pero puede ser útil para otras cosas (ej. icono del acceso directo)
APP_EXE = 'Modula.exe' 
VERSION_FILE = 'version.txt'
API_URL = "https://modula-backend.onrender.com/api/v1/update/check"
UNINSTALLER_EXE = 'uninstaller.exe'

# --- Funciones de Utilidad ---
def get_install_path():
    """Busca la ruta de instalación de Modula en el registro de Windows."""
    try:
        reg_key_path = fr"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{APP_DIR_NAME}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_key_path) as key:
            install_path = winreg.QueryValueEx(key, "InstallLocation")[0]
            return os.path.normpath(install_path)
    except Exception:
        return None

def get_current_version(install_path):
    """Lee la versión del archivo version.txt desde una ruta dada."""
    try:
        with open(os.path.join(install_path, VERSION_FILE), 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0"

# MODIFICADO: La función run_modula ahora inicia la app en el mismo proceso
def run_modula(launcher_window):
    """Oculta la ventana del launcher e inicia la aplicación principal de Modula."""
    # Ocultamos la ventana del launcher en lugar de cerrarla
    launcher_window.hide()
    
    # Obtenemos la instancia de QApplication que ya está en ejecución
    app_instance = QApplication.instance()
    
    # Llamamos a la función que arranca la lógica de Modula
    app_main.start_modula_app(app_instance)

def download_update(url, save_path, progress_callback):
    """Descarga un archivo desde una URL y reporta el progreso."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        bytes_downloaded = 0
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                bytes_downloaded += len(chunk)
                f.write(chunk)
                progress_callback(bytes_downloaded, total_size)
        return True
    except requests.exceptions.RequestException:
        return False

def verify_hash(filepath, expected_hash):
    """Verifica el hash SHA-256 de un archivo."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    file_hash = sha256_hash.hexdigest()
    return file_hash.lower() == expected_hash.lower()

def update_app(zip_filepath, install_path):
    """Actualiza la aplicación de forma segura con el método de backup y rollback."""
    backup_dir = f"{install_path}_backup"
    
    try:
        if os.path.exists(install_path):
            shutil.move(install_path, backup_dir)
        
        os.makedirs(install_path)
        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            zip_ref.extractall(install_path)
        
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
            
        return True
    except Exception as e:
        QMessageBox.critical(None, "Error de Actualización", f"No se pudo actualizar la aplicación. Se restauró la versión anterior. Error: {e}")
        if os.path.exists(install_path):
            shutil.rmtree(install_path)
        if os.path.exists(backup_dir):
            shutil.move(backup_dir, install_path)
        return False

# --- Lógica principal del lanzador ---
def check_for_updates_logic(window, install_path):
    current_version = get_current_version(install_path)
    try:
        response = requests.get(f"{API_URL}?version={current_version}", timeout=10)
        response.raise_for_status()
        if response.status_code == 204:
            window.set_status(f"Abriendo Modula v{current_version}")
            # CORREGIDO: Pasamos 'window' a run_modula
            QTimer.singleShot(1500, lambda: run_modula(window))
            return
            
        update_info = response.json()
        new_version = update_info.get("version")
        download_url = update_info.get("url")
        expected_hash = update_info.get("hash")
        window.set_status(f"Descargando versión {new_version}...")
        window.progress_bar.setRange(0, 100)
        zip_save_path = "update_package.zip"
        
        def update_progress(bytes_downloaded, total_size):
            if total_size > 0:
                percent = int((bytes_downloaded / total_size) * 100)
                window.progress_bar.setValue(percent)
                
        if not download_update(download_url, zip_save_path, update_progress):
            window.set_status("Error de descarga. Iniciando versión actual.")
            # CORREGIDO: Pasamos 'window' a run_modula
            QTimer.singleShot(2000, lambda: run_modula(window))
            return
            
        window.set_status("Verificando integridad del archivo...")
        window.progress_bar.setRange(0, 0)
        
        if not verify_hash(zip_save_path, expected_hash):
            window.set_status("Error de verificación. Archivo corrupto.")
            os.remove(zip_save_path)
            # CORREGIDO: Pasamos 'window' a run_modula
            QTimer.singleShot(2000, lambda: run_modula(window))
            return
            
        window.set_status("Instalando actualización...")
        if not update_app(zip_save_path, install_path):
            # CORREGIDO: Pasamos 'window' a run_modula
            QTimer.singleShot(2000, lambda: run_modula(window))
            return
            
        os.remove(zip_save_path)
        window.set_status(f"Abriendo Modula v{new_version}")
        # CORREGIDO: Pasamos 'window' a run_modula
        QTimer.singleShot(1500, lambda: run_modula(window))
        
    except requests.exceptions.RequestException as e:
        window.set_status("Error de red. Iniciando versión actual.")
        # CORREGIDO: Pasamos 'window' a run_modula
        QTimer.singleShot(2000, lambda: run_modula(window))
        
class LauncherWindow(QWidget):
    """La ventana de la interfaz gráfica del lanzador, ahora con el estilo de Modula."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modula POS Launcher")
        self.setFixedSize(450, 250)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        main_container = QWidget(self)
        main_container.setObjectName("MainContainer")
        main_container.setStyleSheet("""
            #MainContainer {
                background-color: #ffffff;
                border: 1px solid #374151;
                border-radius: 8px;
            }
            QProgressBar {
                border: none;
                background-color: #e0e0e0;
                border-radius: 5px;
                height: 10px;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 5px;
            }
        """)
        
        logo_label = QLabel()
        # NOTA: Asegúrate de tener los recursos del launcher compilados
        pixmap_modula = QPixmap(":/launcher_assets/logo_modula.png") 
        logo_label.setPixmap(pixmap_modula.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        
        title_label = QLabel("MODULA POS")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #1F2937;")
        
        self.status_label = QLabel("Iniciando lanzador...", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; color: #4B5563;")
        
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        
        footer_container = QWidget()
        footer_layout = QHBoxLayout(footer_container)
        footer_layout.setContentsMargins(0,0,0,0)
        footer_layout.setSpacing(6)
        
        footer_text = QLabel("Powered by:")
        footer_text.setStyleSheet("font-size: 12px; color: #6B7280;")
        
        footer_logo = QLabel()
        pixmap_addsy = QPixmap(":/launcher_assets/logo_addsy_powered.png")
        footer_logo.setPixmap(pixmap_addsy.scaledToHeight(16, Qt.SmoothTransformation))
        
        footer_layout.addStretch()
        footer_layout.addWidget(footer_text)
        footer_layout.addWidget(footer_logo)
        footer_layout.addStretch()
        
        container_layout = QVBoxLayout(main_container)
        container_layout.addStretch(1)
        container_layout.addWidget(logo_label)
        container_layout.addWidget(title_label)
        container_layout.addSpacing(20)
        container_layout.addWidget(self.status_label)
        container_layout.addWidget(self.progress_bar)
        container_layout.addStretch(2)
        container_layout.addWidget(footer_container)
        container_layout.setContentsMargins(40, 20, 40, 20)
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)

    def set_status(self, text):
        self.status_label.setText(text)
        QCoreApplication.processEvents()
        print(text)

if __name__ == '__main__':
    # 1. Crea la aplicación PRIMERO
    app = QApplication(sys.argv)

    # NUEVO: Establecer el ícono global de la aplicación
    # Esto asegura que todas las ventanas y la barra de tareas tengan el ícono correcto.
    try:
        icon_path = resource_path("assets/images/logo_modula.ico")
        app.setWindowIcon(QIcon(icon_path))
    except Exception as e:
        print(f"No se pudo cargar el ícono de la aplicación: {e}")

    # 2. Ahora, realiza las comprobaciones
    install_path = get_install_path()
    if not install_path:
        # Es seguro mostrar un QMessageBox porque 'app' ya existe
        QMessageBox.critical(None, "Error", "Modula no está instalado. Ejecute el instalador.")
        sys.exit(1)
    
    # 3. Si todo está bien, crea y muestra la ventana principal
    window = LauncherWindow()
    window.show()
    window.activateWindow()
    window.raise_()
    
    # 4. Inicia la lógica de actualización y el bucle de eventos
    QTimer.singleShot(500, lambda: check_for_updates_logic(window, install_path))
    sys.exit(app.exec())