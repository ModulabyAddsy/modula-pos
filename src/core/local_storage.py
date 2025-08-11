# src/core/local_storage.py
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import shutil 

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
    Escanea recursivamente los directorios de la empresa y devuelve una lista
    con la información de los archivos locales para la sincronización.
    """
    file_info_list = []
    
    # Define la carpeta raíz para esta empresa, p.ej., .../Databases/MOD_EMP_1001
    company_root_path = DB_DIR / id_empresa
    
    # Asegurarse de que el directorio de la empresa exista
    company_root_path.mkdir(parents=True, exist_ok=True)
    
    # Escanea recursivamente todos los archivos .sqlite dentro de la carpeta de la empresa
    # La función rglob es perfecta para esto.
    for file_path in company_root_path.rglob('*.sqlite'):
        try:
            # La "key" en la nube es la ruta relativa desde la carpeta DB_DIR
            # Esto garantiza que 'MOD_EMP_1001/suc_25/tickets.sqlite' coincida en local y en la nube.
            key_en_la_nube = file_path.relative_to(DB_DIR).as_posix()

            mtime_ts = os.path.getmtime(file_path)
            mtime_dt_utc = datetime.fromtimestamp(mtime_ts, tz=timezone.utc)
            
            file_info_list.append({
                "key": key_en_la_nube,
                "last_modified": mtime_dt_utc.isoformat()
            })
        except Exception as e:
            print(f"⚠️  No se pudo leer la información del archivo local {file_path.name}: {e}")
                
    return file_info_list

def limpiar_datos_sucursal_anterior(id_empresa: str, id_sucursal_anterior: int):
    """
    Elimina de forma segura el directorio de una sucursal específica y todo su contenido.
    """
    # Construye la ruta al directorio de la sucursal, ej: .../Databases/MOD_EMP_1001/suc_25
    ruta_sucursal_anterior = DB_DIR / id_empresa / f"suc_{id_sucursal_anterior}"
    
    if ruta_sucursal_anterior.exists() and ruta_sucursal_anterior.is_dir():
        try:
            # shutil.rmtree borra un directorio y todo lo que contiene. ¡Es muy potente!
            shutil.rmtree(ruta_sucursal_anterior)
            print(f"🧹 Datos locales de la sucursal {id_sucursal_anterior} eliminados exitosamente.")
        except OSError as e:
            print(f"❌ Error al eliminar el directorio de la sucursal anterior: {e}")
    else:
        print(f"ℹ️ No se encontraron datos locales para la sucursal {id_sucursal_anterior}. No se requiere limpieza.")