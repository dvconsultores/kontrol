"""MINV · La versión mínima firmada se verifica antes de aplicar la licencia.

(contrato de licencia §Reglas; Spec 004 delta MV-01..06) y PERF · perfil de instalación.
"""

from __future__ import annotations

import contextlib
import json
import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from mfa_mundo import CONTRASENA
from sesion_mfa import login_completo
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

import app.core.database as dm
from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Permission, Role, RolePermission, UserRole, UserScope
from app.modules.licensing import service as licensing_service
from app.modules.licensing.models import LicenseArtifact, LicenseEvent, LicenseState
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine

PASSWORD = CONTRASENA
ACTIVATE = "/api/v1/license/activate"
IMPORT = "/api/v1/license/import"
ANCLA = "KONTROL_LICENSE_PUBLIC_KEY_PEM"
CARACAS = timezone(timedelta(hours=-4))
#: El año del período vigente en el mundo del módulo: el que contiene hoy (FULL_ACCESS).
HOY = datetime.now(UTC).astimezone(CARACAS)
ANIO_VIGENTE = HOY.year if HOY.month >= 4 else HOY.year - 1
VERSION = get_settings().app_version

_CLIENT: TestClient
_FACTORY: sessionmaker
_PROPIETARIO: Ed25519PrivateKey
_INSTALACION: str


def _pem(clave: Ed25519PrivateKey) -> str:
    return clave.public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode()


def _usuario(db: Session, tenant_id: str, empresa: str, username: str, *, sin: set[str]) -> None:
    usuario = identity_service.create_user(
        db, tenant_id=tenant_id, username=username, email=f"{username}@demo.test",
        password=PASSWORD, must_change_password=False, created_by=None)
    rol = Role(code=f"ROL-{username}".upper(), name=f"ROL {username}", protected=False, status="ACTIVE")
    db.add(rol)
    db.flush()
    for p in db.query(Permission).all():
        if f"{p.resource}:{p.action}" not in sin:
            db.add(RolePermission(role_id=str(rol.id), permission_id=str(p.id)))
    db.add(UserRole(user_id=str(usuario.id), role_id=str(rol.id), company_id=None))
    db.add(UserScope(user_id=str(usuario.id), company_id=empresa))


def _anual(license_id: str, anio: int, *, instalacion: str | None = None, **extra) -> dict:
    """Una licencia del contrato: período 1 abr <anio> → 31 mar <anio+1>, aviso crítico 21 abr, solo lectura 1 may."""
    return {
        "issuer": "QA", "license_id": license_id, "installation_id": instalacion or _INSTALACION,
        "customer_id": "C-TEST", "contract_id": "K-TEST", "company_tax_id": "J-00000000-0",
        "period_start": f"{anio}-04-01T00:00:00-04:00", "period_end": f"{anio + 1}-03-31T23:59:59-04:00",
        "critical_warning_start": f"{anio + 1}-04-21T00:00:00-04:00", "read_only_start": f"{anio + 1}-05-01T00:00:00-04:00",
        "entitlements": {"companies": 3, "users": 25}, "minimum_version": "1.0.0", "kid": "kontrol-lic-2026-01", **extra,
    }


def _firmada(payload: dict, clave: Ed25519PrivateKey | None = None) -> dict:
    canonico = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return {"payload": payload, "signature_hex": (clave or _PROPIETARIO).sign(canonico).hex()}


