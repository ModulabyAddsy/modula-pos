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
        self.setFixedSize(450, 250)
        
        # --- PASO 1: HACEMOS LA VENTANA PRINCIPAL TRANSPARENTE ---
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # --- PASO 2: CREAMOS UN CONTENEDOR PRINCIPAL QUE SÍ TENDRÁ ESTILO ---
        main_container = QWidget(self)
        main_container.setObjectName("MainContainer")
        main_container.setStyleSheet("""
            #MainContainer {
                background-color: #ffffff;
                border: 1px solid #374151;
                border-radius: 8px; /* Añadimos bordes redondeados */
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

        # --- PASO 3: TODO LO DEMÁS VA DENTRO DEL CONTENEDOR ---
        
        # Logo de Modula
        logo_label = QLabel()
        pixmap_modula = QPixmap(":/launcher_assets/logo_modula.png")
        logo_label.setPixmap(pixmap_modula.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)

        # Título
        title_label = QLabel("MODULA POS")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #1F2937;")

        # Etiqueta de estado
        self.status_label = QLabel("Iniciando lanzador...", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; color: #4B5563;")

        # Barra de progreso
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)

        # Footer "Powered by Addsy"
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

        # Usamos un layout para el contenedor
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

        # Finalmente, un layout simple para la ventana principal transparente
        # que solo contiene a nuestro contenedor
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)

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
            window.set_status(f"Abriendo Modula v{current_version}")
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
        # --- LÍNEA CORREGIDA ---
        # Usamos la variable 'new_version' que obtuvimos de la API
        window.set_status(f"Abriendo Modula v{new_version}")
        QTimer.singleShot(1500, run_modula)

    except requests.exceptions.RequestException as e:
        window.set_status("Error de red. Iniciando versión actual.")
        print(f"No se pudo conectar al servidor de actualizaciones: {e}")
        QTimer.singleShot(2000, run_modula)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LauncherWindow()
    window.show()
    
    window.activateWindow()
    window.raise_()

    # Inicia el proceso de actualización 500ms después de que la ventana se muestre
    QTimer.singleShot(500, lambda: check_for_updates(window))
    
    sys.exit(app.exec())