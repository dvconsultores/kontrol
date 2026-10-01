"""Mundo de prueba del listado de auditoría: dos tenants y un observador de lo que la
petición hace contra `audit_events`.

Dos tenants —`DEMO` (administrador `admin`) y `DEMO2` (administrador `admin2`)—, para que
todo lo que se afirme del listado pueda afirmarse también con datos ajenos delante. Y un
observador que cuenta, mientras dura una petición, las sentencias `SELECT` que tocan
`audit_events` y las entidades `AuditEvent` que el ORM llega a construir: es la manera de
ver si `total` sale de una cuenta en la base o de traerse la bitácora entera.

SQLite en memoria por defecto; sobre PostgreSQL con `KONTROL_TEST_DB_URL`.
"""
from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from conftest import make_engine
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.audit.models import AuditEvent
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import UserRole
from app.modules.licensing import service as licensing_service
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.setup.api import SetupRequest, _bootstrap_roles, initialize
from app.shared.audit import record_audit

PASSWORD = "Kontrol2026Segura!"
_ENGINE: Engine | None = None
_FACTORY: sessionmaker | None = None
_CLIENT: TestClient | None = None
#: Identificadores del mundo: `tenant_a`, `tenant_b`.
W: dict[str, str] = {}


def _importar_licencia(db: Session) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
    inst = db.execute(select(Installation).limit(1)).scalars().first()
    now = datetime.now(UTC)
    payload = {
        "issuer": "K", "license_id": "LIC-AUD-MUNDO", "installation_id": inst.installation_uuid,
        "customer_id": "C1", "contract_id": "C1", "company_tax_id": "J-12345678-9",
        "period_start": (now - timedelta(days=30)).isoformat(),
        "period_end": (now + timedelta(days=120)).isoformat(),
        "critical_warning_start": (now + timedelta(days=180)).isoformat(),
        "read_only_start": (now + timedelta(days=200)).isoformat(),
        "entitlements": {"companies": 5, "users": 25, "modules": ["*"]},
        "minimum_version": "1.0.0", "kid": "kontrol-lic-2026-01",
    }
    sig = key.sign(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hex()
    os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = pub
    get_settings.cache_clear()
    try:
        licensing_service.import_license(db, payload=payload, signature_hex=sig, source="MANUAL")
    finally:
        os.environ.pop("KONTROL_LICENSE_PUBLIC_KEY_PEM", None)
        get_settings.cache_clear()


def montar() -> None:
    """Crea el mundo y deja listo el cliente. Se llama una vez por módulo de prueba."""
    global _ENGINE, _FACTORY, _CLIENT
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    import app.core.database as dm

    dm._engine = engine  # type: ignore[attr-defined]
    dm._SessionLocal = factory  # type: ignore[attr-defined]

    db = factory()
    initialize(db, SetupRequest(
        tenant_code="DEMO", tenant_name="Tenant A", company_code="D1",
        company_legal_name="Empresa D1 CA", company_rif="J-12345678-9",
        admin_username="admin", admin_password=PASSWORD))
    _importar_licencia(db)

    t_a = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().one()
    inst = db.execute(select(Installation).limit(1)).scalars().first()
    t_b = Tenant(installation_id=str(inst.id), code="DEMO2", name="Tenant B",
                 plan="MONO_COMPANY", status="ACTIVE")
    db.add(t_b)
    db.flush()
    db.add(Company(tenant_id=str(t_b.id), code="E1", legal_name="Empresa E1 CA", rif="J-33333333-3",
                   legal_type="JURIDICA", functional_currency="VED", status="ACTIVE"))
    admin_b = identity_service.create_user(
        db, tenant_id=str(t_b.id), username="admin2", email="admin2@aud.test",
        password=PASSWORD, created_by=None)
    rol = _bootstrap_roles(db, str(t_b.id), str(admin_b.id))
    db.add(UserRole(user_id=str(admin_b.id), role_id=str(rol.id), company_id=None))
    db.commit()
    W.clear()
    W.update(tenant_a=str(t_a.id), tenant_b=str(t_b.id))
    db.close()

    from app.main import create_app

    app = create_app()

    def _db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _db
    _ENGINE, _FACTORY, _CLIENT = engine, factory, TestClient(app)


def login(tenant: str, username: str) -> dict[str, str]:
    """Cabeceras de un usuario. Ojo: cada inicio de sesión escribe un evento de auditoría."""
    r = _CLIENT.post("/api/v1/auth/login", json={
        "tenant_code": tenant, "username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def como_a() -> dict[str, str]:
    return login("DEMO", "admin")


def como_b() -> dict[str, str]:
    return login("DEMO2", "admin2")


def listar(cabeceras: dict[str, str], **params) -> dict:
    r = _CLIENT.get("/api/v1/audit/events", headers=cabeceras, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def marca() -> str:
    """Un identificador único (cabe en `entity_id`) para aislar los eventos de una prueba."""
    return f"aud-{uuid.uuid4().hex[:12]}"


def crear_eventos(tenant_id: str, cuantos: int, *, entity_id: str, action: str = "AUDCOUNT_PROBE",
                  entity_type: str = "Probe") -> list[str]:
    """Crea `cuantos` eventos iguales salvo por el dueño; devuelve sus ids en orden de creación."""
    db = _FACTORY()
    try:
        eventos = [record_audit(db, action=action, entity_type=entity_type, entity_id=entity_id,
                                tenant_id=tenant_id, source="QA", request_id="mismo-request")
                   for _ in range(cuantos)]
        db.commit()
        return [str(e.id) for e in eventos]
    finally:
        db.close()


@dataclass
class Observacion:
    #: Sentencias `SELECT` que tocaron `audit_events`, con los espacios normalizados.
    sentencias: list[str] = field(default_factory=list)
    #: Entidades `AuditEvent` que el ORM construyó.
    cargadas: int = 0

    @property
    def de_conteo(self) -> list[str]:
        return [s for s in self.sentencias if "count(" in s.lower()]

    @property
    def de_filas(self) -> list[str]:
        return [s for s in self.sentencias if "count(" not in s.lower()]


@contextmanager
def observar() -> Iterator[Observacion]:
    """Observa lo que se ejecuta contra `audit_events` mientras dura el bloque."""
    visto = Observacion()

    def _sentencia(conn, cursor, statement, parameters, context, executemany):
        if "audit_events" in statement and statement.lstrip().upper().startswith("SELECT"):
            visto.sentencias.append(" ".join(statement.split()))

    def _carga(target, context):
        visto.cargadas += 1

    event.listen(_ENGINE, "before_cursor_execute", _sentencia)
    event.listen(AuditEvent, "load", _carga)
    try:
        yield visto
    finally:
        event.remove(_ENGINE, "before_cursor_execute", _sentencia)
        event.remove(AuditEvent, "load", _carga)
