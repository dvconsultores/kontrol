"""ROLLA · Una licencia de período anterior no sustituye a la vigente (LICENCIA-DOWNGRADE-FIRMADO
Fase A, FR-010-200..224).

Compuertas 1 (sesión + `license:create`) y 2 (ancla del propietario) siguen delante. La tercera
compara **solo el período firmado** con el estado vigente, releído bajo bloqueo: anterior → 423
`LICENSE_PERIOD_DOWNGRADE` sin tocar nada; posterior → se aplica; el mismo período se acepta como
reemisión (DOC-07 §7.1), riesgo residual `LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN`.

Mundo del módulo (`local`): `initialize`, `admin` con todo, `lector` con todo menos
`license:create`; ancla sintética en el entorno; licencias anuales del contrato (1 abr → 31 mar,
`America/Caracas`) firmadas aquí. La concurrencia se prueba en `test_license_import_race.py`.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

import app.core.database as dm
from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Permission, Role, RolePermission, User, UserRole, UserScope
from app.modules.licensing.models import LicenseArtifact, LicenseEvent, LicenseState
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine

PASSWORD = "Kontrol2026Segura!"
ACTIVATE = "/api/v1/license/activate"
IMPORT = "/api/v1/license/import"
ANCLA = "KONTROL_LICENSE_PUBLIC_KEY_PEM"
CARACAS = timezone(timedelta(hours=-4))
#: El año del período vigente en el mundo del módulo: el que contiene hoy (FULL_ACCESS).
HOY = datetime.now(UTC).astimezone(CARACAS)
ANIO_VIGENTE = HOY.year if HOY.month >= 4 else HOY.year - 1

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


def _simular_licencia_antigua(license_id: str, *, inicio_en_dias: int, fin_en_dias: int, critico_en_dias: int, solo_lectura_en_dias: int) -> None:
    """Simula que el tiempo pasó sobre una licencia **coherente** (las cuatro fechas y su identificador),
    escribiendo el estado como lo habría dejado una importación de hace meses: así el servidor calcula
    otro modo temporal y el período sigue siendo un período del contrato."""
    with _FACTORY() as db:
        estado = db.execute(select(LicenseState)).scalars().one()
        ahora = datetime.now(UTC)
        estado.license_id = license_id
        estado.period_start = ahora + timedelta(days=inicio_en_dias)
        estado.period_end = ahora + timedelta(days=fin_en_dias)
        estado.critical_warning_start = ahora + timedelta(days=critico_en_dias)
        estado.read_only_start = ahora + timedelta(days=solo_lectura_en_dias)
        db.commit()


def _restaurar(anio: int, license_id: str = "LIC-VIGENTE") -> None:
    """Vuelve a dejar el estado del módulo en la licencia del año dado (posterior o igual al vigente)."""
    r = _importa(_anual(license_id, anio))
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------- ROLLA-01..04 · lo que entra
def test_rolla_01_primera_activacion_sin_licencia_vigente():
    assert _huella()["license_id"] is None
    r = _importa(_anual("LIC-VIGENTE", ANIO_VIGENTE), ruta=ACTIVATE)
    assert r.status_code == 200 and r.json() == {"ok": True, "license_id": "LIC-VIGENTE", "mode": "FULL_ACCESS"}, r.text
    assert _huella()["license_id"] == "LIC-VIGENTE"


def test_rolla_02_el_mismo_artefacto_otra_vez_es_idempotente_en_el_estado_y_se_anota():
    antes = _huella()
    r = _importa(_anual("LIC-VIGENTE", ANIO_VIGENTE))
    assert r.status_code == 200, r.text
    despues = _huella()
    assert {k: despues[k] for k in ("license_id", "mode", "period", "entitlements", "artefacto")} == {k: antes[k] for k in ("license_id", "mode", "period", "entitlements", "artefacto")}
    assert despues["artefactos"] == antes["artefactos"] + 1 and despues["eventos"] == antes["eventos"] + 1  # contrato canónico de hoy


def test_rolla_03_otra_legacy_del_mismo_periodo_ya_no_entra_sin_revision_del_emisor():
    """Cerrado LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN (FR-010-330): con una legacy vigente, otra legacy
    distinta del mismo período se rechaza; solo la reemisión revisionada del emisor la sustituye
    (`test_license_revision_client.py`). Nada se mueve salvo el evento de rechazo."""
    antes = _huella()
    r = _importa(_anual("LIC-VIGENTE-REDUCIDA", ANIO_VIGENTE, entitlements={"companies": 1, "users": 5}))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_LEGACY_REISSUE_REQUIRES_REVISION", r.text
    despues = _huella()
    assert {k: v for k, v in despues.items() if k != "eventos"} == {k: v for k, v in antes.items() if k != "eventos"}
    assert despues["eventos"] == antes["eventos"] + 1 and _huella()["entitlements"] == {"companies": 3, "users": 25}


def test_rolla_04_un_periodo_posterior_se_acepta():
    r = _importa(_anual("LIC-SIGUIENTE", ANIO_VIGENTE + 1))
    assert r.status_code == 200 and r.json()["license_id"] == "LIC-SIGUIENTE", r.text
    assert _huella()["period"][0].year == ANIO_VIGENTE + 1


# ---------------------------------------------------------------- ROLLA-05..07 · lo que no entra, y que no mueve nada
def test_rolla_05_06_un_periodo_anterior_se_rechaza_y_nada_cambia_salvo_el_evento_de_rechazo():
    antes = _huella()
    r = _importa(_anual("LIC-VIGENTE", ANIO_VIGENTE))  # el período vigente del módulo ya es el siguiente
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_PERIOD_DOWNGRADE", r.text
    despues = _huella()
    assert {k: v for k, v in despues.items() if k != "eventos"} == {k: v for k, v in antes.items() if k != "eventos"}
    assert despues["eventos"] == antes["eventos"] + 1
    rechazos = _eventos("LICENSE_PERIOD_DOWNGRADE_REJECTED")
    with _FACTORY() as db:
        admin = db.execute(select(User).where(User.username == "admin")).scalars().one()
    assert len(rechazos) == 1 and rechazos[0].user_id == str(admin.id)
    assert rechazos[0].detail["license_id"] == "LIC-VIGENTE" and rechazos[0].detail["current_license_id"] == "LIC-SIGUIENTE"
    assert rechazos[0].detail["outcome"] == "OLDER_PERIOD"


def test_rolla_07_una_licencia_vieja_que_dejaria_la_instalacion_en_solo_lectura_se_rechaza():
    antes = _huella()
    assert antes["mode"] == "FULL_ACCESS"
    r = _importa(_anual("LIC-2020", 2020))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_PERIOD_DOWNGRADE", r.text
    assert _huella()["mode"] == "FULL_ACCESS" and _huella()["license_id"] == antes["license_id"]
    assert _CLIENT.get("/api/v1/license/status").json()["mode"] == "FULL_ACCESS"


# ---------------------------------------------------------------- ROLLA-08..10 · el estado temporal no cambia el orden
def test_rolla_08_en_solo_lectura_un_periodo_posterior_renueva():
    _simular_licencia_antigua("LIC-ANTIGUA", inicio_en_dias=-400, fin_en_dias=-40, critico_en_dias=-20, solo_lectura_en_dias=-10)
    assert _CLIENT.get("/api/v1/license/status").json()["mode"] == "READ_ONLY"
    r = _importa(_anual("LIC-RENOVADA", ANIO_VIGENTE + 2))
    assert r.status_code == 200 and r.json()["mode"] == "FULL_ACCESS", r.text
    assert _CLIENT.get("/api/v1/license/status").json()["mode"] == "FULL_ACCESS"


def test_rolla_09_en_solo_lectura_un_periodo_anterior_sigue_rechazado():
    _simular_licencia_antigua("LIC-ANTIGUA", inicio_en_dias=-400, fin_en_dias=-40, critico_en_dias=-20, solo_lectura_en_dias=-10)
    assert _CLIENT.get("/api/v1/license/status").json()["mode"] == "READ_ONLY"
    r = _importa(_anual("LIC-MAS-VIEJA", ANIO_VIGENTE - 3))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_PERIOD_DOWNGRADE", r.text
    assert _huella()["license_id"] == "LIC-ANTIGUA"
    assert _CLIENT.get("/api/v1/license/status").json()["mode"] == "READ_ONLY"  # el rechazo no «arregla» el modo
    _restaurar(ANIO_VIGENTE + 3)
    assert _CLIENT.get("/api/v1/license/status").json()["mode"] == "FULL_ACCESS"


def test_rolla_10_vencida_en_aviso_critico_un_periodo_anterior_sigue_rechazado():
    _simular_licencia_antigua("LIC-EN-AVISO", inicio_en_dias=-380, fin_en_dias=-15, critico_en_dias=-5, solo_lectura_en_dias=10)
    assert _CLIENT.get("/api/v1/license/status").json()["mode"] == "CRITICAL_RENEWAL_NOTICE"
    r = _importa(_anual("LIC-MAS-VIEJA", ANIO_VIGENTE - 3))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_PERIOD_DOWNGRADE", r.text
    assert _huella()["license_id"] == "LIC-EN-AVISO"
    _restaurar(ANIO_VIGENTE + 4)


# ---------------------------------------------------------------- ROLLA-11..13 · nada más que el período ordena
def test_rolla_11_la_fecha_de_importacion_no_rejuvenece_un_periodo_viejo():
    """Importada hoy, la licencia del año pasado sigue siendo del año pasado: `imported_at` no es versión."""
    with _FACTORY() as db:
        estado = db.execute(select(LicenseState)).scalars().one()
        estado.verified_at = datetime(2000, 1, 1, tzinfo=UTC)  # el estado vigente «parece» importado hace décadas
        for a in db.execute(select(LicenseArtifact)).scalars().all():
            a.imported_at = datetime(2000, 1, 1, tzinfo=UTC)
        db.commit()
    r = _importa(_anual("LIC-VIGENTE", ANIO_VIGENTE))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_PERIOD_DOWNGRADE", r.text


def test_rolla_12_el_nombre_de_la_licencia_no_ordena():
    """Un identificador «mayor» con período anterior sigue siendo anterior; uno «menor» con período posterior, posterior."""
    r = _importa(_anual("ZZZ-9999", ANIO_VIGENTE))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_PERIOD_DOWNGRADE", r.text
    r = _importa(_anual("AAA-0000", ANIO_VIGENTE + 5))
    assert r.status_code == 200 and r.json()["license_id"] == "AAA-0000", r.text


def test_rolla_13_el_kid_no_ordena_ni_cambia_su_semantica():
    antes = _huella()
    r = _importa(_anual("LIC-KID-NUEVO", ANIO_VIGENTE, kid="kontrol-lic-2099-99"))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_PERIOD_DOWNGRADE", r.text
    assert _huella()["license_id"] == antes["license_id"]
    r = _importa(_anual("LIC-KID-VIEJO", ANIO_VIGENTE + 6, kid="kontrol-lic-2000-00"))
    assert r.status_code == 200, r.text
    with _FACTORY() as db:
        assert db.execute(select(LicenseState)).scalars().one().kid == "kontrol-lic-2000-00"  # se guarda tal cual, como hoy


# ---------------------------------------------------------------- ROLLA-14..17 · las compuertas 1 y 2 siguen delante
def test_rolla_14_sin_license_create_ni_una_licencia_posterior_entra():
    antes = _huella()
    cuerpo = _firmada(_anual("LIC-FUTURA", ANIO_VIGENTE + 9))
    assert _CLIENT.post(ACTIVATE, json=cuerpo).status_code == 401
    r = _CLIENT.post(ACTIVATE, json=cuerpo, headers=_sesion("lector"))
    assert r.status_code == 403 and r.json()["code"] == "PERMISSION_DENIED"
    assert _huella() == antes


def test_rolla_15_firma_invalida_posterior_o_no_se_rechaza_antes_de_comparar():
    antes = _huella()
    r = _CLIENT.post(IMPORT, json={"payload": _anual("LIC-FUTURA", ANIO_VIGENTE + 9), "signature_hex": "00" * 64}, headers=_sesion("admin"))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_SIGNATURE_INVALID", r.text
    assert _huella()["license_id"] == antes["license_id"]


def test_rolla_16_otra_instalacion_se_rechaza_antes_de_comparar():
    antes = _huella()
    r = _importa(_anual("LIC-AJENA", ANIO_VIGENTE + 9, instalacion="KTL-XX-OTRA"))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_INSTALLATION_MISMATCH", r.text
    assert _huella()["license_id"] == antes["license_id"]


def test_rolla_17_la_clave_de_la_instalacion_sigue_sin_ser_ancla():
    ruta = os.path.join(get_settings().installation_volume_path, "installation_private_key.pem")
    propia = serialization.load_pem_private_key(open(ruta, "rb").read(), password=None)
    assert isinstance(propia, Ed25519PrivateKey)
    r = _importa(_anual("LIC-AUTOFIRMADA", ANIO_VIGENTE + 9), clave=propia)
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_SIGNATURE_INVALID", r.text


# ---------------------------------------------------------------- ROLLA-18..20 · lo cerrado sigue cerrado
def test_rolla_18_20_estado_publico_diagnostico_y_health_sin_cambios():
    r = _CLIENT.get("/api/v1/license/status")
    assert r.status_code == 200 and set(r.json()) == {"mode", "license_url"}
    assert "period" not in r.text and "DOWNGRADE" not in r.text
    assert _CLIENT.get("/api/v1/system/diagnostics").status_code == 401
    assert _CLIENT.get("/api/v1/system/diagnostics", headers=_sesion("lector")).status_code == 200
    assert _CLIENT.get("/api/v1/health/live").json() == {"status": "ok", "service": "kontrol-backend"}
    assert _CLIENT.get("/api/v1/health/ready").json() == {"status": "ok", "service": "kontrol-backend", "database": "ok"}


# ---------------------------------------------------------------- ROLLA-21 · un período que no es un período no se aplica
def test_rolla_21_un_periodo_incoherente_se_rechaza_cerrado():
    antes = _huella()
    anio = antes["period"][0].year  # el período vigente del módulo (empieza en abril)
    cruzado = _anual("LIC-CRUZADA", anio)
    cruzado["period_start"] = f"{anio}-05-01T00:00:00-04:00"      # empieza después…
    cruzado["period_end"] = f"{anio + 1}-02-28T23:59:59-04:00"    # …y termina antes
    r = _importa(cruzado)
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_PERIOD_CONFLICT", r.text
    assert {k: v for k, v in _huella().items() if k != "eventos"} == {k: v for k, v in antes.items() if k != "eventos"}
    assert [e.detail["outcome"] for e in _eventos("LICENSE_PERIOD_DOWNGRADE_REJECTED") if e.detail["license_id"] == "LIC-CRUZADA"] == ["INCOMPARABLE_PERIOD"]
