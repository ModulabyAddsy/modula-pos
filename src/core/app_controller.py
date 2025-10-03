# src/core/app_controller.py
import webbrowser
import os
import uuid
import psutil
import sqlite3
from pathlib import Path
import bcrypt
from PySide6.QtWidgets import QMessageBox, QInputDialog, QApplication
from PySide6.QtCore import QTimer, QObject, Signal, QThread
from src.ui.main_window import MainWindow
from src.core.api_client import ApiClient
from src.core.local_storage import get_id_terminal, save_terminal_id, DB_DIR, get_local_db_file_info, get_pending_sync_records, mark_records_as_synced, ejecutar_migracion_sql, limpiar_datos_sucursal_anterior, get_last_sync_timestamps, apply_deltas, _get_local_max_timestamps,save_last_server_sync_timestamp
from src.ui.dialogs import mostrar_dialogo_migracion, ResolverUbicacionDialog, SeleccionarSucursalDialog, RecuperarContrasenaDialog, NewTerminalDialog
from src.ui.windows_dialogs.cambiar_contrasena_dialog import CambiarContrasenaDialog
import src.core.local_storage as local_storage
from src.ui.views.login_view import LoginView
from src.ui.views.dashboard_view import DashboardView
from src.core.utils import get_network_identifiers
from src.config.schema_config import TABLE_PRIMARY_KEYS
import time
import shutil
from PySide6.QtCore import QTimer
from .module_manager import ModuleManager
from .module_manager import MODULES_DIR 

class StartupWorker(QObject):
    """
    Orquesta un arranque inteligente y completo: autentica, prepara el entorno local
    y ejecuta el primer ciclo de sincronización delta antes de mostrar el login.
    """
    progress = Signal(str, int)
    finished = Signal(object, list, list)

    def __init__(self, controller_ref):
        super().__init__()
        self.controller = controller_ref
        self.api_client = controller_ref.api_client
        self.response = None
        
    def run(self):
        """El trabajo pesado que se ejecuta en el hilo secundario."""
        try:
            # === FASE 1: VERIFICACIÓN Y AUTENTICACIÓN (Intacto) ===
            self.progress.emit("Verificando terminal...", 10)
            hardware_id = self.controller._generar_id_estable()
            local_id = get_id_terminal()
            
            self.progress.emit("Verificando credenciales con el servidor...", 20)
            if local_id and local_id == hardware_id:
                self.response = self.api_client.verificar_terminal(hardware_id)
            else:
                self.response = self.api_client.verificar_terminal(hardware_id)
                if self.response.get("status") == "ok":
                    save_terminal_id(hardware_id)
            
            if self.response.get("status") != "ok":
                self.finished.emit(self.response, [], []) 
                return
            
            self.api_client.set_auth_token(self.response["access_token"])
            id_sucursal = self.response['id_sucursal']
            id_empresa = self.response['id_empresa']
            self.controller.id_empresa_addsy = self.response['id_empresa']
            
            # === FASE 2: PREPARACIÓN INTELIGENTE DEL ENTORNO LOCAL (Intacto) ===
            self.progress.emit("Revisando datos locales...", 30)
            hay_datos_pendientes = bool(get_pending_sync_records(id_empresa))

            self.progress.emit("Preparando la nube para la sincronización...", 40)
            cloud_plan = self.api_client.initialize_sync()
            files_to_pull = cloud_plan.get("files_to_pull", [])
            
            if hay_datos_pendientes:
                self.progress.emit("Datos locales pendientes detectados. Omitiendo descarga.", 50)
            elif files_to_pull:
                self.progress.emit("Descargando la versión más reciente de la nube...", 50)
                ruta_empresa_local = DB_DIR / id_empresa
                if ruta_empresa_local.exists():
                    shutil.rmtree(ruta_empresa_local)
                for i, key_path in enumerate(files_to_pull):
                    progreso = 50 + int((i / len(files_to_pull)) * 20)
                    nombre_archivo = Path(key_path).name
                    self.progress.emit(f"Descargando {nombre_archivo}...", progreso)
                    ruta_destino_local = DB_DIR / key_path
                    ruta_destino_local.parent.mkdir(parents=True, exist_ok=True)
                    self.api_client.pull_db_file(key_path, ruta_destino_local)
            else:
                self.progress.emit("Primera ejecución. Creando bases de datos locales...", 50)
                # ... (Tu lógica para crear DBs desde plantillas va aquí) ...

            # === FASE 3: PRIMERA SINCRONIZACIÓN DELTA COMPLETA (Lógica Añadida) ===
            # PUSH: Enviamos cualquier cambio local que haya sobrevivido.
            self.progress.emit("Enviando cambios locales...", 75)
            pending_pushes = get_pending_sync_records(id_empresa)
            if pending_pushes:
                for push_data in pending_pushes:
                    self.api_client.push_records(push_data)

            # PULL: Pedimos los últimos cambios al servidor usando el marcador.
            self.progress.emit("Recibiendo últimos cambios...", 85)
            timestamps_para_pull = get_last_sync_timestamps(id_empresa)
            response_package = self.api_client.get_deltas(timestamps_para_pull)
            
            delta_package = response_package.get("deltas")
            server_timestamp = response_package.get("server_sync_timestamp")

            if delta_package:
                apply_deltas(id_empresa, delta_package)
            
            if server_timestamp:
                save_last_server_sync_timestamp(id_empresa, server_timestamp)

            # CLEANUP: Marcamos los registros que se subieron como sincronizados.
            mark_records_as_synced(id_empresa)
            
                    # === NUEVA FASE: ACTUALIZACIÓN DE MÓDULOS ===
            self.progress.emit("Revisando módulos...", 90)
            self.controller.module_manager.check_for_updates()
            installed_modules = self.controller.module_manager.get_installed_modules()
            self.progress.emit("Módulos actualizados.", 95)

            # === FASE FINAL: FINALIZACIÓN ===
            self.progress.emit("¡Arranque completado!", 100)
            # Emitimos el resultado, los logs Y la lista de módulos
            self.finished.emit(self.response, ["Arranque y sincronización inicial completados."], installed_modules)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished.emit({"status": "error", "message": f"Error crítico en el arranque: {e}"}, [], [])
            
