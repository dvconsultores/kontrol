"""AUDIT-TOTAL-CARGA-TODO · qué hace el listado de auditoría para saber su `total`.

Mide, contra la aplicación real en proceso y la base que se le indique, lo que una
petición a `GET /api/v1/audit/events` ejecuta: cuántas sentencias lanza sobre
`audit_events`, cuántas filas le devuelve la base, cuántas entidades `AuditEvent`
construye el ORM y cuánto tarda. No escribe nada salvo el evento del inicio de sesión.

Uso (base de QA sembrada):
    KONTROL_DB_URL=postgresql+psycopg2://kontrol_migrator:qa@localhost:55432/kaud \
    PYTHONPATH=resources/backend resources/backend/.venv/bin/python qa/repro-audit-total.py
"""
from __future__ import annotations

import os
import statistics
import time

os.environ.setdefault("KONTROL_SECRET_KEY", "qa-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")
os.environ.setdefault("KONTROL_COOKIE_SECURE", "false")
os.environ.setdefault("KONTROL_INSTALLATION_VOLUME_PATH", "/tmp/kontrol-kaud-license")
os.environ.setdefault("KONTROL_STORAGE_PATH", "/tmp/kontrol-kaud-storage")
os.environ.setdefault("KONTROL_BACKUP_PATH", "/tmp/kontrol-kaud-backups")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event, inspect, text  # noqa: E402

from app.core.database import get_engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.audit.models import AuditEvent  # noqa: E402

PASSWORD = os.environ.get("KONTROL_E2E_PASSWORD", "Kontrol2026Segura!")
REPETICIONES = 5
TAMANO = 10

engine = get_engine()
cliente = TestClient(create_app())

sentencias: list[dict] = []
cargadas = [0]


@event.listens_for(engine, "before_cursor_execute")
def _antes(conn, cursor, statement, parameters, context, executemany):
    context._inicio = time.perf_counter()


@event.listens_for(engine, "after_cursor_execute")
def _despues(conn, cursor, statement, parameters, context, executemany):
    if "audit_events" in statement and statement.lstrip().upper().startswith("SELECT"):
        sentencias.append({"sql": " ".join(statement.split()), "parametros": parameters,
                           "filas": cursor.rowcount, "ms": (time.perf_counter() - context._inicio) * 1000})


@event.listens_for(AuditEvent, "load")
def _carga(target, context):
    cargadas[0] += 1


def forma(sql: str) -> str:
    """La forma de la sentencia, sin la lista de columnas."""
    if sql.lower().startswith("select count("):
        cuerpo = sql[sql.lower().index(" from "):]
        return "SELECT count(*)" + cuerpo.replace(
            cuerpo[cuerpo.index("(SELECT ") + 8:cuerpo.index(" FROM audit_events")], "<columnas>") if "(SELECT " in cuerpo else "SELECT count(*)" + cuerpo
    return "SELECT <columnas> " + sql[sql.index("FROM audit_events"):]


r = cliente.post("/api/v1/auth/login", json={"tenant_code": "DEMO", "username": "admin", "password": PASSWORD})
assert r.status_code == 200, r.text
cabeceras = {"Authorization": f"Bearer {r.json()['access_token']}"}

print(f"motor: {engine.dialect.name} · índices de audit_events: "
      f"{sorted(i['name'] for i in inspect(engine).get_indexes('audit_events'))}")
with engine.connect() as c:
    print(f"filas en audit_events (todos los tenants): {c.execute(text('SELECT count(*) FROM audit_events')).scalar_one()}")

ultimas: list[dict] = []
for etiqueta, pagina in (("primera página", 1), ("página 51", 51)):
    tiempos, n_sentencias, filas_bd, entidades, ms_bd = [], [], [], [], []
    cuerpo = {}
    for _ in range(REPETICIONES):
        sentencias.clear()
        cargadas[0] = 0
        t0 = time.perf_counter()
        resp = cliente.get("/api/v1/audit/events", headers=cabeceras, params={"page": pagina, "page_size": TAMANO})
        tiempos.append((time.perf_counter() - t0) * 1000)
        assert resp.status_code == 200, resp.text
        cuerpo = resp.json()
        n_sentencias.append(len(sentencias))
        filas_bd.append(sum(s["filas"] for s in sentencias))
        entidades.append(cargadas[0])
        ms_bd.append(sum(s["ms"] for s in sentencias))
        ultimas = [dict(s) for s in sentencias]
    print(f"\n== {etiqueta}: page={pagina} page_size={TAMANO} · {REPETICIONES} peticiones ==")
    print(f"respuesta: claves={sorted(cuerpo)} items={len(cuerpo['items'])} total={cuerpo['total']}")
    print(f"latencia del endpoint (ms): min={min(tiempos):.0f} mediana={statistics.median(tiempos):.0f} max={max(tiempos):.0f}")
    print(f"sentencias sobre audit_events por petición: {sorted(set(n_sentencias))}")
    print(f"filas que la base devuelve por petición: {sorted(set(filas_bd))}")
    print(f"entidades AuditEvent construidas por petición: {sorted(set(entidades))}")
    print(f"tiempo en la base por petición (ms): mediana={statistics.median(ms_bd):.1f}")
    for i, s in enumerate(ultimas, 1):
        print(f"  [{i}] filas={s['filas']} · {s['ms']:.1f} ms · {forma(s['sql'])}")

if engine.dialect.name == "postgresql":
    print("\n== EXPLAIN ANALYZE de las sentencias de la última petición ==")
    with engine.connect() as c:
        for i, s in enumerate(ultimas, 1):
            plan = c.exec_driver_sql("EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY ON) " + s["sql"], s["parametros"]).scalars().all()
            print(f"  [{i}] {forma(s['sql'])[:110]}")
            for linea in plan:
                print(f"      {linea}")
