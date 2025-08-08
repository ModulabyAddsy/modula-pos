# src/core/app_controller.py
import webbrowser
import os
import uuid
import psutil
from PySide6.QtWidgets import QMessageBox, QInputDialog, QApplication
from PySide6.QtCore import QTimer, QObject, Signal, QThread
from src.ui.main_window import MainWindow
from src.core.api_client import ApiClient
from src.core.local_storage import get_id_terminal, save_terminal_id, get_local_db_file_info,DB_DIR
from src.ui.dialogs import mostrar_dialogo_migracion, ResolverUbicacionDialog, SeleccionarSucursalDialog, RecuperarContrasenaDialog

class StartupWorker(QObject):
    """
    Trabajador que realiza TODA la lógica de arranque en segundo plano para no congelar la UI.
    Decide si la terminal es válida, necesita recuperación o es nueva.
    """
    finished = Signal(object, list) #CAMBIO: La señal ahora emitirá el resultado y una lista de strings (el resumen)

    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client

    def run(self):
        """El trabajo pesado que se ejecuta en el hilo secundario."""
        try:
            # --- FASE 1: Verificación de la Terminal (Lógica existente) ---
            hardware_id = self._generar_id_estable()
            local_id = get_id_terminal()
            respuesta_verificacion = None

            if local_id and local_id == hardware_id:
                respuesta_verificacion = self.api_client.verificar_terminal(local_id)
            else:
                try:
                    self.api_client.buscar_terminal_por_hardware(hardware_id)
                    save_terminal_id(hardware_id)
                    respuesta_verificacion = self.api_client.verificar_terminal(hardware_id)
                except Exception:
                    self.finished.emit("activacion_requerida", []); return

            if "access_token" not in respuesta_verificacion:
                self.finished.emit(respuesta_verificacion, []); return
            
            self.api_client.set_auth_token(respuesta_verificacion["access_token"])

            # --- FASE 2: Planificación de la Sincronización (Lógica existente) ---
            print("Verificación exitosa. Planificando sincronización de bases de datos...")
            id_sucursal = respuesta_verificacion['id_sucursal']
            id_empresa = respuesta_verificacion['id_empresa']
            
            archivos_locales = get_local_db_file_info(id_empresa, id_sucursal)
            
            plan_sync = self.api_client.check_sync_status(id_sucursal, archivos_locales)
            
            # --- ✅ NUEVO: FASE 3: Ejecución del Plan y Creación de Resumen ---
            resumen_sync = []
            print("Ejecutando plan de sincronización...")

            # Ejecutar acciones de esquema (descargar nuevas DBs)
            for accion in plan_sync.get("schema_actions", []):
                nombre_archivo = os.path.basename(accion['key_destino'])
                ruta_local = DB_DIR / nombre_archivo
                if self.api_client.descargar_archivo(accion['key_origen'], ruta_local):
                    resumen_sync.append(f"Nueva base de datos '{nombre_archivo}' instalada.")

            # Ejecutar acciones de datos (subir/bajar actualizaciones)
            for accion in plan_sync.get("data_actions", []):
                # La 'key' ya es la ruta completa en la nube, la usamos para construir la ruta local
                nombre_archivo = os.path.basename(accion['key'])
                ruta_local = DB_DIR / nombre_archivo
                
                if accion['accion'] == "descargar_actualizacion":
                    if self.api_client.descargar_archivo(accion['key'], ruta_local):
                        resumen_sync.append(f"'{nombre_archivo}' actualizado desde la nube.")
                elif accion['accion'] == "subir_actualizacion":
                    if self.api_client.subir_archivo(ruta_local, accion['key']):
                        resumen_sync.append(f"'{nombre_archivo}' sincronizado con la nube.")
            
            if not resumen_sync:
                resumen_sync.append("Todo está sincronizado.")

            # Emitimos ambos resultados: la verificación y el resumen.
            self.finished.emit(respuesta_verificacion, resumen_sync)

        except Exception as e:
            self.finished.emit(str(e), []) # Emitimos un error y un resumen vacío

    def _generar_id_estable(self) -> str:
        """Genera un ID único y consistente para la máquina."""
        try:
            addrs = psutil.net_if_addrs()
            mac_address = None
            for _, interfaces in addrs.items():
                for interface in interfaces:
                    if interface.family == psutil.AF_LINK and interface.address and "00:00:00:00:00:00" not in interface.address:
                        mac_address = interface.address; break
                if mac_address: break
            if not mac_address: mac_address = uuid.getnode()
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(mac_address)))
        except:
            return str(uuid.uuid4())

