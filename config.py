import os
from dotenv import load_dotenv

load_dotenv()

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_BD = os.path.join(BASE, os.getenv("RUTA_BD", "monitor.db"))
TIMEOUT = float(os.getenv("TIMEOUT", "2.0"))
MONTO_ALTO = float(os.getenv("MONTO_ALTO", "1000000"))
DIAS_ALERTA = 3
SESION_HORAS = int(os.getenv("SESION_HORAS", "12"))
REGISTRO_ABIERTO = os.getenv("REGISTRO_ABIERTO", "1") == "1"
COOKIE_SEGURA = os.getenv("COOKIE_SEGURA", "0") == "1"  # pon 1 si usas HTTPS
NIVELES = ["baja", "media", "alta"]


FUENTES = {
    "servidor_archivos": ("alta", 0.2, 1.0),
    "router": ("media", 0.1, 0.5),
    "equipo_practica": ("media", 0.3, 1.5),
    "impresora": ("baja", 0.4, 2.5),
    "pasarela_a": ("alta", 0.2, 1.0),
    "pasarela_b": ("media", 0.3, 1.5),
    "banco_simulado": ("media", 0.1, 0.8),
}


MENU = {
    1: "Consultar fuentes y registrar fallas",
    2: "Ver casos abiertos",
    3: "Registrar un caso",
    4: "Resolver un caso",
    5: "Ver historial",
    6: "Facturas",
    0: "Salir",
}
