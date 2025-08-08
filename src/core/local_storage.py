# src/core/local_storage.py
import json
import os
from pathlib import Path
from datetime import datetime, timezone

# --- RUTA DE CONFIGURACIÓN ESTÁNDAR ---
# Se define una única ubicación para el archivo de configuración.
# Usar os.getenv('APPDATA') es una práctica común en Windows para encontrar la carpeta
# de datos de aplicación del usuario.
# La ruta final será algo como: C:\Users\TuUsuario\AppData\Roaming\Modula\modula_config.json
CONFIG_DIR = Path(os.getenv('APPDATA')) / "Modula"
CONFIG_FILE = CONFIG_DIR / "modula_config.json"
# ✅ NUEVO: Definir el directorio para las bases de datos locales
DB_DIR = CONFIG_DIR / "Databases"

def _ensure_config_dir_exists():
    """
    Función de ayuda privada para asegurar que el directorio de configuración exista.
    Si no existe, lo crea.
    """
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"❌ Error crítico: No se pudo crear el directorio de configuración en {CONFIG_DIR}. Error: {e}")
        # En una aplicación real, podrías lanzar una excepción aquí para detener la ejecución.
        raise

def save_terminal_id(terminal_id: str):
    """
    Guarda el ID de la terminal en el archivo de configuración.
    Sobrescribe el archivo si ya existe.
    """
    try:
        _ensure_config_dir_exists() # Se asegura de que la carpeta exista antes de escribir.
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"id_terminal": terminal_id}, f, indent=4)
        print(f"✔️ ID de terminal guardado localmente: {terminal_id}")
    except (IOError, OSError) as e:
        print(f"❌ Error al guardar el ID de la terminal: {e}")

def get_id_terminal() -> str | None:
    """
    Obtiene el ID de la terminal desde el archivo de configuración.
    Devuelve el ID si lo encuentra, o None si el archivo no existe o hay un error.
    """
    if not CONFIG_FILE.exists():
        return None
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get("id_terminal")
    except (IOError, json.JSONDecodeError) as e:
        print(f"❌ Error al leer el archivo de configuración: {e}")
        return None

def delete_config():
    """
    Elimina el archivo de configuración por completo.
    Útil si el ID de terminal guardado resulta ser inválido.
    """
    try:
        if CONFIG_FILE.exists():
            os.remove(CONFIG_FILE)
            print("🗑️ Archivo de configuración local eliminado.")
    except OSError as e:
        print(f"❌ Error al borrar el archivo de configuración: {e}")


# ✅ NUEVA FUNCIÓN: Para escanear los archivos de base de datos locales
def get_local_db_file_info(id_empresa: str, id_sucursal: int) -> list:
    """
    Escanea el directorio de bases de datos locales y devuelve una lista con
    la información que el backend necesita para la comparación.
    """
    file_info_list = []
    
    # Asegurarse de que el directorio de bases de datos exista
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    # Directorios en la nube
    ruta_cloud_generales = f"{id_empresa}/databases_generales/"
    ruta_cloud_sucursal = f"{id_empresa}/suc_{id_sucursal}/"

    for filename in os.listdir(DB_DIR):
        if filename.endswith(".sqlite"):
            file_path = DB_DIR / filename
            try:
                mtime_ts = os.path.getmtime(file_path)
                mtime_dt_utc = datetime.fromtimestamp(mtime_ts, tz=timezone.utc)
                
                # Inteligencia para construir la 'key' correcta de la nube
                # (Asumimos que el nombre del archivo nos dice a qué carpeta pertenece)
                # Esta lógica se puede hacer más robusta en el futuro.
                key_en_la_nube = ""
                if filename in ["usuarios.sqlite", "clientes.sqlite", "productos_servicios.sqlite"]:
                    key_en_la_nube = f"{ruta_cloud_generales}{filename}"
                else: # Asumimos que es un archivo de sucursal
                    key_en_la_nube = f"{ruta_cloud_sucursal}{filename}"
                
                file_info_list.append({
                    "key": key_en_la_nube,
                    "last_modified": mtime_dt_utc.isoformat()
                })
            except Exception as e:
                print(f"⚠️  No se pudo leer la información del archivo local {filename}: {e}")
                
    return file_info_list