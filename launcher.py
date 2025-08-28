import sys
import os
import subprocess
import requests
import hashlib
import shutil
import zipfile
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QProgressBar, QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QTimer # <-- ¡NUEVA IMPORTACIÓN DE RECURSOS!

# --- Configuración (sin cambios) ---
APP_DIR = 'app'
APP_EXE = 'Modula.exe'
VERSION_FILE = 'version.txt'
API_URL = "https://modula-backend.onrender.com/api/v1/update/check"

class LauncherWindow(QWidget):
    """La ventana de la interfaz gráfica del lanzador, ahora con el estilo de Modula."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modula POS Launcher")
        self.setFixedSize(450, 250) # Hacemos la ventana un poco más grande
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        # --- NUEVO: Aplicamos un estilo general ---
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                font-family: 'Inter', sans-serif;
            }
            QProgressBar {
                border: none;
                background-color: #e0e0e0;
                border-radius: 5px;
                height: 10px;
            }
            QProgressBar::chunk {
                background-color: #0078d4; /* Azul Modula */
                border-radius: 5px;
            }
        """)

        # --- NUEVO: Logo de Modula ---
        logo_label = QLabel()
        pixmap_modula = QPixmap(":/launcher_assets/logo_modula.png")
        logo_label.setPixmap(pixmap_modula.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)

        # --- NUEVO: Título ---
        title_label = QLabel("MODULA POS")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #1F2937;")

        # Etiqueta de estado (sin cambios en la lógica)
        self.status_label = QLabel("Iniciando lanzador...", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; color: #4B5563;")

        # Barra de progreso (sin cambios en la lógica)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)

        # --- NUEVO: Footer "Powered by Addsy" ---

        # --- Layout Principal Reestructurado ---
        main_layout = QVBoxLayout(self)
        main_layout.addStretch(1)
        main_layout.addWidget(logo_label)
        main_layout.addWidget(title_label)
        main_layout.addSpacing(20)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.progress_bar)
        main_layout.addStretch(2)
        main_layout.setContentsMargins(40, 20, 40, 20)

    def set_status(self, text):
        """Actualiza el texto de la etiqueta de estado."""
        self.status_label.setText(text)
        print(text)


def get_current_version():
    """Lee la versión del archivo version.txt."""
    try:
        with open(os.path.join(APP_DIR, VERSION_FILE), 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0"  # Si no existe, asumimos que no hay nada instalado


def run_modula():
    """Lanza la aplicación principal y cierra el lanzador."""
    path_to_exe = os.path.join(APP_DIR, APP_EXE)
    if os.path.exists(path_to_exe):
        subprocess.Popen([path_to_exe])
    else:
        # Aquí podríamos mostrar un error en la GUI
        print(f"Error: No se encontró {APP_EXE}")
    
    QApplication.instance().quit()


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
    except requests.exceptions.RequestException as e:
        print(f"Error de descarga: {e}")
        return False


def verify_hash(filepath, expected_hash):
    """Verifica el hash SHA-256 de un archivo."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    file_hash = sha256_hash.hexdigest()
    print(f"Hash esperado: {expected_hash}")
    print(f"Hash calculado: {file_hash}")
    return file_hash.lower() == expected_hash.lower()


def install_update(zip_filepath):
    """Instala la actualización de forma segura usando el método de backup y rollback."""
    backup_dir = f"{APP_DIR}_backup"
    
    try:
        if os.path.exists(APP_DIR):
            print(f"Creando backup en '{backup_dir}'...")
            shutil.move(APP_DIR, backup_dir)

        print(f"Extrayendo nueva versión en '{APP_DIR}'...")
        os.makedirs(APP_DIR)
        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            zip_ref.extractall(APP_DIR)
        
        if os.path.exists(backup_dir):
            print("Instalación exitosa. Eliminando backup...")
            shutil.rmtree(backup_dir)
            
        return True

    except Exception as e:
        print(f"🔥🔥 ERROR durante la instalación: {e}. Restaurando backup...")
        if os.path.exists(APP_DIR):
            shutil.rmtree(APP_DIR)
        if os.path.exists(backup_dir):
            shutil.move(backup_dir, APP_DIR)
        return False


def check_for_updates(window):
    """Función principal que orquesta el proceso de actualización."""
    window.set_status("Buscando actualizaciones...")
    current_version = get_current_version()
    
    try:
        response = requests.get(f"{API_URL}?version={current_version}", timeout=10)
        response.raise_for_status()

        if response.status_code == 204:
            window.set_status("¡Estás al día!")
            QTimer.singleShot(1500, run_modula)
            return

        update_info = response.json()
        new_version = update_info.get("version")
        download_url = update_info.get("url")
        expected_hash = update_info.get("hash")
        
        # 1. Descarga
        window.set_status(f"Descargando versión {new_version}...")
        window.progress_bar.setRange(0, 100)
        zip_save_path = "update_package.zip"
        
        def update_progress(bytes_downloaded, total_size):
            if total_size > 0:
                percent = int((bytes_downloaded / total_size) * 100)
                window.progress_bar.setValue(percent)
        
        if not download_update(download_url, zip_save_path, update_progress):
            window.set_status("Error de descarga. Iniciando versión actual.")
            QTimer.singleShot(2000, run_modula)
            return
            
        # 2. Verificación
        window.set_status("Verificando integridad del archivo...")
        window.progress_bar.setRange(0, 0)
        if not verify_hash(zip_save_path, expected_hash):
            window.set_status("Error de verificación. Archivo corrupto.")
            os.remove(zip_save_path)
            QTimer.singleShot(2000, run_modula)
            return

        # 3. Instalación
        window.set_status("Instalando actualización...")
        if not install_update(zip_save_path):
            window.set_status("Error de instalación. Se restauró la versión anterior.")
            os.remove(zip_save_path)
            QTimer.singleShot(2000, run_modula)
            return

        os.remove(zip_save_path)
        window.set_status("¡Actualización completada!")
        QTimer.singleShot(1500, run_modula)

    except requests.exceptions.RequestException as e:
        window.set_status("Error de red. Iniciando versión actual.")
        print(f"No se pudo conectar al servidor de actualizaciones: {e}")
        QTimer.singleShot(2000, run_modula)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LauncherWindow()
    window.show()

    # Inicia el proceso de actualización 500ms después de que la ventana se muestre
    QTimer.singleShot(500, lambda: check_for_updates(window))
    
    sys.exit(app.exec())