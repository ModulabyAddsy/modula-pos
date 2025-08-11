# src/core/app_controller.py
import webbrowser
import os
import uuid
import psutil
from PySide6.QtWidgets import QMessageBox, QInputDialog, QApplication
from PySide6.QtCore import QTimer, QObject, Signal, QThread
from src.ui.main_window import MainWindow
from src.core.api_client import ApiClient
from src.core.local_storage import get_id_terminal, save_terminal_id, DB_DIR, get_local_db_file_info
from src.ui.dialogs import mostrar_dialogo_migracion, ResolverUbicacionDialog, SeleccionarSucursalDialog, RecuperarContrasenaDialog
import time

class StartupWorker(QObject):
    """
    Orquesta todo el proceso de arranque en un hilo secundario,
    ejecutando las tareas en el orden correcto y reportando el progreso.
    """

    progress = Signal(str, int)      # Emite (mensaje, porcentaje) para la UI
    finished = Signal(object, list)       # Emite el resultado final (dict) o un error (str)

    def __init__(self, controller_ref):
        super().__init__()
        self.controller = controller_ref
        self.api_client = controller_ref.api_client

    def run(self):
        """El trabajo pesado que se ejecuta en el hilo secundario."""
        try:
            # === PASO 1 y 2: VERIFICACIÓN Y PLANIFICACIÓN (como ya lo tienes) ===
            self.progress.emit("Buscando actualizaciones...", 10)
            time.sleep(5)
            
            self.progress.emit("Verificando terminal...", 30)
            hardware_id = self.controller._generar_id_estable()
            local_id = get_id_terminal()
            respuesta_verificacion = None

            if local_id and local_id == hardware_id:
                respuesta_verificacion = self.api_client.verificar_terminal(hardware_id)
            else:
                try:
                    self.api_client.buscar_terminal_por_hardware(hardware_id)
                    save_terminal_id(hardware_id)
                    respuesta_verificacion = self.api_client.verificar_terminal(hardware_id)
                except Exception:
                    self.finished.emit("activacion_requerida", []); return
            
            if respuesta_verificacion.get("status") != "ok":
                self.finished.emit(respuesta_verificacion, []); return
            
            self.api_client.set_auth_token(respuesta_verificacion["access_token"])

            self.progress.emit("Sincronizando bases de datos...", 70)
            id_sucursal = respuesta_verificacion['id_sucursal']
            id_empresa = respuesta_verificacion['id_empresa']
            archivos_locales = get_local_db_file_info(id_empresa, id_sucursal)
            plan_sync = self.api_client.check_sync_status(id_sucursal, archivos_locales)
            
            # === ✅ NUEVO: PASO 3: EJECUCIÓN DEL PLAN Y CREACIÓN DE RESUMEN ===
            resumen_sync = []
            
            # Ejecutar acciones de esquema (descargar nuevas DBs de la plantilla)
            for accion in plan_sync.get("schema_actions", []):
                nombre_archivo = os.path.basename(accion['key_destino'])
                ruta_local = DB_DIR / nombre_archivo
                self.progress.emit(f"Instalando: {nombre_archivo}...", 80)
                if self.api_client.descargar_archivo(accion['key_origen'], ruta_local):
                    resumen_sync.append(f"Nueva base de datos '{nombre_archivo}' instalada.")

            # Ejecutar acciones de datos (subir/bajar actualizaciones)
            for accion in plan_sync.get("data_actions", []):
                nombre_archivo = os.path.basename(accion['key'])
                ruta_local = DB_DIR / nombre_archivo
                
                if accion['accion'] == "descargar_actualizacion":
                    self.progress.emit(f"Descargando: {nombre_archivo}...", 90)
                    if self.api_client.descargar_archivo(accion['key'], ruta_local):
                        resumen_sync.append(f"'{nombre_archivo}' actualizado desde la nube.")
                elif accion['accion'] == "subir_actualizacion":
                    self.progress.emit(f"Subiendo: {nombre_archivo}...", 90)
                    if self.api_client.subir_archivo(ruta_local, accion['key']):
                        resumen_sync.append(f"'{nombre_archivo}' sincronizado con la nube.")
            
            if not resumen_sync:
                resumen_sync.append("Todo está sincronizado.")
            
            self.progress.emit("¡Listo!", 100)
            self.finished.emit(respuesta_verificacion, resumen_sync)

        except Exception as e:
            self.finished.emit(f"Error crítico en el arranque: {e}", [])


