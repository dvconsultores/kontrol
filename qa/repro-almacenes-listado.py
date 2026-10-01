"""E2E-FLAKY-BAJO-CARGA · cuánto cuesta el listado de almacenes que cargan Picking y Put-away.

Las dos pantallas llenan su desplegable «Almacén» con el listado entero de la empresa. Este
guion mide, contra la aplicación real en proceso, cuántas sentencias SQL ejecuta una
petición a `GET /organization/warehouses` y cuánto tarda; y contra el backend levantado,
cuánto tarda esa misma petición sola y cuando llegan varias a la vez, que es lo que pasa
cuando la suite E2E corre con seis navegadores.

Uso (pila de QA arriba, base sembrada):
    KONTROL_DB_URL=postgresql+psycopg2://kontrol_migrator:qa@localhost:55432/kaud \
    PYTHONPATH=resources/backend resources/backend/.venv/bin/python qa/repro-almacenes-listado.py
"""
from __future__ import annotations

import json
import os
import statistics
import threading
import time
import urllib.request

os.environ.setdefault("KONTROL_SECRET_KEY", "qa-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")
os.environ.setdefault("KONTROL_COOKIE_SECURE", "false")
os.environ.setdefault("KONTROL_INSTALLATION_VOLUME_PATH", "/tmp/kontrol-kaud-license")
os.environ.setdefault("KONTROL_STORAGE_PATH", "/tmp/kontrol-kaud-storage")
os.environ.setdefault("KONTROL_BACKUP_PATH", "/tmp/kontrol-kaud-backups")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event  # noqa: E402

from app.core.database import get_engine  # noqa: E402
from app.main import create_app  # noqa: E402

PASSWORD = os.environ.get("KONTROL_E2E_PASSWORD", "Kontrol2026Segura!")
API = os.environ.get("KONTROL_E2E_API", "http://127.0.0.1:8000/api/v1")

engine = get_engine()
cliente = TestClient(create_app())
sentencias = [0]


@event.listens_for(engine, "before_cursor_execute")
def _contar(conn, cursor, statement, parameters, context, executemany):
    sentencias[0] += 1


r = cliente.post("/api/v1/auth/login", json={"tenant_code": "DEMO", "username": "admin", "password": PASSWORD})
assert r.status_code == 200, r.text
token = r.json()["access_token"]
empresa = cliente.get("/api/v1/organization/companies", headers={"Authorization": f"Bearer {token}"}).json()["items"][0]["id"]
cabeceras = {"Authorization": f"Bearer {token}", "X-Kontrol-Company": empresa}

print("== en proceso: sentencias SQL por petición ==")
total = 0
for ruta in ("/organization/warehouses?limit=1", "/organization/warehouses?limit=50",
             "/organization/warehouses?limit=200&offset=0", "/organization/warehouses?limit=500"):
    sentencias[0] = 0
    t0 = time.perf_counter()
    cuerpo = cliente.get(f"/api/v1{ruta}", headers=cabeceras).json()
    ms = (time.perf_counter() - t0) * 1000
    total = cuerpo["total"]
    n = len(cuerpo["items"])
    print(f"  GET {ruta:<44} items={n:>3} total={total} · sentencias={sentencias[0]:>5} "
          f"({sentencias[0] / max(n, 1):.1f} por almacén) · {ms:.0f} ms")
print(f"almacenes de la empresa: {total}")


def pedir(ruta: str) -> float:
    t0 = time.perf_counter()
    peticion = urllib.request.Request(f"{API}{ruta}", headers=cabeceras)
    with urllib.request.urlopen(peticion, timeout=120) as resp:
        json.load(resp)
    return (time.perf_counter() - t0) * 1000


def a_la_vez(ruta: str, cuantas: int) -> list[float]:
    tiempos: list[float] = []
    hilos = [threading.Thread(target=lambda: tiempos.append(pedir(ruta))) for _ in range(cuantas)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    return sorted(tiempos)


try:
    pedir("/organization/warehouses?limit=1")
except Exception as e:  # noqa: BLE001
    print(f"\n(backend en {API} no disponible: {type(e).__name__}; se omite la medida por HTTP)")
else:
    print(f"\n== por HTTP contra {API}: la misma petición, sola y con otras a la vez ==")
    for etiqueta, ruta in (("Put-away (limit=500)", "/organization/warehouses?limit=500"),
                           ("Picking, una tanda (limit=200)", "/organization/warehouses?limit=200&offset=0")):
        solas = sorted(pedir(ruta) for _ in range(3))
        print(f"  {etiqueta}")
        print(f"    1 petición ........ mediana {statistics.median(solas):.0f} ms")
        for cuantas in (3, 6):
            t = a_la_vez(ruta, cuantas)
            print(f"    {cuantas} a la vez ........ la más lenta {t[-1]:.0f} ms · mediana {statistics.median(t):.0f} ms")
    tandas = -(-total // 200)
    print(f"  Picking carga el desplegable con {tandas} tandas seguidas de 200: la opción del almacén recién creado")
    print("  no existe en la página hasta que termina la última.")
