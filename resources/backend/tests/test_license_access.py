"""LIC · La licencia antes de la sesión y sin permiso (LICENCIA-STATUS-SIN-SESION,
LICENCIA-LECTURA-SIN-PERMISO, HEALTH-LIVE-VERSION; FR-010-102..120).

`GET /license/status` respondía a cualquiera la identidad de la instalación, `license_id`,
`kid`, fechas y derechos; el historial y la solicitud de activación eran anónimos, y las
lecturas de licenciamiento central exigían sesión pero no `license:view`. Ahora el estado
público es una lista explícita de dos campos —`mode`, `license_url`—, y toda lectura
detallada exige sesión y `license:view` en el backend, que es la autoridad. `/health/live`
deja de publicar la versión.

Mundo del módulo: `initialize`, una licencia firmada de prueba (`LIC-010000`), `admin` con
todo el catálogo y `operador` con todo el catálogo menos `license:view`. Un mundo aparte,
sin licencia, para el estado `PENDING`.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

import app.core.database as dm
from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Permission, Role, RolePermission, User, UserRole, UserScope
from app.modules.licensing import service as licensing_service
from app.modules.licensing.models import LicenseState
from app.modules.organization.models import Company, Tenant
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine
from tests.test_licensing_central import _activate_license

PASSWORD = "Kontrol2026Segura!"
STATUS = "/api/v1/license/status"
DETAIL = "/api/v1/license/detail"
#: Todas las lecturas detalladas de licencia o instalación (FR-010-107/108).
DETALLADAS = (
    DETAIL,
    "/api/v1/license/history",
    "/api/v1/license/installation-request",
    "/api/v1/licensing/central-config",
    "/api/v1/licensing/sync-runs",
    "/api/v1/licensing/entitlements",
    "/api/v1/licensing/entitlement-snapshots",
    "/api/v1/licensing/offline-status",
    "/api/v1/licensing/renewal-requests",
    "/api/v1/licensing/overview",
)
PUBLICO = {"mode", "license_url"}
MODOS = {"FULL_ACCESS", "RENEWAL_NOTICE", "CRITICAL_RENEWAL_NOTICE", "READ_ONLY", "SECURITY_SUSPENSION", "PENDING"}
#: Lo que nunca puede salir por el estado público ni por un rechazo (FR-010-103/109).
SENSIBLE = re.compile(
    r"installation_id|license_id|\bkid\b|period_|read_only_start|critical_warning|entitlements|minimum_version"
    r"|customer|contract|signature|public_key|private|KTL-|LIC-0|postgres|sqlite|psycopg|/tmp|/home|tenant_id|company_id",
    re.IGNORECASE,
)

_CLIENT: TestClient
_FACTORY: sessionmaker


def _usuario(db: Session, tenant_id: str, empresa: str, username: str, *, sin: set[str]) -> None:
    """Usuario del tenant con un rol que lleva todo el catálogo menos `sin`."""
    usuario = identity_service.create_user(
        db, tenant_id=tenant_id, username=username, email=f"{username}@demo.test",
        password=PASSWORD, must_change_password=False, created_by=None)
    rol = Role(code=f"LIC-{username}".upper(), name=f"LIC {username}", protected=False, status="ACTIVE")
    db.add(rol)
    db.flush()
    excluidos = set()
    for p in db.query(Permission).all():
        clave = f"{p.resource}:{p.action}"
        if clave in sin:
            excluidos.add(clave)
            continue
        db.add(RolePermission(role_id=str(rol.id), permission_id=str(p.id)))
    assert excluidos == sin, f"el catálogo no trae {sin - excluidos}"
    db.add(UserRole(user_id=str(usuario.id), role_id=str(rol.id), company_id=None))
    db.add(UserScope(user_id=str(usuario.id), company_id=empresa))


def _mundo(*, con_licencia: bool) -> tuple[TestClient, sessionmaker]:
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    dm._engine = engine  # type: ignore[attr-defined]
    dm._SessionLocal = factory  # type: ignore[attr-defined]
    with factory() as db:
        initialize(db, SetupRequest(
            tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1",
            company_legal_name="Demo C.A.", company_rif="J-12345678-9",
            admin_username="admin", admin_password=PASSWORD,
        ))
        tenant = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().one()
        empresa = db.execute(select(Company).where(Company.tenant_id == tenant.id)).scalars().one()
        _usuario(db, str(tenant.id), str(empresa.id), "operador", sin={"license:view"})
        if con_licencia:
            _activate_license(db)
            estado = db.execute(select(LicenseState)).scalars().one()
            # Sin fecha confiable, `verify_offline` responde `NO_RELIABLE_DATE` en los dos
            # motores. Con ella, sobre SQLite compara una fecha sin zona con UTC y rompe
            # `/overview` y `/offline-status` (deuda OFFLINE-NAIVE-EN-SQLITE, ajena a este
            # delta). Aquí se prueba la frontera de acceso, no la tolerancia offline.
            estado.last_reliable_date = None
        db.commit()

    from app.main import create_app

    app = create_app()

    def _override_get_db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _override_get_db
    # Un fallo del servidor debe verse como 500, no como excepción: así se afirma qué sale.
    return TestClient(app, raise_server_exceptions=False), factory


@pytest.fixture(scope="module", autouse=True)
def _app_client():
    global _CLIENT, _FACTORY
    _CLIENT, _FACTORY = _mundo(con_licencia=True)
    yield _CLIENT


def _sesion(username: str, cliente: TestClient | None = None) -> dict[str, str]:
    cliente = cliente or _CLIENT
    r = cliente.post("/api/v1/auth/login", json={"tenant_code": "DEMO", "username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _caducado() -> dict[str, str]:
    with _FACTORY() as db:
        admin = db.execute(select(User).where(User.username == "admin")).scalars().first()
    settings = get_settings()
    token = jwt.encode(
        {"sub": str(admin.id), "type": "access", "iat": datetime.now(UTC) - timedelta(hours=2),
         "exp": datetime.now(UTC) - timedelta(hours=1), "tenant_id": admin.tenant_id},
        settings.secret_key, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


def _sin_fuga(r) -> None:
    assert SENSIBLE.search(r.text) is None, r.text


def _publico(r) -> dict:
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert set(cuerpo) == PUBLICO, sorted(cuerpo)
    assert cuerpo["mode"] in MODOS and cuerpo["license_url"] == "/mi-licencia"
    _sin_fuga(r)
    return cuerpo


# ---------------------------------------------------------------- LIC-01..05 · estado público mínimo
def test_lic_01_sin_sesion_el_estado_publico_trae_exactamente_modo_y_enlace():
    cuerpo = _publico(_CLIENT.get(STATUS))
    assert cuerpo["mode"] == "FULL_ACCESS"


def test_lic_02_sin_licencia_el_modo_es_pending_con_las_mismas_dos_claves_nunca_full_access():
    anterior = (dm._engine, dm._SessionLocal)  # type: ignore[attr-defined]
    try:
        cliente, _ = _mundo(con_licencia=False)
        cuerpo = _publico(cliente.get(STATUS))
        assert cuerpo["mode"] == "PENDING"
        assert "FULL_ACCESS" not in cliente.get(STATUS).text
    finally:
        dm._engine, dm._SessionLocal = anterior  # type: ignore[attr-defined]


def test_lic_03_el_estado_publico_no_lleva_identidad_licencia_fechas_ni_derechos():
    r = _CLIENT.get(STATUS)
    _publico(r)
    with _FACTORY() as db:
        estado = db.execute(select(LicenseState)).scalars().one()
    for valor in (estado.installation_id, estado.license_id, estado.kid, "2026-04-01", "2027-03-31", "companies", "1.0.0"):
        assert valor and valor not in r.text, valor


@pytest.mark.parametrize("cabecera", [{"Authorization": "Bearer inventado"}, {"Authorization": "Basic Zm9v"}, {"Authorization": ""}])
def test_lic_04_un_token_inventado_o_caducado_no_cambia_el_contrato_publico(cabecera):
    assert _publico(_CLIENT.get(STATUS, headers=cabecera)) == _publico(_CLIENT.get(STATUS))
    assert _publico(_CLIENT.get(STATUS, headers=_caducado())) == _publico(_CLIENT.get(STATUS))


def test_lic_05_con_sesion_y_permiso_el_estado_publico_es_el_mismo_contrato():
    assert _publico(_CLIENT.get(STATUS, headers=_sesion("admin"))) == _publico(_CLIENT.get(STATUS))
    assert _publico(_CLIENT.get(STATUS, headers=_sesion("operador"))) == _publico(_CLIENT.get(STATUS))


# ---------------------------------------------------------------- LIC-06..10 · el detalle
def test_lic_06_sin_credenciales_el_detalle_es_401_y_sin_fuga():
    r = _CLIENT.get(DETAIL)
    assert r.status_code == 401 and r.json()["code"] == "AUTH_REQUIRED", r.text
    _sin_fuga(r)


@pytest.mark.parametrize("cabecera", [{"Authorization": "Bearer inventado"}, {"Authorization": "Bearer a.b.c"}, {"Authorization": "Basic Zm9v"}])
def test_lic_07_credenciales_ilegibles_401_y_sin_fuga(cabecera):
    r = _CLIENT.get(DETAIL, headers=cabecera)
    assert r.status_code == 401, r.text
    _sin_fuga(r)


def test_lic_08_un_token_caducado_firmado_con_la_clave_real_401_y_sin_fuga():
    r = _CLIENT.get(DETAIL, headers=_caducado())
    assert r.status_code == 401 and r.json()["code"] == "AUTH_INVALID_TOKEN", r.text
    _sin_fuga(r)


def test_lic_09_una_sesion_valida_sin_el_permiso_403_y_sin_fuga():
    r = _CLIENT.get(DETAIL, headers=_sesion("operador"))
    assert r.status_code == 403 and r.json()["code"] == "PERMISSION_DENIED", r.text
    _sin_fuga(r)


def test_lic_10_con_el_permiso_el_detalle_sale_entero_y_su_modo_es_el_publico():
    r = _CLIENT.get(DETAIL, headers=_sesion("admin"))
    assert r.status_code == 200, r.text
    detalle = r.json()
    assert {"installation_id", "activated", "license_id", "mode", "period_start", "period_end", "read_only_start", "entitlements", "license_url"} <= set(detalle)
    assert detalle["activated"] is True and detalle["license_id"] == "LIC-010000"
    assert detalle["mode"] == _CLIENT.get(STATUS).json()["mode"]


# ---------------------------------------------------------------- LIC-11..14 · todas las lecturas detalladas
@pytest.mark.parametrize("ruta", DETALLADAS)
def test_lic_11_sin_credenciales_toda_lectura_detallada_es_401(ruta):
    r = _CLIENT.get(ruta)
    assert r.status_code == 401 and r.json()["code"] == "AUTH_REQUIRED", (ruta, r.text)
    _sin_fuga(r)
    assert _CLIENT.get(ruta, headers={"Authorization": "Bearer inventado"}).status_code == 401


@pytest.mark.parametrize("ruta", DETALLADAS)
def test_lic_12_sin_el_permiso_toda_lectura_detallada_es_403_y_sin_fuga(ruta):
    r = _CLIENT.get(ruta, headers=_sesion("operador"))
    assert r.status_code == 403 and r.json()["code"] == "PERMISSION_DENIED", (ruta, r.text)
    _sin_fuga(r)


@pytest.mark.parametrize("ruta", DETALLADAS)
def test_lic_13_con_el_permiso_toda_lectura_detallada_responde_200(ruta):
    r = _CLIENT.get(ruta, headers=_sesion("admin"))
    assert r.status_code == 200, (ruta, r.text)


@pytest.mark.parametrize("empresa", ["00000000-0000-0000-0000-000000000000", "", "otra"])
def test_lic_14_la_cabecera_de_empresa_no_concede_ni_cambia_nada(empresa):
    cabecera = {"X-Kontrol-Company": empresa}
    con = _CLIENT.get(DETAIL, headers={**_sesion("admin"), **cabecera})
    sin = _CLIENT.get(DETAIL, headers=_sesion("admin"))
    assert con.status_code == 200 and con.json() == sin.json()
    r = _CLIENT.get(DETAIL, headers={**_sesion("operador"), **cabecera})
    assert r.status_code == 403 and r.json()["code"] == "PERMISSION_DENIED"
    assert _CLIENT.get(DETAIL, headers=cabecera).status_code == 401
    assert _publico(_CLIENT.get(STATUS, headers=cabecera)) == _publico(_CLIENT.get(STATUS))


# ---------------------------------------------------------------- LIC-15..16 · una sola fuente de verdad, cerrado ante error
@contextmanager
def _licencia_vencida() -> Iterator[None]:
    """Mueve las fechas al pasado para que el modo real sea READ_ONLY; las devuelve al salir."""
    with _FACTORY() as db:
        estado = db.execute(select(LicenseState)).scalars().one()
        originales = (estado.period_start, estado.period_end, estado.critical_warning_start, estado.read_only_start, estado.mode)
        ahora = datetime.now(UTC)
        estado.period_start, estado.period_end = ahora - timedelta(days=400), ahora - timedelta(days=40)
        estado.critical_warning_start, estado.read_only_start = ahora - timedelta(days=20), ahora - timedelta(days=10)
        db.commit()
    try:
        yield
    finally:
        with _FACTORY() as db:
            estado = db.execute(select(LicenseState)).scalars().one()
            (estado.period_start, estado.period_end, estado.critical_warning_start, estado.read_only_start, estado.mode) = originales
            db.commit()


def test_lic_15_el_estado_publico_dice_read_only_cuando_la_licencia_lo_esta():
    with _licencia_vencida():
        assert _publico(_CLIENT.get(STATUS))["mode"] == "READ_ONLY"
        assert _CLIENT.get(DETAIL, headers=_sesion("admin")).json()["mode"] == "READ_ONLY"
    assert _publico(_CLIENT.get(STATUS))["mode"] == "FULL_ACCESS"


def test_lic_16_lista_explicita_un_campo_extra_no_sale_y_sin_modo_no_hay_200(monkeypatch):
    real = licensing_service.get_status
    monkeypatch.setattr(licensing_service, "get_status", lambda db: {**real(db), "secret": "no-debe-salir", "login_allowed": True})
    r = _CLIENT.get(STATUS)
    assert _publico(r) and "secret" not in r.text and "login_allowed" not in r.text
    monkeypatch.setattr(licensing_service, "get_status", lambda db: {k: v for k, v in real(db).items() if k != "mode"})
    r = _CLIENT.get(STATUS)
    assert r.status_code == 500 and "mode" not in r.json() and "FULL_ACCESS" not in r.text, r.text


# ---------------------------------------------------------------- HEALTH-01..05 · públicos y mínimos
def test_health_01_live_responde_estado_y_servicio_exactamente():
    r = _CLIENT.get("/api/v1/health/live")
    assert r.status_code == 200 and r.json() == {"status": "ok", "service": "kontrol-backend"}


def test_health_02_live_no_publica_la_version():
    r = _CLIENT.get("/api/v1/health/live")
    assert "version" not in r.text and get_settings().app_version not in r.text


def test_health_03_ready_sigue_minimo():
    r = _CLIENT.get("/api/v1/health/ready")
    assert r.status_code == 200 and r.json() == {"status": "ok", "service": "kontrol-backend", "database": "ok"}


@pytest.mark.parametrize("ruta", ["/api/v1/health/live", "/api/v1/health/ready"])
def test_health_04_ningun_health_lleva_identidad_licencia_entorno_ni_rutas(ruta):
    r = _CLIENT.get(ruta)
    assert not ({"installation", "license", "environment", "storage", "version"} & set(r.json()))
    _sin_fuga(r)


@pytest.mark.parametrize("ruta", ["/api/v1/health/live", "/api/v1/health/ready"])
def test_health_05_los_health_siguen_publicos_con_cualquier_credencial(ruta):
    for cabecera in ({}, {"Authorization": "Bearer inventado"}, _caducado(), _sesion("operador")):
        r = _CLIENT.get(ruta, headers=cabecera)
        assert r.status_code == 200 and r.json() == _CLIENT.get(ruta).json()
