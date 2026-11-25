import re
from .config import MENU

_PATRON = re.compile(r"^\d+(\s*[+\-*]\s*\d+)*$")


def interpretar_opcion(texto):
    """Devuelve (opcion, error). Acepta un número o una suma/resta/multiplicación
    cuyo resultado coincida con una opción del menú. Ej: '1+1' -> 2, '3*0' -> 0."""
    texto = (texto or "").strip()
    if not texto:
        return None, "Escribe una opción."
    if "-" in texto and (texto.startswith("-") or re.search(r"[+\-*]\s*-", texto)):
        return None, "Valor negativo no válido. Sigues en el menú."
    if not _PATRON.match(texto):
        return None, "Entrada no válida. Usa números y + - * solamente."
    # Evaluación segura: el patrón ya garantiza que solo hay dígitos y + - *
    resultado = eval(texto, {"__builtins__": {}}, {})
    if resultado < 0:
        return None, f"El resultado ({resultado}) es negativo: no válido. Sigues en el menú."
    if resultado not in MENU:
        return None, f"El resultado ({resultado}) no corresponde a ninguna opción."
    return resultado, None