class RegisterWorker(QObject):
    """Ejecuta el proceso de registro en un hilo secundario."""
    finished = Signal(dict)
    progress = Signal(str, int)

    def __init__(self, controller_ref, user_data: dict):
        super().__init__()
        self.controller = controller_ref
        self.api_client = controller_ref.api_client
        self.user_data = user_data

    def run(self):
        """El trabajo pesado que se ejecuta en el hilo secundario."""
        try:
            self.progress.emit("Registrando cuenta...", 10)
            hardware_id = self.controller._generar_id_estable()
            self.user_data["id_terminal"] = hardware_id
            
            self.controller.claim_token = str(uuid.uuid4())
            self.user_data["claim_token"] = self.controller.claim_token
            
            respuesta = self.api_client.registrar_cuenta(self.user_data)
            self.finished.emit(respuesta)

        # --- 👇 ESTE BLOQUE AHORA ES MÁS SIMPLE Y CORRECTO ---
        except Exception as e:
            # Simplemente tomamos el mensaje de error que el ApiClient ya preparó
            # y se lo pasamos al hilo principal.
            self.finished.emit({"error": str(e)})
        
class LoginWorker(QObject):
    """Ejecuta el proceso de login y activación en un hilo secundario."""
    finished = Signal(dict)
    progress = Signal(str, int) # <-- ¡SEÑAL AÑADIDA!

    def __init__(self, controller_ref, email: str, password: str):
        super().__init__()
        self.controller = controller_ref
        self.api_client = controller_ref.api_client
        self.email = email
        self.password = password

    def run(self):
        """El trabajo pesado que se ejecuta en el hilo secundario."""
        try:
            self.progress.emit("Verificando credenciales...", 10) # <-- La primera emisión
            print(f"Autenticando cuenta Addsy: {self.email}...")
            self.api_client.login(self.email, self.password)
            
            print("Cuenta autenticada. Verificando si esta PC ya está registrada como terminal...")
            hardware_id = self.controller._generar_id_estable()
            terminales_existentes = self.api_client.get_mis_terminales()
            terminal_ya_registrada = any(t['id_terminal'] == hardware_id for t in terminales_existentes)
            
            if terminal_ya_registrada:
                print(f"Este hardware ya está registrado. Vinculando con ID: {hardware_id}")
                save_terminal_id(hardware_id)
                self.finished.emit({"status": "ok", "action": "restart"})
            else:
                print("No se encontró una terminal para este hardware. Iniciando flujo de creación.")
                self.finished.emit({"status": "ok", "action": "new_terminal"})

        except Exception as e:
            self.finished.emit({"status": "error", "message": f"Error en el proceso de activación: {e}"})

