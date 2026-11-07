"""SYS · El diagnóstico de la instalación exige sesión y permiso; los health siguen públicos y mínimos.

`GET /system/diagnostics` respondía a cualquiera —sin sesión, con un token inventado— la
identidad de la instalación, la licencia y la ruta de almacenamiento del servidor
(DIAGNOSTICO-SIN-SESION). Ahora lo gobierna `license:view`, el permiso que ya gobierna leer la
identidad y la licencia (FR-001-084, FR-001-042). Los health checks que usan Docker, el panel y
el lanzador de QA no cambian.

Sobre PostgreSQL cuando `KONTROL_TEST_DB_URL` lo indica (P21).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Permission, Role, RolePermission, User, UserRole, UserScope
from app.modules.organization.models import Company, Tenant
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine

PASSWORD = "Kontrol2026Segura!"
DIAGNOSTICO = "/api/v1/system/diagnostics"
CLAVES_DEL_DIAGNOSTICO = {"environment", "version", "database", "installation", "license", "backup"}
#: Lo que nunca puede salir por un health público ni por un rechazo.
SENSIBLE = re.compile(
    r"postgres|sqlite|psycopg|dsn|password|contrase|secret_key|traceback|tenant_id|company_id|user_id|/tmp|/data|/home|\\\\",
    re.IGNORECASE,
)

_CLIENT: TestClient
_FACTORY: sessionmaker


def _usuario(db: Session, tenant_id: str, empresa: str, username: str, *, sin: set[str]) -> None:
    """Usuario del tenant con un rol que lleva todo el catálogo menos `sin`."""
    usuario = identity_service.create_user(
        db, tenant_id=tenant_id, username=username, email=f"{username}@demo.test",
        password=PASSWORD, must_change_password=False, created_by=None)
    rol = Role(code=f"SYS-{username}".upper(), name=f"SYS {username}", protected=False, status="ACTIVE")
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


@pytest.fixture(scope="module", autouse=True)
def _app_client():
    global _CLIENT, _FACTORY
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    import app.core.database as dm

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
    _FACTORY = factory
    _CLIENT = TestClient(app)
    yield _CLIENT


def _sesion(username: str) -> dict[str, str]:
    r = login_completo(_CLIENT, "/api/v1/auth/login", json={"tenant_code": "DEMO", "username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _sin_diagnostico(r) -> None:
    cuerpo = r.json()
    assert not (CLAVES_DEL_DIAGNOSTICO & set(cuerpo)), f"el rechazo trae diagnóstico: {sorted(cuerpo)}"
    assert "storage" not in r.text and SENSIBLE.search(r.text) is None, r.text


# ---------------------------------------------------------------- SYS-01..03 · autenticación
def test_sys_01_sin_credenciales_401_y_sin_diagnostico():
    r = _CLIENT.get(DIAGNOSTICO)
    assert r.status_code == 401 and r.json()["code"] == "AUTH_REQUIRED", r.text
    _sin_diagnostico(r)


@pytest.mark.parametrize("cabecera", [
    "Bearer no.es.un.token", "Bearer ", "Basic YWRtaW46YWRtaW4=", "Token abc", "Bearer eyJhbGciOiJub25lIn0.e30.",
])
def test_sys_02_credenciales_ilegibles_401_y_sin_diagnostico(cabecera):
    r = _CLIENT.get(DIAGNOSTICO, headers={"Authorization": cabecera})
    assert r.status_code == 401 and r.json()["code"] in {"AUTH_REQUIRED", "AUTH_INVALID_TOKEN"}, r.text
    _sin_diagnostico(r)


def test_sys_03_un_token_caducado_firmado_con_la_clave_real_401_y_sin_diagnostico():
    with _FACTORY() as db:
        admin = db.execute(select(User).where(User.username == "admin")).scalars().first()
    settings = get_settings()
    caducado = jwt.encode(
        {"sub": str(admin.id), "type": "access", "iat": datetime.now(UTC) - timedelta(hours=2),
         "exp": datetime.now(UTC) - timedelta(hours=1), "tenant_id": admin.tenant_id},
        settings.secret_key, algorithm=settings.jwt_algorithm)
    r = _CLIENT.get(DIAGNOSTICO, headers={"Authorization": f"Bearer {caducado}"})
    assert r.status_code == 401 and r.json()["code"] == "AUTH_INVALID_TOKEN", r.text
    _sin_diagnostico(r)


# ---------------------------------------------------------------- SYS-04..06 · autorización
def test_sys_04_una_sesion_valida_sin_el_permiso_403_y_sin_diagnostico():
    r = _CLIENT.get(DIAGNOSTICO, headers=_sesion("operador"))
    assert r.status_code == 403 and r.json()["code"] == "PERMISSION_DENIED", r.text
    _sin_diagnostico(r)


def test_sys_05_con_el_permiso_el_diagnostico_sale_entero_y_sin_rutas():
    r = _CLIENT.get(DIAGNOSTICO, headers=_sesion("admin"))
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert set(cuerpo) == CLAVES_DEL_DIAGNOSTICO
    assert cuerpo["database"] == {"ok": True}
    assert set(cuerpo["installation"]) == {"id", "state"} and cuerpo["installation"]["id"].startswith("KTL-")
    # `verification` es la clase de la reverificación del vigente (LICENCIA-ESTADO-SIN-REVERIFICAR): solo la clase, sin material.
    assert set(cuerpo["license"]) == {"activated", "mode", "period_end", "verification"}
    assert cuerpo["license"]["verification"] in {"VALID", "NO_CURRENT_LICENSE"} or cuerpo["license"]["verification"].isupper()
    assert isinstance(cuerpo["version"], str) and isinstance(cuerpo["environment"], str)
    assert cuerpo["backup"]["rpo_state"] == "DISABLED"
    assert "sha256" not in cuerpo["backup"]
    assert "storage" not in r.text
    # Ningún valor con aspecto de ruta del servidor.
    for valor in (cuerpo["environment"], cuerpo["version"], *cuerpo["installation"].values(), *cuerpo["license"].values()):
        assert not (isinstance(valor, str) and ("/" in valor or "\\" in valor)), valor
    assert SENSIBLE.search(r.text) is None, r.text


@pytest.mark.parametrize("empresa", ["00000000-0000-0000-0000-000000000000", "", "otra"])
def test_sys_06_la_cabecera_de_empresa_no_concede_ni_cambia_nada(empresa):
    cabecera = {"X-Kontrol-Company": empresa}
    con = _CLIENT.get(DIAGNOSTICO, headers={**_sesion("admin"), **cabecera})
    sin = _CLIENT.get(DIAGNOSTICO, headers=_sesion("admin"))
    assert con.status_code == 200 and con.json() == sin.json()
    r = _CLIENT.get(DIAGNOSTICO, headers={**_sesion("operador"), **cabecera})
    assert r.status_code == 403 and r.json()["code"] == "PERMISSION_DENIED"
    assert _CLIENT.get(DIAGNOSTICO, headers=cabecera).status_code == 401


# ---------------------------------------------------------------- SYS-07..08 · health públicos
def test_sys_07_los_health_siguen_publicos_con_su_contrato_de_hoy():
    live = _CLIENT.get("/api/v1/health/live")
    ready = _CLIENT.get("/api/v1/health/ready")
    assert live.status_code == 200 and set(live.json()) == {"status", "service"}  # sin versión (FR-010-116)
    assert live.json()["status"] == "ok"
    assert ready.status_code == 200 and set(ready.json()) == {"status", "service", "database"}
    assert ready.json() == {"status": "ok", "service": "kontrol-backend", "database": "ok"}


def test_sys_08_ningun_health_lleva_nada_del_diagnostico_ni_del_servidor():
    for ruta in ("/api/v1/health/live", "/api/v1/health/ready"):
        r = _CLIENT.get(ruta)
        # `version` y `database` también existen en los health, con otro contenido: lo propio del
        # diagnóstico es la identidad de la instalación, la licencia y el entorno.
        assert not {"environment", "installation", "license"} & set(r.json()), (ruta, r.json())
        assert "storage" not in r.text and "installation" not in r.text and "license" not in r.text
        assert SENSIBLE.search(r.text) is None, (ruta, r.text)
        assert "/" not in "".join(str(v) for v in r.json().values()), r.text
