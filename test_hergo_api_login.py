import requests
import os
from dotenv import load_dotenv

# === CARGAR VARIABLES DE ENTORNO ===
load_dotenv()
USUARIO = os.environ.get("HERGO_USER")
PASSWORD = os.environ.get("HERGO_PASS")

if not USUARIO or not PASSWORD:
    raise RuntimeError("Faltan las variables de entorno HERGO_USER y/o HERGO_PASS.\nCrea un archivo .env en la raíz del proyecto con:\nHERGO_USER=tu_usuario@hergo.com.bo\nHERGO_PASS=tu_contraseña\n")

# === URLS ===
LOGIN_URL = "https://hergo.app/index.php/auth/login"
API_URL = "https://hergo.app/index.php/Reportes/mostrarVentasLineaMes"

# === HEADERS DE NAVEGADOR ===
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": LOGIN_URL,
    "X-Requested-With": "XMLHttpRequest"
}

# === DATOS DE CONSULTA ===
data_api = {
    "inicio": "2025-01-01",
    "fin": "2025-01-31",
    "sucursal": "0"  # Cambia a "" para total general
}

# === INICIAR SESIÓN ===
session = requests.Session()
login_payload = {
    "identity": USUARIO,
    "password": PASSWORD
}
session.post(LOGIN_URL, data=login_payload, headers=HEADERS)

# === SIMULAR NAVEGACIÓN PREVIA ===
principal_url = "https://hergo.app/principal"
reportes_url = "https://hergo.app/reportes/resumenVentasLineaMes"
session.get(principal_url, headers=HEADERS)
session.get(reportes_url, headers=HEADERS)

# === CONSULTAR API AUTENTICADO ===
api_resp = session.post(API_URL, data=data_api, headers=HEADERS)
try:
    ventas = api_resp.json()
    print(ventas)
except Exception as e:
    print("[ERROR] No se pudo parsear JSON de la respuesta de la API:", e)
