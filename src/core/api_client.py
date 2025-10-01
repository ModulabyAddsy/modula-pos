# src/core/api_client.py
import httpx
import os
from pathlib import Path
import hashlib
from src.core.local_storage import calcular_hash_md5
from src.core.utils import get_network_identifiers
from datetime import datetime
import uuid

class ApiClient:
    """Gestiona toda la comunicación con el backend de Modula."""
    def __init__(self):
        self.base_url = os.getenv("MODULA_API_BASE_URL", "https://modula-backend.onrender.com")
        if not self.base_url:
            raise ValueError("La URL del API no está configurada. Revisa tu archivo .env")
        self.auth_token = None
    
    def _get_auth_headers(self):
        """Crea el diccionario de cabeceras para una petición autenticada."""
        if not self.auth_token:
            raise Exception("No se ha establecido un token de autenticación.")
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    def _request(self, method: str, endpoint: str, json_data: dict = None):
        """
        Función auxiliar genérica para realizar peticiones a la API.
        Añade automáticamente la URL base y el token de autorización.
        """
        if not self.base_url or not self.auth_token: # <--- LÍNEA CORREGIDA
            raise Exception("ApiClient no inicializado o sin token.")

        url = f"{self.base_url}/{endpoint}"
        headers = self._get_auth_headers()

        try:
            # Usamos un bloque 'with' para asegurar que el cliente se cierre
            with httpx.Client() as client:
                response = client.request(
                    method.upper(),
                    url,
                    json=json_data,
                    headers=headers,
                    timeout=30.0 # Timeout de 30 segundos
                )
                # Lanza una excepción si la respuesta es un error (4xx o 5xx)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            print(f"🔥🔥 Error HTTP: {e.response.status_code} - {e.response.text}")
            # Re-lanzamos la excepción para que sea capturada por el ModuleManager
            raise e
        except Exception as e:
            print(f"🔥🔥 Error de red o conexión: {e}")
            raise e
        
    def _sanitize_data_for_json(self, data):
        """
        Sanea recursivamente los datos para asegurar que sean serializables a JSON.
        Convierte UUIDs, datetimes y otros tipos no estándar a cadenas.
        """
        if isinstance(data, dict):
            return {k: self._sanitize_data_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_data_for_json(item) for item in data]
        elif isinstance(data, (datetime, uuid.UUID)):
            return str(data)
        else:
            return data

    def set_auth_token(self, token: str):
        """Almacena el token de autenticación para futuras peticiones."""
        self.auth_token = token
        print(f"DEBUG: Token guardado en ApiClient: {self.auth_token}")
        print("Token de sesión guardado.")

    # --- FUNCIÓN NUEVA AÑADIDA ---
    def registrar_cuenta(self, datos_registro: dict) -> dict:
        """
        Envía los datos de un nuevo usuario al backend para pre-registrarlo
        y obtener la URL de checkout de Stripe.
        """
        url = f"{self.base_url}/api/v1/auth/registrar-cuenta"
        try:
            with httpx.Client() as client:
                response = client.post(url, json=datos_registro, timeout=15.0)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            # --- 👇 ESTE BLOQUE AHORA ES MÁS ROBUSTO ---
            detail = ""
            try:
                # Intenta leer el mensaje de error específico del JSON
                detail = e.response.json().get("detail", "Error del servidor.")
            except Exception:
                # Si la respuesta de error no es JSON, usa el texto plano o un mensaje genérico
                detail = e.response.text if e.response.text else "El servidor devolvió un error inesperado."
            
            raise Exception(f"Error al registrar cuenta: {detail}")
            # --- ------------------------------------ ---
            
        except httpx.RequestError:
            raise Exception("Error de conexión al intentar registrar la cuenta.")

    def login(self, correo: str, contrasena: str) -> dict:
        """Envía las credenciales para iniciar sesión y guarda el token si es exitoso."""
        url = f"{self.base_url}/api/v1/auth/login"
        payload = {"correo": correo, "contrasena": contrasena}
        
        try:
            with httpx.Client() as client:
                response = client.post(url, json=payload, timeout=10.0)

            response.raise_for_status()
            data = response.json()
            if "access_token" in data:
                self.set_auth_token(data["access_token"])
            return data

        except httpx.HTTPStatusError as e:
            # --- 👇 APLICAMOS LA MISMA LÓGICA ROBUSTA AQUÍ ---
            detail = ""
            try:
                detail = e.response.json().get("detail", "Error del servidor.")
            except Exception:
                detail = e.response.text if e.response.text else "Correo o contraseña incorrectos."

            raise Exception(f"Error de autenticación: {detail}") from e
            # --- ------------------------------------------- ---
            
        except httpx.RequestError as e:
            raise Exception("Error de conexión: No se pudo conectar al servidor.") from e
        
    def buscar_terminal_por_hardware(self, hardware_id: str) -> dict:
        """Busca si una terminal con un ID de hardware ya existe en el backend."""
        url = f"{self.base_url}/api/v1/terminales/buscar-por-hardware"
        payload = {"id_terminal": hardware_id}
        try:
            with httpx.Client() as client:
                response = client.post(url, json=payload, timeout=15.0)
            # Levanta una excepción para errores 4xx o 5xx
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Captura específicamente el error 404 y lo relanza
            if e.response.status_code == 404:
                raise Exception("Terminal no encontrada en el backend.")
            # Para otros errores, muestra el detalle
            detail = e.response.json().get("detail", "Error del servidor.")
            raise Exception(f"Error HTTP al buscar terminal: {detail}")
        except httpx.RequestError:
            raise Exception("Error de conexión al buscar terminal por hardware.")
    
    def verificar_terminal(self, terminal_id: str) -> dict:
        """Verifica una terminal enviando su ID de hardware y los de la red local."""
        url = f"{self.base_url}/api/v1/auth/verificar-terminal"
        network_ids = get_network_identifiers()
        payload = {"id_terminal": terminal_id, **network_ids}
        
        try:
            with httpx.Client() as client:
                response = client.post(url, json=payload, timeout=15.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # --- 👇 APLICAMOS LA MISMA LÓGICA ROBUSTA AQUÍ ---
            try:
                # Intenta leer el JSON de la respuesta de error (ej. {"detail": "Not Found"})
                return e.response.json()
            except Exception:
                # Si la respuesta no es JSON (ej. un 500), creamos un diccionario de error
                return {"status": "error", "message": f"Error del servidor (código {e.response.status_code})"}
                
        except httpx.RequestError:
            return {"status": "error", "message": "No se pudo conectar con el servidor."}

    def anclar_red_a_sucursal(self, id_sucursal: int, network_ids: dict):
        """
        Envía los identificadores de la red local actual al backend para
        autorizarlos (anclarlos) para una sucursal específica.
        """
        if not self.auth_token:
            raise Exception("Se requiere autenticación para anclar una red.")
        
        url = f"{self.base_url}/api/v1/sucursales/{id_sucursal}/anclar-red"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # El payload son los identificadores que recolectamos (gateway_mac, ssid)
        payload = network_ids
        
        try:
            with httpx.Client() as client:
                response = client.post(url, headers=headers, json=payload, timeout=15.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", e.response.text)
            raise Exception(f"Error al anclar la red: {detail}")
        except httpx.RequestError:
            raise Exception("Error de conexión al intentar anclar la red.")

    
    def crear_sucursal(self, nombre_sucursal: str) -> dict:
        """Llama al endpoint para crear una nueva sucursal."""
        if not self.auth_token:
            raise Exception("Se requiere autenticación para realizar esta acción.")
        url = f"{self.base_url}/api/v1/sucursales/"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        payload = {"nombre": nombre_sucursal}
        try:
            with httpx.Client() as client:
                response = client.post(url, headers=headers, json=payload, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", e.response.text)
            raise Exception(f"Error al crear sucursal: {detail}")
        except httpx.RequestError:
            raise Exception("Error de conexión al crear sucursal.")
        
    def asignar_terminal_a_sucursal(self, id_terminal: str, id_sucursal: int) -> dict:
        """Llama al endpoint para migrar/asignar una terminal a otra sucursal."""
        if not self.auth_token:
            raise Exception("Se requiere autenticación para realizar esta acción.")
        
        url = f"{self.base_url}/api/v1/terminales/asignar-a-sucursal"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        payload = {"id_terminal_origen": id_terminal, "id_sucursal_destino": id_sucursal}
        
        try:
            with httpx.Client() as client:
                response = client.post(url, headers=headers, json=payload, timeout=15.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", e.response.text)
            raise Exception(f"Error al asignar terminal: {detail}")
        except httpx.RequestError:
            raise Exception("Error de conexión al asignar la terminal.")

    def crear_sucursal_y_asignar_terminal(self, id_terminal: str, nombre_sucursal: str) -> dict:
        """Llama al endpoint que crea una sucursal y asigna la terminal."""
        if not self.auth_token:
            raise Exception("Se requiere autenticación para realizar esta acción.")

        url = f"{self.base_url}/api/v1/terminales/crear-sucursal-y-asignar"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        payload = {"id_terminal_origen": id_terminal, "nombre_nueva_sucursal": nombre_sucursal}
        
        try:
            with httpx.Client() as client:
                response = client.post(url, headers=headers, json=payload, timeout=20.0) # Mayor timeout
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", e.response.text)
            raise Exception(f"Error al crear y asignar: {detail}")
        except httpx.RequestError:
            raise Exception("Error de conexión al crear la nueva sucursal.")
        
    def get_mis_sucursales(self) -> list:
        """Obtiene la lista de sucursales del usuario autenticado."""
        if not self.auth_token:
            raise Exception("Se requiere autenticación.")
        url = f"{self.base_url}/api/v1/sucursales/mi-cuenta"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        try:
            with httpx.Client() as client:
                response = client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Error al obtener sucursales: {e}")
        
    def get_mis_terminales(self) -> list:
        """Obtiene la lista de terminales asociadas a la cuenta autenticada."""
        if not self.auth_token:
            raise Exception("Se requiere autenticación para obtener la lista de terminales.")
        
        url = f"{self.base_url}/api/v1/terminales/mi-cuenta"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Reutilizamos el cliente httpx si ya existe, o creamos uno nuevo
            with httpx.Client() as client:
                response = client.get(url, headers=headers, timeout=15.0)
            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", "Error del servidor.")
            raise Exception(f"Error al obtener la lista de terminales: {detail}")
        except httpx.RequestError:
            raise Exception("Error de conexión al obtener la lista de terminales.")
    
    def registrar_nueva_terminal(self, datos_terminal: dict) -> dict:
        """Llama al endpoint para registrar una nueva terminal para la cuenta."""
        if not self.auth_token:
            raise Exception("Se requiere autenticación para registrar una terminal.")
        
        url = f"{self.base_url}/api/v1/terminales/"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            with httpx.Client() as client:
                # El backend espera un JSON con los datos de la nueva terminal
                response = client.post(url, headers=headers, json=datos_terminal, timeout=15.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", e.response.text)
            raise Exception(f"Error al registrar la terminal: {detail}")
        except httpx.RequestError:
            raise Exception("Error de conexión al intentar registrar la terminal.")
        
    def check_activation_status(self, claim_token: str) -> dict:
        url = f"{self.base_url}/api/v1/auth/check-activation-status/{claim_token}"
        try:
            with httpx.Client() as client:
                response = client.get(url, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", "Error del servidor.")
            raise Exception(f"Error de activación: {detail}")
        except httpx.RequestError:
            raise Exception("Error de conexión al verificar activación.")
    
    def solicitar_reseteo_contrasena(self, email: str) -> dict:
        """Llama al endpoint para solicitar un reseteo de contraseña."""
        url = f"{self.base_url}/api/v1/auth/solicitar-reseteo"
        payload = {"email": email}
        try:
            with httpx.Client() as client:
                response = client.post(url, json=payload, timeout=15.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Error al solicitar reseteo: {e}")
    
    # --- ✅ NUEVOS MÉTODOS PARA SINCRONIZACIÓN ---

    def check_sync_status(self, id_sucursal: int, archivos_locales: list) -> dict:
        """
        Envía el estado de los archivos locales al backend y recibe un plan de sincronización.
        """
        if not self.auth_token:
            raise Exception("Se requiere autenticación para la sincronización.")
        
        url = f"{self.base_url}/api/v1/sync/check"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        payload_archivos = [
            {"key": f["key"], "last_modified": f["last_modified"], "hash": f["hash"]}
            for f in archivos_locales
        ]
        
        payload = {
            "id_sucursal_actual": id_sucursal,
            "archivos_locales": payload_archivos
        }
        
        try:
            with httpx.Client() as client:
                response = client.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Error al verificar estado de sincronización: {e}")
        
    def descargar_archivo(self, key_en_la_nube: str, ruta_local_destino: Path):
        """Descarga un archivo específico desde la nube y lo guarda localmente."""
        if not self.auth_token: 
            raise Exception("Se requiere autenticación para descargar.")

        url = f"{self.base_url}/api/v1/sync/pull-db/{key_en_la_nube}"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # ✅ CORRECCIÓN: Usar la variable correcta del argumento de la función.
        ruta_local_destino.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with httpx.stream("GET", url, headers=headers, timeout=120.0) as response:
                response.raise_for_status()
                with open(ruta_local_destino, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
            print(f"✅ Descarga completa: {key_en_la_nube}")
            return True
        except httpx.HTTPStatusError as e:
            print(f"❌ Error al descargar {key_en_la_nube}: Error HTTP {e.response.status_code}")
            return False
        except Exception as e:
            print(f"❌ Error al descargar {key_en_la_nube}: {e}")
            return False

    def subir_archivo(self, ruta_local, key_cloud, hash_base):
        """
        Sube un archivo a la nube, incluyendo el hash de la versión base para detectar conflictos.
        """
        if not self.auth_token:
            raise Exception("Autenticación requerida.")
        url = f"{self.base_url}/api/v1/sync/upload/{key_cloud}"
        headers = {'Authorization': f'Bearer {self.auth_token}', 'X-Base-Version-Hash': hash_base}
        try:
            with open(ruta_local, 'rb') as f:
                with httpx.Client() as client:
                    response = client.post(url, files={'file': f}, headers=headers)
                
            if response.status_code == 409:
                raise Exception("Conflicto detectado")

            response.raise_for_status()
            print(f"✅ Subida completa: {os.path.basename(ruta_local)}")
            return True
        except Exception as e:
            if "Conflicto detectado" in str(e):
                print(f"⚠️  Conflicto detectado para {os.path.basename(ruta_local)}. Se requiere sincronización.")
                raise ConnectionAbortedError("conflict")
            print(f"❌ Error al subir {os.path.basename(ruta_local)}: {e}")
            return False
        
    def initialize_sync(self) -> dict:
        """Llama al backend para preparar la nube (Etapas 1 y 2)."""
        print(f"DEBUG: Token a punto de ser usado en initialize_sync: {self.auth_token}")
        if not self.auth_token:
            raise Exception("Intento de llamar a 'initialize_sync' sin un token de autenticación.")
        
        url = f"{self.base_url}/api/v1/sync/initialize"
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            with httpx.Client() as client:
                response = client.post(url, headers=headers, timeout=120.0)
            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error en la petición a {url}: {e.response.text}")

    def push_records(self, push_data: dict) -> dict:
        """Envía un paquete de registros locales a la nube para fusionarlos."""
        if not self.auth_token: raise Exception("Autenticación requerida.")
        url = f"{self.base_url}/api/v1/sync/push-records"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # ✅ LÍNEA CRÍTICA: Llama a la función de limpieza antes de enviar.
        sanitized_data = self._sanitize_data_for_json(push_data)
        
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=sanitized_data, timeout=120.0)
        
        response.raise_for_status()
        return response.json()

    def pull_db_file(self, key_path: str, local_destination: Path):
        """Descarga un archivo de DB desde el endpoint de pull."""
        if not self.auth_token:
            raise Exception("Autenticación requerida.")
            
        url = f"{self.base_url}/api/v1/sync/pull-db/{key_path}"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        local_destination.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with httpx.stream("GET", url, headers=headers, timeout=120.0) as response:
                response.raise_for_status()
                with open(local_destination, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
                print(f"✅ Descarga completa: {key_path}")
                return True
        except httpx.HTTPStatusError as e:
            print(f"❌ Error al descargar {key_path}: Error HTTP {e.response.status_code}")
            return False
        except Exception as e:
            print(f"❌ Error al descargar {key_path}: {e}")
            return False
        
    def get_deltas(self, sync_timestamps: dict) -> dict:
        """Pide al backend los registros que han cambiado desde los timestamps dados."""
        if not self.auth_token: raise Exception("Autenticación requerida.")
        url = f"{self.base_url}/api/v1/sync/get-deltas"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        try:
            with httpx.Client() as client:
                response = client.post(url, headers=headers, json=sync_timestamps, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Error al obtener deltas: {e}")
        
    def get_modules_manifest(self):
        """
        Obtiene el manifiesto de módulos desde el backend.
        """
        print("ℹ️ Solicitando manifiesto de módulos al servidor...")
        # Añadimos el prefijo /api/v1/ para que coincida con la ruta del backend
        return self._request("get", "api/v1/modules/manifest")