class SyncWorker(QObject):
    """Ejecuta la sincronización delta en un hilo secundario."""
    finished = Signal(str)
    
    def __init__(self, controller):
        super().__init__()
        self.api_client = controller.api_client
        self.id_empresa = controller.id_empresa_addsy

    def run(self):
        try:
            # FASE 1: PUSH (Enviar cambios locales)
            print("🔄 [SYNC] Buscando y enviando cambios locales...")
            pending_pushes = get_pending_sync_records(self.id_empresa)
            if pending_pushes:
                for push_data in pending_pushes:
                    pk_column = TABLE_PRIMARY_KEYS.get(push_data['table_name'], 'uuid')
                    push_data['primary_key_column'] = pk_column
                    for record in push_data['records']:
                        if 'id' in record: del record['id']
                    self.api_client.push_records(push_data)
            
            # FASE 2: PULL (Recibir cambios de la nube)
            print("🔄 [SYNC] Solicitando cambios de otras terminales...")
            
            # --- ▼▼▼ LA CORRECCIÓN FINAL Y DEFINITIVA ▼▼▼ ---
            # Antes aquí llamábamos a la función incorrecta.
            # Ahora llamamos a la que lee el marcador del servidor de sync_state.json
            timestamps_para_pull = get_last_sync_timestamps(self.id_empresa)
            # --- ▲▲▲ FIN DE LA CORRECCIÓN ▲▲▲ ---

            response_package = self.api_client.get_deltas(timestamps_para_pull)
            
            delta_package = response_package.get("deltas")
            server_timestamp = response_package.get("server_sync_timestamp")

            if delta_package:
                apply_deltas(self.id_empresa, delta_package)
            
            if server_timestamp:
                save_last_server_sync_timestamp(self.id_empresa, server_timestamp)

            # FASE 3: LIMPIEZA
            mark_records_as_synced(self.id_empresa)
            self.finished.emit("success")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished.emit(str(e))
            
