"""RL-CLIENTE · Cuando la Autoridad Central limita la emisión de desafíos (429 `SYNC_RATE_LIMITED`), el cliente lo
trata como un rechazo acotado: una sola petición de desafío, ninguna de sync, sin reintentos, sin
retroceso a un sync anónimo, estado de licencia intacto; un intento explícito posterior, cuando la ventana
se ha movido, sincroniza con normalidad (`CENTRAL-SYNC-SIN-LIMITE-DE-TASA`; FR-010-554..556, 558). La
autoridad real corre en proceso con capacidad 1. Nada real.
"""

from __future__ import annotations

import json
import os

# `central_authority.main` construye su app al importarse y lee `Settings` del entorno: base en memoria y `qa`.
os.environ.setdefault("KONTROL_CENTRAL_DB_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("KONTROL_CENTRAL_ENVIRONMENT", "qa")
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

import app.core.database as dm
from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.licensing import service as svc
from app.modules.licensing.models import LicenseEvent, LicenseState, LicenseSyncRun
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.setup.api import SetupRequest, initialize
from central_authority import database as central_db
from central_authority import main as central_main
from central_authority import service as central
from central_authority.config import Settings as CentralSettings
from central_authority.models import Base as CentralBase
from central_authority.models import SyncChallenge
from tests.central.conftest import pem_privada, pem_publica
from tests.conftest import make_engine
from tests.test_license_revision_client import _usuario
from tests.test_license_sync_client import TransporteReal

PASSWORD = "Kontrol2026Segura!"
SYNC = "/api/v1/licensing/sync"
ANCLA = "KONTROL_LICENSE_PUBLIC_KEY_PEM"

_FACTORY: sessionmaker
_CENTRAL: sessionmaker
_CLIENT: TestClient
_TRANSPORTE: TransporteReal
_INSTALACION: str


@pytest.fixture(scope="module", autouse=True)
def _mundo() -> Iterator[None]:
    global _FACTORY, _CENTRAL, _CLIENT, _TRANSPORTE, _INSTALACION
    propietario = Ed25519PrivateKey.generate()
    anterior = os.environ.get(ANCLA)
    os.environ[ANCLA] = pem_publica(propietario)
    for v in ("KONTROL_LICENSE_PUBLIC_KEY_KID", "KONTROL_LICENSE_TRUST_KEYS"):
        os.environ.pop(v, None)
    get_settings.cache_clear()
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    _FACTORY = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    dm._engine, dm._SessionLocal = engine, _FACTORY  # type: ignore[attr-defined]
    with _FACTORY() as db:
        initialize(db, SetupRequest(tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1", company_legal_name="Demo C.A.",
                                    company_rif="J-12345678-9", admin_username="admin", admin_password=PASSWORD))
        tenant = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().one()
        empresa = db.execute(select(Company).where(Company.tenant_id == tenant.id)).scalars().one()
        _usuario(db, str(tenant.id), str(empresa.id), "lector", sin={"license:create"})
        inst = db.execute(select(Installation)).scalars().first()
        _INSTALACION, clave_publica = inst.installation_uuid, inst.public_key
        svc.upsert_central_config(db, server_url="http://127.0.0.1:8010", public_key=None, sync_policy={"mode": "MANUAL"}, grace_days=7, enabled=True, actor="admin")
        db.commit()
    ajustes = CentralSettings(_env_file=None, environment="qa", db_url="sqlite+pysqlite:///:memory:", signing_private_key_pem=pem_privada(propietario),
                              sync_challenge_rate_limit_capacity=1, sync_challenge_rate_limit_window_seconds=60)
    motor_central = make_engine()
    CentralBase.metadata.create_all(motor_central)
    _CENTRAL = sessionmaker(bind=motor_central, class_=Session, expire_on_commit=False)
    with _CENTRAL() as db:
        central.register_installation(db, installation_uuid=_INSTALACION, public_key_pem=clave_publica, customer_id="C-TEST", contract_id="K-TEST",
                                      company_tax_id=None, operator="qa")
        inicio, fin = central.periodo_anual(2031)
        central.issue_license(db, settings=ajustes, installation_uuid=_INSTALACION, period_start=inicio, period_end=fin, entitlements={"companies": 3},
                              minimum_version="1.0.0", operator="qa")
    central_main.get_settings = lambda: ajustes  # type: ignore[assignment]
    app_central = central_main.create_app()

    def _db_central():
        d = _CENTRAL()
        try:
            yield d
        finally:
            d.close()

    app_central.dependency_overrides[central_db.get_db] = _db_central
    _TRANSPORTE = TransporteReal(TestClient(app_central))
    from app.main import create_app

    app = create_app()

    def _db():
        d = _FACTORY()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _db
    _CLIENT = TestClient(app, raise_server_exceptions=False)
    transporte_original = svc.UrllibSyncTransport
    svc.UrllibSyncTransport = lambda: _TRANSPORTE  # type: ignore[assignment,misc]
    try:
        yield
    finally:
        svc.UrllibSyncTransport = transporte_original  # type: ignore[misc]
        if anterior is None:
            os.environ.pop(ANCLA, None)
        else:
            os.environ[ANCLA] = anterior
        get_settings.cache_clear()


def _sesion() -> dict[str, str]:
    r = _CLIENT.post("/api/v1/auth/login", json={"tenant_code": "DEMO", "username": "admin", "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _olvida_idempotencia() -> None:
    with _FACTORY() as db:
        for r in db.execute(select(LicenseSyncRun)).scalars().all():
            r.idempotency_key = f"usada-{r.id}"
        db.commit()


def _llamadas(tipo: str) -> int:
    return sum(1 for nombre, _ in _TRANSPORTE.llamadas if nombre == tipo)


def _estado() -> dict[str, Any]:
    with _FACTORY() as db:
        s = db.execute(select(LicenseState)).scalars().first()
        return {"license_id": s.license_id, "mode": s.mode} if s else {}


def test_rlc_01_la_primera_sincronizacion_entra_y_agota_la_ventana_de_la_autoridad():
    r = _CLIENT.post(SYNC, headers=_sesion())
    assert r.status_code == 200, r.text
    assert _estado()["mode"] == "FULL_ACCESS" and _llamadas("challenge") == 1 and _llamadas("sync") == 1


def test_rlc_02_con_la_autoridad_limitando_el_cliente_falla_acotado_sin_reintentos_ni_retroceso():
    _olvida_idempotencia()
    antes = _estado()
    r = _CLIENT.post(SYNC, headers=_sesion())
    assert r.status_code == 502 and r.json()["code"] == "CENTRAL_SYNC_REJECTED", r.text
    assert r.json()["details"]["central_code"] == "SYNC_RATE_LIMITED"
    assert _llamadas("challenge") == 2 and _llamadas("sync") == 1  # una sola petición de desafío más; ningún sync sin desafío
    assert _estado() == antes  # el estado de licencia no se toca
    with _FACTORY() as db:
        corridas = list(db.execute(select(LicenseSyncRun).order_by(LicenseSyncRun.ran_at)).scalars().all())
        assert [c.status for c in corridas] == ["SUCCESS", "FAILED"] and corridas[-1].error == "SYNC_RATE_LIMITED"
        evento = db.execute(select(LicenseEvent).where(LicenseEvent.event_type == "LICENSE_SYNC_REJECTED")).scalars().one()
        assert evento.detail == {"central_code": "SYNC_RATE_LIMITED"}
    assert "nonce" not in json.dumps(r.json()).lower() and "KTL-" not in r.text


def test_rlc_03_un_intento_explicito_posterior_con_la_ventana_movida_sincroniza_con_normalidad():
    with _CENTRAL() as db:  # el tiempo pasa en la autoridad: la ventana se vacía
        for fila in db.execute(select(SyncChallenge)).scalars().all():
            fila.created_at, fila.expires_at = fila.created_at - timedelta(seconds=61), fila.expires_at - timedelta(seconds=61)
        db.commit()
    _olvida_idempotencia()
    r = _CLIENT.post(SYNC, headers=_sesion())
    assert r.status_code == 200, r.text
    assert _llamadas("challenge") == 3 and _llamadas("sync") == 2 and _estado()["mode"] == "FULL_ACCESS"
