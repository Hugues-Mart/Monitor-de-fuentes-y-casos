import os
from datetime import date
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import auth, db, facturas, monitor
from .config import BASE, FUENTES, MENU
from .menu import interpretar_opcion

app = FastAPI(title="Monitor de fuentes y casos")
app.include_router(auth.router)
app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")


class Entrada(BaseModel):
    texto: str


class NuevoCaso(BaseModel):
    fuente: str
    descripcion: str
    categoria: str = "otro"


@app.get("/")
def inicio():
    return FileResponse(os.path.join(BASE, "static", "index.html"))


@app.get("/api/menu", dependencies=[Depends(auth.requerir)])
def ver_menu():
    return {"menu": MENU, "fuentes": list(FUENTES)}


@app.post("/api/opcion", dependencies=[Depends(auth.requerir)])
def validar_opcion(e: Entrada):
    opcion, error = interpretar_opcion(e.texto)
    if error:
        return {"valida": False, "mensaje": error}
    return {"valida": True, "opcion": opcion, "nombre": MENU[opcion]}


@app.post("/api/consultar", dependencies=[Depends(auth.requerir)])
async def consultar():
    return await monitor.consultar_y_registrar()


@app.get("/api/casos", dependencies=[Depends(auth.requerir)])
def casos(estado: str | None = None):
    if estado not in (None, "abierto", "resuelto"):
        raise HTTPException(400, "Estado no válido")
    return db.listar_casos(estado)


@app.post("/api/casos", dependencies=[Depends(auth.requerir)])
def crear(c: NuevoCaso):
    if c.fuente not in FUENTES:
        raise HTTPException(400, "Fuente no válida")
    if not c.descripcion.strip():
        raise HTTPException(400, "La descripción no puede estar vacía")
    prioridad = monitor.calcular_prioridad(c.fuente, 1)
    caso_id = db.registrar_caso(c.fuente, c.descripcion.strip(), c.categoria.strip() or "otro", prioridad)
    return {"id": caso_id, "prioridad": prioridad}


@app.post("/api/casos/{caso_id}/resolver", dependencies=[Depends(auth.requerir)])
def resolver(caso_id: int):
    if not db.resolver_caso(caso_id):
        raise HTTPException(404, "No hay un caso abierto con ese ID")
    return {"ok": True}


class NuevaFactura(BaseModel):
    concepto: str
    monto: float
    vencimiento: str


@app.get("/api/facturas", dependencies=[Depends(auth.requerir)])
def cola_facturas():
    return facturas.armar_cola(db.listar_facturas())


@app.post("/api/facturas", dependencies=[Depends(auth.requerir)])
def crear_factura(f: NuevaFactura):
    if not f.concepto.strip():
        raise HTTPException(400, "El concepto no puede estar vacío")
    if f.monto <= 0:
        raise HTTPException(400, "El monto no es válido: debe ser mayor que cero")
    try:
        venc = date.fromisoformat(f.vencimiento)
    except ValueError:
        raise HTTPException(400, "La fecha de vencimiento no es válida")
    factura_id = db.registrar_factura(f.concepto.strip(), f.monto, venc.isoformat())
    prioridad = facturas.calcular_prioridad_factura(f.monto, venc, False)
    return {"id": factura_id, "prioridad": prioridad}


@app.post("/api/facturas/{factura_id}/pagar", dependencies=[Depends(auth.requerir)])
def pagar(factura_id: int):
    if not db.pagar_factura(factura_id):
        raise HTTPException(404, "No hay una factura pendiente con ese ID")
    return {"ok": True}