class AppController(QObject):
    """Controla todo el flujo de la aplicación."""
    def __init__(self, app):
        super().__init__()
        self.main_window = MainWindow(self) 
        self.app = app
        self.api_client = ApiClient()
        self.module_manager = ModuleManager(self.api_client, self)
        
        # Atributos únicos para CADA tarea asíncrona
        self.startup_thread = None
        self.startup_worker = None
        self.auth_thread = None  # Usaremos este para login y registro
        self.auth_worker = None
        self.sync_thread = None  # Dedicado EXCLUSIVAMENTE a la sincronización
        self.sync_worker = None
        self.module_update_thread = None
        self.module_update_worker = None
        
        self.respuesta_conflicto = None
        self.claim_token = None
        self.polling_timer = QTimer()
        self.polling_timer.timeout.connect(self._poll_for_activation)
        
        self.id_empresa_addsy = None
        
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self.sincronizar_ahora)
        
        self._connect_signals()

    def _connect_signals(self):
        self.main_window.auth_view.login_solicitado.connect(self.handle_account_login_and_activate)
        self.main_window.auth_view.registro_solicitado.connect(self.handle_register)
        self.main_window.auth_view.recuperacion_solicitada.connect(self.handle_recovery_request)
        

    def run(self):
        self.main_window.show()
        self._iniciar_arranque_inteligente()

    def _iniciar_arranque_inteligente(self):
        """Inicia la lógica de arranque en un hilo secundario."""
        self.main_window.mostrar_vista_carga()
        
        self.startup_thread = QThread()
        self.startup_worker = StartupWorker(self)
        self.startup_worker.moveToThread(self.startup_thread)

        self.startup_thread.started.connect(self.startup_worker.run)
        self.startup_worker.progress.connect(self.main_window.loading_view.update_status)
        self.startup_worker.finished.connect(self.handle_startup_result)
        
        self.startup_worker.finished.connect(self.startup_thread.quit)
        self.startup_worker.finished.connect(self.startup_worker.deleteLater)
        self.startup_thread.finished.connect(self.startup_thread.deleteLater)
        # Limpia también la referencia al finalizar
        self.startup_thread.finished.connect(lambda: setattr(self, 'startup_thread', None))
        
        self.startup_thread.start()

    def _execute_startup_logic(self):
        """
        Esta es tu lógica de arranque funcional, ahora ejecutándose de forma segura en segundo plano.
        Devuelve el resultado final para que el worker lo emita.
        """
        hardware_id = self._generar_id_estable()
        local_id = get_id_terminal()

        if local_id and local_id == hardware_id:
            print(f"Archivo local encontrado y válido. Verificando terminal ID: {hardware_id}...")
            return self.api_client.verificar_terminal(hardware_id)
        else:
            print("Archivo local no encontrado o inválido. Intentando recuperar identidad...")
            try:
                self.api_client.buscar_terminal_por_hardware(hardware_id)
                print("¡Identidad recuperada! El backend reconoce esta terminal.")
                save_terminal_id(hardware_id)
                # Volvemos a llamar a la verificación, que ahora tendrá éxito
                return self.api_client.verificar_terminal(hardware_id)
            except Exception as e:
                print("El backend no reconoce este hardware. Es una terminal nueva.")
                return "activacion_requerida"

    def handle_startup_result(self, result, logs, installed_modules):
        """
        Manejador central para el resultado del worker de arranque.
        """
        # Este bloque se ejecuta si el arranque NO FUE EXITOSO (status no es "ok").
        if not isinstance(result, dict) or result.get("status") != "ok":
            
            # 1. NUEVO: Manejamos específicamente el conflicto de ubicación.
            if result.get("status") == "location_mismatch":
                print("Conflicto de ubicación detectado. Se requiere login para resolver.")
                QMessageBox.warning(self.main_window, "Conflicto de Ubicación", 
                                    "Hemos detectado que estás en una nueva red o ubicación.\n\n"
                                    "Por favor, inicia sesión con tu cuenta para autorizar este cambio.")
                
                self.respuesta_conflicto = result # Guardamos la respuesta para usarla después del login
                
                # Preparamos la vista de login para que llame al manejador de conflictos.
                try:
                    self.main_window.auth_view.login_solicitado.disconnect()
                except RuntimeError:
                    pass # Ignorar si no estaba conectada
                
                self.main_window.auth_view.login_solicitado.connect(self.handle_login_para_resolver_conflicto)
                self.main_window.mostrar_vista_auth()

            # 2. Mantenemos la lógica para otros tipos de error.
            elif result == "activacion_requerida" or "Terminal no encontrada" in result.get("message", ""):
                self.solicitar_login_activacion()
            else:
                self.show_error(result.get("message", "Error desconocido en el arranque."))
                self.main_window.mostrar_vista_auth()
                
            # 3. El return es clave: detiene la ejecución aquí si hubo cualquier error.
            return

        # --- Este código solo se ejecuta SI EL ARRANQUE FUE EXITOSO (status es "ok") ---

        # LÓGICA DE MÓDULOS: Se ejecuta sin problemas en un arranque correcto.
        print(f"✅ Carga de módulos completada. {len(installed_modules)} módulos encontrados.")
        sidebar = self.main_window.dashboard_view.nav_sidebar
        sidebar.populate_modules(installed_modules, MODULES_DIR)

        # Preparamos la vista de login local.
        self.main_window.mostrar_vista_login_local()
        
        # Conectamos las señales de la vista de login local para que los botones funcionen.
        try:
            self.main_window.login_view.login_solicitado.disconnect()
            self.main_window.login_view.recuperacion_solicitada.disconnect()
        except RuntimeError:
            pass  # Ignorar si no estaban conectadas
        
        self.main_window.login_view.login_solicitado.connect(self._handle_local_login)
        self.main_window.login_view.recuperacion_solicitada.connect(self.handle_recovery_request)
            
    def solicitar_login_activacion(self):
        """Configura la UI para el login de activación."""
        try:
            self.main_window.login_view.login_solicitado.disconnect()
        except RuntimeError:
            pass # Ignora el error si las señales no estaban conectadas
        
        self.main_window.auth_view.login_solicitado.connect(self.handle_account_login_and_activate)
        self.main_window.mostrar_vista_auth()

    def _generar_id_estable(self) -> str:
        try:
            addrs = psutil.net_if_addrs()
            mac_address = None
            for _, interfaces in addrs.items():
                for interface in interfaces:
                    if interface.family == psutil.AF_LINK and interface.address and "00:00:00:00:00:00" not in interface.address:
                        mac_address = interface.address; break
                if mac_address: break
            if not mac_address: mac_address = uuid.getnode()
            hardware_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(mac_address)))
            print(f"ID de hardware estable generado: {hardware_id}")
            return hardware_id
        except Exception as e:
            print(f"ADVERTENCIA: No se pudo obtener la dirección MAC. Se usará un UUID aleatorio. Error: {e}")
            return str(uuid.uuid4())

    def _manejar_respuesta_verificacion(self, respuesta: dict):
        status = respuesta.get("status")

        if status == "ok" and "access_token" in respuesta:
            print("Verificación exitosa. Iniciando sesión automáticamente.")
            self.api_client.set_auth_token(respuesta["access_token"])
            self.main_window.mostrar_vista_login_local()
        
        # --- ¡NUEVA LÓGICA PARA SUSCRIPCIÓN VENCIDA! ---
        elif status == "subscription_expired":
            print("Suscripción vencida. Mostrando panel de pago.")
            url_pago = respuesta.get("payment_url")
            mensaje = respuesta.get("message", "Tu suscripción ha vencido.")
            
            # 1. Mostramos un diálogo informativo al usuario
            QMessageBox.warning(self.main_window, "Suscripción Vencida", 
                                f"{mensaje}\n\nSerás redirigido a nuestro portal de pagos para regularizar tu situación.")
            
            # 2. Abrimos el navegador web con la URL del portal de Stripe
            if url_pago:
                webbrowser.open(url_pago)
            
            # 3. Cerramos la aplicación de escritorio, ya que no puede continuar
            self.app.quit()
            
        elif status == "location_mismatch":
            print("Conflicto de ubicación detectado. Se requiere login para resolver.")
            QMessageBox.warning(self.main_window, "Conflicto de Ubicación", "Hemos detectado que estás en una nueva ubicación.\n\nPor favor, inicia sesión con tu cuenta para autorizar este cambio.")
            self.respuesta_conflicto = respuesta
            
            # Desconectamos cualquier conexión anterior para evitar duplicados
        try:
            self.main_window.login_view.login_solicitado.disconnect()
        except RuntimeError:
            pass # Ignora el error si las señales no estaban conectadas

            self.main_window.auth_view.login_solicitado.connect(self.handle_login_para_resolver_conflicto)
            self.main_window.mostrar_vista_auth()

        else:
            error_detail = respuesta.get("detail", "Error desconocido.")
            print(f"Fallo en verificación: {error_detail}.")
            QMessageBox.critical(self.main_window, "Error de Verificación", error_detail)
            self.main_window.mostrar_vista_auth()

    def handle_account_login_and_activate(self, email: str, password: str):
        """Inicia el proceso de login y activación en un hilo secundario."""
        self.main_window.mostrar_vista_carga()
        self.main_window.auth_view.clear_inputs()
        self.thread = QThread()
        self.worker = LoginWorker(self, email, password)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.main_window.loading_view.update_status) # <-- Conexión a la nueva señal
        self.worker.finished.connect(self.handle_login_result)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

        
    def handle_login_result(self, result: dict):
        """Maneja el resultado del proceso de login."""
        status = result.get("status")
        
        if status == "error":
            self.show_error(result.get("message", "Error desconocido."))
            self.main_window.mostrar_vista_auth() # Regresamos al login si hay error
            return

        if status == "ok":
            action = result.get("action")
            if action == "restart":
                QMessageBox.information(self.main_window, "Terminal Vinculada", "Este equipo ha sido vinculado exitosamente a tu terminal existente.\n\nLa aplicación se reiniciará para aplicar la configuración.")
                self._iniciar_arranque_inteligente()
            elif action == "new_terminal":
                self.handle_nueva_terminal()

    def handle_nueva_terminal(self):
        try:
            # <<-- CAMBIO: Instanciamos nuestro nuevo diálogo personalizado.
            dialogo_terminos = NewTerminalDialog(self.main_window)
            
            # <<-- CAMBIO: Usamos .exec() que devuelve True si el usuario acepta, False si cancela.
            # La lógica interna del diálogo ya se encarga de que el botón "Aceptar"
            # solo se active si se marca el checkbox.
            if not dialogo_terminos.exec():
                print("El usuario canceló el registro de la nueva terminal.")
                return # Si el usuario cancela, simplemente salimos de la función.

            # El resto de tu lógica se ejecuta solo si el usuario aceptó los términos.
            sucursales = self.api_client.get_mis_sucursales()
            id_sucursal_seleccionada = None

            if len(sucursales) == 1:
                id_sucursal_seleccionada = sucursales[0]["id"]
            else:
                dialogo_sucursal = SeleccionarSucursalDialog(sucursales, self.main_window)
                if dialogo_sucursal.exec():
                    id_sucursal_seleccionada = dialogo_sucursal.get_selected_sucursal_id()
                else:
                    print("El usuario canceló la selección de sucursal.")
                    return # Cancelación en el segundo paso
            
            # Asegurarse de que se seleccionó una sucursal
            if not id_sucursal_seleccionada:
                return

            nombre_terminal, ok = QInputDialog.getText(self.main_window, "Nombre de la Terminal", "Ingresa un nombre para identificar esta terminal (ej. 'Caja 2'):")
            if not ok or not nombre_terminal.strip():
                QMessageBox.warning(self.main_window, "Acción Cancelada", "El nombre de la terminal no puede estar vacío.")
                return
            
            hardware_id = self._generar_id_estable()
            datos_terminal = {"id_terminal": hardware_id, "nombre_terminal": nombre_terminal.strip(), "id_sucursal": id_sucursal_seleccionada}
            
            self.api_client.registrar_nueva_terminal(datos_terminal)
            save_terminal_id(hardware_id)
            
            QMessageBox.information(self.main_window, "¡Éxito!", "La nueva terminal ha sido registrada y configurada.")
            
            # <<-- CAMBIO SUTIL: En lugar de ir al dashboard, es más robusto reiniciar el
            # proceso de arranque para que verifique la nueva terminal y sincronice todo.
            self._iniciar_arranque_inteligente()

        except Exception as e:
            self.show_error(f"No se pudo registrar la nueva terminal: {e}")

    def handle_login_para_resolver_conflicto(self, email: str, password: str):
        try:
            # 1. Autenticar al administrador
            self.main_window.auth_view.login_solicitado.disconnect(self.handle_login_para_resolver_conflicto)
            self.main_window.auth_view.login_solicitado.connect(self.handle_account_login_and_activate)
            self.api_client.login(email, password)
            
            # 2. Preparar datos para la resolución
            id_terminal_local = get_id_terminal()
            respuesta_conflicto = self.respuesta_conflicto
            self.respuesta_conflicto = None # Limpiar para la próxima vez
            
            sucursales = respuesta_conflicto.get("sucursales_existentes", [])
            dialogo = ResolverUbicacionDialog(sucursales, self.main_window)
            
            # 3. Mostrar diálogo al administrador para que decida qué hacer
            if dialogo.exec():
                accion, datos = dialogo.get_resultado()
                
                # Recolectamos las huellas de la red actual una sola vez
                huellas_de_red = get_network_identifiers()
                id_sucursal_objetivo = None

                if accion == "crear":
                    # Si decide crear una nueva sucursal
                    res = self.api_client.crear_sucursal_y_asignar_terminal(id_terminal_local, datos["nombre"])
                    self.api_client.set_auth_token(res["access_token"])
                    # El ID de la sucursal recién creada viene en el token o en la respuesta
                    # (Asegúrate que tu API devuelva el id de la nueva sucursal)
                    # Por ahora, asumimos que se puede obtener de alguna manera.
                    # Para simplificar, reiniciaremos el flujo y la siguiente vez ya aparecerá.
                    
                elif accion == "asignar":
                    # Si decide asignar a una sucursal existente
                    id_sucursal_objetivo = datos["id_sucursal"]
                    self.api_client.asignar_terminal_a_sucursal(id_terminal_local, id_sucursal_objetivo)
                
                # 4. EL PASO CLAVE: Anclar la red a la sucursal objetivo
                if id_sucursal_objetivo:
                    print(f"Anclando red a sucursal {id_sucursal_objetivo} con datos: {huellas_de_red}")
                    self.api_client.anclar_red_a_sucursal(id_sucursal_objetivo, huellas_de_red)
                    QMessageBox.information(self.main_window, "Éxito", "Red autorizada. Reiniciando verificación...")
                
                # 5. Reiniciar el proceso de arranque para una nueva verificación
                self._iniciar_arranque_inteligente()

            else: # Si el administrador cancela el diálogo
                self.main_window.mostrar_vista_auth()
                
        except Exception as e:
            self.show_error(f"Error resolviendo conflicto: {e}")

    def handle_register(self, user_data: dict):
        """Inicia el proceso de registro en un hilo secundario."""
        self.main_window.mostrar_vista_carga()
        self.main_window.auth_view.clear_inputs()
        self.thread = QThread()
        self.worker = RegisterWorker(self, user_data)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.main_window.loading_view.update_status) # <-- Conexión a la nueva señal
        self.worker.finished.connect(self.handle_register_result)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def handle_register_result(self, result: dict):
        """Maneja el resultado del proceso de registro."""
        if "error" in result:
            self.show_error(result["error"])
            self.main_window.mostrar_vista_auth()
            return

        url_checkout = result.get("url_checkout")
        if url_checkout:
            webbrowser.open(url_checkout)
            self.main_window.loading_view.set_message("Esperando activación...", "Completa el pago y la verificación en tu navegador.", indeterminate=True)
            self.polling_timer.start(30000) # 5 segundos
        else:
            self.show_error("El servidor no devolvió una URL de pago.")
            self.main_window.mostrar_vista_auth()

    def _poll_for_activation(self):
        print("Polling para verificar activación...")
        try:
            respuesta = self.api_client.check_activation_status(self.claim_token)
            print(f"{self.claim_token}")
            if respuesta.get("status") == "complete":
                print("¡Activación completada!")
                self.polling_timer.stop()
                self.api_client.set_auth_token(respuesta["access_token"])
                save_terminal_id(respuesta["id_terminal"])
                QMessageBox.information(self.main_window, "¡Cuenta Activada!", "Tu cuenta y tu primera terminal han sido configuradas exitosamente.")
                self._iniciar_arranque_inteligente()
        except Exception as e:
            print(f"Error durante el polling: {e}. Se reintentará...")

    def handle_recovery_request(self):
        dialogo = RecuperarContrasenaDialog(self.main_window)
        if dialogo.exec():
            email = dialogo.get_email()
            if not email:
                self.show_error("El correo no puede estar vacío.")
                return
            try:
                respuesta = self.api_client.solicitar_reseteo_contrasena(email)
                QMessageBox.information(self.main_window, "Solicitud Enviada", respuesta.get("message", "Si el correo está registrado, recibirás un enlace."))
            except Exception as e:
                self.show_error(str(e))

    def show_error(self, message: str):
        """Muestra un diálogo de error estandarizado."""
        QMessageBox.critical(self.main_window, "Error", message)
        
    def _handle_local_login(self, empleado_id: str, contrasena: str):
        """
        Verifica las credenciales y orquesta el flujo de cambio de contraseña obligatorio.
        """
        if not self.id_empresa_addsy:
            self.show_error("No se pudo obtener el ID de la empresa. Reinicia la aplicación.")
            return

        db_path = DB_DIR / self.id_empresa_addsy / "databases_generales" / "usuarios.sqlite"
        
        if not db_path.exists():
            self.show_error("No se encontró la base de datos de usuarios local.")
            return
            
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM usuarios WHERE numero_empleado = ? OR nombre_usuario = ?", (empleado_id, empleado_id))
            usuario_row = cursor.fetchone()
            
            if not usuario_row:
                self.show_error("Número de empleado o contraseña incorrectos.")
                return

            usuario_info = dict(usuario_row)
            if bcrypt.checkpw(contrasena.encode('utf-8'), usuario_info['contrasena'].encode('utf-8')):
                # Si la contraseña es correcta, ahora decidimos qué hacer.
                
                # --- Verificamos la bandera de cambio de contraseña ---
                if usuario_info.get('cambio_contrasena_obligatorio') == 1:
                    dialog = CambiarContrasenaDialog(self.main_window)
                    if dialog.exec():
                        nueva_pass = dialog.get_nueva_contrasena()
                        try:
                            local_storage.actualizar_contrasena_usuario(
                                self.id_empresa_addsy,
                                usuario_info['uuid'],
                                nueva_pass
                            )
                            print("Contraseña cambiada. Disparando sincronización...")
                            self.sincronizar_ahora(
                                on_finished_callback=lambda s: print(f"Sincronización de contraseña finalizada: {s}")
                            )
                            # Después de cambiar la contraseña exitosamente, AHORA SÍ vamos al dashboard.
                            self.main_window.mostrar_vista_dashboard()
                            self.sync_timer.start(20000)
                            print("🔄 Sincronización periódica iniciada (cada 20 segundos).")
                            
                        except Exception as e:
                            self.show_error(f"No se pudo actualizar la contraseña: {e}")
                            return # Detenemos si hay error al guardar

                    else:
                        # Si el usuario presiona "Cancelar", se le avisa y la función termina aquí.
                        self.show_error("El cambio de contraseña es obligatorio para continuar.")
                        return
                else:
                    # --- SI NO ES OBLIGATORIO CAMBIAR LA CONTRASEÑA ---
                    # Entonces procedemos directamente al dashboard.
                    self.main_window.mostrar_vista_dashboard()
                    self.sync_timer.start(20000)
                    print("🔄 Sincronización periódica iniciada (cada 20 segundos).")
            else:
                self.show_error("Número de empleado o contraseña incorrectos.")
                
        except sqlite3.Error as e:
            self.show_error(f"Error al verificar credenciales: {e}")
        finally:
            if conn:
                conn.close()

    def _on_sync_finished(self, status):
        """
        Esta función ahora se ejecuta en el HILO PRINCIPAL.
        Orquesta de forma segura la detención y limpieza del hilo de trabajo.
        """
        print(f"✅ Sincronización finalizada con estado: {status}. Limpiando recursos de sync.")
        
        if self.sync_thread:
            # 1. Pide al hilo que termine.
            self.sync_thread.quit()
            # 2. ESPERA a que realmente termine. Esto ya no causa un error
            #    porque estamos llamando a wait() desde el hilo principal.
            self.sync_thread.wait()

        # 3. Anula las referencias de forma segura.
        self.sync_thread = None
        self.sync_worker = None

        # 4. Ejecuta el callback que guardamos temporalmente.
        if self.sync_callback:
            self.sync_callback(status)
            self.sync_callback = None # Limpiamos el callback para la próxima vez.

    def sincronizar_ahora(self, on_finished_callback=None):
        """
        Ahora guarda el callback y usa una conexión de señal directa,
        lo que garantiza que _on_sync_finished se ejecute en el hilo principal.
        """
        if self.sync_thread and self.sync_thread.isRunning():
            print("ℹ️  [SYNC] Intento de sincronización omitido, ya hay un proceso en curso.")
            if on_finished_callback:
                on_finished_callback("skipped")
            return

        # Guardamos temporalmente el callback para esta ejecución específica.
        self.sync_callback = on_finished_callback

        self.sync_thread = QThread()
        self.sync_worker = SyncWorker(self)
        self.sync_worker.moveToThread(self.sync_thread)

        # --- CONEXIÓN SIMPLIFICADA ---
        # Al conectar directamente, Qt se encarga de que la función _on_sync_finished
        # se invoque de forma segura en el hilo del objeto receptor (el hilo principal).
        self.sync_worker.finished.connect(self._on_sync_finished)
        
        self.sync_thread.started.connect(self.sync_worker.run)
        
        # Estas conexiones de autodestrucción siguen siendo seguras.
        self.sync_worker.finished.connect(self.sync_worker.deleteLater)
        self.sync_thread.finished.connect(self.sync_thread.deleteLater)
        
        print("🚀 [SYNC] Iniciando nueva sincronización en segundo plano...")
        self.sync_thread.start()
