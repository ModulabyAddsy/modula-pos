# test_sync.py (Prueba de estrés con múltiples terminales)
import os
import shutil
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timezone
import sys
import time

from PySide6.QtCore import QCoreApplication, QEventLoop, Signal, QObject, QThread
from src.core.api_client import ApiClient
from src.core.local_storage import (
    get_pending_sync_records, 
    get_last_sync_timestamps, 
    apply_deltas, 
    mark_records_as_synced,
    DB_DIR
)
import src.core.local_storage as local_storage_module

# --- CONFIGURACIÓN ---
TABLE_PRIMARY_KEYS = {'egresos': 'uuid', 'usuarios': 'uuid'}
APPDATA_DB_ROOT = Path(os.getenv('APPDATA')) / "Modula/Databases"
ID_EMPRESA_PRUEBA = "MOD_EMP_1001"
ID_SUCURSAL_PRUEBA = 52
TEST_DIR = Path("./_test_environment")

def preparar_entorno():
    """Crea un entorno limpio, simulando TRES terminales (A, B, C)."""
    print("--- Preparando entorno de prueba ---")
    ruta_sucursal_real = APPDATA_DB_ROOT / ID_EMPRESA_PRUEBA / f"suc_{ID_SUCURSAL_PRUEBA}"
    if not ruta_sucursal_real.exists():
        raise FileNotFoundError(f"¡Error Crítico! No se encontró la carpeta de la sucursal en AppData: {ruta_sucursal_real}")
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)
    
    # MODIFICADO: Creamos 3 terminales
    for terminal_letra in ["A", "B", "C"]:
        ruta_db_sucursal = TEST_DIR / f"Terminal_{terminal_letra}" / ID_EMPRESA_PRUEBA / f"suc_{ID_SUCURSAL_PRUEBA}"
        os.makedirs(ruta_db_sucursal, exist_ok=True)
        shutil.copytree(ruta_sucursal_real, ruta_db_sucursal, dirs_exist_ok=True)
    print(f"✅ Entorno listo. Se ha copiado la estructura a Terminal A, B y C.\n")

def simular_egreso(terminal_id_letra: str, razon: str, monto: float) -> str:
    """Inserta un nuevo egreso en la DB de una terminal específica."""
    print(f"--- Simulando egreso en Terminal {terminal_id_letra} ---")
    db_path = TEST_DIR / f"Terminal_{terminal_id_letra}" / ID_EMPRESA_PRUEBA / f"suc_{ID_SUCURSAL_PRUEBA}" / "egresos.sqlite"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    nuevo_egreso = {
        "uuid": str(uuid.uuid4()), "last_modified": datetime.now(timezone.utc).isoformat(),
        "needs_sync": 1, "razon_egreso": razon, "monto_egreso": monto,
        "fecha_egreso": datetime.now(timezone.utc).isoformat(), "id_usuario": f"USER_{terminal_id_letra}"
    }
    cursor.execute(
        "INSERT INTO egresos (uuid, last_modified, needs_sync, razon_egreso, monto_egreso, fecha_egreso, id_usuario) VALUES (:uuid, :last_modified, :needs_sync, :razon_egreso, :monto_egreso, :fecha_egreso, :id_usuario)",
        nuevo_egreso
    )
    conn.commit()
    conn.close()
    print(f"✅ Egreso '{razon}' registrado localmente en Terminal {terminal_id_letra}.\n")
    return nuevo_egreso['uuid']

def verificar_integridad(terminales_a_verificar: list, uuids_esperados: set):
    """Comprueba que todas las terminales tengan todos los registros esperados."""
    print("\n--- Verificando Integridad Final de Datos ---")
    todos_ok = True
    for terminal_letra in terminales_a_verificar:
        db_path = TEST_DIR / f"Terminal_{terminal_letra}" / ID_EMPRESA_PRUEBA / f"suc_{ID_SUCURSAL_PRUEBA}" / "egresos.sqlite"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT uuid FROM egresos")
        uuids_encontrados = {row[0] for row in cursor.fetchall()}
        conn.close()

        if uuids_esperados.issubset(uuids_encontrados):
            print(f"✅ Terminal {terminal_letra}: OK ({len(uuids_encontrados)} registros encontrados).")
        else:
            print(f"🔥 Terminal {terminal_letra}: FALLO. Faltan {len(uuids_esperados - uuids_encontrados)} registros.")
            todos_ok = False
            
    if todos_ok:
        print("\n🎉 ¡PRUEBA DE ESTRÉS EXITOSA! Todas las terminales están sincronizadas y no hubo pérdida de datos.")
    else:
        print("\n🔥 FALLO EN LA PRUEBA DE ESTRÉS. No todas las terminales tienen la información completa.")

# --- Clase del Worker (Sin cambios) ---
class SyncWorker(QObject):
    finished = Signal(str)
    def __init__(self, api_client, id_empresa):
        super().__init__()
        self.api_client = api_client
        self.id_empresa = id_empresa
    def run(self):
        try:
            # PUSH
            pending_pushes = get_pending_sync_records(self.id_empresa)
            if pending_pushes:
                for push_data in pending_pushes:
                    pk_column = TABLE_PRIMARY_KEYS.get(push_data['table_name'], 'uuid')
                    push_data['primary_key_column'] = pk_column
                    for record in push_data['records']:
                        if 'id' in record: del record['id']
                    self.api_client.push_records(push_data)
            
            # PULL
            timestamps_locales = get_last_sync_timestamps(self.id_empresa)
            delta_package = self.api_client.get_deltas(timestamps_locales)
            if delta_package:
                apply_deltas(self.id_empresa, delta_package)
            
            # CLEANUP
            mark_records_as_synced(self.id_empresa)
            self.finished.emit("success")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished.emit(str(e))
            