def _hash(payload: dict) -> str:
    import hashlib

    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


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
    r = login_completo(_CLIENT, "/api/v1/auth/login", json={"tenant_code": "DEMO", "username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _huella() -> dict:
    """Todo lo que una importación puede mover, para afirmar que un rechazo no mueve nada."""
    with _FACTORY() as db:
        s = db.execute(select(LicenseState)).scalars().first()
        ultimo = db.execute(select(LicenseArtifact).order_by(LicenseArtifact.imported_at.desc())).scalars().first()
        inst = db.execute(select(Installation)).scalars().one()
        return {
            "license_id": s.license_id if s else None, "mode": s.mode if s else None,
            "period": (s.period_start, s.period_end) if s else None, "entitlements": s.entitlements if s else None,
            "artefacto": ultimo.payload_hash if ultimo else None, "artefactos": db.execute(select(func.count()).select_from(LicenseArtifact)).scalar(),
            "eventos": db.execute(select(func.count()).select_from(LicenseEvent)).scalar(),
            "instalacion": (inst.installation_uuid, inst.public_key),
        }


def _eventos(tipo: str) -> list[LicenseEvent]:
    with _FACTORY() as db:
        return list(db.execute(select(LicenseEvent).where(LicenseEvent.event_type == tipo)).scalars().all())


def _importa(payload: dict, quien: str = "admin", ruta: str = IMPORT, clave: Ed25519PrivateKey | None = None):
    return _CLIENT.post(ruta, json=_firmada(payload, clave), headers=_sesion(quien))


def test_minv_01_sin_version_minima_entra():
    payload = _anual("LIC-MV-01", ANIO_VIGENTE)
    payload.pop("minimum_version")
    r = _importa(payload, ruta=ACTIVATE)
    assert r.status_code == 200, r.text


def test_minv_02_igual_a_la_version_en_ejecucion_entra():
    r = _importa(_anual("LIC-MV-02", ANIO_VIGENTE + 1, minimum_version=VERSION))
    assert r.status_code == 200, r.text


def test_minv_03_menor_entra():
    r = _importa(_anual("LIC-MV-03", ANIO_VIGENTE + 2, minimum_version="0.9.9"))
    assert r.status_code == 200, r.text
    with _FACTORY() as db:
        estado = db.execute(select(LicenseState)).scalars().one()
        assert estado.minimum_version == "0.9.9"


def test_minv_04_mayor_se_rechaza_sin_tocar_nada():
    partes = [int(p) for p in VERSION.split(".")]
    candidatas = [f"{partes[0] + 1}.0.0", f"{partes[0]}.{partes[1] + 1}.0", f"{partes[0]}.{partes[1]}.{partes[2] + 1}"]
    ultimo_v = None
    for v in candidatas:
        antes = _huella()
        r = _importa(_anual("LIC-MV-04", ANIO_VIGENTE + 10, minimum_version=v))
        assert r.status_code == 423, r.text
        assert r.json()["code"] == "LICENSE_MINIMUM_VERSION_INCOMPATIBLE", r.text
        despues = _huella()
        assert {k: v for k, v in despues.items() if k != "eventos"} == {k: v for k, v in antes.items() if k != "eventos"}
        assert despues["eventos"] == antes["eventos"] + 1
        ultimo_v = v
    ultimas = _eventos("LICENSE_MINIMUM_VERSION_REJECTED")
    ultimo = ultimas[-1]
    assert ultimo.detail == {"license_id": "LIC-MV-04", "minimum_version": ultimo_v, "running_version": VERSION,
                             "outcome": "INCOMPATIBLE"}
    assert "signature" not in json.dumps(ultimo.detail)


def test_minv_05_comparacion_numerica_no_lexicografica():
    from app.core import license_contract

    assert license_contract.minimum_version_satisfied("1.9.0", "1.10.0") is True
    assert license_contract.minimum_version_satisfied("1.10.0", "1.9.0") is False
    assert license_contract.minimum_version_satisfied(None, "1.0.0") is True
    assert license_contract.minimum_version_satisfied("1.0.0", "1.0.0") is True


def test_minv_06_formato_invalido_se_rechaza():
    invalidos = ["1.0", "v1.0.0", "1.0.0-beta", "01.0.0", "", " 1.0.0", 100, True, ["1.0.0"]]
    for valor in invalidos:
        antes = _huella()
        r = _importa(_anual("LIC-MV-06", ANIO_VIGENTE + 11, minimum_version=valor))
        assert r.status_code == 423, r.text
        assert r.json()["code"] == "LICENSE_INVALID_MINIMUM_VERSION", r.text
        despues = _huella()
        assert {k: v for k, v in despues.items() if k != "eventos"} == {k: v for k, v in antes.items() if k != "eventos"}
        assert despues["eventos"] == antes["eventos"] + 1
        ultimas = _eventos("LICENSE_MINIMUM_VERSION_REJECTED")
        ultimo = ultimas[-1]
        assert ultimo.detail["outcome"] == "INVALID"
        assert ultimo.detail["minimum_version"] is None


def test_minv_07_las_compuertas_anteriores_van_primero():
    payload = _anual("LIC-MV-07", ANIO_VIGENTE + 12, minimum_version="99.0.0")
    r = _importa(payload, clave=Ed25519PrivateKey.generate())
    assert r.status_code == 423, r.text
    assert r.json()["code"] == "LICENSE_SIGNATURE_INVALID", r.text

    payload_falso = _anual("LIC-MV-07", ANIO_VIGENTE + 12, instalacion="00000000-0000-0000-0000-000000000000",
                           minimum_version="99.0.0")
    r = _importa(payload_falso)
    assert r.status_code == 423, r.text
    assert r.json()["code"] == "LICENSE_INSTALLATION_MISMATCH", r.text


def test_minv_08_el_anti_retroceso_va_antes():
    r = _importa(_anual("LIC-MV-08", ANIO_VIGENTE - 5, minimum_version="99.0.0"))
    assert r.status_code == 423, r.text
    assert r.json()["code"] == "LICENSE_PERIOD_DOWNGRADE", r.text


def test_perf_01_04_perfil_por_derechos_firmados():
    casos = [
        (["gobierno"], True, "GOBIERNO"),
        (["gobierno", "ventas"], True, "MIXTO"),
        (["reportes"], False, "EMPRESA"),
        ([], False, "EMPRESA"),
        ({"gobierno": True, "ventas": False}, True, "GOBIERNO"),
    ]
    with _FACTORY() as db:
        estado = db.execute(select(LicenseState)).scalars().one()
        original = estado.entitlements
    try:
        for modules, habilitado, perfil in casos:
            with _FACTORY() as db:
                estado = db.execute(select(LicenseState)).scalars().one()
                estado.entitlements = {"modules": modules}
                db.commit()
                assert licensing_service.perfil_de_instalacion(db) == perfil
            r = _CLIENT.get("/api/v1/gobierno/modulo", headers=_sesion("admin"))
            assert r.status_code == 200, r.text
            assert r.json() == {"habilitado": habilitado, "perfil": perfil}, r.text
    finally:
        with _FACTORY() as db:
            estado = db.execute(select(LicenseState)).scalars().one()
            estado.entitlements = original
            db.commit()


def test_perf_05_la_lectura_del_perfil_no_exige_permiso_de_pantalla():
    with _FACTORY() as db:
        estado = db.execute(select(LicenseState)).scalars().one()
        entitlements_originales = estado.entitlements
        estado.entitlements = {"modules": ["gobierno"]}
        db.commit()
    try:
        r = _CLIENT.get("/api/v1/gobierno/modulo", headers=_sesion("lector"))
        assert r.status_code == 200, r.text
        assert r.json() == {"habilitado": True, "perfil": "GOBIERNO"}, r.text
    finally:
        with _FACTORY() as db:
            estado = db.execute(select(LicenseState)).scalars().one()
            estado.entitlements = entitlements_originales
            db.commit()


@contextlib.contextmanager
def _con_modulos(modules: list[str]) -> Iterator[None]:
    with _FACTORY() as db:
        estado = db.execute(select(LicenseState)).scalars().one()
        original = estado.entitlements
        estado.entitlements = {"modules": modules}
        db.commit()
    try:
        yield
    finally:
        with _FACTORY() as db:
            estado = db.execute(select(LicenseState)).scalars().one()
            estado.entitlements = original
            db.commit()


def test_penf_01_gobierno_deniega_lo_empresarial() -> None:
    with _con_modulos(["gobierno"]):
        for ruta in ["/api/v1/sales/orders", "/api/v1/purchasing/requisitions", "/api/v1/maestros/terceros", "/api/v1/organization/branches"]:
            r = _CLIENT.get(ruta, headers=_sesion("admin"))
            assert r.status_code == 403, r.text
            assert r.json()["code"] == "PRODUCT_PROFILE_DENIED", r.text

        for ruta in ["/api/v1/organization/companies", "/api/v1/license/detail", "/api/v1/gobierno/modulo"]:
            r = _CLIENT.get(ruta, headers=_sesion("admin"))
            assert r.status_code == 200, r.text

        r = _CLIENT.get("/api/v1/gobierno/ente", headers=_sesion("admin"))
        assert r.status_code in {200, 404}, r.text


def test_penf_02_mixto_exige_cada_derecho() -> None:
    with _con_modulos(["gobierno", "ventas"]):
        r = _CLIENT.get("/api/v1/sales/orders", headers=_sesion("admin"))
        assert r.status_code == 200, r.text

        r = _CLIENT.get("/api/v1/purchasing/requisitions", headers=_sesion("admin"))
        assert r.status_code == 403, r.text
        assert r.json()["code"] == "MODULE_NOT_ENTITLED", r.text

        r = _CLIENT.get("/api/v1/maestros/terceros", headers=_sesion("admin"))
        assert r.status_code == 200, r.text

        r = _CLIENT.get("/api/v1/organization/branches", headers=_sesion("admin"))
        assert r.status_code == 200, r.text


def test_penf_03_empresa_sin_cambio() -> None:
    for modules in [[], ["reportes"]]:
        with _con_modulos(modules):
            for ruta in ["/api/v1/sales/orders", "/api/v1/purchasing/requisitions", "/api/v1/maestros/terceros"]:
                r = _CLIENT.get(ruta, headers=_sesion("admin"))
                assert r.status_code == 200, r.text

            r = _CLIENT.get("/api/v1/gobierno/ente", headers=_sesion("admin"))
            assert r.status_code == 403, r.text
            assert r.json()["code"] == "MODULE_NOT_ENTITLED", r.text


def test_penf_04_el_permiso_sigue_mandando() -> None:
    modules = ["gobierno", "ventas", "compras", "inventario", "tesoreria", "fiscal", "regulatorio", "reportes"]
    with _con_modulos(modules):
        r = _CLIENT.get("/api/v1/sales/orders")
        assert r.status_code in {401, 403}, r.text
        assert r.status_code != 200, r.text


def test_penf_06_homologacion_y_aprobaciones_son_empresariales() -> None:
    with _con_modulos(["gobierno"]):
        for ruta in ["/api/v1/approvals/process-types", "/api/v1/homologation/records"]:
            r = _CLIENT.get(ruta, headers=_sesion("admin"))
            assert r.status_code == 403, r.text
            assert r.json()["code"] == "PRODUCT_PROFILE_DENIED", r.text

    with _con_modulos(["gobierno", "ventas"]):
        for ruta in ["/api/v1/approvals/process-types", "/api/v1/homologation/records"]:
            r = _CLIENT.get(ruta, headers=_sesion("admin"))
            assert r.status_code != 403 or r.json().get("code") != "PRODUCT_PROFILE_DENIED", r.text


def test_penf_05_inventario_de_superficies() -> None:
    from fastapi.routing import APIRoute, iter_route_contexts

    from app.main import create_app

    def recoger(dep: Any, encontradas: list[Any]) -> None:
        for d in dep.dependencies:
            encontradas.append(d.call)
            recoger(d, encontradas)

    app = create_app()
    prefijos_empresariales = (
        "/api/v1/sales", "/api/v1/purchasing", "/api/v1/inventory", "/api/v1/planning",
        "/api/v1/storage", "/api/v1/importaciones", "/api/v1/fiscal", "/api/v1/regulatory",
        "/api/v1/reporting", "/api/v1/treasury", "/api/v1/comercial", "/api/v1/maestros",
        "/api/v1/homologation", "/api/v1/approvals", "/api/v1/organization/branches", "/api/v1/organization/establishments",
        "/api/v1/organization/aisles", "/api/v1/organization/levels", "/api/v1/organization/location-types", "/api/v1/organization/locations",
        "/api/v1/organization/racks", "/api/v1/organization/warehouses", "/api/v1/organization/zone-types", "/api/v1/organization/zones",
    )
    enterprise: list[str] = []
    government: list[str] = []
    for contexto in iter_route_contexts(app.routes):
        if not isinstance(contexto.route, APIRoute) or not contexto.path.startswith("/api/v1/"):
            continue
        calls: list[Any] = []
        recoger(contexto.dependant, calls)
        is_enterprise = any(getattr(call, "kontrol_surface", None) == "ENTERPRISE" for call in calls)
        is_government = any(getattr(call, "kontrol_module", None) == "gobierno" for call in calls)
        assert not (is_enterprise and is_government), contexto.path
        if is_enterprise:
            enterprise.append(contexto.path)
        if is_government:
            government.append(contexto.path)

    faltan = [r for r in enterprise if not any(r.startswith(p) for p in prefijos_empresariales)]
    assert not faltan, faltan

    prohibidos = ("/api/v1/organization/companies", "/api/v1/license", "/api/v1/auth", "/api/v1/gobierno")
    invalidos = [r for r in enterprise if r.startswith(prohibidos)]
    assert not invalidos, invalidos
    assert len(enterprise) >= 50, len(enterprise)
    assert len(government) >= 50, len(government)


def test_mvr_01_reverificacion_de_version_minima_en_el_vigente(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _anual("LIC-MVR-01", ANIO_VIGENTE + 30, minimum_version="1.0.0")
    r = _importa(payload, ruta=ACTIVATE)
    assert r.status_code == 200, r.text

    with _FACTORY() as db:
        artefacto = db.execute(select(LicenseArtifact).order_by(LicenseArtifact.imported_at.desc())).scalars().first()
        assert artefacto is not None
        hash_original = artefacto.payload_hash

    monkeypatch.setattr("app.__version__", "0.9.0")
    r = _CLIENT.get("/api/v1/license/detail", headers=_sesion("admin"))
    assert r.status_code == 200, r.text
    assert r.json()["mode"] == "SECURITY_SUSPENSION", r.text
    assert r.json()["verification"] == "MINIMUM_VERSION_INCOMPATIBLE", r.text

    r = _CLIENT.post("/api/v1/organization/companies", json={}, headers=_sesion("admin"))
    assert r.status_code == 423, r.text
    assert r.json()["code"] == "LICENSE_SECURITY_SUSPENSION", r.text

    evento = _eventos("LICENSE_STATE_REVERIFICATION_FAILED")[-1]
    assert evento.detail["status"] == "MINIMUM_VERSION_INCOMPATIBLE", evento.detail
    assert evento.detail["license_id"] == "LIC-MVR-01", evento.detail

    with _FACTORY() as db:
        artefacto = db.execute(select(LicenseArtifact).order_by(LicenseArtifact.imported_at.desc())).scalars().first()
        assert artefacto.payload_hash == hash_original

    monkeypatch.setattr("app.__version__", VERSION)
    r = _CLIENT.get("/api/v1/license/detail", headers=_sesion("admin"))
    assert r.status_code == 200, r.text
    assert r.json()["verification"] == "VALID", r.text
    assert r.json()["mode"] != "SECURITY_SUSPENSION", r.text