class AppController(QObject):
    """Controla todo el flujo de la aplicación."""
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.api_client = ApiClient()
        self.main_window = MainWindow()
        self.worker_thread = None # Se inicializa a None
        self.respuesta_conflicto = None
        self.claim_token = None
        self.polling_timer = QTimer()
        self.polling_timer.timeout.connect(self._poll_for_activation)
        self._connect_signals()

    def _connect_signals(self):
        self.main_window.auth_view.registro_solicitado.connect(self.handle_register)
        self.main_window.auth_view.recuperacion_solicitada.connect(self.handle_recovery_request)

    def run(self):
        self.main_window.show()
        self._iniciar_arranque_inteligente()

    def _iniciar_arranque_inteligente(self):
        """Inicia el 'worker' de arranque en un hilo secundario."""
        self.main_window.mostrar_vista_carga()
        
        self.thread = QThread()
        self.worker = StartupWorker(self.api_client)
        self.worker.moveToThread(self.thread)

        # Conexiones clave para el funcionamiento correcto de hilos
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.handle_startup_result)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        self.thread.start()

    def handle_startup_result(self, result, resumen_sync):
        """
        Manejador central para el resultado del worker de arranque.
        Muestra el resumen y LUEGO continúa con el flujo normal.
        """
        self.main_window.hide()

        # Primero, mostramos el resumen de la sincronización si la lista no está vacía
        if resumen_sync:
            mensaje_sync = "\n".join(f"- {s}" for s in resumen_sync)
            QMessageBox.information(self.main_window, "Sincronización Completada",
                                  f"Resumen de sincronización:\n{mensaje_sync}")

        # ✅ CORRECCIÓN: Esta lógica ahora se ejecuta SIEMPRE,
        # después de que el usuario cierra el diálogo de resumen.
        if isinstance(result, str):
            if result == "activacion_requerida":
                self.solicitar_login_activacion()
            else:
                self.show_error(f"Error en el arranque: {result}")
                self.main_window.mostrar_vista_auth()
        
        elif isinstance(result, dict):
            # Esta llamada es la que te llevará al dashboard o al login de conflicto.
            # Ahora se ejecuta correctamente sin importar si hubo resumen o no.
            self._manejar_respuesta_verificacion(result)

    def solicitar_login_activacion(self):
        """Configura la UI para el login de activación de cuenta Addsy."""
        try: self.main_window.auth_view.login_solicitado.disconnect() 
        except RuntimeError: pass
        self.main_window.auth_view.login_solicitado.connect(self.handle_account_login_and_activate)
        self.main_window.mostrar_vista_auth()

    def _manejar_respuesta_verificacion(self, respuesta: dict):
        """Analiza la respuesta de una verificación."""
        if respuesta.get("status") == "ok" and "access_token" in respuesta:
            self.api_client.set_auth_token(respuesta["access_token"])
            self.main_window.mostrar_vista_dashboard()
        elif respuesta.get("status") == "location_mismatch":
            QMessageBox.warning(self.main_window, "Conflicto de Ubicación",
                                  "Hemos detectado que estás en una nueva ubicación.\n\n"
                                  "Por favor, inicia sesión para autorizar este cambio.")
            self.respuesta_conflicto = respuesta
            try: self.main_window.auth_view.login_solicitado.disconnect()
            except RuntimeError: pass
            self.main_window.auth_view.login_solicitado.connect(self.handle_login_para_resolver_conflicto)
            self.main_window.mostrar_vista_auth()
        else:
            self.show_error(f"Fallo en verificación: {respuesta.get('detail', 'Error desconocido.')}")
            self.main_window.mostrar_vista_auth()

    def handle_account_login_and_activate(self, email: str, password: str):
        """Autentica la CUENTA de Addsy y decide si vincular o crear una terminal."""
        try:
            self.api_client.login(email, password)
            self.handle_nueva_terminal()
        except Exception as e:
            self.show_error(f"Error de Autenticación: {e}")

    def handle_nueva_terminal(self):
        """Gestiona el proceso de registrar una nueva terminal en el backend."""
        try:
            msg = ("<h3>Registrar Nueva Terminal</h3>"
                   "<p>¿Deseas añadir este equipo como una nueva terminal en tu cuenta?</p>"
                   "<p><b>Nota:</b> Se aplicará un cargo adicional recurrente de $50 MXN/mes.</p>")
            if QMessageBox.question(self.main_window, "Nueva Terminal", msg) == QMessageBox.No: return

            sucursales = self.api_client.get_mis_sucursales()
            id_sucursal_seleccionada = None
            if not sucursales:
                self.show_error("No se encontraron sucursales.")
                return
            elif len(sucursales) == 1:
                id_sucursal_seleccionada = sucursales[0]["id"]
            else:
                dialogo = SeleccionarSucursalDialog(sucursales, self.main_window)
                if dialogo.exec():
                    id_sucursal_seleccionada = dialogo.get_selected_sucursal_id()
                else: return

            nombre_terminal, ok = QInputDialog.getText(self.main_window, "Nombre", "Nombre para esta terminal:")
            if not ok or not nombre_terminal.strip(): return

            hardware_id = self._generar_id_estable()
            datos = {"id_terminal": hardware_id, "nombre_terminal": nombre_terminal.strip(), "id_sucursal": id_sucursal_seleccionada}
            self.api_client.registrar_nueva_terminal(datos)
            save_terminal_id(hardware_id)
            QMessageBox.information(self.main_window, "¡Éxito!", "Terminal registrada. Reiniciando...")
            self._iniciar_arranque_inteligente()
        except Exception as e:
            self.show_error(f"No se pudo registrar la nueva terminal: {e}")

    def handle_login_para_resolver_conflicto(self, email: str, password: str):
        try:
            self.api_client.login(email, password)
            id_terminal_local = get_id_terminal()
            respuesta_conflicto = self.respuesta_conflicto
            self.respuesta_conflicto = None
            sugerencia = respuesta_conflicto.get("sugerencia_migracion")
            if sugerencia and mostrar_dialogo_migracion(sugerencia["nombre"]):
                self.api_client.asignar_terminal_a_sucursal(id_terminal_local, sugerencia["id"])
                QMessageBox.information(self.main_window, "Éxito", "Terminal movida. Reiniciando verificación...")
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
                QMessageBox.information(self.main_window, "¡Cuenta Activada!", "Tu cuenta y terminal han sido configuradas.")
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
        QMessageBox.critical(self.main_window, "Error", message)
