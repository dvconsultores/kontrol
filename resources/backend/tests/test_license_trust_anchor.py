"""TRUST · La licencia se verifica solo contra la clave del propietario (LICENCIA-ANCLA-AUTOFIRMADA,
FR-010-148..171).

`import_license` usaba, si no había clave del propietario configurada, la clave pública de la
propia instalación como ancla de confianza: una licencia firmada con la clave privada del
servidor —que la instalación genera y guarda— se aceptaba, también en `prod`. Ahora el ancla es
únicamente `KONTROL_LICENSE_PUBLIC_KEY_PEM`; si falta o no sirve, la importación falla cerrada
(503) sin sustituto, sin evento y sin generar nada; en `prod` la configuración no carga sin ella.
La clave de la instalación conserva su papel: identificarla.

Mundo del módulo (`local`): `initialize`, `admin` con todo, `lector` con todo menos
`license:create`; ancla del propietario SINTÉTICA inyectada en el entorno; se quita y se
sustituye por prueba para recorrer la matriz. Licencias sintéticas.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

import app.core.database as dm
from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Permission, Role, RolePermission, UserRole, UserScope
from app.modules.licensing.models import LicenseEvent, LicenseState
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine

PASSWORD = "Kontrol2026Segura!"
ACTIVATE = "/api/v1/license/activate"
IMPORT = "/api/v1/license/import"
ANCLA = "KONTROL_LICENSE_PUBLIC_KEY_PEM"
#: Material que ningún rechazo, registro ni cuerpo puede llevar (FR-010-156, TEST-09).
MATERIAL = ("BEGIN PUBLIC KEY", "BEGIN PRIVATE KEY", "MCowBQYDK2Vw", "installation_private_key", "/tmp", "/data", "signature_hex")

_CLIENT: TestClient
_FACTORY: sessionmaker
_PROPIETARIO: Ed25519PrivateKey
_INSTALACION: str


def _pem(clave: Ed25519PrivateKey) -> str:
    return clave.public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode()


def _pem_rsa() -> str:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048).public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode()


def _usuario(db: Session, tenant_id: str, empresa: str, username: str, *, sin: set[str]) -> None:
    usuario = identity_service.create_user(
        db, tenant_id=tenant_id, username=username, email=f"{username}@demo.test",
        password=PASSWORD, must_change_password=False, created_by=None)
    rol = Role(code=f"TRU-{username}".upper(), name=f"TRU {username}", protected=False, status="ACTIVE")
    db.add(rol)
    db.flush()
    for p in db.query(Permission).all():
        if f"{p.resource}:{p.action}" not in sin:
            db.add(RolePermission(role_id=str(rol.id), permission_id=str(p.id)))
    db.add(UserRole(user_id=str(usuario.id), role_id=str(rol.id), company_id=None))
    db.add(UserScope(user_id=str(usuario.id), company_id=empresa))


#: Período congelado para todo el módulo: las licencias sintéticas son reemisiones del mismo
#: período (Fase A de LICENCIA-DOWNGRADE-FIRMADO), no retrocesos por segundos de diferencia.
AHORA = datetime.now(UTC).replace(microsecond=0)


def _licencia(license_id: str, instalacion: str, **extra) -> dict:
    ahora = AHORA
    return {
        "issuer": "QA", "license_id": license_id, "installation_id": instalacion,
        "customer_id": "C-TEST", "contract_id": "K-TEST", "company_tax_id": "J-00000000-0",
        "period_start": (ahora - timedelta(days=30)).isoformat(), "period_end": (ahora + timedelta(days=300)).isoformat(),
        "critical_warning_start": (ahora + timedelta(days=320)).isoformat(), "read_only_start": (ahora + timedelta(days=330)).isoformat(),
        "entitlements": {}, "minimum_version": "1.0.0", "kid": "kontrol-lic-2026-01", **extra,
    }


def _firmada(payload: dict, clave: Ed25519PrivateKey) -> dict:
    canonico = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return {"payload": payload, "signature_hex": clave.sign(canonico).hex()}


def _clave_de_la_instalacion() -> Ed25519PrivateKey:
    """La clave privada que la propia instalación generó y guardó en su volumen."""
    ruta = os.path.join(get_settings().installation_volume_path, "installation_private_key.pem")
    clave = serialization.load_pem_private_key(open(ruta, "rb").read(), password=None)
    assert isinstance(clave, Ed25519PrivateKey)
    return clave


@contextmanager
def _ancla(valor: str | None) -> Iterator[None]:
    """Configura (o quita) el ancla del propietario para lo que dure el bloque."""
    anterior = os.environ.get(ANCLA)
    if valor is None:
        os.environ.pop(ANCLA, None)
    else:
        os.environ[ANCLA] = valor
    get_settings.cache_clear()
    try:
        yield
    finally:
        if anterior is None:
            os.environ.pop(ANCLA, None)
        else:
            os.environ[ANCLA] = anterior
        get_settings.cache_clear()


@pytest.fixture(scope="module", autouse=True)
def _app_client():
    global _CLIENT, _FACTORY, _PROPIETARIO, _INSTALACION
    _PROPIETARIO = Ed25519PrivateKey.generate()
    anterior = os.environ.get(ANCLA)
    os.environ[ANCLA] = _pem(_PROPIETARIO)
    get_settings.cache_clear()
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
        _usuario(db, str(tenant.id), str(empresa.id), "lector", sin={"license:create"})
        _INSTALACION = db.execute(select(Installation)).scalars().first().installation_uuid
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
    _CLIENT, _FACTORY = TestClient(app, raise_server_exceptions=False), factory
    try:
        yield _CLIENT
    finally:
        if anterior is None:
            os.environ.pop(ANCLA, None)
        else:
            os.environ[ANCLA] = anterior
        get_settings.cache_clear()


def _sesion(username: str) -> dict[str, str]:
    r = _CLIENT.post("/api/v1/auth/login", json={"tenant_code": "DEMO", "username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _estado() -> tuple[str | None, int]:
    with _FACTORY() as db:
        s = db.execute(select(LicenseState)).scalars().first()
        n = db.execute(select(func.count()).select_from(LicenseEvent)).scalar()
        return (s.license_id if s else None, int(n or 0))


def _sin_material(texto: str) -> None:
    for trozo in MATERIAL:
        assert trozo not in texto, trozo


# ---------------------------------------------------------------- PROD-01 · con el ancla del propietario, la licencia entra
def test_trust_01_con_el_ancla_del_propietario_una_licencia_suya_se_acepta():
    r = _CLIENT.post(ACTIVATE, json=_firmada(_licencia("LIC-PROPIETARIO", _INSTALACION), _PROPIETARIO), headers=_sesion("admin"))
    assert r.status_code == 200 and r.json()["mode"] == "FULL_ACCESS", r.text
    assert _estado()[0] == "LIC-PROPIETARIO"


# ---------------------------------------------------------------- PROD-02/03 · sin ancla: cerrado, sin sustituto
def test_trust_02_sin_ancla_la_importacion_falla_cerrada_sin_evento_y_sin_sustituto():
    antes = _estado()
    cuerpo = _firmada(_licencia("LIC-SIN-ANCLA", _INSTALACION), _PROPIETARIO)
    with _ancla(None):
        r = _CLIENT.post(ACTIVATE, json=cuerpo, headers=_sesion("admin"))
    assert r.status_code == 503 and r.json()["code"] == "LICENSE_TRUST_ANCHOR_MISSING", r.text
    assert r.json()["details"] is None
    _sin_material(r.text)
    assert _estado() == antes  # ni estado ni evento: no es un artefacto malo, es una instalación sin ancla


def test_trust_03_sin_ancla_una_licencia_firmada_con_la_clave_de_la_propia_instalacion_se_rechaza():
    antes = _estado()
    autofirmada = _firmada(_licencia("LIC-AUTOFIRMADA", _INSTALACION, entitlements={"companies": 999}), _clave_de_la_instalacion())
    with _ancla(None):
        for ruta in (ACTIVATE, IMPORT):
            r = _CLIENT.post(ruta, json=autofirmada, headers=_sesion("admin"))
            assert r.status_code == 503 and r.json()["code"] == "LICENSE_TRUST_ANCHOR_MISSING", (ruta, r.text)
    assert _estado() == antes


def test_trust_03b_con_ancla_del_propietario_la_autofirmada_tampoco_entra():
    antes = _estado()
    r = _CLIENT.post(ACTIVATE, json=_firmada(_licencia("LIC-AUTOFIRMADA", _INSTALACION), _clave_de_la_instalacion()), headers=_sesion("admin"))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_SIGNATURE_INVALID", r.text
    assert _estado()[0] == antes[0]


# ---------------------------------------------------------------- PROD-04/05 · otro propietario, otra instalación
def test_trust_04_una_licencia_firmada_por_otra_autoridad_se_rechaza():
    antes = _estado()
    otra = Ed25519PrivateKey.generate()
    r = _CLIENT.post(ACTIVATE, json=_firmada(_licencia("LIC-AJENA", _INSTALACION), otra), headers=_sesion("admin"))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_SIGNATURE_INVALID", r.text
    assert _estado()[0] == antes[0]


def test_trust_04b_una_clave_publica_dentro_del_artefacto_no_se_convierte_en_ancla():
    """El atacante firma con su clave y la pega en el payload: el ancla es la configurada, no la del artefacto."""
    antes = _estado()
    otra = Ed25519PrivateKey.generate()
    payload = _licencia("LIC-TRAE-SU-CLAVE", _INSTALACION, public_key=_pem(otra), trust_anchor=_pem(otra))
    r = _CLIENT.post(IMPORT, json=_firmada(payload, otra), headers=_sesion("admin"))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_SIGNATURE_INVALID", r.text
    assert _estado()[0] == antes[0]


def test_trust_05_una_licencia_del_propietario_para_otra_instalacion_se_rechaza():
    antes = _estado()
    r = _CLIENT.post(ACTIVATE, json=_firmada(_licencia("LIC-OTRA", "KTL-XX-OTRA-INSTALACION"), _PROPIETARIO), headers=_sesion("admin"))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_INSTALLATION_MISMATCH", r.text
    assert _estado()[0] == antes[0]


# ---------------------------------------------------------------- PROD-06/07 · las dos compuertas, en orden
def test_trust_06_07_la_autorizacion_del_llamador_va_antes_que_el_ancla_y_sigue_igual():
    antes = _estado()
    cuerpo = _firmada(_licencia("LIC-ORDEN", _INSTALACION), _PROPIETARIO)
    with _ancla(None):
        # Sin ancla, un anónimo o un lector reciben su 401/403: el ancla no se consulta antes de autorizar.
        assert _CLIENT.post(ACTIVATE, json=cuerpo).status_code == 401
        assert _CLIENT.post(ACTIVATE, json=cuerpo, headers=_sesion("lector")).status_code == 403
        assert _CLIENT.post(ACTIVATE, json=cuerpo, headers=_sesion("admin")).status_code == 503
    assert _CLIENT.post(ACTIVATE, json=cuerpo, headers=_sesion("lector")).status_code == 403
    r = _CLIENT.post(ACTIVATE, json=cuerpo, headers=_sesion("admin"))
    assert r.status_code == 200, r.text
    assert _estado()[1] == antes[1] + 1  # solo la importación autorizada y verificada deja evento


# ---------------------------------------------------------------- TEST-10/11 · un ancla rota no cae en nada
@pytest.mark.parametrize("ancla,motivo", [
    ("esto no es una clave", "INVALID"),
    ("-----BEGIN PUBLIC KEY-----\nQUJD\n-----END PUBLIC KEY-----\n", "INVALID"),
    ("   ", "MISSING"),
])
def test_trust_10_un_ancla_malformada_falla_cerrada_sin_caer_en_la_clave_de_la_instalacion(ancla, motivo):
    antes = _estado()
    with _ancla(ancla):
        propia = _CLIENT.post(ACTIVATE, json=_firmada(_licencia("LIC-X", _INSTALACION), _clave_de_la_instalacion()), headers=_sesion("admin"))
        ajena = _CLIENT.post(IMPORT, json=_firmada(_licencia("LIC-Y", _INSTALACION), _PROPIETARIO), headers=_sesion("admin"))
    for r in (propia, ajena):
        assert r.status_code == 503 and r.json()["code"] == f"LICENSE_TRUST_ANCHOR_{motivo}", r.text
        _sin_material(r.text)
    assert _estado() == antes


def test_trust_10b_una_clave_que_no_es_ed25519_falla_cerrada_sin_500():
    antes = _estado()
    with _ancla(_pem_rsa()):
        r = _CLIENT.post(ACTIVATE, json=_firmada(_licencia("LIC-RSA", _INSTALACION), _PROPIETARIO), headers=_sesion("admin"))
    assert r.status_code == 503 and r.json()["code"] == "LICENSE_TRUST_ANCHOR_INVALID", r.text
    assert _estado() == antes


def test_trust_11_sin_ancla_el_backend_no_se_fabrica_una_ni_toca_el_volumen():
    volumen = get_settings().installation_volume_path
    ficheros = sorted(os.listdir(volumen))
    with _ancla(None):
        assert get_settings().license_public_key_pem is None
        _CLIENT.post(ACTIVATE, json=_firmada(_licencia("LIC-Z", _INSTALACION), _PROPIETARIO), headers=_sesion("admin"))
        assert get_settings().license_public_key_pem is None
    assert sorted(os.listdir(volumen)) == ficheros == ["installation_private_key.pem"]


# ---------------------------------------------------------------- TEST-12 · la clave de la instalación sigue siendo identidad
def test_trust_12_la_clave_de_la_instalacion_conserva_su_papel_y_no_cambia():
    with _FACTORY() as db:
        fila = db.execute(select(Installation)).scalars().one()
    assert fila.public_key == _pem(_clave_de_la_instalacion())
    r = _CLIENT.get("/api/v1/license/installation-request", headers=_sesion("admin"))
    assert r.status_code == 200 and r.json()["public_key"] == fila.public_key and r.json()["installation_id"] == _INSTALACION
    with _ancla(None):
        _CLIENT.post(ACTIVATE, json=_firmada(_licencia("LIC-W", _INSTALACION), _PROPIETARIO), headers=_sesion("admin"))
    with _FACTORY() as db:
        assert db.execute(select(Installation)).scalars().one().public_key == fila.public_key


# ---------------------------------------------------------------- TEST-09 · nada de material en los registros
def test_trust_09_los_registros_no_llevan_material_de_clave_ni_firma(caplog):
    with caplog.at_level(logging.DEBUG), _ancla(None):
        _CLIENT.post(ACTIVATE, json=_firmada(_licencia("LIC-LOG", _INSTALACION), _PROPIETARIO), headers=_sesion("admin"))
    with caplog.at_level(logging.DEBUG), _ancla("basura"):
        _CLIENT.post(ACTIVATE, json=_firmada(_licencia("LIC-LOG2", _INSTALACION), _PROPIETARIO), headers=_sesion("admin"))
    texto = "\n".join(f"{r.name} {r.getMessage()}" for r in caplog.records)
    assert "ancla de confianza del propietario missing" in texto and "ancla de confianza del propietario invalid" in texto
    _sin_material(texto)
    assert "basura" not in texto and _pem(_PROPIETARIO).splitlines()[1] not in texto


# ---------------------------------------------------------------- TEST-06..08 · lo cerrado sigue cerrado
def test_trust_06_08_estado_publico_diagnostico_y_health_sin_cambios():
    with _ancla(None):
        r = _CLIENT.get("/api/v1/license/status")
        assert r.status_code == 200 and set(r.json()) == {"mode", "license_url"}
        _sin_material(r.text)
        assert "ANCHOR" not in r.text and "anchor" not in r.text
        assert _CLIENT.get("/api/v1/health/live").json() == {"status": "ok", "service": "kontrol-backend"}
        assert _CLIENT.get("/api/v1/health/ready").json() == {"status": "ok", "service": "kontrol-backend", "database": "ok"}
    assert _CLIENT.get("/api/v1/system/diagnostics").status_code == 401
    assert _CLIENT.get("/api/v1/system/diagnostics", headers=_sesion("lector")).status_code == 200
