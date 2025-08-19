# src/core/api_client.py
import httpx
import os
from pathlib import Path
import hashlib
from src.core.local_storage import calcular_hash_md5

class ApiClient:
    """Gestiona toda la comunicación con el backend de Modula."""
    def __init__(self):
        self.base_url = os.getenv("MODULA_API_BASE_URL", "https://modula-backend.onrender.com")
        if not self.base_url:
            raise ValueError("La URL del API no está configurada. Revisa tu archivo .env")
        self.auth_token = None

    def set_auth_token(self, token: str):
        """Almacena el token de autenticación para futuras peticiones."""
        self.auth_token = token
        print("Token de sesión guardado.")

    # --- FUNCIÓN NUEVA AÑADIDA ---
    def registrar_cuenta(self, datos_registro: dict) -> dict:
        """
        Envía los datos de un nuevo usuario al backend para pre-registrarlo
        y obtener la URL de checkout de Stripe.
        """
        url = f"{self.base_url}/auth/registrar-cuenta"
        try:
            with httpx.Client() as client:
                response = client.post(url, json=datos_registro, timeout=15.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", "Error desconocido del servidor.")
            raise Exception(f"Error al registrar cuenta: {detail}")
        except httpx.RequestError:
            raise Exception("Error de conexión al intentar registrar la cuenta.")

    def login(self, correo: str, contrasena: str) -> dict:
        """Envía las credenciales para iniciar sesión y guarda el token si es exitoso."""
        url = f"{self.base_url}/auth/login"
        
        # --- CORRECCIÓN AQUÍ ---
        # El backend espera un JSON con las claves "correo" y "contrasena",
        # no un formulario con "username" y "password".
        payload = {"correo": correo, "contrasena": contrasena}
        
        try:
            with httpx.Client() as client:
                # Se cambia `data=payload` por `json=payload`.
                # Esto envía los datos como un objeto JSON con la cabecera correcta.
                response = client.post(url, json=payload, timeout=10.0)

            response.raise_for_status()
            data = response.json()
            if "access_token" in data:
                self.set_auth_token(data["access_token"])
            return data
        except httpx.HTTPStatusError as e:
            detail = e.response.json().get("detail", e.response.text)
            raise Exception(f"Error de autenticación: {detail}") from e
        except httpx.RequestError as e:
            raise Exception("Error de conexión: No se pudo conectar al servidor.") from e
        
    def buscar_terminal_por_hardware(self, hardware_id: str) -> dict:
        """Busca si una terminal con un ID de hardware ya existe en el backend."""
        url = f"{self.base_url}/terminales/buscar-por-hardware"
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
        """Verifica una terminal en el backend."""
        url = f"{self.base_url}/auth/verificar-terminal"
        payload = {"id_terminal": terminal_id}
        try:
            with httpx.Client() as client:
                response = client.post(url, json=payload, timeout=15.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return e.response.json()
        except httpx.RequestError:
            return {"detail": "No se pudo conectar con el servidor."}

    def crear_sucursal(self, nombre_sucursal: str) -> dict:
        """Llama al endpoint para crear una nueva sucursal."""
        if not self.auth_token:
            raise Exception("Se requiere autenticación para realizar esta acción.")
        url = f"{self.base_url}/sucursales/"
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
        
        url = f"{self.base_url}/terminales/asignar-a-sucursal"
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

        url = f"{self.base_url}/terminales/crear-sucursal-y-asignar"
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
        url = f"{self.base_url}/sucursales/mi-cuenta"
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
        
        url = f"{self.base_url}/terminales/mi-cuenta"
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
        
        url = f"{self.base_url}/terminales/"
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
        url = f"{self.base_url}/auth/check-activation-status/{claim_token}"
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
        url = f"{self.base_url}/auth/solicitar-reseteo"
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
        
        url = f"{self.base_url}/sync/check"
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
        if not self.auth_token: raise Exception("Se requiere autenticación para descargar.")
        url = f"{self.base_url}/sync/download/{key_en_la_nube}"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        try:
            # ✅ LÍNEA CLAVE: Asegura que el directorio padre exista antes de escribir.
            # Por ejemplo, si la ruta es '.../Databases/MOD_EMP_1001/suc_25/tickets.sqlite',
            # esto creará la carpeta 'suc_25' si no existe.
            ruta_local_destino.parent.mkdir(parents=True, exist_ok=True)

            with httpx.stream("GET", url, headers=headers, timeout=60.0) as response:
                response.raise_for_status()
                with open(ruta_local_destino, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
            print(f"✅ Descarga completa: {key_en_la_nube}")
            return True
        except Exception as e:
            print(f"❌ Error al descargar {key_en_la_nube}: {e}")
            return False

    def subir_archivo(self, ruta_local, key_cloud, hash_base):
        """
        Sube un archivo a la nube, incluyendo el hash de la versión base para detectar conflictos.
        """
        try:
            with open(ruta_local, 'rb') as f:
                # Añadimos el hash base como un header personalizado
                headers = {'Authorization': f'Bearer {self.token}', 'X-Base-Version-Hash': hash_base}
                response = self.client.post(f"{self.base_url}/sync/upload/{key_cloud}", files={'file': f}, headers=headers)
                
                if response.status_code == 409: # Conflicto detectado
                    raise Exception("conflict")

                response.raise_for_status()
                print(f"✅ Subida completa: {os.path.basename(ruta_local)}")
                return True
        except Exception as e:
            if str(e) == "conflict":
                print(f"⚠️  Conflicto detectado para {os.path.basename(ruta_local)}. Se requiere sincronización.")
                # Relanzamos una excepción específica o un código para que el controller la maneje
                raise ConnectionAbortedError("conflict")
            print(f"❌ Error al subir {os.path.basename(ruta_local)}: {e}")
            return False
        
    def initialize_sync(self) -> dict:
        """Llama al backend para preparar la nube (Etapas 1 y 2)."""
        if not self.auth_token: raise Exception("Autenticación requerida.")
        url = f"{self.base_url}/sync/initialize"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        with httpx.Client() as client:
            response = client.post(url, headers=headers, timeout=120.0) # Timeout más largo
        response.raise_for_status()
        return response.json()

    def push_records(self, push_data: dict) -> dict:
        """Envía un paquete de registros locales a la nube para fusionarlos."""
        if not self.auth_token: raise Exception("Autenticación requerida.")
        url = f"{self.base_url}/sync/push-records"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=push_data, timeout=120.0)
        response.raise_for_status()
        return response.json()

    def pull_db_file(self, key_path: str, local_destination: Path):
        """Descarga un archivo de DB desde el endpoint de pull."""
        if not self.auth_token: raise Exception("Autenticación requerida.")
        url = f"{self.base_url}/sync/pull-db/{key_path}"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        local_destination.parent.mkdir(parents=True, exist_ok=True)
        
        with httpx.stream("GET", url, headers=headers, timeout=120.0) as response:
            response.raise_for_status()
            with open(local_destination, "wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
        print(f"✅ Descarga completa: {key_path}")