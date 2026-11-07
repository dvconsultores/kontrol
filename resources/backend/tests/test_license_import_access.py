"""LICIMP · Importar una licencia firmada exige autoridad (LICENCIA-IMPORT-SIN-SESION,
FR-010-125..147).

`POST /license/activate` y `POST /license/import` respondían a cualquiera: con una licencia
firmada válida —incluso una antigua— un anónimo activaba o dejaba en solo lectura la
instalación, y cada intento fallido escribía un evento. Ahora el llamador necesita sesión y
`license:create`, la autoridad de activar que ya tenía `POST /licensing/sync`; la firma del
propietario y la identidad de la instalación siguen siendo la otra compuerta. Dos compuertas:
un artefacto válido no autoriza al llamador y un llamador autorizado no cuela un artefacto
inválido.

Mundo del módulo: `initialize` (`admin` con el catálogo entero), `lector` con todo menos
`license:create` (tiene `license:view`), `comun` sin ningún `license:*`; clave de autoridad
generada aquí e inyectada en `KONTROL_LICENSE_PUBLIC_KEY_PEM`; licencias SINTÉTICAS. Un mundo
aparte, sin licencia, para la primera activación.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

import app.core.database as dm
from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Permission, Role, RolePermission, User, UserRole, UserScope
from app.modules.licensing.models import LicenseEvent, LicenseState
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine

PASSWORD = "Kontrol2026Segura!"
ACTIVATE = "/api/v1/license/activate"
IMPORT = "/api/v1/license/import"
RUTAS = (ACTIVATE, IMPORT)
LICENCIA_PERMISOS = {"license:view", "license:create", "license:edit", "license:approve"}
#: Lo que un rechazo de autorización nunca puede llevar (FR-010-143, LICIMP-20).
SENSIBLE = re.compile(
    r"installation_id|license_id|LIC-|KTL-|signature|firma|verif|ed25519|public_key|private|pem|/tmp|/home|postgres|sqlite|tenant_id|company_id",
    re.IGNORECASE,
)

_CLIENT: TestClient
_FACTORY: sessionmaker
_CLAVE: Ed25519PrivateKey
_INSTALACION: str
_BASE: dict


def _usuario(db: Session, tenant_id: str, empresa: str, username: str, *, sin: set[str]) -> None:
    usuario = identity_service.create_user(
        db, tenant_id=tenant_id, username=username, email=f"{username}@demo.test",
        password=PASSWORD, must_change_password=False, created_by=None)
    rol = Role(code=f"IMP-{username}".upper(), name=f"IMP {username}", protected=False, status="ACTIVE")
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


#: El período de todas las licencias sintéticas del módulo, fijado una vez: licencias del mismo
#: período son reemisiones entre sí (Fase A, FR-010-206..208); una con fechas anteriores es un
#: retroceso y se rechaza (FR-010-200). Congelarlo evita que los segundos entre pruebas ordenen.
AHORA = datetime.now(UTC).replace(microsecond=0)


def _licencia(license_id: str, instalacion: str, *, fin_en_dias: int = 300, inicio_en_dias: int = -30) -> dict:
    """Payload sintético; las fechas relativas al instante congelado fijan período y modo."""
    ahora = AHORA
    return {
        "issuer": "QA", "license_id": license_id, "installation_id": instalacion,
        "customer_id": "C-TEST", "contract_id": "K-TEST", "company_tax_id": "J-00000000-0",
        "period_start": (ahora + timedelta(days=inicio_en_dias)).isoformat(),
        "period_end": (ahora + timedelta(days=fin_en_dias)).isoformat(),
        "critical_warning_start": (ahora + timedelta(days=fin_en_dias + 20)).isoformat(),
        "read_only_start": (ahora + timedelta(days=fin_en_dias + 30)).isoformat(),
        "entitlements": {}, "minimum_version": "1.0.0", "kid": "kontrol-lic-2026-01",
    }


def _firmada(payload: dict, clave: Ed25519PrivateKey | None = None) -> dict:
    canonico = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return {"payload": payload, "signature_hex": (clave or _CLAVE).sign(canonico).hex()}


def _mundo(*, con_licencia: bool) -> tuple[TestClient, sessionmaker, str]:
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
        _usuario(db, str(tenant.id), str(empresa.id), "comun", sin=LICENCIA_PERMISOS)
        instalacion = db.execute(select(Installation)).scalars().first().installation_uuid
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
    cliente = TestClient(app, raise_server_exceptions=False)
    if con_licencia:
        r = cliente.post(ACTIVATE, json=_firmada(_licencia("LIC-BASE", instalacion)), headers=_sesion("admin", cliente))
        assert r.status_code == 200, r.text
    return cliente, factory, instalacion


@pytest.fixture(scope="module", autouse=True)
def _app_client():
    global _CLIENT, _FACTORY, _CLAVE, _INSTALACION, _BASE
    _CLAVE = Ed25519PrivateKey.generate()
    publica = _CLAVE.public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    anterior = os.environ.get("KONTROL_LICENSE_PUBLIC_KEY_PEM")
    os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = publica
    get_settings.cache_clear()
    try:
        _CLIENT, _FACTORY, _INSTALACION = _mundo(con_licencia=True)
        _BASE = _firmada(_licencia("LIC-BASE", _INSTALACION))
        yield _CLIENT
    finally:
        if anterior is None:
            os.environ.pop("KONTROL_LICENSE_PUBLIC_KEY_PEM", None)
        else:
            os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = anterior
        get_settings.cache_clear()


def _sesion(username: str, cliente: TestClient | None = None) -> dict[str, str]:
    cliente = cliente or _CLIENT
    r = login_completo(cliente, "/api/v1/auth/login", json={"tenant_code": "DEMO", "username": username, "password": PASSWORD})
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


def _estado(factory: sessionmaker | None = None) -> tuple[str | None, str | None, int]:
    """(license_id, mode, nº de eventos): la huella de lo que una importación puede mover."""
    with (factory or _FACTORY)() as db:
        s = db.execute(select(LicenseState)).scalars().first()
        n = db.execute(select(func.count()).select_from(LicenseEvent)).scalar()
        return (s.license_id if s else None, s.mode if s else None, int(n or 0))


def _sin_fuga(r) -> None:
    assert SENSIBLE.search(r.text) is None, r.text


def _restaurar_base() -> None:
    r = _CLIENT.post(ACTIVATE, json=_BASE, headers=_sesion("admin"))
    assert r.status_code == 200 and r.json()["license_id"] == "LIC-BASE", r.text


@contextmanager
def _fechas(*, fin_en_dias: int, critico_en_dias: int, solo_lectura_en_dias: int) -> Iterator[None]:
    """Mueve las fechas del estado para que el servidor calcule otro modo; al salir, licencia base."""
    with _FACTORY() as db:
        estado = db.execute(select(LicenseState)).scalars().one()
        ahora = datetime.now(UTC)
        estado.period_start = ahora - timedelta(days=400)
        estado.period_end = ahora + timedelta(days=fin_en_dias)
        estado.critical_warning_start = ahora + timedelta(days=critico_en_dias)
        estado.read_only_start = ahora + timedelta(days=solo_lectura_en_dias)
        db.commit()
    try:
        yield
    finally:
        _restaurar_base()


# ---------------------------------------------------------------- LICIMP-01..03 · sin autoridad, con y sin artefacto válido
@pytest.mark.parametrize("ruta", RUTAS)
def test_licimp_01_anonimo_con_licencia_valida_401_y_nada_cambia(ruta):
    antes = _estado()
    r = _CLIENT.post(ruta, json=_firmada(_licencia("LIC-ANONIMA", _INSTALACION)))
    assert r.status_code == 401 and r.json()["code"] == "AUTH_REQUIRED", r.text
    _sin_fuga(r)
    assert _estado() == antes  # ni estado ni evento: la firma válida no autoriza a nadie


@pytest.mark.parametrize("ruta", RUTAS)
def test_licimp_02_anonimo_con_firma_invalida_recibe_el_mismo_rechazo_que_con_firma_valida(ruta):
    antes = _estado()
    valida = _CLIENT.post(ruta, json=_firmada(_licencia("LIC-ANONIMA", _INSTALACION)))
    invalida = _CLIENT.post(ruta, json={"payload": _licencia("LIC-ANONIMA", _INSTALACION), "signature_hex": "00" * 64})
    assert valida.status_code == invalida.status_code == 401
    quitar = lambda r: {k: v for k, v in r.json().items() if k != "request_id"}  # noqa: E731
    assert quitar(valida) == quitar(invalida), "antes de autorizar, nada distingue una firma válida de una inválida"
    _sin_fuga(invalida)
    assert _estado() == antes


@pytest.mark.parametrize("cabecera", [{"Authorization": "Bearer inventado"}, {"Authorization": "Basic Zm9v"}, {"Authorization": "Bearer a.b.c"}])
def test_licimp_03_token_inventado_o_caducado_401_y_nada_cambia(cabecera):
    antes = _estado()
    cuerpo = _firmada(_licencia("LIC-TOKEN", _INSTALACION))
    r = _CLIENT.post(ACTIVATE, json=cuerpo, headers=cabecera)
    assert r.status_code == 401, r.text
    _sin_fuga(r)
    r = _CLIENT.post(IMPORT, json=cuerpo, headers=_caducado())
    assert r.status_code == 401 and r.json()["code"] == "AUTH_INVALID_TOKEN", r.text
    assert _estado() == antes


# ---------------------------------------------------------------- LICIMP-04..05 · sesión sin la autoridad de activar
@pytest.mark.parametrize("ruta", RUTAS)
def test_licimp_04_un_usuario_sin_permisos_de_licencia_403_y_nada_cambia(ruta):
    antes = _estado()
    r = _CLIENT.post(ruta, json=_firmada(_licencia("LIC-COMUN", _INSTALACION)), headers=_sesion("comun"))
    assert r.status_code == 403 and r.json()["code"] == "PERMISSION_DENIED", r.text
    _sin_fuga(r)
    assert _estado() == antes


@pytest.mark.parametrize("ruta", RUTAS)
def test_licimp_05_license_view_no_es_license_create_403_y_nada_cambia(ruta):
    antes = _estado()
    r = _CLIENT.post(ruta, json=_firmada(_licencia("LIC-LECTOR", _INSTALACION)), headers=_sesion("lector"))
    assert r.status_code == 403 and r.json()["code"] == "PERMISSION_DENIED", r.text
    _sin_fuga(r)
    assert _estado() == antes
    # El lector sí lee: la frontera de lectura de la 004 sigue donde estaba.
    assert _CLIENT.get("/api/v1/license/detail", headers=_sesion("lector")).status_code == 200


# ---------------------------------------------------------------- LICIMP-06..10 · con autoridad, la segunda compuerta manda
def test_licimp_06_el_administrador_con_licencia_valida_activa_y_el_evento_lleva_su_identidad():
    _, _, eventos = _estado()
    # El artefacto base exacto: con el período vigente, otra legacy distinta ya no entra (FR-010-330); la
    # reimportación exacta sí, y es la que prueba la compuerta del llamador y la identidad en el evento.
    r = _CLIENT.post(IMPORT, json=_BASE, headers=_sesion("admin"))
    assert r.status_code == 200 and r.json() == {"ok": True, "license_id": "LIC-BASE", "mode": "FULL_ACCESS"}, r.text
    with _FACTORY() as db:
        estado = db.execute(select(LicenseState)).scalars().one()
        ultimo = db.execute(select(LicenseEvent).order_by(LicenseEvent.created_at.desc())).scalars().first()
        admin = db.execute(select(User).where(User.username == "admin")).scalars().one()
    assert estado.license_id == "LIC-BASE" and estado.mode == "FULL_ACCESS"
    assert ultimo.event_type == "LICENSE_IMPORTED" and ultimo.user_id == str(admin.id)  # el evento lleva ahora quién importó
    assert _estado()[2] == eventos + 1
    _restaurar_base()


def test_licimp_07_el_administrador_con_firma_invalida_423_y_el_estado_no_cambia():
    licencia, modo, _ = _estado()
    r = _CLIENT.post(ACTIVATE, json={"payload": _licencia("LIC-FALSA", _INSTALACION), "signature_hex": "ab" * 64}, headers=_sesion("admin"))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_SIGNATURE_INVALID", r.text
    assert _estado()[:2] == (licencia, modo)


def test_licimp_07b_una_firma_valida_de_otra_autoridad_tampoco_entra():
    licencia, modo, _ = _estado()
    r = _CLIENT.post(ACTIVATE, json=_firmada(_licencia("LIC-AJENA", _INSTALACION), Ed25519PrivateKey.generate()), headers=_sesion("admin"))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_SIGNATURE_INVALID", r.text
    assert _estado()[:2] == (licencia, modo)


def test_licimp_08_el_administrador_con_licencia_de_otra_instalacion_423_y_el_estado_no_cambia():
    licencia, modo, _ = _estado()
    r = _CLIENT.post(IMPORT, json=_firmada(_licencia("LIC-OTRA", "KTL-XX-OTRA-INSTALACION")), headers=_sesion("admin"))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_INSTALLATION_MISMATCH", r.text
    assert _estado()[:2] == (licencia, modo)


def test_licimp_09_la_misma_licencia_otra_vez_deja_el_estado_igual_y_anota_el_evento():
    licencia, modo, eventos = _estado()
    r = _CLIENT.post(ACTIVATE, json=_BASE, headers=_sesion("admin"))
    assert r.status_code == 200 and r.json()["license_id"] == "LIC-BASE"
    assert _estado() == (licencia, modo, eventos + 1)


def test_licimp_10_una_licencia_firmada_mas_vieja_ya_no_reemplaza_la_actual_ni_siquiera_al_administrador():
    """Cerrado en la Fase A de LICENCIA-DOWNGRADE-FIRMADO (FR-010-200): antes, el administrador la
    aplicaba y la instalación quedaba en READ_ONLY. Las compuertas 1 y 2 siguen delante."""
    vieja = _firmada(_licencia("LIC-VIEJA", _INSTALACION, inicio_en_dias=-800, fin_en_dias=-400))
    assert _CLIENT.post(IMPORT, json=vieja).status_code == 401
    assert _CLIENT.post(IMPORT, json=vieja, headers=_sesion("lector")).status_code == 403
    assert _estado()[0] == "LIC-BASE"
    r = _CLIENT.post(IMPORT, json=vieja, headers=_sesion("admin"))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_PERIOD_DOWNGRADE", r.text
    assert _estado()[:2] == ("LIC-BASE", "FULL_ACCESS")


# ---------------------------------------------------------------- LICIMP-11..13 · ningún estado deja fuera al administrador
def test_licimp_11_primera_instalacion_sin_licencia_el_administrador_entra_y_activa_nadie_mas():
    anterior = (dm._engine, dm._SessionLocal)  # type: ignore[attr-defined]
    try:
        cliente, factory, instalacion = _mundo(con_licencia=False)
        assert _estado(factory) == (None, None, 0)
        assert cliente.get("/api/v1/license/status").json()["mode"] == "PENDING"
        cuerpo = _firmada(_licencia("LIC-PRIMERA", instalacion))
        assert cliente.post(ACTIVATE, json=cuerpo).status_code == 401
        assert cliente.post(ACTIVATE, json=cuerpo, headers=_sesion("lector", cliente)).status_code == 403
        assert _estado(factory) == (None, None, 0)
        r = cliente.post(ACTIVATE, json=cuerpo, headers=_sesion("admin", cliente))
        assert r.status_code == 200 and r.json()["mode"] == "FULL_ACCESS", r.text
        assert _estado(factory)[:2] == ("LIC-PRIMERA", "FULL_ACCESS")
        assert cliente.get("/api/v1/license/status").json()["mode"] == "FULL_ACCESS"
    finally:
        dm._engine, dm._SessionLocal = anterior  # type: ignore[attr-defined]


def test_licimp_12_en_solo_lectura_las_escrituras_se_bloquean_pero_el_administrador_renueva():
    with _fechas(fin_en_dias=-40, critico_en_dias=-20, solo_lectura_en_dias=-10):
        assert _CLIENT.get("/api/v1/license/status").json()["mode"] == "READ_ONLY"
        bloqueada = _CLIENT.put("/api/v1/licensing/central-config", json={"server_url": "https://central.test"}, headers=_sesion("admin"))
        assert bloqueada.status_code == 423 and bloqueada.json()["code"] == "LICENSE_READ_ONLY", bloqueada.text
        # La renovación es la licencia base (período posterior al estado envejecido): otra legacy distinta del
        # mismo período que la base ya no podría volver a ella (FR-010-330).
        assert _CLIENT.post(IMPORT, json=_BASE, headers=_sesion("lector")).status_code == 403
        r = _CLIENT.post(IMPORT, json=_BASE, headers=_sesion("admin"))
        assert r.status_code == 200 and r.json()["mode"] == "FULL_ACCESS", r.text
        assert _CLIENT.get("/api/v1/license/status").json()["mode"] == "FULL_ACCESS"


@pytest.mark.parametrize("fechas,modo", [
    ((-5, 10, 20), "RENEWAL_NOTICE"),
    ((-15, -5, 10), "CRITICAL_RENEWAL_NOTICE"),
])
def test_licimp_13_en_aviso_y_aviso_critico_el_administrador_renueva(fechas, modo):
    with _fechas(fin_en_dias=fechas[0], critico_en_dias=fechas[1], solo_lectura_en_dias=fechas[2]):
        assert _CLIENT.get("/api/v1/license/status").json()["mode"] == modo
        r = _CLIENT.post(ACTIVATE, json=_BASE, headers=_sesion("admin"))  # posterior al estado envejecido
        assert r.status_code == 200 and r.json()["mode"] == "FULL_ACCESS", r.text


# ---------------------------------------------------------------- LICIMP-14..16 · lo cerrado sigue cerrado
def test_licimp_14_el_estado_publico_sigue_anonimo_y_minimo():
    r = _CLIENT.get("/api/v1/license/status")
    assert r.status_code == 200 and set(r.json()) == {"mode", "license_url"} and r.json()["mode"] == "FULL_ACCESS"


def test_licimp_15_el_diagnostico_sigue_con_sesion_y_license_view():
    assert _CLIENT.get("/api/v1/system/diagnostics").status_code == 401
    assert _CLIENT.get("/api/v1/system/diagnostics", headers=_sesion("comun")).status_code == 403
    assert _CLIENT.get("/api/v1/system/diagnostics", headers=_sesion("lector")).status_code == 200


_POLITICA_COPIAS = {
    "configured_rpo_minutes": 15, "schedule_interval_minutes": 5, "safety_margin_minutes": 2,
    "retention_days": 7, "retention_min_copies": 1, "destination_type": "MOUNTED_FILESYSTEM",
    "destination_label": "nas-1", "scheduler_enabled": True, "version": 0,
}
_RUTA_COPIAS = "/api/v1/system/backup-config"


def test_copias_diagnostico_informa_estado_con_license_view():
    r = _CLIENT.get("/api/v1/system/diagnostics", headers=_sesion("lector"))
    assert r.status_code == 200, r.text
    assert r.json()["backup"]["rpo_state"] == "DISABLED"
    assert "backup_path" not in r.text and "KONTROL_BACKUP_KEY" not in r.text


def test_copias_configurar_sin_sesion_responde_401():
    assert _CLIENT.put(_RUTA_COPIAS, json=_POLITICA_COPIAS).status_code == 401


def test_copias_configurar_sin_permiso_responde_403():
    r = _CLIENT.put(_RUTA_COPIAS, json=_POLITICA_COPIAS, headers=_sesion("comun"))
    assert r.status_code == 403, r.text


def test_copias_campo_desconocido_se_rechaza():
    r = _CLIENT.put(_RUTA_COPIAS, json={**_POLITICA_COPIAS, "ruta": "/x"}, headers=_sesion("admin"))
    assert r.status_code == 422, r.text


def test_copias_rpo_mayor_de_15_se_rechaza_por_api():
    cuerpo = {**_POLITICA_COPIAS, "configured_rpo_minutes": 16}
    r = _CLIENT.put(_RUTA_COPIAS, json=cuerpo, headers=_sesion("admin"))
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "BACKUP_POLICY_INVALID"


def test_copias_sesion_autorizada_guarda_y_diagnostico_lo_refleja():
    cabeceras = _sesion("admin")
    r = _CLIENT.put(_RUTA_COPIAS, json=_POLITICA_COPIAS, headers=cabeceras)
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 1
    copias = _CLIENT.get("/api/v1/system/diagnostics", headers=cabeceras).json()["backup"]
    assert copias["scheduler_enabled"] is True
    assert copias["rpo_state"] == "NO_VALID_BACKUP"


def test_licimp_16_los_health_siguen_publicos_y_minimos():
    assert _CLIENT.get("/api/v1/health/live").json() == {"status": "ok", "service": "kontrol-backend"}
    assert _CLIENT.get("/api/v1/health/ready").json() == {"status": "ok", "service": "kontrol-backend", "database": "ok"}


# ---------------------------------------------------------------- LICIMP-18..20 · carga no autorizada: ni estado ni auditoría
def test_licimp_18_19_treinta_intentos_sin_autoridad_no_mueven_estado_ni_auditoria():
    antes = _estado()
    valida = _firmada(_licencia("LIC-CARGA", _INSTALACION))
    invalida = {"payload": _licencia("LIC-CARGA", _INSTALACION), "signature_hex": "ff" * 64}
    lector = _sesion("lector")
    for _ in range(10):
        assert _CLIENT.post(ACTIVATE, json=valida).status_code == 401
        assert _CLIENT.post(IMPORT, json=invalida, headers={"Authorization": "Bearer inventado"}).status_code == 401
        assert _CLIENT.post(ACTIVATE, json=valida, headers=lector).status_code == 403
    assert _estado() == antes


def test_licimp_20_los_rechazos_de_autorizacion_no_cuentan_nada_de_la_licencia():
    cuerpo = _firmada(_licencia("LIC-FUGA", _INSTALACION))
    for r in (
        _CLIENT.post(ACTIVATE, json=cuerpo),
        _CLIENT.post(IMPORT, json=cuerpo, headers={"Authorization": "Bearer inventado"}),
        _CLIENT.post(ACTIVATE, json=cuerpo, headers=_sesion("comun")),
        _CLIENT.post(IMPORT, json=cuerpo, headers=_sesion("lector")),
    ):
        assert r.status_code in (401, 403)
        assert set(r.json()) == {"code", "message", "field_errors", "request_id", "details"} and r.json()["details"] is None
        _sin_fuga(r)
