# src/core/utils.py
import sys
import subprocess
import os
from getmac import get_mac_address

def resource_path(relative_path):
    """ Obtiene la ruta absoluta al recurso, funciona para desarrollo y para PyInstaller """
    try:
        # PyInstaller crea una carpeta temporal y guarda la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # En desarrollo, la base es la raíz del proyecto, pero los assets están en 'src'
        base_path = os.path.abspath("./src")

    return os.path.join(base_path, relative_path)

def get_network_identifiers():
    """Obtiene identificadores de la red local (MAC del Gateway y SSID de WiFi)."""
    identifiers = {"gateway_mac": None, "ssid": None}
    try:
        # Obtener MAC del Gateway (router) es muy fiable para redes cableadas y WiFi
        identifiers["gateway_mac"] = get_mac_address(interface="Ethernet") or get_mac_address(interface="Wi-Fi")
    except Exception as e:
        print(f"No se pudo obtener la MAC del gateway: {e}")

    try:
        # Para WiFi, el SSID es un excelente identificador
        if sys.platform == "win32":
            result = subprocess.check_output(["netsh", "wlan", "show", "interfaces"])
            for line in result.decode("utf-8").split("\\n"):
                if "SSID" in line and ":" in line:
                    identifiers["ssid"] = line.split(":")[1].strip()
                    break
    except Exception as e:
        print(f"No se pudo obtener el SSID: {e}")

    return identifiers