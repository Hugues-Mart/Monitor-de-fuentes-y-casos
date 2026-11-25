import hashlib, hmac, re, secrets, time
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from . import db
from .config import COOKIE_SEGURA, REGISTRO_ABIERTO, SESION_HORAS

router = APIRouter(prefix="/api/auth")
_USUARIO = re.compile(r"^[a-z0-9_.-]{3,30}$")
_intentos = {}  


def _hash(clave, sal):
    return hashlib.scrypt(clave.encode(), salt=sal, n=2**14, r=8, p=1, dklen=32)


def _token_hash(t):
    return hashlib.sha256(t.encode()).hexdigest()


class Registro(BaseModel):
    nombre: str
    usuario: str
    clave: str


class Login(BaseModel):
    usuario: str
    clave: str


def _abrir_sesion(resp, uid):
    token = secrets.token_urlsafe(32)
    expira = datetime.now() + timedelta(hours=SESION_HORAS)
    conn = db.conectar()
    with conn:
        conn.execute("DELETE FROM sesiones WHERE expira < ?", (datetime.now().isoformat(),))
        conn.execute("INSERT INTO sesiones VALUES (?, ?, ?)", (_token_hash(token), uid, expira.isoformat()))
    conn.close()
    resp.set_cookie("sid", token, max_age=SESION_HORAS * 3600, httponly=True,
                    samesite="lax", secure=COOKIE_SEGURA)


def usuario_actual(request: Request):
    token = request.cookies.get("sid")
    if not token:
        return None
    conn = db.conectar()
    fila = conn.execute(
        "SELECT u.id, u.usuario, u.nombre FROM sesiones s JOIN usuarios u ON u.id = s.usuario_id "
        "WHERE s.token = ? AND s.expira > ?", (_token_hash(token), datetime.now().isoformat())).fetchone()
    conn.close()
    return dict(fila) if fila else None


def requerir(request: Request):
    u = usuario_actual(request)
    if not u:
        raise HTTPException(401, "Inicia sesión para continuar")
    return u


@router.get("/yo")
def yo(request: Request):
    return {"usuario": usuario_actual(request), "registro": REGISTRO_ABIERTO}


@router.post("/registro")
def registro(r: Registro, resp: Response):
    if not REGISTRO_ABIERTO:
        raise HTTPException(403, "El registro está cerrado")
    usuario, nombre = r.usuario.strip().lower(), r.nombre.strip()
    if not nombre or len(nombre) > 60:
        raise HTTPException(400, "Escribe tu nombre (máx. 60 caracteres)")
    if not _USUARIO.match(usuario):
        raise HTTPException(400, "Usuario: 3 a 30 caracteres (letras, números, . _ -)")
    if len(r.clave) < 8:
        raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres")
    sal = secrets.token_bytes(16)
    conn = db.conectar()
    try:
        with conn:
            cur = conn.execute("INSERT INTO usuarios (usuario, nombre, sal, clave, fecha) VALUES (?,?,?,?,?)",
                               (usuario, nombre, sal, _hash(r.clave, sal), datetime.now().isoformat(timespec="seconds")))
    except Exception:
        raise HTTPException(409, "Ese usuario ya existe")
    finally:
        conn.close()
    _abrir_sesion(resp, cur.lastrowid)
    return {"usuario": {"id": cur.lastrowid, "usuario": usuario, "nombre": nombre}}


@router.post("/login")
def login(r: Login, request: Request, resp: Response):
    usuario = r.usuario.strip().lower()
    llave = (request.client.host if request.client else "?", usuario)
    ahora = time.time()
    recientes = [t for t in _intentos.get(llave, []) if ahora - t < 300]
    if len(recientes) >= 5:
        raise HTTPException(429, "Demasiados intentos. Espera unos minutos.")
    conn = db.conectar()
    fila = conn.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario,)).fetchone()
    conn.close()
    sal = fila["sal"] if fila else b"\0" * 16  # mismo costo exista o no el usuario
    ok = hmac.compare_digest(_hash(r.clave, sal), fila["clave"] if fila else b"\0" * 32) and fila is not None
    if not ok:
        _intentos[llave] = recientes + [ahora]
        raise HTTPException(401, "Usuario o contraseña incorrectos")
    _intentos.pop(llave, None)
    _abrir_sesion(resp, fila["id"])
    return {"usuario": {"id": fila["id"], "usuario": fila["usuario"], "nombre": fila["nombre"]}}


@router.post("/logout")
def logout(request: Request, resp: Response):
    token = request.cookies.get("sid")
    if token:
        conn = db.conectar()
        with conn:
            conn.execute("DELETE FROM sesiones WHERE token = ?", (_token_hash(token),))
        conn.close()
    resp.delete_cookie("sid")
    return {"ok": True}
