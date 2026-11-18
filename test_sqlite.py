import os
import sqlite3
import tempfile
from datetime import date

import pytest

from src.db import base_datos as bd


def nueva_bd():
    return bd.conectar(":memory:")


def contar(conn, tabla):
    return conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]


def test_la_base_se_crea_en_disco_y_conserva_los_datos():
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = os.path.join(carpeta, "datos", "monitor.db")
        conn = bd.conectar(ruta)
        d = bd.agregar_dispositivo(conn, "router", "media")
        bd.registrar_caso(conn, d, "caído", "conectividad", "media")
        conn.close()
        existe = os.path.exists(ruta)
        conn = bd.conectar(ruta)
        casos = bd.listar_casos(conn)
        conn.close()
    assert existe
    assert len(casos) == 1
    assert casos[0]["dispositivo"] == "router"


def test_conectar_dos_veces_no_duplica_tablas():
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = os.path.join(carpeta, "monitor.db")
        bd.conectar(ruta).close()
        conn = bd.conectar(ruta)
        n = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'casos'"
        ).fetchone()[0]
        conn.close()
    assert n == 1


def test_las_claves_foraneas_estan_activadas():
    assert nueva_bd().execute("PRAGMA foreign_keys").fetchone()[0] == 1


@pytest.mark.parametrize("criticidad", ["critica", "", "ALTA", None])
def test_criticidad_invalida(criticidad):
    conn = nueva_bd()
    with pytest.raises(sqlite3.IntegrityError):
        bd.agregar_dispositivo(conn, "x", criticidad)
    assert contar(conn, "dispositivos") == 0


def test_nombre_de_dispositivo_nulo():
    conn = nueva_bd()
    with pytest.raises(sqlite3.IntegrityError):
        bd.agregar_dispositivo(conn, None, "baja")


def test_dispositivo_repetido_conserva_la_criticidad_original():
    conn = nueva_bd()
    a = bd.agregar_dispositivo(conn, "router", "media")
    b = bd.agregar_dispositivo(conn, "router", "alta")
    fila = conn.execute("SELECT criticidad FROM dispositivos WHERE id = ?", (a,)).fetchone()
    assert a == b
    assert fila["criticidad"] == "media"


def test_estado_invalido_se_rechaza():
    conn = nueva_bd()
    d = bd.agregar_dispositivo(conn, "router", "media")
    c = bd.registrar_caso(conn, d, "x", "conectividad", "media")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE casos SET estado = 'cerrado' WHERE id = ?", (c,))


def test_texto_con_comillas_y_sql_se_guarda_literal():
    conn = nueva_bd()
    nombre = "x'); DROP TABLE casos;--"
    d = bd.agregar_dispositivo(conn, nombre, "baja")
    bd.registrar_caso(conn, d, 'it\'s "raro"', "conectividad", "baja")
    casos = bd.listar_casos(conn)
    assert casos[0]["dispositivo"] == nombre
    assert casos[0]["descripcion"] == 'it\'s "raro"'


def test_texto_con_acentos_y_unicode():
    conn = nueva_bd()
    d = bd.agregar_dispositivo(conn, "equipo_práctica", "media")
    bd.registrar_caso(conn, d, "caído ñandú 日本", "conectividad", "media")
    assert bd.listar_casos(conn)[0]["descripcion"] == "caído ñandú 日本"


@pytest.mark.parametrize("monto", [0, -10])
def test_pago_con_monto_cero_o_negativo(monto):
    conn = nueva_bd()
    f = bd.agregar_factura(conn, "uso de impresión", 100, date(2026, 12, 1))
    with pytest.raises(sqlite3.IntegrityError):
        bd.registrar_pago(conn, f, "pasarela_a", monto)
    assert contar(conn, "pagos") == 0


def test_pago_a_factura_inexistente_no_deja_registros():
    conn = nueva_bd()
    with pytest.raises(sqlite3.IntegrityError):
        bd.registrar_pago(conn, 999, "pasarela_a", 10)
    assert contar(conn, "pagos") == 0


def test_sobrepago_marca_la_factura_como_pagada():
    conn = nueva_bd()
    f = bd.agregar_factura(conn, "uso de equipos", 100, date(2026, 12, 1))
    bd.registrar_pago(conn, f, "banco_simulado", 150)
    assert bd.listar_facturas_pendientes(conn) == []


def test_factura_con_monto_cero_es_valida():
    conn = nueva_bd()
    bd.agregar_factura(conn, "cortesía", 0, date(2026, 12, 1))
    assert len(bd.listar_facturas_pendientes(conn)) == 1


def test_facturas_pendientes_salen_por_vencimiento_y_sin_las_pagadas():
    conn = nueva_bd()
    tarde = bd.agregar_factura(conn, "tarde", 10, date(2026, 12, 20))
    pronto = bd.agregar_factura(conn, "pronto", 10, date(2026, 12, 1))
    medio = bd.agregar_factura(conn, "medio", 10, date(2026, 12, 10))
    pagada = bd.agregar_factura(conn, "pagada", 10, date(2026, 11, 1))
    bd.registrar_pago(conn, pagada, "pasarela_a", 10)
    pendientes = [f["concepto"] for f in bd.listar_facturas_pendientes(conn)]
    assert pendientes == ["pronto", "medio", "tarde"]
    assert {tarde, pronto, medio} == {f["id"] for f in bd.listar_facturas_pendientes(conn)}


def test_usar_una_conexion_cerrada_falla():
    conn = nueva_bd()
    conn.close()
    with pytest.raises(sqlite3.ProgrammingError):
        bd.listar_casos(conn)
