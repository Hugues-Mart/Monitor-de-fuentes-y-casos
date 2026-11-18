import asyncio
import time
from datetime import date, datetime
from unittest.mock import patch

import pytest

from src.core.consulta import consultar_con_timeout, consultar_todas
from src.core.prioridad import prioridad_dispositivo, prioridad_factura, subir_nivel

HOY = date(2026, 11, 9)


def estados(resultados):
    return {r["fuente"]: r["estado"] for r in resultados}


@pytest.mark.parametrize("valor", [None, 2.5, "3", [], True, False])
def test_total_caidos_con_tipos_invalidos(valor):
    with pytest.raises(ValueError):
        prioridad_dispositivo("router", valor)


@pytest.mark.parametrize("fuente", [None, "", "Router", "ROUTER", 5])
def test_fuente_desconocida(fuente):
    with pytest.raises(ValueError):
        prioridad_dispositivo(fuente, 1)


@pytest.mark.parametrize("nivel", ["maxima", "", "ALTA", None])
def test_subir_nivel_invalido(nivel):
    with pytest.raises(ValueError):
        subir_nivel(nivel)


def test_subir_nivel_en_cadena_se_detiene_en_alta():
    nivel = "baja"
    for _ in range(5):
        nivel = subir_nivel(nivel)
    assert nivel == "alta"


@pytest.mark.parametrize("monto", [True, None, [], "100", "", {}])
def test_monto_con_tipos_invalidos(monto):
    with pytest.raises(ValueError):
        prioridad_factura(date(2026, 11, 20), monto, False, HOY)


@pytest.mark.parametrize("vencimiento", [20261120, 1.5, [], "", object()])
def test_vencimiento_con_tipos_invalidos(vencimiento):
    with pytest.raises(ValueError):
        prioridad_factura(vencimiento, 100, False, HOY)


def test_fecha_con_hora_se_trata_como_fecha():
    assert prioridad_factura(datetime(2026, 11, 10, 23, 59), 100, False, HOY) == "alta"


def test_monto_infinito_vencido_es_maxima():
    assert prioridad_factura(date(2026, 11, 1), float("inf"), False, HOY) == "maxima"


def test_monto_infinito_negativo_se_rechaza():
    with pytest.raises(ValueError):
        prioridad_factura(date(2026, 11, 20), float("-inf"), False, HOY)


def test_factura_pagada_con_monto_negativo_tambien_se_rechaza():
    with pytest.raises(ValueError):
        prioridad_factura(date(2026, 11, 20), -1, True, HOY)


def test_monto_alto_personalizado():
    assert prioridad_factura(date(2026, 11, 1), 50, False, HOY, monto_alto=50) == "maxima"


def test_fuente_que_siempre_falla_no_lanza_excepcion():
    res = asyncio.run(consultar_con_timeout("x", 1.0, 0.2))
    assert res == {"fuente": "x", "estado": "caido"}


def test_fuente_confiable_responde_ok():
    res = asyncio.run(consultar_con_timeout("x", 0.0, 0.2))
    assert res == {"fuente": "x", "estado": "ok"}


def test_el_timeout_gana_sobre_el_fallo():
    res = asyncio.run(consultar_con_timeout("x", 1.0, 1.0, timeout=0.01))
    assert res == {"fuente": "x", "estado": "timeout"}


def test_timeout_muy_corto_marca_todas_como_timeout():
    fuentes = {"a": (0.0, 1.0), "b": (1.0, 1.0), "c": (0.5, 1.0)}
    res = asyncio.run(consultar_todas(fuentes, timeout=0.01))
    assert set(estados(res).values()) == {"timeout"}


def test_mezcla_de_estados_en_una_consulta():
    fuentes = {"a": (1.0, 0.2), "b": (0.0, 0.2), "c": (0.0, 2.0)}
    with patch("src.core.consulta.random.uniform", lambda minimo, maximo: maximo):
        res = asyncio.run(consultar_todas(fuentes, timeout=0.5))
    assert estados(res) == {"a": "caido", "b": "ok", "c": "timeout"}


def test_el_orden_de_los_resultados_sigue_el_de_las_fuentes():
    fuentes = {"z": (0.0, 0.2), "a": (0.0, 0.1), "m": (0.0, 0.3)}
    res = asyncio.run(consultar_todas(fuentes))
    assert [r["fuente"] for r in res] == ["z", "a", "m"]


def test_consulta_concurrente_tarda_menos_que_la_suma_de_las_esperas():
    fuentes = {f"f{i}": (0.0, 0.3) for i in range(5)}
    with patch("src.core.consulta.random.uniform", lambda minimo, maximo: maximo):
        inicio = time.perf_counter()
        asyncio.run(consultar_todas(fuentes))
        total = time.perf_counter() - inicio
    assert total < 1.0
