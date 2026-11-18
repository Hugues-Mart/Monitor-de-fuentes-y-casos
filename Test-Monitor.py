import asyncio
import os
import random
import sqlite3
from datetime import datetime

RUTA_BD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "monitor.db")
TIMEOUT = 2.0
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


def subir_nivel(nivel):
    return NIVELES[min(NIVELES.index(nivel) + 1, len(NIVELES) - 1)]


def calcular_prioridad(fuente, total_caidos):
    nivel = FUENTES[fuente][0]
    return subir_nivel(nivel) if total_caidos > 1 else nivel


async def consultar(prob_falla, retraso_max):
    await asyncio.sleep(random.uniform(0.1, retraso_max))
    if random.random() < prob_falla:
        raise ConnectionError
    return "ok"


async def consultar_con_timeout(nombre):
    _, prob_falla, retraso_max = FUENTES[nombre]
    try:
        estado = await asyncio.wait_for(consultar(prob_falla, retraso_max), TIMEOUT)
    except asyncio.TimeoutError:
        estado = "timeout"
    except ConnectionError:
        estado = "caido"
    return nombre, estado


async def consultar_todas():
    return await asyncio.gather(*(consultar_con_timeout(n) for n in FUENTES))


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
    return conn


def registrar_caso(conn, fuente, descripcion, categoria, prioridad):
    with conn:
        cur = conn.execute(
            "INSERT INTO casos (fuente, descripcion, categoria, prioridad, fecha) VALUES (?, ?, ?, ?, ?)",
            (fuente, descripcion, categoria, prioridad, datetime.now().isoformat(timespec="seconds")),
        )
    return cur.lastrowid


def listar_casos(conn, estado=None):
    consulta = "SELECT * FROM casos "
    parametros = ()
    if estado:
        consulta += "WHERE estado = ? "
        parametros = (estado,)
    consulta += "ORDER BY CASE prioridad WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END, fecha DESC"
    return conn.execute(consulta, parametros).fetchall()


def resolver_caso(conn, caso_id):
    with conn:
        cur = conn.execute(
            "UPDATE casos SET estado = 'resuelto' WHERE id = ? AND estado = 'abierto'", (caso_id,)
        )
    return cur.rowcount > 0


def tiene_caso_abierto(conn, fuente, categoria):
    fila = conn.execute(
        "SELECT 1 FROM casos WHERE fuente = ? AND categoria = ? AND estado = 'abierto'",
        (fuente, categoria),
    ).fetchone()
    return fila is not None


def mostrar_casos(casos):
    if not casos:
        print("No hay casos.")
        return
    print(f"{'ID':<4} {'Prioridad':<10} {'Fuente':<18} {'Categoría':<13} {'Estado':<9} {'Descripción':<22} Fecha")
    for c in casos:
        print(
            f"{c['id']:<4} {c['prioridad']:<10} {c['fuente']:<18} {c['categoria']:<13} "
            f"{c['estado']:<9} {c['descripcion']:<22} {c['fecha']}"
        )


def opcion_consultar(conn):
    resultados = asyncio.run(consultar_todas())
    for nombre, estado in resultados:
        print(f"  {nombre:<18} {estado}")
    caidas = [(n, e) for n, e in resultados if e != "ok"]
    nuevos = 0
    for nombre, estado in caidas:
        categoria = "conectividad" if estado == "caido" else "lentitud"
        if tiene_caso_abierto(conn, nombre, categoria):
            continue
        descripcion = "No responde" if estado == "caido" else f"Tardó más de {TIMEOUT:.0f} s"
        registrar_caso(conn, nombre, descripcion, categoria, calcular_prioridad(nombre, len(caidas)))
        nuevos += 1
    print(f"\nFallas: {len(caidas)} | Casos nuevos: {nuevos}")


def opcion_registrar(conn):
    nombres = list(FUENTES)
    for i, nombre in enumerate(nombres, 1):
        print(f"  {i}. {nombre}")
    eleccion = input("Fuente (número): ").strip()
    if not eleccion.isdigit() or not 1 <= int(eleccion) <= len(nombres):
        print("Opción no válida.")
        return
    fuente = nombres[int(eleccion) - 1]
    descripcion = input("Descripción: ").strip()
    if not descripcion:
        print("La descripción no puede estar vacía.")
        return
    categoria = input("Categoría (Enter = otro): ").strip() or "otro"
    prioridad = calcular_prioridad(fuente, 1)
    caso = registrar_caso(conn, fuente, descripcion, categoria, prioridad)
    print(f"Caso {caso} registrado con prioridad {prioridad}.")


def opcion_resolver(conn):
    abiertos = listar_casos(conn, "abierto")
    mostrar_casos(abiertos)
    if not abiertos:
        return
    texto = input("ID del caso a resolver: ").strip()
    if texto.isdigit() and resolver_caso(conn, int(texto)):
        print("Caso resuelto.")
    else:
        print("No hay un caso abierto con ese ID.")


def main():
    conn = conectar()
    while True:
        print("\n1. Consultar fuentes y registrar fallas")
        print("2. Ver casos abiertos")
        print("3. Registrar un caso")
        print("4. Resolver un caso")
        print("5. Ver historial")
        print("0. Salir")
        try:
            opcion = input("Opción: ").strip()
        except EOFError:
            break
        print()
        if opcion == "1":
            opcion_consultar(conn)
        elif opcion == "2":
            mostrar_casos(listar_casos(conn, "abierto"))
        elif opcion == "3":
            opcion_registrar(conn)
        elif opcion == "4":
            opcion_resolver(conn)
        elif opcion == "5":
            mostrar_casos(listar_casos(conn))
        elif opcion == "0":
            break
        else:
            print("Opción no válida.")
    conn.close()


if __name__ == "__main__":
    main()