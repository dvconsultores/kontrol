"""VER · La versión del producto tiene una sola autoridad y una sola vía de lectura (PANEL-VERSION-VACIA;
FR-001-084; ADR-D0-006 R-D0-06-4). Autoridad: `app.__version__`, que viaja con el artefacto; `pyproject.toml`
la refleja; el diagnóstico (sesión + `license:view`) y la solicitud de activación la publican; `/health/*` y la
raíz pública no. Sin hash de commit en el producto y sin `.git` en tiempo de ejecución.
"""

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

import app as paquete
from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.main import create_app
from app.modules.licensing import service as licensing_service
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine
from tests.test_system_access import PASSWORD, _usuario

DIAGNOSTICO = "/api/v1/system/diagnostics"
_CLIENT: TestClient


@pytest.fixture(scope="module", autouse=True)
def _mundo():
    """Mundo propio (el de `test_system_access` solo existe dentro de su módulo): DEMO, `admin` y un
    `operador` con todo el catálogo menos `license:view`."""
    global _CLIENT
    import app.core.database as dm

    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    dm._engine, dm._SessionLocal = engine, factory  # type: ignore[attr-defined]
    with factory() as db:
        initialize(db, SetupRequest(tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1", company_legal_name="Demo C.A.",
                                    company_rif="J-12345678-9", admin_username="admin", admin_password=PASSWORD))
        tenant = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().one()
        empresa = db.execute(select(Company).where(Company.tenant_id == tenant.id)).scalars().one()
        _usuario(db, str(tenant.id), str(empresa.id), "operador", sin={"license:view"})
        db.commit()
    app = create_app()

    def _db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _db
    _CLIENT = TestClient(app)
    yield


def _sesion(username: str) -> dict[str, str]:
    r = login_completo(_CLIENT, "/api/v1/auth/login", json={"tenant_code": "DEMO", "username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

BACKEND = Path(__file__).resolve().parents[1]
RAIZ = BACKEND.parents[1]
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


# ---------------------------------------------------------------- VER-02 · la autoridad y su espejo
def test_ver_02_la_autoridad_es_el_paquete_y_pyproject_la_refleja():
    assert SEMVER.match(paquete.__version__), paquete.__version__
    assert get_settings().app_version == paquete.__version__  # sin literal duplicado en los ajustes
    pyproject = tomllib.loads((BACKEND / "pyproject.toml").read_text())
    assert pyproject["project"]["version"] == paquete.__version__  # las dos suben juntas; la imagen solo lleva `app/`
    assert "app_version" not in type(get_settings()).model_fields  # no es un ajuste: ninguna variable de entorno la cambia


def test_ver_02b_el_entorno_no_puede_declarar_otra_version(monkeypatch):
    monkeypatch.setenv("KONTROL_APP_VERSION", "9.9.9")
    get_settings.cache_clear()
    try:
        assert get_settings().app_version == paquete.__version__
    finally:
        get_settings.cache_clear()


# ---------------------------------------------------------------- VER-03 · quién la publica y quién no
def test_ver_03_el_diagnostico_publica_la_version_del_paquete_con_sesion_y_permiso():
    r = _CLIENT.get(DIAGNOSTICO, headers=_sesion("admin"))
    assert r.status_code == 200 and r.json()["version"] == paquete.__version__
    assert r.json()["version"].strip() != ""


def test_ver_13_la_raiz_publica_y_los_health_no_publican_la_version():
    raiz = _CLIENT.get("/")
    assert raiz.status_code == 200 and set(raiz.json()) == {"service", "status"} and paquete.__version__ not in raiz.text
    for ruta in ("/api/v1/health/live", "/api/v1/health/ready"):
        r = _CLIENT.get(ruta)
        assert r.status_code == 200 and "version" not in r.text and paquete.__version__ not in r.text
    assert _CLIENT.get(DIAGNOSTICO).status_code == 401  # sin sesión no hay versión
    sin_permiso = _CLIENT.get(DIAGNOSTICO, headers=_sesion("operador"))
    assert sin_permiso.status_code == 403 and paquete.__version__ not in sin_permiso.text  # con sesión pero sin `license:view`, tampoco


def test_ver_03b_la_solicitud_de_activacion_lleva_la_version_del_producto():
    instalacion = Installation(installation_uuid="KTL-XX-VER", public_key="-----BEGIN PUBLIC KEY-----\nsintetica\n-----END PUBLIC KEY-----\n", state="ACTIVE")
    assert licensing_service.installation_request_payload(instalacion)["version"] == paquete.__version__


# ---------------------------------------------------------------- VER-16 · cambiar la autoridad cambia la salida sin tocar la cadena
def test_ver_16_una_version_nueva_en_la_autoridad_llega_al_diagnostico_sin_editar_la_cadena(monkeypatch):
    monkeypatch.setattr(paquete, "__version__", "7.3.1")
    get_settings.cache_clear()
    try:
        assert get_settings().app_version == "7.3.1"
        assert _CLIENT.get(DIAGNOSTICO, headers=_sesion("admin")).json()["version"] == "7.3.1"
        assert "7.3.1" not in _CLIENT.get("/").text
    finally:
        get_settings.cache_clear()


# ---------------------------------------------------------------- VER-08 / VER-09 · sin hash de commit ni `.git` en tiempo de ejecución
def test_ver_08_ningun_hash_del_commit_actual_esta_escrito_en_el_producto():
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("sin repositorio Git: la guarda del hash solo aplica en desarrollo")
    producto = [*(BACKEND / "app").rglob("*.py"), *(RAIZ / "resources" / "frontend" / "src").rglob("*.ts*")]
    with_sha = [f for f in producto if sha[:7] in f.read_text(errors="ignore")]
    assert with_sha == []


def test_ver_09_el_producto_no_ejecuta_git_ni_depende_de_git_para_la_version():
    fuentes = "\n".join(f.read_text(errors="ignore") for f in (BACKEND / "app").rglob("*.py"))
    assert "rev-parse" not in fuentes and "git describe" not in fuentes and "GIT_SHA" not in fuentes


def test_ver_18_el_backend_arranca_con_la_version_del_paquete_sin_pyproject_ni_git(tmp_path, monkeypatch):
    """Lo que la imagen despliega: `app/` sin `pyproject.toml` ni `.git`; la versión sigue siendo la del paquete."""
    monkeypatch.chdir(tmp_path)  # ni pyproject ni .git alcanzables desde el cwd
    monkeypatch.delenv("GIT_DIR", raising=False)
    with TestClient(create_app()) as c:
        assert c.get("/").json() == {"service": get_settings().app_name, "status": "ok"}
    assert get_settings().app_version == paquete.__version__
