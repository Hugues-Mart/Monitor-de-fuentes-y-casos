import sqlite3
from datetime import datetime
from unittest.mock import patch

import pytest

from src.core.prioridad import CRITICIDAD, prioridad_dispositivo
from src.db import base_datos as bd


def nueva_bd():
    conn = bd.conectar(":memory:")
    ids = {n: bd.agregar_dispositivo(conn, n, c) for n, c in CRITICIDAD.items()}
    return conn, ids


def registrar_en(conn, fecha, dispositivo_id, descripcion, prioridad):
    with patch.object(bd, "_ahora", return_value=fecha):
        return bd.registrar_caso(conn, dispositivo_id, descripcion, "conectividad", prioridad)


def test_sin_casos_la_lista_esta_vacia():
    conn, _ = nueva_bd()
    assert bd.listar_casos(conn) == []


def test_los_ids_de_los_casos_son_consecutivos():
    conn, ids = nueva_bd()
    nuevos = [
        bd.registrar_caso(conn, ids["router"], f"falla {i}", "conectividad", "media")
        for i in range(3)
    ]
    assert nuevos == [1, 2, 3]


def test_el_caso_devuelve_todos_los_campos():
    conn, ids = nueva_bd()
    bd.registrar_caso(conn, ids["router"], "sin respuesta", "conectividad", "media")
    caso = bd.listar_casos(conn)[0]
    assert set(caso.keys()) == {
        "id", "dispositivo", "descripcion", "categoria", "estado", "prioridad", "fecha",
    }
    assert caso["categoria"] == "conectividad"
    assert caso["descripcion"] == "sin respuesta"


def test_la_fecha_se_guarda_en_formato_iso():
    conn, ids = nueva_bd()
    bd.registrar_caso(conn, ids["router"], "x", "conectividad", "media")
    fecha = bd.listar_casos(conn)[0]["fecha"]
    assert isinstance(datetime.fromisoformat(fecha), datetime)


def test_el_caso_nuevo_queda_abierto():
    conn, ids = nueva_bd()
    bd.registrar_caso(conn, ids["router"], "x", "conectividad", "media")
    assert len(bd.listar_casos(conn, estado="abierto")) == 1
    assert bd.listar_casos(conn, estado="resuelto") == []


def test_estado_inexistente_devuelve_lista_vacia():
    conn, ids = nueva_bd()
    bd.registrar_caso(conn, ids["router"], "x", "conectividad", "media")
    assert bd.listar_casos(conn, estado="cerrado") == []


@pytest.mark.parametrize("campo", ["descripcion", "categoria"])
def test_campos_obligatorios_no_aceptan_nulos(campo):
    conn, ids = nueva_bd()
    datos = {"descripcion": "x", "categoria": "conectividad"}
    datos[campo] = None
    with pytest.raises(sqlite3.IntegrityError):
        bd.registrar_caso(conn, ids["router"], datos["descripcion"], datos["categoria"], "media")
    assert bd.listar_casos(conn) == []


def test_varios_casos_del_mismo_dispositivo():
    conn, ids = nueva_bd()
    for i in range(3):
        bd.registrar_caso(conn, ids["impresora"], f"falla {i}", "conectividad", "baja")
    casos = bd.listar_casos(conn)
    assert len(casos) == 3
    assert {c["dispositivo"] for c in casos} == {"impresora"}


def test_orden_por_prioridad_y_luego_por_fecha_reciente():
    conn, ids = nueva_bd()
    registrar_en(conn, "2026-11-09T08:00:00", ids["impresora"], "b1", "baja")
    registrar_en(conn, "2026-11-09T08:00:00", ids["servidor_archivos"], "a1", "alta")
    registrar_en(conn, "2026-11-09T09:00:00", ids["servidor_archivos"], "a2", "alta")
    registrar_en(conn, "2026-11-09T07:00:00", ids["router"], "m1", "media")
    registrar_en(conn, "2026-11-09T10:00:00", ids["impresora"], "b2", "baja")
    orden = [c["descripcion"] for c in bd.listar_casos(conn)]
    assert orden == ["a2", "a1", "m1", "b2", "b1"]


def test_resolver_un_caso_no_afecta_a_los_demas():
    conn, ids = nueva_bd()
    primero = bd.registrar_caso(conn, ids["router"], "uno", "conectividad", "media")
    bd.registrar_caso(conn, ids["router"], "dos", "conectividad", "media")
    bd.resolver_caso(conn, primero)
    abiertos = bd.listar_casos(conn, estado="abierto")
    assert [c["descripcion"] for c in abiertos] == ["dos"]


def test_los_casos_resueltos_siguen_en_el_historial():
    conn, ids = nueva_bd()
    caso = bd.registrar_caso(conn, ids["router"], "uno", "conectividad", "media")
    bd.resolver_caso(conn, caso)
    historial = bd.listar_casos(conn)
    assert len(historial) == 1
    assert historial[0]["estado"] == "resuelto"


def test_registrar_fallas_con_la_prioridad_calculada():
    conn, ids = nueva_bd()
    fallas = ["servidor_archivos", "impresora"]
    for fuente in fallas:
        prioridad = prioridad_dispositivo(fuente, len(fallas))
        bd.registrar_caso(conn, ids[fuente], "Estado: caido", "conectividad", prioridad)
    guardadas = {c["dispositivo"]: c["prioridad"] for c in bd.listar_casos(conn)}
    assert guardadas == {"servidor_archivos": "alta", "impresora": "media"}


def test_un_caso_fallido_no_deja_registros_a_medias():
    conn, ids = nueva_bd()
    with pytest.raises(sqlite3.IntegrityError):
        bd.registrar_caso(conn, 999, "x", "conectividad", "media")
    bd.registrar_caso(conn, ids["router"], "bueno", "conectividad", "media")
    assert len(bd.listar_casos(conn)) == 1