class AppController(QObject):
    """Controla todo el flujo de la aplicación."""
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.api_client = ApiClient()
        self.main_window = MainWindow()
        self.thread = None
        self.worker = None
        self.respuesta_conflicto = None
        self.claim_token = None
        self.polling_timer = QTimer()
        self.polling_timer.timeout.connect(self._poll_for_activation)
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
        
        self.thread = QThread()
        self.worker = StartupWorker(self)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.main_window.loading_view.update_status)
        self.worker.finished.connect(self.handle_startup_result)
        
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        self.thread.start()

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

    def handle_startup_result(self, result):
        """
        Manejador central para el resultado del worker de arranque.
        Ahora es más directo y no muestra un diálogo de resumen.
        """
        if isinstance(result, str): # Si el resultado es un string, es un error o acción
            if result == "activacion_requerida":
                self.solicitar_login_activacion()
            else:
                self.show_error(f"Error en el arranque: {result}")
                self.main_window.mostrar_vista_auth()
        
        elif isinstance(result, dict): # Si es un diccionario, es una respuesta de API
            # ✅ CORRECCIÓN: Llamamos directamente a la función que decide a dónde ir,
            # sin mostrar el QMessageBox que causaba el bloqueo.
            self._manejar_respuesta_verificacion(result)
            
    def solicitar_login_activacion(self):
        """Configura la UI para el login de activación."""
        try: self.main_window.auth_view.login_solicitado.disconnect()
        except RuntimeError: pass
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
        if respuesta.get("status") == "ok" and "access_token" in respuesta:
            print("Verificación exitosa. Iniciando sesión automáticamente.")
            self.api_client.set_auth_token(respuesta["access_token"])
            self.main_window.mostrar_vista_dashboard()
        elif respuesta.get("status") == "location_mismatch":
            print("Conflicto de ubicación detectado. Se requiere login para resolver.")
            QMessageBox.warning(self.main_window, "Conflicto de Ubicación", "Hemos detectado que estás en una nueva ubicación.\n\nPor favor, inicia sesión con tu cuenta para autorizar este cambio.")
            self.respuesta_conflicto = respuesta
            self.main_window.auth_view.login_solicitado.disconnect()
            self.main_window.auth_view.login_solicitado.connect(self.handle_login_para_resolver_conflicto)
            self.main_window.mostrar_vista_auth()
        else:
            error_detail = respuesta.get("detail", "Error desconocido.")
            print(f"Fallo en verificación: {error_detail}.")
            self.main_window.mostrar_vista_auth()

    def handle_account_login_and_activate(self, email: str, password: str):
        try:
            print(f"Autenticando cuenta Addsy: {email}...")
            self.api_client.login(email, password)
            print("Cuenta autenticada. Verificando si esta PC ya está registrada como terminal...")
            hardware_id = self._generar_id_estable()
            terminales_existentes = self.api_client.get_mis_terminales()
            terminal_ya_registrada = any(t['id_terminal'] == hardware_id for t in terminales_existentes)
            if terminal_ya_registrada:
                print(f"Este hardware ya está registrado. Vinculando con ID: {hardware_id}")
                save_terminal_id(hardware_id)
                QMessageBox.information(self.main_window, "Terminal Vinculada", "Este equipo ha sido vinculado exitosamente a tu terminal existente.\n\nLa aplicación se reiniciará para aplicar la configuración.")
                self._iniciar_arranque_inteligente()
            else:
                print("No se encontró una terminal para este hardware. Iniciando flujo de creación.")
                self.handle_nueva_terminal()
        except Exception as e:
            self.show_error(f"Error en el proceso de activación: {e}")

    def handle_nueva_terminal(self):
        try:
            msg = (
                "<h3>Registrar Nueva Terminal</h3>"
                "<p>Hemos detectado que estás iniciando sesión desde un dispositivo no registrado.</p>"
                "<p>¿Deseas añadir este equipo como una nueva terminal en tu cuenta?</p>"
                "<p><b>Nota:</b> Se aplicará un cargo adicional recurrente de $50 MXN/mes a tu suscripción.</p>"
            )
            respuesta = QMessageBox.question(self.main_window, "Nueva Terminal Detectada", msg, QMessageBox.Yes | QMessageBox.No)
            if respuesta == QMessageBox.No: return

            sucursales = self.api_client.get_mis_sucursales()
            id_sucursal_seleccionada = None
            if len(sucursales) == 1:
                id_sucursal_seleccionada = sucursales[0]["id"]
            else:
                dialogo = SeleccionarSucursalDialog(sucursales, self.main_window)
                if dialogo.exec():
                    id_sucursal_seleccionada = dialogo.get_selected_sucursal_id()
                else: return
            
            nombre_terminal, ok = QInputDialog.getText(self.main_window, "Nombre de la Terminal", "Ingresa un nombre para identificar esta terminal (ej. 'Caja 2'):")
            if not ok or not nombre_terminal.strip():
                QMessageBox.warning(self.main_window, "Acción Cancelada", "El nombre de la terminal no puede estar vacío.")
                return
            
            hardware_id = self._generar_id_estable()
            datos_terminal = {"id_terminal": hardware_id, "nombre_terminal": nombre_terminal.strip(), "id_sucursal": id_sucursal_seleccionada}
            self.api_client.registrar_nueva_terminal(datos_terminal)
            save_terminal_id(hardware_id)
            QMessageBox.information(self.main_window, "¡Éxito!", "La nueva terminal ha sido registrada y configurada.")
            self.main_window.mostrar_vista_dashboard()
        except Exception as e:
            self.show_error(f"No se pudo registrar la nueva terminal: {e}")

    def handle_login_para_resolver_conflicto(self, email: str, password: str):
        try:
            self.main_window.auth_view.login_solicitado.disconnect(self.handle_login_para_resolver_conflicto)
            self.main_window.auth_view.login_solicitado.connect(self.handle_account_login_and_activate)
            self.api_client.login(email, password)
            id_terminal_local = get_id_terminal()
            respuesta_conflicto = self.respuesta_conflicto
            self.respuesta_conflicto = None
            sugerencia = respuesta_conflicto.get("sugerencia_migracion")
            if sugerencia and mostrar_dialogo_migracion(sugerencia["nombre"]):
                self.api_client.asignar_terminal_a_sucursal(id_terminal_local, sugerencia["id"])
                QMessageBox.information(self.main_window, "Éxito", "La terminal se ha movido de sucursal. Reiniciando verificación...")
                self._iniciar_arranque_inteligente()
                return
            sucursales = respuesta_conflicto.get("sucursales_existentes", [])
            dialogo = ResolverUbicacionDialog(sucursales, self.main_window)
            if dialogo.exec():
                accion, datos = dialogo.get_resultado()
                if accion == "crear":
                    res = self.api_client.crear_sucursal_y_asignar_terminal(id_terminal_local, datos["nombre"])
                    self.api_client.set_auth_token(res["access_token"])
                    self.main_window.mostrar_vista_dashboard()
                elif accion == "asignar":
                    self.api_client.asignar_terminal_a_sucursal(id_terminal_local, datos["id_sucursal"])
                    QMessageBox.information(self.main_window, "Éxito", "Terminal asignada. Verificando acceso...")
                    self._iniciar_arranque_inteligente()
            else:
                self.main_window.mostrar_vista_auth()
        except Exception as e:
            self.show_error(f"Error resolviendo conflicto: {e}")

    def handle_register(self, user_data: dict):
        try:
            hardware_id = self._generar_id_estable()
            user_data["id_terminal"] = hardware_id
            self.claim_token = str(uuid.uuid4())
            user_data["claim_token"] = self.claim_token
            respuesta = self.api_client.registrar_cuenta(user_data)
            url_checkout = respuesta.get("url_checkout")
            if url_checkout:
                webbrowser.open(url_checkout)
                self.main_window.loading_view.set_message("Esperando activación...", "Completa el pago y la verificación en tu navegador.")
                self.polling_timer.start(5000)
            else:
                self.show_error("El servidor no devolvió una URL de pago.")
        except Exception as e:
            self.show_error(str(e))
            self.main_window.mostrar_vista_auth()

    def _poll_for_activation(self):
        print("Polling para verificar activación...")
        try:
            respuesta = self.api_client.check_activation_status(self.claim_token)
            if respuesta.get("status") == "complete":
                print("¡Activación completada!")
                self.polling_timer.stop()
                self.api_client.set_auth_token(respuesta["access_token"])
                save_terminal_id(respuesta["id_terminal"])
                QMessageBox.information(self.main_window, "¡Cuenta Activada!", "Tu cuenta y tu primera terminal han sido configuradas exitosamente.")
                self.main_window.mostrar_vista_dashboard()
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