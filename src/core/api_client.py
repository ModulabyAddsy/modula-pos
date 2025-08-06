# src/core/api_client.py
import httpx
import os

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

