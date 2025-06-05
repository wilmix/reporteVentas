"""
Módulo para consultar totales de ventas por sucursal y general desde la API de Hergo.
"""
import requests
import os
from datetime import datetime, timedelta

class HergoAPI:
    """
    Cliente para consultar ventas de Hergo con sesión autenticada y cabeceras AJAX.
    """
    LOGIN_URL = "https://hergo.app/index.php/auth/login"
    API_URL = "https://hergo.app/index.php/Reportes/mostrarVentasLineaMes"
    PRINCIPAL_URL = "https://hergo.app/principal"
    REPORTES_URL = "https://hergo.app/reportes/resumenVentasLineaMes"
    SUCURSALES = {
        'CENTRAL': 0,
        'SANTA CRUZ': 5,
        'POTOSI': 6,
    }

    def __init__(self, usuario=None, password=None):
        self.usuario = usuario or os.environ.get("HERGO_USER")
        self.password = password or os.environ.get("HERGO_PASS")
        if not self.usuario or not self.password:
            raise ValueError("Credenciales de Hergo no configuradas. Usa argumentos o variables de entorno HERGO_USER y HERGO_PASS.")
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": self.LOGIN_URL,
            "X-Requested-With": "XMLHttpRequest"
        }
        self._login_and_navigate()

    def _login_and_navigate(self):
        login_payload = {"identity": self.usuario, "password": self.password}
        resp = self.session.post(self.LOGIN_URL, data=login_payload, headers=self.headers)
        if resp.status_code != 200 or "error" in resp.text.lower():
            raise RuntimeError("No se pudo iniciar sesión en Hergo. Verifica credenciales.")
        # Simular navegación previa
        self.session.get(self.PRINCIPAL_URL, headers=self.headers)
        self.session.get(self.REPORTES_URL, headers=self.headers)

    def get_sales_totals(self, year, month=None, sucursal=None):
        if month is None:
            inicio = f"{year}-01-01"
            fin = f"{year}-12-31"
        else:
            inicio = f"{year}-{int(month):02d}-01"
            if int(month) == 12:
                fin = f"{year}-12-31"
            else:
                next_month = datetime(year, int(month), 1).replace(day=28) + timedelta(days=4)
                last_day = (next_month - timedelta(days=next_month.day)).day
                fin = f"{year}-{int(month):02d}-{last_day}"
        data = {
            'inicio': inicio,
            'fin': fin,
            'sucursal': '' if sucursal is None else str(sucursal)
        }
        try:
            resp = self.session.post(self.API_URL, data=data, headers=self.headers, timeout=20)
            resp.raise_for_status()
            ventas = resp.json()
            # Buscar la fila resumen (Sigla is None)
            total = 0.0
            for linea in ventas:
                if linea.get('Sigla') is None:
                    try:
                        total = float(linea.get('total', 0) or 0)
                    except Exception:
                        pass
                    break
            return {'total': total, 'detalle': ventas}
        except Exception as e:
            return {'total': None, 'detalle': [], 'error': f"Error consultando API Hergo: {e}"}

# Para compatibilidad con el código existente:
def get_hergo_sales_totals(year, month=None, sucursal=None, usuario=None, password=None):
    """
    Consulta el total de ventas por sucursal o general desde la API de Hergo usando sesión autenticada.
    """
    api = HergoAPI(usuario=usuario, password=password)
    return api.get_sales_totals(year, month, sucursal)
