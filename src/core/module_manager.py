# src/core/module_manager.py

import os
import json
import shutil
import requests
import zipfile
import importlib.util
from pathlib import Path
from PySide6.QtCore import Qt

# Usamos la misma base que ya tienes definida para la configuración
CONFIG_DIR = Path(os.getenv('APPDATA')) / "Modula"

# Creamos un directorio hermano a 'Databases' para los módulos
MODULES_DIR = CONFIG_DIR / "Modules"
LOCAL_MANIFEST_FILE = MODULES_DIR / "installed.json"


class ModuleManager:
    """
    Gestiona la descarga, actualización, carga y acceso a los módulos de Modula.
    """
    def __init__(self, api_client, app_controller):
        self.api_client = api_client
        self.app_controller = app_controller
        MODULES_DIR.mkdir(exist_ok=True) # Se asegura de que la carpeta de módulos exista

    def check_for_updates(self):
        """
        Orquesta el proceso completo de verificación y actualización de módulos.
        """
        print("▶️ Iniciando revisión de módulos...")
        try:
            # 1. Obtener el manifiesto del servidor
            response = self.api_client.get_modules_manifest()
            if response.get("status") != "ok":
                print("❌ No se pudo obtener el manifiesto de módulos del servidor.")
                return
            
            server_manifest = response.get("modules", {})

            # 2. Cargar el manifiesto local de módulos ya instalados
            local_manifest = {}
            if LOCAL_MANIFEST_FILE.exists():
                with open(LOCAL_MANIFEST_FILE, "r", encoding="utf-8") as f:
                    local_manifest = json.load(f)

            # 3. Comparar y descargar
            for module_id, server_data in server_manifest.items():
                local_version = local_manifest.get(module_id, {}).get("version", "0.0.0")
                
                if server_data["version"] > local_version:
                    print(f"🔄 Actualización encontrada para '{server_data['nombre']}' (v{server_data['version']})...")
                    self._download_and_install_module(module_id, server_data)
                    local_manifest[module_id] = {"version": server_data["version"]}

            # 4. Guardar el estado actualizado del manifiesto local
            with open(LOCAL_MANIFEST_FILE, "w", encoding="utf-8") as f:
                json.dump(local_manifest, f, indent=4)
            
            print("✅ Revisión de módulos finalizada.")

        except Exception as e:
            print(f"🔥🔥 ERROR durante la actualización de módulos: {e}")

    def _download_and_install_module(self, module_id, server_data):
        """Descarga, verifica y descomprime un paquete de módulo."""
        download_url = server_data.get("download_url")
        if not download_url:
            print(f"⚠️  No se proporcionó URL de descarga para {module_id}. Omitiendo.")
            return

        module_path = MODULES_DIR / module_id
        zip_path = MODULES_DIR / f"{module_id}.zip"

        # Descargar el archivo
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # (Aquí iría la verificación del checksum si la implementamos)

        # Descomprimir
        if module_path.exists():
            shutil.rmtree(module_path) # Eliminar la versión vieja
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(module_path)
        
        os.remove(zip_path) # Limpiar el archivo .zip
        print(f"✔️ Módulo '{server_data['nombre']}' instalado correctamente en: {module_path}")

    def get_installed_modules(self):
        """
        Escanea el directorio de módulos y devuelve una lista con los manifiestos
        de todos los módulos válidos que están instalados.
        """
        installed = []
        for item in MODULES_DIR.iterdir():
            if item.is_dir():
                manifest_path = item / "manifest.json"
                if manifest_path.exists():
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        installed.append(json.load(f))
        return sorted(installed, key=lambda m: m.get('nombre', ''))

    def load_module_widget(self, module_manifest: dict):
        """
        Carga dinámicamente el widget principal de un módulo usando su manifiesto.
        """
        try:
            module_id = module_manifest['id']
            entry_point = module_manifest['entry_point']
            class_name = module_manifest['clase_principal']
            
            module_path = MODULES_DIR / module_id / entry_point
            
            spec = importlib.util.spec_from_file_location(f"modules.{module_id}", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            ModuleWidgetClass = getattr(module, class_name)
            
            # Instanciamos la clase del módulo, pasándole el app_controller
            return ModuleWidgetClass(app_controller=self.app_controller)
            
        except Exception as e:
            print(f"🔥🔥 ERROR al cargar dinámicamente el módulo '{module_manifest.get('nombre')}': {e}")
            # Devolvemos un widget de error para no romper la UI
            from PySide6.QtWidgets import QLabel
            error_widget = QLabel(f"Error al cargar el módulo:\n{module_manifest.get('nombre')}")
            error_widget.setAlignment(Qt.AlignCenter)
            return error_widget
