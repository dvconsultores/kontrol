"""Reproduce AUDIT-EVENTS-SIN-TENANT contra una base PostgreSQL de QA sembrada con `qa/e2e-seed.sh`.

Uso:  PYTHONPATH=resources/backend <python> qa/repro-audit-tenant-leak.py [pre|post]

A. Un inicio de sesión en DEMO y otro en DEMO2 (los eventos «accidentales» del hallazgo
   original); el administrador de DEMO lista y se cuenta, leyendo el dueño en la base,
   cuántos de los devueltos son de DEMO2.
B. Dos eventos controlados de contenido idéntico, uno por tenant, con marcador único.
C. El camino de escritura: el último LOGIN_SUCCESS de cada tenant lleva su tenant.

No borra ni modifica ninguna fila: solo añade los eventos que la propia reproducción genera.
La URL de la base se toma de KONTROL_DB_URL si está definida.
"""
from __future__ import annotations

import os
import sys
import uuid

os.environ.setdefault("KONTROL_DB_URL", "postgresql+psycopg2://kontrol_migrator:qa@localhost:55432/kaud")
os.environ.setdefault("KONTROL_SECRET_KEY", "qa-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_COOKIE_SECURE", "false")
os.environ.setdefault("KONTROL_LOG_JSON", "false")
os.environ.setdefault("KONTROL_INSTALLATION_VOLUME_PATH", "/tmp/kontrol-kaud-license")
os.environ.setdefault("KONTROL_STORAGE_PATH", "/tmp/kontrol-kaud-storage")
os.environ.setdefault("KONTROL_BACKUP_PATH", "/tmp/kontrol-kaud-backups")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.core.database import get_session_factory  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.audit.models import AuditEvent  # noqa: E402
from app.modules.organization.models import Tenant  # noqa: E402
from app.shared.audit import record_audit  # noqa: E402

PW = os.environ.get("KONTROL_E2E_PASSWORD", "Kontrol2026Segura!")
client = TestClient(create_app())
F = get_session_factory()
FASE = sys.argv[1] if len(sys.argv) > 1 else "pre"


def login(tenant: str, user: str) -> dict:
    r = client.post("/api/v1/auth/login", json={"tenant_code": tenant, "username": user, "password": PW})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def tenants() -> dict[str, str]:
    db = F()
    try:
        return {t.code: str(t.id) for t in db.execute(select(Tenant)).scalars().all()}
    finally:
        db.close()


def owner_of(ids: list[str]) -> dict[str, str | None]:
    db = F()
    try:
        return dict(db.execute(select(AuditEvent.id, AuditEvent.tenant_id).where(AuditEvent.id.in_(ids))).all())
    finally:
        db.close()


def listar(h: dict, **params) -> tuple[int, list[dict]]:
    items: list[dict] = []
    page = 1
    while True:
        r = client.get("/api/v1/audit/events", headers=h, params={"page": page, "page_size": 100, **params})
        assert r.status_code == 200, r.text
        body = r.json()
        items += body["items"]
        if len(items) >= body["total"] or not body["items"]:
            return body["total"], items
        page += 1


T = tenants()
por_id = {v: k for k, v in T.items()}
print(f"== FASE {FASE} == tenants: {T}")

# --- A. eventos accidentales: un login en cada tenant, como en el hallazgo original
h_demo = login("DEMO", "admin")
h_demo2 = login("DEMO2", "uc")
total, items = listar(h_demo)
duenos = owner_of([i["id"] for i in items])
por_tenant: dict[str | None, int] = {}
for i in items:
    codigo = por_id.get(duenos.get(i["id"]), duenos.get(i["id"]))
    por_tenant[codigo] = por_tenant.get(codigo, 0) + 1
print(f"A. admin/DEMO GET /audit/events -> total={total} items={len(items)} por tenant real={por_tenant}")
fuga_a = [i["id"] for i in items if duenos.get(i["id"]) == T["DEMO2"]]
print(f"A. eventos de DEMO2 devueltos a admin/DEMO: {len(fuga_a)} {fuga_a[:3]}")

# --- B. eventos controlados: mismo contenido, tenants distintos, marcador único
marca = f"AUDTEN-{uuid.uuid4().hex[:8]}"
db = F()
try:
    ea = record_audit(db, action="AUDTEN_PROBE", entity_type="Probe", entity_id="probe-mismo-id",
                      tenant_id=T["DEMO"], source="QA", request_id=marca, after={"marca": marca})
    eb = record_audit(db, action="AUDTEN_PROBE", entity_type="Probe", entity_id="probe-mismo-id",
                      tenant_id=T["DEMO2"], source="QA", request_id=marca, after={"marca": marca})
    db.commit()
    ida, idb = str(ea.id), str(eb.id)
finally:
    db.close()
print(f"B. EVENT_A={ida} tenant=DEMO({T['DEMO']})")
print(f"B. EVENT_B={idb} tenant=DEMO2({T['DEMO2']})")
total_a, items_a = listar(h_demo, action="AUDTEN_PROBE")
ids_a = {i["id"] for i in items_a}
print(f"B. admin/DEMO  ?action=AUDTEN_PROBE -> total={total_a} EVENT_A visible={ida in ids_a} EVENT_B visible={idb in ids_a}")
total_b, items_b = listar(h_demo2, action="AUDTEN_PROBE")
ids_b = {i["id"] for i in items_b}
print(f"B. uc/DEMO2    ?action=AUDTEN_PROBE -> total={total_b} EVENT_A visible={ida in ids_b} EVENT_B visible={idb in ids_b}")

# --- C. write path: el login de cada tenant queda con su tenant
db = F()
try:
    for code in ("DEMO", "DEMO2"):
        ev = db.execute(select(AuditEvent).where(AuditEvent.action == "LOGIN_SUCCESS", AuditEvent.tenant_id == T[code])
                        .order_by(AuditEvent.event_time.desc()).limit(1)).scalars().first()
        print(f"C. último LOGIN_SUCCESS con tenant={code}: {'existe' if ev else 'NO EXISTE'} company_id={ev.company_id if ev else None}")
finally:
    db.close()
veredicto = "LEAK" if (fuga_a or idb in ids_a or ida in ids_b) else "AISLADO"
print(f"== VEREDICTO {FASE}: {veredicto} ==")
