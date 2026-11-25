from datetime import date
from .config import DIAS_ALERTA, MONTO_ALTO

ORDEN = {"maxima": 0, "alta": 1, "baja": 2}


def calcular_prioridad_factura(monto, vencimiento, pagada, hoy=None):
    if pagada:
        return None
    hoy = hoy or date.today()
    dias = (vencimiento - hoy).days
    if dias < 0 and monto >= MONTO_ALTO:
        return "maxima"
    if dias < DIAS_ALERTA:
        return "alta"
    return "baja"


def armar_cola(filas, hoy=None):
    hoy = hoy or date.today()
    cola = []
    for f in filas:
        venc = date.fromisoformat(f["vencimiento"])
        prioridad = calcular_prioridad_factura(f["monto"], venc, bool(f["pagada"]), hoy)
        if prioridad is None:
            continue
        cola.append({**f, "prioridad": prioridad, "dias": (venc - hoy).days})
    cola.sort(key=lambda f: (ORDEN[f["prioridad"]], f["vencimiento"]))
    return cola
