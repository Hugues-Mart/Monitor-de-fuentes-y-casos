import asyncio
import random
from .config import FUENTES, NIVELES, TIMEOUT
from . import db


def calcular_prioridad(fuente, total_caidos):
    nivel = FUENTES[fuente][0]
    if total_caidos > 1:
        return NIVELES[min(NIVELES.index(nivel) + 1, len(NIVELES) - 1)]
    return nivel


async def _consultar(prob_falla, retraso_max):
    await asyncio.sleep(random.uniform(0.1, retraso_max))
    if random.random() < prob_falla:
        raise ConnectionError
    return "ok"


async def _con_timeout(nombre):
    _, prob, retraso = FUENTES[nombre]
    try:
        estado = await asyncio.wait_for(_consultar(prob, retraso), TIMEOUT)
    except asyncio.TimeoutError:
        estado = "timeout"
    except ConnectionError:
        estado = "caido"
    return nombre, estado


async def consultar_y_registrar():
    resultados = await asyncio.gather(*(_con_timeout(n) for n in FUENTES))
    caidas = [(n, e) for n, e in resultados if e != "ok"]
    nuevos = 0
    for nombre, estado in caidas:
        categoria = "conectividad" if estado == "caido" else "lentitud"
        if db.tiene_caso_abierto(nombre, categoria):
            continue
        desc = "No responde" if estado == "caido" else f"Tardó más de {TIMEOUT:.0f} s"
        db.registrar_caso(nombre, desc, categoria, calcular_prioridad(nombre, len(caidas)))
        nuevos += 1
    return {
        "fuentes": [{"nombre": n, "estado": e} for n, e in resultados],
        "fallas": len(caidas),
        "nuevos": nuevos,
    }
