# src/core/local_storage.py
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import shutil 
import sqlite3
import hashlib
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

def calcular_hash_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

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
            
            file_hash = calcular_hash_md5(file_path)
            
            file_info_list.append({
                "key": key_en_la_nube,
                "last_modified": mtime_dt_utc.isoformat(), # <-- Esto lo convierte a texto JSON-compatible
                "hash": file_hash
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

def ejecutar_migracion_sql(db_path: Path, comandos: list[str]):
    """
    Se conecta a una base de datos SQLite local y ejecuta una lista de comandos SQL.
    """
    if not db_path.exists():
        print(f"❌ Error de migración: La base de datos {db_path} no existe.")
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print(f"🚀 Migrando esquema para {db_path.name}...")
        for comando in comandos:
            print(f"   -> Ejecutando: {comando}")
            cursor.execute(comando)
        conn.commit()
        print(f"✅ Esquema de {db_path.name} migrado exitosamente.")
        return True
    except sqlite3.Error as e:
        print(f"❌ Error fatal durante la migración de {db_path.name}: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()
            
def get_pending_sync_records(id_empresa: str) -> list:
    """
    Scans all local DBs and extracts records marked with needs_sync = 1,
    ensuring that the UUID and dates are in the correct string format.
    """
    all_pending_pushes = []
    company_root_path = DB_DIR / id_empresa
    if not company_root_path.exists():
        return []

    for db_path in company_root_path.rglob('*.sqlite'):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # To access results as dictionaries
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            cursor.execute(f"PRAGMA table_info('{table}')")
            column_names = {info[1] for info in cursor.fetchall()}
            if 'needs_sync' in column_names and 'uuid' in column_names:
                cursor.execute(f"SELECT * FROM {table} WHERE needs_sync = 1")
                records_to_sync = [dict(row) for row in cursor.fetchall()]

                for record in records_to_sync:
                    # ✅ CRITICAL FIX 1: Convert UUID to string if it exists
                    if 'uuid' in record and record['uuid'] is not None:
                        record['uuid'] = str(record['uuid'])

                    # ✅ CRITICAL FIX 2: Convert last_modified to string if it exists
                    if 'last_modified' in record and record['last_modified'] is not None:
                        # Convert datetime object to ISO 8601 string, which is standard for APIs
                        record['last_modified'] = str(record['last_modified'])


                if records_to_sync:
                    db_relative_path = db_path.relative_to(DB_DIR).as_posix()
                    all_pending_pushes.append({
                        "db_relative_path": db_relative_path,
                        "table_name": table,
                        "records": records_to_sync
                    })
        conn.close()
    return all_pending_pushes

def mark_records_as_synced(id_empresa: str):
    """
    Una vez que la sincronización es exitosa, resetea la bandera 'needs_sync' a 0
    en todos los registros de todas las bases de datos locales.
    """
    company_root_path = DB_DIR / id_empresa
    if not company_root_path.exists():
        return

    print("✅ Banderas 'needs_sync' locales reseteadas.")
    for db_path in company_root_path.rglob('*.sqlite'):
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                cursor.execute(f"PRAGMA table_info('{table}')")
                columns = [info[1] for info in cursor.fetchall()]
                if 'needs_sync' in columns:
                    cursor.execute(f"UPDATE {table} SET needs_sync = 0 WHERE needs_sync = 1")
            
            conn.commit()
        except sqlite3.Error as e:
            print(f"⚠️  Advertencia al resetear banderas en {db_path.name}: {e}")
        finally:
            if conn:
                conn.close()
    
def get_last_sync_timestamps(id_empresa: str) -> dict:
    """
    Escanea las DBs locales para encontrar el timestamp UTC más reciente de cada tabla,
    normalizando todos los valores al formato ISO 8601 antes de enviarlos al servidor.
    """
    timestamps = {}
    company_root_path = DB_DIR / id_empresa
    if not company_root_path.exists():
        return {}

    for db_path in company_root_path.rglob('*.sqlite'):
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                cursor.execute(f"PRAGMA table_info('{table}')")
                columns = [info[1] for info in cursor.fetchall()]
                if 'last_modified' in columns:
                    query = f"SELECT MAX(last_modified) FROM {table}"
                    cursor.execute(query)
                    max_ts = cursor.fetchone()[0]
                    
                    if max_ts:
                        # --- ▼▼▼ AQUÍ ESTÁ LA CORRECCIÓN CLAVE ▼▼▼ ---
                        # Se normaliza el timestamp para evitar errores en el backend.
                        try:
                            # 1. Intenta tratar el valor como un número (timestamp de Unix).
                            #    Usamos float() para ser flexibles con decimales.
                            unix_ts = int(float(max_ts))
                            # 2. Si tiene éxito, lo convierte a un objeto datetime con zona horaria UTC.
                            dt_object = datetime.fromtimestamp(unix_ts, tz=timezone.utc)
                            # 3. Lo formatea al estándar ISO 8601 que el servidor espera.
                            timestamps[table] = dt_object.isoformat()
                        except (ValueError, TypeError):
                            # 4. Si falla la conversión a número, significa que ya es un texto.
                            #    Asumimos que está en el formato correcto y lo usamos directamente.
                            timestamps[table] = str(max_ts)
                        # --- ▲▲▲ FIN DE LA CORRECCIÓN ▲▲▲ ---
                    else:
                        # Si la tabla está vacía, usamos una fecha "cero" para pedir todo.
                        timestamps[table] = "1970-01-01T00:00:00+00:00"

        except sqlite3.Error as e:
            print(f"Advertencia: No se pudo leer timestamps de {db_path.name}: {e}")
        finally:
            if conn:
                conn.close()
                
    print(f"DEBUG CLIENTE: Timestamps que se enviarán al servidor: {timestamps}")
    return timestamps



def _build_table_to_db_map(id_empresa: str) -> dict:
    """
    Crea un mapa de {nombre_tabla: ruta_completa_al_archivo_db}.
    """
    table_map = {}
    company_root_path = DB_DIR / id_empresa
    if not company_root_path.exists():
        return {}

    for db_path in company_root_path.rglob('*.sqlite'):
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            for table in tables:
                table_map[table] = db_path
        except Exception as e:
            print(f"Advertencia: No se pudo leer el mapa de tablas de {db_path}: {e}")
        finally:
            if conn:
                conn.close()
    return table_map

def apply_deltas(id_empresa: str, delta_package: dict):
    """
    Recibe un paquete de cambios desde el servidor y los aplica a las DBs locales.
    Versión corregida SIN la cláusula WHERE en el UPDATE.
    """
    print("--- Iniciando apply_deltas ---")
    print(f"DEBUG: Paquete de cambios recibido: {delta_package}")

    table_map = _build_table_to_db_map(id_empresa)
    if not table_map:
        print("❌ Error crítico: No se pudo construir el mapa de tablas locales.")
        return

    db_connections = {}
    try:
        for table_name, records in delta_package.items():
            if not records: continue

            db_path = table_map.get(table_name)
            if not db_path:
                print(f"⚠️  Advertencia: No se encontró DB local para la tabla '{table_name}'.")
                continue

            conn = db_connections.setdefault(db_path, sqlite3.connect(db_path))
            cursor = conn.cursor()

            for record in records:
                # El servidor es la autoridad, siempre marcamos como sincronizado.
                record['needs_sync'] = 0
                
                columns = ", ".join(record.keys())
                placeholders = ", ".join([f":{k}" for k in record.keys()])
                pk_column = "uuid"
                
                # Construimos la cláusula SET para actualizar todos los campos excepto la PK
                update_assignments = ", ".join([f"{key} = excluded.{key}" for key in record.keys() if key != pk_column])

                # --- LA CONSULTA CORREGIDA ---
                # Se eliminó la cláusula "WHERE excluded.last_modified > ..."
                # para forzar la actualización y el seteo de needs_sync = 0.
                sql = (f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) "
                       f"ON CONFLICT({pk_column}) DO UPDATE SET {update_assignments};")
                
                cursor.execute(sql, record)

        for conn in db_connections.values():
            conn.commit()

        print(f"✅ {sum(len(v) for v in delta_package.values())} cambios de la nube aplicados localmente.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Error aplicando deltas: {e}")
    finally:
        for conn in db_connections.values():
            conn.rollback()
            conn.close()