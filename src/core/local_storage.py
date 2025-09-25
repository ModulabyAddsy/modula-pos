# src/core/local_storage.py
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import shutil 
import sqlite3
import hashlib
import uuid
from src.config.schema_config import TABLE_PRIMARY_KEYS, TABLAS_GENERALES
import bcrypt

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
    Escanea todas las DBs locales, extrae los registros con needs_sync = 1
    y los empaqueta correctamente para el endpoint de PUSH.
    """
    all_pending_pushes = []
    company_root_path = DB_DIR / id_empresa
    if not company_root_path.exists():
        return []

    # Este diccionario es crucial para decirle al backend cuál es la clave primaria de cada tabla
    TABLE_PRIMARY_KEYS = {'egresos': 'uuid', 'usuarios': 'uuid', 'ingresos': 'uuid'}

    for db_path in company_root_path.rglob('*.sqlite'):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            cursor.execute(f"PRAGMA table_info('{table}')")
            column_names = {info[1] for info in cursor.fetchall()}
            if 'needs_sync' in column_names and 'uuid' in column_names:
                cursor.execute(f"SELECT * FROM {table} WHERE needs_sync = 1")
                records_to_sync = [dict(row) for row in cursor.fetchall()]

                # Normalizamos los datos antes de enviarlos (esto ya estaba bien)
                for record in records_to_sync:
                    if 'uuid' in record and record['uuid'] is not None:
                        record['uuid'] = str(record['uuid'])
                    if 'last_modified' in record and record['last_modified'] is not None:
                        record['last_modified'] = str(record['last_modified'])

                if records_to_sync:
                    db_relative_path = db_path.relative_to(DB_DIR).as_posix()
                    
                    # --- ▼▼▼ LA CORRECCIÓN CLAVE ▼▼▼ ---
                    # El servidor necesita saber explícitamente cuál es la columna
                    # que funciona como clave primaria para hacer el 'ON CONFLICT'.
                    pk_column = TABLE_PRIMARY_KEYS.get(table, 'uuid') # Usamos 'uuid' por defecto

                    all_pending_pushes.append({
                        "db_relative_path": db_relative_path,
                        "table_name": table,
                        "records": records_to_sync,
                        "primary_key_column": pk_column # <-- CAMPO AÑADIDO
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
    
def _get_local_max_timestamps(id_empresa: str) -> dict:
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

def get_last_sync_timestamps(id_empresa: str) -> dict:
    """
    Obtiene el último timestamp exitoso guardado del servidor.
    Este es el único marcador que usaremos para el PULL.
    """
    last_sync = get_last_server_sync_timestamp(id_empresa)
    # Devolvemos un diccionario porque el backend espera uno. Usamos un
    # marcador genérico 'global' que el backend ignorará (sólo le importa el valor).
    return {"global": last_sync}


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

def _debug_inspect_local_db(db_path, table_name, uuids_to_check):
    """
    Función temporal para conectar a una DB local e imprimir el estado
    de 'needs_sync' para UUIDs específicos.
    """
    if not uuids_to_check:
        return
    print(f"--- 🕵️  INSPECCIÓN DE DEBUG EN {table_name} ---")
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        for uuid in uuids_to_check:
            cursor.execute(f"SELECT uuid, needs_sync FROM {table_name} WHERE uuid = ?", (uuid,))
            result = cursor.fetchone()
            if result:
                print(f"INSPECT: UUID {result[0]} -> needs_sync = {result[1]}")
            else:
                print(f"INSPECT: UUID {uuid} -> No encontrado.")
    except Exception as e:
        print(f"INSPECT_ERROR: {e}")
    finally:
        if conn:
            conn.close()
    print("--- 🕵️  FIN DE INSPECCIÓN ---")

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

            uuids_procesados = [r['uuid'] for r in records]
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
            _debug_inspect_local_db(db_path, table_name, uuids_procesados)
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

def save_last_server_sync_timestamp(id_empresa: str, timestamp: str):
    """Guarda el último timestamp exitoso del servidor en un archivo de estado."""
    sync_state_path = DB_DIR / id_empresa / "sync_state.json"
    sync_state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(sync_state_path, "w") as f:
        json.dump({"last_server_sync": timestamp}, f)
    print(f"✅ Marcador de sincronización guardado: {timestamp}")

def get_last_server_sync_timestamp(id_empresa: str) -> str:
    """Lee el último timestamp guardado del servidor."""
    sync_state_path = DB_DIR / id_empresa / "sync_state.json"
    if not sync_state_path.exists():
        # Si nunca se ha sincronizado, devuelve la fecha mínima.
        return "1970-01-01T00:00:00+00:00"
    with open(sync_state_path, "r") as f:
        data = json.load(f)
        return data.get("last_server_sync", "1970-01-01T00:00:00+00:00")
    
def guardar_nuevo_registro(id_empresa: str, id_sucursal: int, table_name: str, data_dict: dict) -> str:
    """
    Guarda un nuevo registro en la tabla especificada, añadiendo automáticamente
    uuid, last_modified y la bandera needs_sync.

    Args:
        id_empresa: El ID de la empresa actual (ej. 'MOD_EMP_1001').
        id_sucursal: El ID de la sucursal actual (ej. 52).
        table_name: El nombre de la tabla (ej. 'ventas', 'egresos').
        data_dict: Un diccionario con los datos del registro.

    Returns:
        El UUID del nuevo registro creado.
    """
    # 1. Enriquecer el registro con metadatos de sincronización (¡Correcto!)
    data_dict['uuid'] = str(uuid.uuid4())
    data_dict['last_modified'] = datetime.now(timezone.utc).isoformat()
    data_dict['needs_sync'] = 1

    # 2. Determinar la ruta de la base de datos (Lógica mejorada)
    if table_name in TABLAS_GENERALES:
        db_path = DB_DIR / id_empresa / "databases_generales" / f"{table_name}.sqlite"
    else:
        db_path = DB_DIR / id_empresa / f"suc_{id_sucursal}" / f"{table_name}.sqlite"
        
    if not db_path.exists():
        raise FileNotFoundError(f"La base de datos para la tabla '{table_name}' no existe en {db_path}")

    # 3. Construir y ejecutar la consulta SQL (Intacto, estaba bien)
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        columns = ", ".join(data_dict.keys())
        placeholders = ", ".join([f":{k}" for k in data_dict.keys()])
        
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        
        cursor.execute(sql, data_dict)
        conn.commit()
        
        print(f"✅ Registro guardado localmente en '{table_name}' con UUID: {data_dict['uuid']}")
        return data_dict['uuid']

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"🔥🔥 ERROR al guardar nuevo registro en {table_name}: {e}")
        raise
    finally:
        if conn:
            conn.close()

def actualizar_contrasena_usuario(id_empresa: str, uuid_usuario: str, nueva_contrasena_plana: str):
    """
    Hashea una nueva contraseña y actualiza el registro del usuario en la DB local,
    marcando el cambio para sincronización.
    """
    # 1. Hashear la nueva contraseña
    bytes_contrasena = nueva_contrasena_plana.encode('utf-8')
    contrasena_hash = bcrypt.hashpw(bytes_contrasena, bcrypt.gensalt()).decode('utf-8')

    # 2. Preparar la actualización
    db_path = DB_DIR / id_empresa / "databases_generales" / "usuarios.sqlite"
    ahora_iso = datetime.now(timezone.utc).isoformat()
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        sql = """
            UPDATE usuarios
            SET 
                contrasena = ?,
                cambio_contrasena_obligatorio = 0,
                needs_sync = 1,
                last_modified = ?
            WHERE uuid = ?;
        """
        
        cursor.execute(sql, (contrasena_hash, ahora_iso, uuid_usuario))
        conn.commit()
        
        print(f"✅ Contraseña actualizada localmente para el usuario {uuid_usuario}.")
    
    except Exception as e:
        if conn: conn.rollback()
        print(f"🔥🔥 ERROR al actualizar la contraseña para {uuid_usuario}: {e}")
        raise
    finally:
        if conn: conn.close()
        
def actualizar_registro(id_empresa: str, id_sucursal: int, table_name: str, uuid_registro: str, data_a_actualizar: dict):
    """
    Actualiza uno o más campos de un registro existente, usando su UUID.
    Automáticamente actualiza 'last_modified' y 'needs_sync'.

    Args:
        id_empresa: El ID de la empresa actual.
        id_sucursal: El ID de la sucursal actual.
        table_name: El nombre de la tabla (ej. 'usuarios', 'ventas').
        uuid_registro: El UUID del registro que se va a modificar.
        data_a_actualizar: Un diccionario con los campos y nuevos valores.
                           Ej: {'contrasena': 'nuevo_hash', 'campo_obligatorio': 0}
    """
    # 1. Enriquecer los datos con metadatos de sincronización
    data_a_actualizar['last_modified'] = datetime.now(timezone.utc).isoformat()
    data_a_actualizar['needs_sync'] = 1

    # 2. Determinar la ruta de la DB usando la configuración central
    if table_name in TABLAS_GENERALES:
        db_path = DB_DIR / id_empresa / "databases_generales" / f"{table_name}.sqlite"
    else:
        db_path = DB_DIR / id_empresa / f"suc_{id_sucursal}" / f"{table_name}.sqlite"

    if not db_path.exists():
        raise FileNotFoundError(f"La base de datos para la tabla '{table_name}' no existe.")

    # 3. Construir la consulta UPDATE dinámicamente
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Crea la parte "SET" de la consulta: "campo1 = ?, campo2 = ?, ..."
        set_clause = ", ".join([f"{key} = ?" for key in data_a_actualizar.keys()])
        
        # Prepara los valores en el orden correcto, con el UUID al final para el WHERE
        valores = list(data_a_actualizar.values())
        valores.append(uuid_registro)
        
        sql = f"UPDATE {table_name} SET {set_clause} WHERE uuid = ?"
        
        cursor.execute(sql, valores)
        conn.commit()
        
        print(f"✅ Registro {uuid_registro} actualizado localmente en '{table_name}'.")

    except Exception as e:
        if conn: conn.rollback()
        print(f"🔥🔥 ERROR al actualizar el registro {uuid_registro}: {e}")
        raise
    finally:
        if conn: conn.close()