# --- Orquestador de la Prueba ---
def ejecutar_prueba_de_estres():
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    
    # 1. PREPARACIÓN
    preparar_entorno()
    
    db_inicial = TEST_DIR / "Terminal_A" / ID_EMPRESA_PRUEBA / f"suc_{ID_SUCURSAL_PRUEBA}" / "egresos.sqlite"
    conn = sqlite3.connect(db_inicial)
    registros_previos = conn.execute("SELECT uuid FROM egresos").fetchall()
    conn.close()
    uuids_existentes = {row[0] for row in registros_previos}
    print(f"ℹ️  La base de datos de origen tiene {len(uuids_existentes)} registros.\n")

    # 2. SIMULACIÓN
    uuid_a = simular_egreso("A", "Compra de café para la oficina", 250.0)
    time.sleep(1)
    uuid_b = simular_egreso("B", "Pago de servicio de internet", 899.0)

    # 3. EJECUCIÓN DE SINCRONIZACIONES
    api_client = ApiClient()
    
    # --- LÓGICA DE LOGIN Y VERIFICACIÓN AUTOMÁTICA ---
    print("--- Autenticando y Verificando la Terminal de Prueba ---")
    try:
        # Credenciales de una cuenta de prueba real
        TEST_USER_EMAIL = "edgargerardo1401@outlook.com"
        TEST_USER_PASS = "Edgarger456" # <-- Asegúrate que esta sea la contraseña correcta
        
        # Paso A: Hacemos login para obtener un token de cuenta básico
        api_client.login(TEST_USER_EMAIL, TEST_USER_PASS)
        print("✅ Login de cuenta exitoso.")

        # Paso B: Usamos el ID de hardware para simular la verificación de la terminal
        # Esto nos devolverá el token COMPLETO con el id_sucursal
        id_hardware_prueba = "4a9da0ca-e852-53ff-a2cc-ab7276cb5172" # Usamos un ID de prueba consistente
        respuesta_verificacion = api_client.verificar_terminal(id_hardware_prueba)
        
        if respuesta_verificacion.get("status") != "ok":
            raise Exception(f"La verificación de la terminal falló: {respuesta_verificacion.get('message')}")

        # Guardamos el token final y completo para el resto de la prueba
        api_client.set_auth_token(respuesta_verificacion["access_token"])
        print("✅ Verificación de terminal exitosa. Token completo obtenido.\n")
        
    except Exception as e:
        print(f"🔥 FALLO EN LOGIN/VERIFICACIÓN AUTOMÁTICA: {e}. La prueba no puede continuar.")
        return
    # --- FIN DE LA LÓGICA DE LOGIN Y VERIFICACIÓN ---

    # --- ▼▼▼ PEGA AQUÍ LA FUNCIÓN COMPLETA ▼▼▼ ---
    def run_sync_and_wait(terminal_id_letra: str):
        """
        Función auxiliar que ejecuta la sincronización para una terminal específica
        y espera a que el hilo de trabajo termine.
        """
        print(f"\n--- Ejecutando sincronización para Terminal {terminal_id_letra} ---")
        local_storage_module.DB_DIR = TEST_DIR / f"Terminal_{terminal_id_letra}"
        
        loop = QEventLoop()
        thread = QThread()
        worker = SyncWorker(api_client, ID_EMPRESA_PRUEBA)
        worker.moveToThread(thread)

        sync_status = ""
        def on_sync_finished(status):
            nonlocal sync_status
            sync_status = status
            print(f"Resultado de la sincronización: {status}")
            thread.quit()

        worker.finished.connect(on_sync_finished)
        thread.finished.connect(loop.quit)
        thread.started.connect(worker.run)
        
        thread.start()
        loop.exec()
        
        worker.deleteLater()
        thread.deleteLater()
        
        return sync_status
    # --- ▲▲▲ FIN DE LA FUNCIÓN PEGADA ▲▲▲ ---

    # SINCRONIZAMOS EN ORDEN: A, luego B, y finalmente C que estaba inactiva

    print("--- PRIMERA RONDA DE SINCRONIZACIÓN (ACTIVIDAD PRINCIPAL) ---")
    if run_sync_and_wait("A") != "success": return
    if run_sync_and_wait("B") != "success": return
    if run_sync_and_wait("C") != "success": return

    print("\n--- SEGUNDA RONDA DE SINCRONIZACIÓN (CONSOLIDACIÓN) ---")
    if run_sync_and_wait("A") != "success": return
    if run_sync_and_wait("B") != "success": return
    if run_sync_and_wait("C") != "success": return

    # 4. VERIFICACIÓN FINAL
    uuids_esperados = uuids_existentes.union({uuid_a, uuid_b})
    verificar_integridad(["A", "B", "C"], uuids_esperados)

if __name__ == "__main__":
    ejecutar_prueba_de_estres()