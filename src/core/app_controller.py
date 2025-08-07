# src/core/app_controller.py
import webbrowser
import os
from PySide6.QtWidgets import QMessageBox, QInputDialog
from PySide6.QtCore import Signal, Qt, QDate, QTimer
from src.ui.main_window import MainWindow
from src.core.api_client import ApiClient
from src.core.local_storage import get_id_terminal, delete_config, save_terminal_id
# ✅ CORRECCIÓN: Añadir la importación de ResolverUbicacionDialog
from src.ui.dialogs import mostrar_dialogo_migracion, ResolverUbicacionDialog, SeleccionarSucursalDialog, RecuperarContrasenaDialog
import uuid
import psutil

class AppController:
    """Controla todo el flujo de la aplicación."""
    def __init__(self, app):
        self.app = app
        self.api_client = ApiClient()
        self.main_window = MainWindow()
        self.respuesta_conflicto = None # Inicializamos la variable de estado
        self._connect_signals()
        self.polling_timer = QTimer() # <-- Crea el timer
        self.polling_timer.timeout.connect(self._poll_for_activation)
        self.claim_token = None

    def _connect_signals(self):
        """Conecta las señales de las vistas a los manejadores del controlador."""
        self.main_window.auth_view.login_solicitado.connect(self.handle_account_login_and_activate)
        self.main_window.auth_view.registro_solicitado.connect(self.handle_register)
        self.main_window.auth_view.recuperacion_solicitada.connect(self.handle_recovery_request)
        
    def handle_recovery_request(self):
        """Muestra el diálogo para solicitar la recuperación de contraseña."""
        dialogo = RecuperarContrasenaDialog(self.main_window)
        if dialogo.exec():
            email = dialogo.get_email()
            if not email:
                self.show_error("El correo no puede estar vacío.")
                return
            try:
                # La función en el api_client la crearemos en el siguiente paso
                respuesta = self.api_client.solicitar_reseteo_contrasena(email)
                QMessageBox.information(self.main_window, "Solicitud Enviada",
                                      respuesta.get("message", "Si el correo está registrado, recibirás un enlace para restablecer tu contraseña."))
            except Exception as e:
                self.show_error(str(e))
    
    def _generar_id_estable(self) -> str:
        """
        Genera un ID único y consistente para la máquina buscando la dirección MAC
        de la interfaz de red principal (Ethernet o Wi-Fi).
        """
        try:
            # psutil nos da todas las interfaces de red
            addrs = psutil.net_if_addrs()
            mac_address = None
            # Buscamos la primera dirección MAC válida y física
            for _, interfaces in addrs.items():
                for interface in interfaces:
                    if interface.family == psutil.AF_LINK and interface.address and "00:00:00:00:00:00" not in interface.address:
                        mac_address = interface.address
                        break
                if mac_address:
                    break
            
            if not mac_address:
                # Si no se encuentra una MAC, recurrimos al método anterior como fallback
                mac_address = uuid.getnode()
            
            # Usamos la MAC como base para un UUID determinista
            hardware_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(mac_address)))
            print(f"ID de hardware estable generado: {hardware_id}")
            return hardware_id
        except Exception as e:
            print(f"ADVERTENCIA: No se pudo obtener la dirección MAC. Se usará un UUID aleatorio. Error: {e}")
            return str(uuid.uuid4())

    def run(self):
        """Punto de entrada: Muestra la ventana e inicia el arranque inteligente."""
        self.main_window.show()
        self._iniciar_arranque_inteligente()

    def _iniciar_arranque_inteligente(self):
        """
        Nuevo flujo de arranque: La terminal siempre sabe quién es.
        """
        self.main_window.mostrar_vista_carga()
        
        # 1. La app siempre genera primero su ID de hardware estable.
        hardware_id = self._generar_id_estable()
        
        # 2. Revisa si el archivo local existe y coincide.
        local_id = get_id_terminal()

        if local_id and local_id == hardware_id:
            # 2A. El archivo local es correcto, procedemos con la verificación normal.
            print(f"Archivo local encontrado y válido. Verificando terminal ID: {hardware_id}...")
            respuesta = self.api_client.verificar_terminal(hardware_id)
            self._manejar_respuesta_verificacion(respuesta)
        else:
            # 2B. No hay archivo local o no coincide. La app debe recuperar su identidad.
            print("Archivo local no encontrado o inválido. Intentando recuperar identidad desde el backend...")
            try:
                # 3. Preguntamos al backend si conoce este hardware.
                respuesta = self.api_client.buscar_terminal_por_hardware(hardware_id)
                
                # 4. Si el backend la encuentra, re-creamos el archivo local.
                print("¡Identidad recuperada! El backend reconoce esta terminal.")
                save_terminal_id(hardware_id)
                
                # 5. Ahora que tenemos el archivo, re-intentamos el arranque inteligente.
                self._iniciar_arranque_inteligente()
                
            except Exception as e:
                # 6. Si el backend no la encuentra (404), es una terminal genuinamente nueva.
                print("El backend no reconoce este hardware. Es una terminal nueva.")
                self.main_window.auth_view.login_solicitado.connect(self.handle_account_login_and_activate)
                self.main_window.mostrar_vista_auth()

    def _manejar_respuesta_verificacion(self, respuesta: dict):
        """
        Analiza la respuesta de la verificación. YA NO BORRA EL ARCHIVO LOCAL.
        """
        if respuesta.get("status") == "ok" and "access_token" in respuesta:
            print("Verificación exitosa. Iniciando sesión automáticamente.")
            self.api_client.set_auth_token(respuesta["access_token"])
            self.main_window.mostrar_vista_dashboard()
            return

        if respuesta.get("status") == "location_mismatch":
            print("Conflicto de ubicación detectado. Se requiere login para resolver.")
            # ✅ CORRECCIÓN CRÍTICA: Ya no borramos el archivo.
            QMessageBox.warning(self.main_window, "Conflicto de Ubicación",
                                  "Hemos detectado que estás en una nueva ubicación.\n\n"
                                  "Por favor, inicia sesión con tu cuenta para autorizar este cambio.")
            
            self.respuesta_conflicto = respuesta
            self.main_window.auth_view.login_solicitado.disconnect()
            self.main_window.auth_view.login_solicitado.connect(self.handle_login_para_resolver_conflicto)
            self.main_window.mostrar_vista_auth()
            return

        # Para cualquier otro error (ej. terminal desactivada), mostramos el login.
        error_detail = respuesta.get("detail", "Error desconocido.")
        print(f"Fallo en verificación: {error_detail}.")
        self.main_window.mostrar_vista_auth()

    def handle_account_login_and_activate(self, email: str, password: str):
        """
        Maneja el login manual. Un login exitoso siempre llevará al flujo
        de configuración de una nueva terminal.
        """
        try:
            print(f"Intentando iniciar sesión como {email}...")
            # El login ahora solo nos da el token, no el ID de la terminal.
            self.api_client.login(email, password) 
            
            # ✅ CORRECCIÓN: Después de un login exitoso, siempre vamos
            # al flujo para registrar el nuevo dispositivo.
            self.handle_nueva_terminal()

        except Exception as e:
            self.show_error(f"Error de Login: {e}")
    
    def handle_nueva_terminal(self):
        """Gestiona el proceso de registrar una nueva terminal tras el login."""
        try:
            # 1. Preguntar al usuario y advertir del costo
            msg = (
                "<h3>Registrar Nueva Terminal</h3>"
                "<p>Hemos detectado que estás iniciando sesión desde un dispositivo no registrado.</p>"
                "<p>¿Deseas añadir este equipo como una nueva terminal en tu cuenta?</p>"
                "<p><b>Nota:</b> Se aplicará un cargo adicional recurrente de $50 MXN/mes a tu suscripción.</p>"
            )
            respuesta = QMessageBox.question(self.main_window, "Nueva Terminal Detectada", msg,
                                             QMessageBox.Yes | QMessageBox.No)

            if respuesta == QMessageBox.No:
                QMessageBox.information(self.main_window, "Acción Cancelada", "El registro de la terminal ha sido cancelado.")
                return

            # 2. Obtener la lista de sucursales
            sucursales = self.api_client.get_mis_sucursales()
            id_sucursal_seleccionada = None

            if len(sucursales) == 1:
                id_sucursal_seleccionada = sucursales[0]["id"]
                QMessageBox.information(self.main_window, "Sucursal Asignada", 
                                      f"La nueva terminal será asignada automáticamente a tu única sucursal: '{sucursales[0]['nombre']}'.")
            else:
                dialogo = SeleccionarSucursalDialog(sucursales, self.main_window)
                if dialogo.exec():
                    id_sucursal_seleccionada = dialogo.get_selected_sucursal_id()
                else:
                    QMessageBox.information(self.main_window, "Acción Cancelada", "No se seleccionó una sucursal.")
                    return

            # 3. Pedir un nombre para la nueva terminal
            nombre_terminal, ok = QInputDialog.getText(self.main_window, "Nombre de la Terminal", 
                                                       "Ingresa un nombre para identificar esta terminal (ej. 'Caja 2'):")
            if not ok or not nombre_terminal.strip():
                QMessageBox.warning(self.main_window, "Acción Cancelada", "El nombre de la terminal no puede estar vacío.")
                return
            
            # ✅ CORRECCIÓN: Generar un ID estable basado en el hardware (dirección MAC)
            try:
                # uuid.getnode() obtiene la dirección MAC como un número entero
                mac_address_int = uuid.getnode()
                # Creamos un UUID a partir de ese número. Siempre será el mismo en esta PC.
                nuevo_id_terminal = str(uuid.UUID(int=mac_address_int))
                print(f"ID de hardware generado: {nuevo_id_terminal}")
            except Exception as e:
                # Fallback por si no se puede obtener la MAC (muy raro)
                print(f"No se pudo obtener MAC, generando UUID aleatorio como fallback. Error: {e}")
                nuevo_id_terminal = str(uuid.uuid4())

            # 4. Crear la nueva terminal en el backend
            datos_terminal = {
                "id_terminal": nuevo_id_terminal,
                "nombre_terminal": nombre_terminal.strip(),
                "id_sucursal": id_sucursal_seleccionada
            }
            
            self.api_client.registrar_nueva_terminal(datos_terminal)
            
            # 5. Guardar localmente y proceder al dashboard
            save_terminal_id(nuevo_id_terminal)
            QMessageBox.information(self.main_window, "¡Éxito!", "La nueva terminal ha sido registrada y configurada.")
            self.main_window.mostrar_vista_dashboard()

        except Exception as e:
            self.show_error(f"No se pudo registrar la nueva terminal: {e}")

    def handle_login_para_resolver_conflicto(self, email: str, password: str):
        """
        Función que se ejecuta después del login para resolver un conflicto de ubicación.
        """
        try:
            # Desconectamos esta señal para evitar bucles.
            self.main_window.auth_view.login_solicitado.disconnect(self.handle_login_para_resolver_conflicto)
            # Reconectamos la señal de login de activación normal.
            self.main_window.auth_view.login_solicitado.connect(self.handle_account_login_and_activate)

            # Hacemos login para obtener un token válido
            self.api_client.login(email, password)
            id_terminal_local = get_id_terminal()

            respuesta_conflicto = self.respuesta_conflicto
            self.respuesta_conflicto = None

            # Flujo de Migración Sugerida
            sugerencia = respuesta_conflicto.get("sugerencia_migracion")
            if sugerencia and mostrar_dialogo_migracion(sugerencia["nombre"]):
                self.api_client.asignar_terminal_a_sucursal(id_terminal_local, sugerencia["id"])
                QMessageBox.information(self.main_window, "Éxito", "La terminal se ha movido de sucursal. Reiniciando verificación...")
                # Re-ejecutamos el arranque inteligente, que ahora debería ser exitoso
                self._iniciar_arranque_inteligente()
                return

            # Flujo de Creación o Asignación Manual
            sucursales = respuesta_conflicto.get("sucursales_existentes", [])
            dialogo = ResolverUbicacionDialog(sucursales, self.main_window)
            
            if dialogo.exec():
                accion, datos = dialogo.get_resultado()
                if accion == "crear":
                    # Este flujo ya es correcto: obtiene un token y va al dashboard.
                    res = self.api_client.crear_sucursal_y_asignar_terminal(id_terminal_local, datos["nombre"])
                    self.api_client.set_auth_token(res["access_token"])
                    self.main_window.mostrar_vista_dashboard()
                
                elif accion == "asignar":
                    # ✅ CORRECCIÓN: Ya no borramos el config ni pedimos login de nuevo.
                    self.api_client.asignar_terminal_a_sucursal(id_terminal_local, datos["id_sucursal"])
                    QMessageBox.information(self.main_window, "Éxito", "La terminal ha sido asignada a la nueva sucursal. Verificando acceso...")
                    # Re-ejecutamos el arranque inteligente. Como el backend ya actualizó la IP,
                    # esta verificación será exitosa y nos llevará al dashboard.
                    self._iniciar_arranque_inteligente()
            else:
                # Si el usuario cancela, lo dejamos en la vista de autenticación
                self.main_window.mostrar_vista_auth()
        except Exception as e:
            self.show_error(f"Error resolviendo conflicto: {e}")
            self.main_window.mostrar_vista_auth()

    def handle_register(self, user_data: dict):
        """
        Inicia el nuevo flujo de registro con polling.
        """
        try:
            # 1. Generar y añadir el claim token
            self.claim_token = str(uuid.uuid4())
            user_data["claim_token"] = self.claim_token
            
            # 2. Llamar al backend para obtener la URL de Stripe
            respuesta = self.api_client.registrar_cuenta(user_data)
            
            url_checkout = respuesta.get("url_checkout")
            if url_checkout:
                webbrowser.open(url_checkout)
                
                # 3. Cambiar a la vista de espera y empezar el polling
                self.main_window.mostrar_vista_carga()
                self.main_window.loading_view.set_message(
                    "Esperando activación de la cuenta...",
                    "Por favor, completa el pago y la verificación por correo en tu navegador."
                )
                self.polling_timer.start(5000) # Preguntar cada 5 segundos
            else:
                self.show_error("El servidor no devolvió una URL de pago.")
        except Exception as e:
            self.show_error(str(e))
            self.main_window.mostrar_vista_auth() # Volver al login si algo falla

    def _poll_for_activation(self):
        """Función que el QTimer llamará repetidamente."""
        print("Polling para verificar activación...")
        try:
            respuesta = self.api_client.check_activation_status(self.claim_token)
            
            if respuesta.get("status") == "complete":
                print("¡Activación completada!")
                self.polling_timer.stop()
                
                # Auto-login
                self.api_client.set_auth_token(respuesta["access_token"])
                save_terminal_id(respuesta["id_terminal"])
                
                QMessageBox.information(self.main_window, "¡Cuenta Activada!", 
                                      "Tu cuenta y tu primera terminal han sido configuradas exitosamente.")
                self.main_window.mostrar_vista_dashboard()
        
        except Exception as e:
            print(f"Error durante el polling: {e}. Se reintentará...")
            
    def show_error(self, message: str):
        """Muestra un diálogo de error estandarizado."""
        QMessageBox.critical(self.main_window, "Error", message) 
