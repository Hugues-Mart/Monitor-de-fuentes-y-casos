import sqlite3
from datetime import datetime
from .config import RUTA_BD


def conectar():
    conn = sqlite3.connect(RUTA_BD)
    conn.row_factory = sqlite3.Row
    
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS casos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fuente TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            categoria TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'abierto' CHECK (estado IN ('abierto', 'resuelto')),
            prioridad TEXT NOT NULL CHECK (prioridad IN ('baja', 'media', 'alta')),
            fecha TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concepto TEXT NOT NULL,
            monto REAL NOT NULL CHECK (monto > 0),
            vencimiento TEXT NOT NULL,
            pagada INTEGER NOT NULL DEFAULT 0 CHECK (pagada IN (0, 1)),
            fecha TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            sal BLOB NOT NULL,
            clave BLOB NOT NULL,
            fecha TEXT NOT NULL)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sesiones (
            token TEXT PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            expira TEXT NOT NULL)"""
    )
    return conn


def registrar_caso(fuente, descripcion, categoria, prioridad):
    conn = conectar()
    with conn:
        cur = conn.execute(
            "INSERT INTO casos (fuente, descripcion, categoria, prioridad, fecha) VALUES (?, ?, ?, ?, ?)",
            (fuente, descripcion, categoria, prioridad, datetime.now().isoformat(timespec="seconds")),
        )
    conn.close()
    return cur.lastrowid


def listar_casos(estado=None):
    conn = conectar()
    consulta = "SELECT * FROM casos "
    params = ()
    if estado:
        consulta += "WHERE estado = ? "
        params = (estado,)
    consulta += "ORDER BY CASE prioridad WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END, fecha DESC"
    filas = [dict(f) for f in conn.execute(consulta, params).fetchall()]
    conn.close()
    return filas


def resolver_caso(caso_id):
    conn = conectar()
    with conn:
        cur = conn.execute(
            "UPDATE casos SET estado = 'resuelto' WHERE id = ? AND estado = 'abierto'", (caso_id,)
        )
    conn.close()
    return cur.rowcount > 0


def tiene_caso_abierto(fuente, categoria):
    conn = conectar()
    fila = conn.execute(
        "SELECT 1 FROM casos WHERE fuente = ? AND categoria = ? AND estado = 'abierto'",
        (fuente, categoria),
    ).fetchone()
    conn.close()
    return fila is not None


def registrar_factura(concepto, monto, vencimiento):
    conn = conectar()
    with conn:
        cur = conn.execute(
            "INSERT INTO facturas (concepto, monto, vencimiento, fecha) VALUES (?, ?, ?, ?)",
            (concepto, monto, vencimiento, datetime.now().isoformat(timespec="seconds")),
        )
    conn.close()
    return cur.lastrowid


def listar_facturas():
    conn = conectar()
    filas = [dict(f) for f in conn.execute("SELECT * FROM facturas").fetchall()]
    conn.close()
    return filas


def pagar_factura(factura_id):
    conn = conectar()
    with conn:
        cur = conn.execute(
            "UPDATE facturas SET pagada = 1 WHERE id = ? AND pagada = 0", (factura_id,)
        )
    conn.close()
    return cur.rowcount > 0
