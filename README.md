# Monitor de fuentes y casos

Proyecto final de Programación Avanzada A1. Es una aplicación web que revisa el estado de varios equipos y pasarelas de pago al mismo tiempo, registra cada falla como un caso, ordena los casos según su urgencia y guarda el historial para consultarlo.

## Problema que resuelve

hay equipos, impresoras y servidores que fallan sin que nadie lo note a tiempo, y los cobros se pierden de vista entre distintos canales. El encargado de soporte se entera de una falla solo cuando alguien se queja y tiene que revisar equipo por equipo.

## Qué hace

- Consulta varias fuentes en paralelo con `asyncio`, aunque alguna falle o se demore (cada consulta tiene un tiempo límite).
- Registra cada falla como un caso con descripción, categoría, estado y prioridad.
- No duplica casos: si ya hay uno abierto para la misma fuente y categoría, no crea otro.
- Calcula la prioridad con una función pura (`calcular_prioridad`).
- Guarda el historial en una base de datos SQLite (`monitor.db`).
- Permite ver casos abiertos, registrar un caso a mano, resolverlo y consultar el historial.
- Interfaz web con menú en tarjetas, contadores de casos abiertos y estado de las fuentes en vivo.
- Validación de la opción del menú: los valores negativos son inválidos y el usuario se queda en el menú. También se puede escribir una suma, resta o multiplicación cuyo resultado sea una opción (por ejemplo `1+1` abre la opción 2 y `5-5` la opción 0, salir).

## Fuentes monitoreadas (simuladas)

**Dispositivos**

| Fuente | Criticidad base |
|---|---|
| Servidor de archivos | Alta |
| Router / switch | Media |
| Equipo de práctica | Media |
| Impresora | Baja |

**Pagos**

| Fuente | Criticidad base |
|---|---|
| Pasarela A (cobros en línea) | Alta |
| Pasarela B (cobros alternativos) | Media |
| Banco simulado (transferencias) | Media |

Las fuentes son simuladas, con fallas y retrasos aleatorios, para poder demostrar el funcionamiento. Todas comparten el mismo motor de consulta, las mismas reglas de prioridad y la misma base de datos.


## Reglas de prioridad

**Dispositivos**
- Servidor caído: prioridad alta.
- Impresora sin respuesta: prioridad baja.
- Si hay más de un dispositivo caído a la vez, la prioridad sube un nivel.

**Facturas**
- Vencida y con monto alto: prioridad máxima.
- Vence en menos de 3 días: prioridad alta.
- Pagada: sale de la cola.

## Estructura del proyecto

```
monitor/
├── app/
│   ├── main.py
│   ├── menu.py
│   ├── monitor.py
│   ├── db.py
│   └── config.py
├── static/
│   └── index.html
├── requirements.txt
├── .env.example
└── .gitignore
```

**Dónde se guarda cada listado**

- Casos: tabla `casos` de `monitor.db` (SQLite), creada en `app/db.py` → `conectar()`.
- Opciones del menú: diccionario `MENU` en `app/config.py`.
- Fuentes monitoreadas: diccionario `FUENTES` en `app/config.py`.

  ## Instalación y ejecución

Requisitos: Python 3.10 o superior.

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --reload
```

Abrir en el navegador: http://127.0.0.1:8000 (la documentación automática de la API está en `/docs`).

El servidor debe quedar corriendo mientras se usa la página. Para detenerlo, `Ctrl + C`.

**Variables de entorno (`.env`)**

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `RUTA_BD` | Archivo de la base de datos | `monitor.db` |
| `TIMEOUT` | Segundos máximos de espera por fuente | `2.0` |

## Uso de IA

Se usó **Claude** (Anthropic) como apoyo en estas partes del proyecto:

- Convertir la versión de consola en una API con FastAPI y una interfaz web.
- Escribir la validación de la opción del menú (`app/menu.py`).
- Diseñar la interfaz (`static/index.html`).

## Avance del proyecto

- [X]  consulta concurrente de fuentes simuladas con `asyncio`
- [X]  comparación entre hilos, procesos y `asyncio`
- [X]  funciones para clasificar y priorizar
- [X]  pruebas con entradas inesperadas y fallos de red
- [X]  base de datos con SQLite
- [X]  registrar y consultar casos
- [ ]  integración y presentación final
