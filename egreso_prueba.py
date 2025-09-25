# crear_egreso_prueba.py
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
import os

# Apuntamos a la base de datos real en AppData
DB_DIR = Path(os.getenv('APPDATA')) / "Modula" / "Databases"
ID_EMPRESA = "MOD_EMP_1001"
ID_SUCURSAL = 52 # Asegúrate que este sea el ID correcto de tu sucursal de prueba
DB_PATH = DB_DIR / ID_EMPRESA / f"suc_{ID_SUCURSAL}" / "egresos.sqlite"

def inyectar_egreso():
    """Inyecta un único egreso de prueba con needs_sync = 1."""
    if not DB_PATH.exists():
        print(f"❌ ERROR: La base de datos no existe en {DB_PATH}")
        print("Asegúrate de haber ejecutado la aplicación principal al menos una vez para que se cree.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    nuevo_egreso = {
        "uuid": str(uuid.uuid4()),
        "last_modified": datetime.now(timezone.utc).isoformat(),
        "needs_sync": 1, # Marcado para ser subido
        "razon_egreso": "Prueba de bucle definitiva",
        "monto_egreso": 99.99,
        "fecha_egreso": datetime.now(timezone.utc).isoformat(),
        "id_usuario": "DEBUG-USER"
    }

    try:
        cursor.execute(
            """
            INSERT INTO egresos (uuid, last_modified, needs_sync, razon_egreso, monto_egreso, fecha_egreso, id_usuario)
            VALUES (:uuid, :last_modified, :needs_sync, :razon_egreso, :monto_egreso, :fecha_egreso, :id_usuario)
            """,
            nuevo_egreso
        )
        conn.commit()
        print(f"✅ Egreso de prueba inyectado exitosamente en '{DB_PATH.name}' con UUID: {nuevo_egreso['uuid']}")
    except Exception as e:
        print(f"🔥🔥 ERROR al inyectar egreso: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inyectar_egreso()
