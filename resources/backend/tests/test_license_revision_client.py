"""REVC · El cliente consume la `revision` firmada de la Autoridad Central y la aplica dentro del
mismo período, después del período y bajo el bloqueo de la Fase A (LICENCIA-REEMISION-INTRAPERIODO-
SIN-ORDEN; FR-010-322..361).

El emisor es el real: `central_authority.service` sobre una base propia, firmando con la clave
sintética que esta suite declara como ancla del propietario del cliente. El cliente no asigna ni
corrige revisiones: valida y compara. Los artefactos hostiles (conflicto, manipulación, revisiones
inválidas, otra instalación) se firman a mano con la misma clave sintética, nunca con una real.
Corre en SQLite y en PostgreSQL (`KONTROL_TEST_DB_URL`); las carreras van en
`test_license_revision_race.py`.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

import app.core.database as dm
from app.core import license_contract as contract
from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Permission, Role, RolePermission, User, UserRole, UserScope
from app.modules.licensing.models import LicenseArtifact, LicenseEvent, LicenseState
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.setup.api import SetupRequest, initialize
from central_authority import service as central
from central_authority.config import Settings as CentralSettings
from central_authority.models import Base as CentralBase
from tests.conftest import make_engine

PASSWORD = "Kontrol2026Segura!"
ACTIVATE = "/api/v1/license/activate"
IMPORT = "/api/v1/license/import"
ANCLA = "KONTROL_LICENSE_PUBLIC_KEY_PEM"
CARACAS = timezone(timedelta(hours=-4))
HOY = datetime.now(UTC).astimezone(CARACAS)
#: El año contractual que contiene hoy: su licencia queda en FULL_ACCESS.
ANIO = HOY.year if HOY.month >= 4 else HOY.year - 1
KID = "kontrol-lic-2026-01"

_CLIENT: TestClient
_FACTORY: sessionmaker
_CENTRAL: sessionmaker
_AJUSTES: CentralSettings
_PROPIETARIO: Ed25519PrivateKey
_INSTALACION: str


def _pem_privada(clave: Ed25519PrivateKey) -> str:
    return clave.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8,
                               encryption_algorithm=serialization.NoEncryption()).decode()


def _pem_publica(clave: Ed25519PrivateKey) -> str:
    return clave.public_key().public_bytes(encoding=serialization.Encoding.PEM,
                                           format=serialization.PublicFormat.SubjectPublicKeyInfo).decode()


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


def _anual(license_id: str, anio: int, *, instalacion: str | None = None, **extra: Any) -> dict[str, Any]:
    """Una licencia legacy sintética del contrato (sin `revision`); `extra` añade o sustituye claves."""
    return {
        "issuer": "QA", "license_id": license_id, "installation_id": instalacion or _INSTALACION,
        "customer_id": "C-TEST", "contract_id": "K-TEST", "company_tax_id": "J-00000000-0",
        "period_start": f"{anio}-04-01T00:00:00-04:00", "period_end": f"{anio + 1}-03-31T23:59:59-04:00",
        "critical_warning_start": f"{anio + 1}-04-21T00:00:00-04:00", "read_only_start": f"{anio + 1}-05-01T00:00:00-04:00",
        "entitlements": {"companies": 3, "users": 25}, "minimum_version": "1.0.0", "kid": KID, **extra,
    }


def _firmada(payload: dict[str, Any], clave: Ed25519PrivateKey | None = None) -> dict[str, Any]:
    return {"payload": payload, "signature_hex": contract.sign_license_payload(payload, clave or _PROPIETARIO)}


@pytest.fixture(scope="module", autouse=True)
def _mundo():
    """Cliente activado sobre su base, y la Autoridad Central sobre la suya, con la clave sintética
    del propietario como ancla del cliente y clave de firma del emisor. Nada real."""
    global _CLIENT, _FACTORY, _CENTRAL, _AJUSTES, _PROPIETARIO, _INSTALACION
    _PROPIETARIO = Ed25519PrivateKey.generate()
    anterior = os.environ.get(ANCLA)
    os.environ[ANCLA] = _pem_publica(_PROPIETARIO)
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
        instalacion = db.execute(select(Installation)).scalars().first()
        _INSTALACION, clave_publica = instalacion.installation_uuid, instalacion.public_key
        db.commit()

    # La autoridad: base propia, clave propia (la sintética), instalación registrada con su clave pública.
    motor_central = make_engine()
    CentralBase.metadata.create_all(motor_central)
    _CENTRAL = sessionmaker(bind=motor_central, class_=Session, expire_on_commit=False)
    _AJUSTES = CentralSettings(environment="qa", db_url="sqlite+pysqlite:///:memory:",
                               signing_private_key_pem=_pem_privada(_PROPIETARIO), signing_kid=KID)
    with _CENTRAL() as db:
        central.register_installation(db, installation_uuid=_INSTALACION, public_key_pem=clave_publica, customer_id="C-TEST",
                                      contract_id="K-TEST", company_tax_id="J-00000000-0", operator="qa")

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
        yield
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


def _emite(anio: int, *, entitlements: dict[str, Any] | None = None, minimum_version: str = "1.0.0") -> dict[str, Any]:
    """La Autoridad Central real emite la siguiente `revision` del período anual dado."""
    inicio, fin = central.periodo_anual(anio)
    with _CENTRAL() as db:
        return central.issue_license(db, settings=_AJUSTES, installation_uuid=_INSTALACION, period_start=inicio, period_end=fin,
                                     entitlements=entitlements if entitlements is not None else {"companies": 3, "users": 25},
                                     minimum_version=minimum_version, operator="qa")


def _importa(artefacto: dict[str, Any], quien: str = "admin", ruta: str = IMPORT):
    return _CLIENT.post(ruta, json={"payload": artefacto["payload"], "signature_hex": artefacto["signature_hex"]}, headers=_sesion(quien))


def _huella() -> dict[str, Any]:
    """Todo lo que una importación puede mover, para afirmar que un rechazo no mueve nada."""
    with _FACTORY() as db:
        s = db.execute(select(LicenseState)).scalars().first()
        ultimo = db.execute(select(LicenseArtifact).order_by(LicenseArtifact.imported_at.desc(), LicenseArtifact.created_at.desc())).scalars().first()
        return {
            "license_id": s.license_id if s else None, "mode": s.mode if s else None,
            "period": (s.period_start, s.period_end) if s else None, "entitlements": s.entitlements if s else None,
            "minimum_version": s.minimum_version if s else None, "kid": s.kid if s else None,
            "artefacto": ultimo.payload_hash if ultimo else None,
            "revision": (ultimo.payload.get("revision") if ultimo else None),  # crudo: la huella no interpreta
            "artefactos": db.execute(select(func.count()).select_from(LicenseArtifact)).scalar(),
            "eventos": db.execute(select(func.count()).select_from(LicenseEvent)).scalar(),
        }


def _rechazos() -> list[LicenseEvent]:
    with _FACTORY() as db:
        return list(db.execute(select(LicenseEvent).where(LicenseEvent.event_type == "LICENSE_REISSUE_REJECTED")
                               .order_by(LicenseEvent.created_at)).scalars().all())


def _sin_mover(antes: dict[str, Any], despues: dict[str, Any]) -> None:
    assert {k: v for k, v in despues.items() if k != "eventos"} == {k: v for k, v in antes.items() if k != "eventos"}
    assert despues["eventos"] == antes["eventos"] + 1  # solo el evento de rechazo


LEGACY_A = None  # se fija en REVC-01
LEGACY_B = None


# ---------------------------------------------------------------- REVC-01..03 · legacy vigente
def test_revc_01_sin_licencia_vigente_entra_una_legacy_valida():
    global LEGACY_A
    assert _huella()["license_id"] is None
    LEGACY_A = _firmada(_anual("LIC-LEGACY-A", ANIO))
    r = _importa(LEGACY_A, ruta=ACTIVATE)
    assert r.status_code == 200 and r.json() == {"ok": True, "license_id": "LIC-LEGACY-A", "mode": "FULL_ACCESS"}, r.text
    assert _huella()["revision"] is None  # legacy: el claim no existe en el artefacto guardado
    with _FACTORY() as db:
        assert "revision" not in db.execute(select(LicenseArtifact)).scalars().one().payload


def test_revc_02_la_misma_legacy_exacta_es_idempotente():
    antes = _huella()
    r = _importa(LEGACY_A)
    assert r.status_code == 200, r.text
    despues = _huella()
    assert {k: despues[k] for k in ("license_id", "mode", "period", "entitlements", "artefacto", "revision")} == \
        {k: antes[k] for k in ("license_id", "mode", "period", "entitlements", "artefacto", "revision")}
    assert despues["artefactos"] == antes["artefactos"] + 1 and despues["eventos"] == antes["eventos"] + 1


def test_revc_03_otra_legacy_del_mismo_periodo_se_rechaza_y_nada_se_mueve():
    global LEGACY_B
    LEGACY_B = _firmada(_anual("LIC-LEGACY-B", ANIO, entitlements={"companies": 99}))
    antes = _huella()
    r = _importa(LEGACY_B)
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_LEGACY_REISSUE_REQUIRES_REVISION", r.text
    _sin_mover(antes, _huella())
    rechazo = _rechazos()[-1]
    with _FACTORY() as db:
        admin = db.execute(select(User).where(User.username == "admin")).scalars().one()
    assert rechazo.user_id == str(admin.id)
    assert rechazo.detail == {"license_id": "LIC-LEGACY-B", "current_license_id": "LIC-LEGACY-A", "current_revision": None,
                              "incoming_revision": None, "outcome": "LEGACY_REISSUE_REQUIRES_REVISION"}
    assert not any(k in json.dumps(rechazo.detail) for k in ("signature", "payload_hash", "PRIVATE", "entitlements"))


# ---------------------------------------------------------------- REVC-04..07 · el puente y el linaje real
def test_revc_04_la_revisionada_del_emisor_entra_sobre_la_legacy_y_fija_el_linaje():
    r1 = _emite(ANIO, entitlements={"companies": 5})
    assert r1["revision"] == 1 and r1["payload"]["kid"] == KID
    r = _importa(r1)
    assert r.status_code == 200, r.text
    h = _huella()
    assert h["license_id"] == r1["license_id"] and h["revision"] == 1 and h["entitlements"] == {"companies": 5}
    assert h["period"][0].year == ANIO
    historial = _CLIENT.get("/api/v1/license/history", headers=_sesion("admin")).json()
    assert any(e["event_type"] == "LICENSE_IMPORTED" and e["detail"].get("revision") == 1 for e in historial)


def test_revc_05_tras_la_revisionada_ninguna_legacy_del_mismo_periodo_entra():
    for legacy in (LEGACY_A, LEGACY_B):
        antes = _huella()
        r = _importa(legacy)
        assert r.status_code == 423 and r.json()["code"] == "LICENSE_LEGACY_AFTER_REVISION", r.text
        _sin_mover(antes, _huella())
    assert _rechazos()[-1].detail["current_revision"] == 1 and _rechazos()[-1].detail["incoming_revision"] is None


def test_revc_06_una_revision_mayor_con_menos_derechos_entra_y_la_menor_ya_no():
    r1 = _huella()
    r2 = _emite(ANIO, entitlements={"companies": 1})  # menos derechos: la revisión manda, no los derechos
    assert r2["revision"] == 2
    assert _importa(r2).status_code == 200
    assert _huella()["revision"] == 2 and _huella()["entitlements"] == {"companies": 1}
    # La r1 del emisor (más derechos) ya es anterior: no vuelve.
    with _CENTRAL() as db:
        emision_r1 = central.get_issuance(db, r1["license_id"])
    antes = _huella()
    r = _importa({"payload": emision_r1["payload"], "signature_hex": emision_r1["signature_hex"]})
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_REVISION_DOWNGRADE", r.text
    _sin_mover(antes, _huella())
    assert _rechazos()[-1].detail["outcome"] == "REVISION_DOWNGRADE" and _rechazos()[-1].detail["incoming_revision"] == 1


def test_revc_07_la_misma_revisionada_exacta_es_idempotente_y_los_huecos_no_importan():
    r3 = _emite(ANIO)
    assert _importa(r3).status_code == 200
    antes = _huella()
    assert _importa(r3).status_code == 200  # exacta
    despues = _huella()
    assert {k: despues[k] for k in ("license_id", "revision", "artefacto", "entitlements")} == {k: antes[k] for k in ("license_id", "revision", "artefacto", "entitlements")}
    # El linaje del emisor sigue en 3 y el cliente no inventó ninguna revisión intermedia ni posterior.
    with _CENTRAL() as db:
        assert [e["revision"] for e in central.list_issuances(db, _INSTALACION)] == [1, 2, 3]


# ---------------------------------------------------------------- REVC-08..11 · hostiles firmados por el propietario
def test_revc_08_misma_revision_con_otra_carga_es_conflicto_aunque_cambie_el_kid():
    for extra in ({"entitlements": {"companies": 500}}, {"minimum_version": "9.9.9"}):
        antes = _huella()
        hostil = _firmada(_anual("LIC-HOSTIL-R3", ANIO, revision=3, **extra))
        r = _importa(hostil)
        assert r.status_code == 423 and r.json()["code"] == "LICENSE_REVISION_CONFLICT", r.text
        _sin_mover(antes, _huella())
    assert _rechazos()[-1].detail["outcome"] == "REVISION_CONFLICT"
    # Un `kid` distinto ya no es «otra carga»: es una clave desconocida y se rechaza antes (LICENCIA-SIN-ROTACION-DE-CLAVE).
    assert _importa(_firmada(_anual("LIC-HOSTIL-R3", ANIO, revision=3, kid="kontrol-lic-2099-99"))).json()["code"] == "LICENSE_SIGNING_KID_UNKNOWN"


def test_revc_09_ni_el_kid_ni_los_derechos_ni_la_version_minima_ordenan_solo_la_revision():
    # Una r4 firmada por el propietario con menos derechos y versión mínima menor: es más nueva y entra (el `kid` es
    # el de la clave de confianza: ya no es una etiqueta libre, LICENCIA-SIN-ROTACION-DE-CLAVE).
    r4 = _firmada(_anual("LIC-R4-SINTETICA", ANIO, revision=4, entitlements={"companies": 1}, minimum_version="0.0.1"))
    assert _importa(r4).status_code == 200
    h = _huella()
    assert h["revision"] == 4 and h["kid"] == KID and h["entitlements"] == {"companies": 1}
    # El emisor, ajeno a esa r4, emite su r4: misma revisión, otra carga → conflicto; su r5 → entra.
    r4_central = _emite(ANIO)
    assert r4_central["revision"] == 4
    assert _importa(r4_central).status_code == 423 and _importa(r4_central).json()["code"] == "LICENSE_REVISION_CONFLICT"
    r5 = _emite(ANIO)
    assert r5["revision"] == 5 and _importa(r5).status_code == 200 and _huella()["revision"] == 5


def test_revc_10_alterar_la_revision_sin_refirmar_rompe_la_firma_antes_de_ordenar():
    r5 = _huella()
    with _CENTRAL() as db:
        emision = central.get_issuance(db, r5["license_id"])
    manipulado = {"payload": {**emision["payload"], "revision": 6}, "signature_hex": emision["signature_hex"]}
    antes, rechazos = _huella(), len(_rechazos())
    r = _importa(manipulado)
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_SIGNATURE_INVALID", r.text
    _sin_mover(antes, _huella())
    assert len(_rechazos()) == rechazos  # no llegó a la comparación: el evento es el de firma


@pytest.mark.parametrize("invalida", [True, False, 0, -1, "7", 1.5, None], ids=["true", "false", "cero", "negativa", "cadena", "decimal", "null"])
def test_revc_11_una_revision_invalida_firmada_se_rechaza_cerrada_y_sin_mover_nada(invalida):
    antes, rechazos = _huella(), len(_rechazos())
    r = _importa(_firmada(_anual("LIC-INVALIDA", ANIO, revision=invalida)))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_INVALID_REVISION", r.text
    despues = _huella()
    assert {k: v for k, v in despues.items()} == {k: v for k, v in antes.items()}  # ni evento: se decide antes del bloqueo
    assert len(_rechazos()) == rechazos


# ---------------------------------------------------------------- REVC-12..14 · períodos, READ_ONLY, otra instalación
def test_revc_12_la_revision_no_cruza_periodos_y_el_periodo_sigue_mandando():
    siguiente = _emite(ANIO + 1)  # el linaje del período nuevo empieza en 1 aunque el vigente vaya por 5
    assert siguiente["revision"] == 1
    assert _importa(siguiente).status_code == 200
    h = _huella()
    assert h["revision"] == 1 and h["period"][0].year == ANIO + 1
    antes = _huella()
    r = _importa(_firmada(_anual("LIC-VIEJA-R999", ANIO, revision=999)))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_PERIOD_DOWNGRADE", r.text
    _sin_mover(antes, _huella())
    with _CENTRAL() as db:
        assert [(e["period_start"][:4], e["revision"]) for e in central.list_issuances(db, _INSTALACION)][-1] == (str(ANIO + 1), 1)


def test_revc_13_en_solo_lectura_una_revision_mayor_del_mismo_periodo_entra_y_la_menor_no():
    """Como lo habría dejado una importación de hace dos años: la r1 del período ANIO-2, emitida por el
    emisor, vigente y ya en solo lectura. La r2 del mismo período entra (el bloqueo de escritura no
    frena una reemisión legítima), la r1 no vuelve, y un período posterior renueva."""
    inicio, fin = central.periodo_anual(ANIO - 2)
    with _CENTRAL() as db:
        r1_vieja = central.issue_license(db, settings=_AJUSTES, installation_uuid=_INSTALACION, period_start=inicio, period_end=fin,
                                         entitlements={"companies": 3}, minimum_version="1.0.0", operator="qa")
        r2_vieja = central.issue_license(db, settings=_AJUSTES, installation_uuid=_INSTALACION, period_start=inicio, period_end=fin,
                                         entitlements={"companies": 3}, minimum_version="1.0.0", operator="qa")
    datos = contract.parse_license_payload(r1_vieja["payload"])
    with _FACTORY() as db:
        db.add(LicenseArtifact(license_id=datos.license_id, payload=r1_vieja["payload"], signature_hex=r1_vieja["signature_hex"],
                               payload_hash=contract.payload_hash(r1_vieja["payload"]), kid=KID, imported_at=datos.period_start))
        estado = db.execute(select(LicenseState)).scalars().one()
        estado.license_id, estado.mode = datos.license_id, "READ_ONLY"
        estado.period_start, estado.period_end = datos.period_start.astimezone(UTC), datos.period_end.astimezone(UTC)
        estado.critical_warning_start, estado.read_only_start = datos.critical_warning_start.astimezone(UTC), datos.read_only_start.astimezone(UTC)
        db.commit()
    assert _CLIENT.get("/api/v1/license/status").json()["mode"] == "READ_ONLY"
    assert _importa(r2_vieja).status_code == 200
    h = _huella()
    assert h["revision"] == 2 and h["period"][0].year == ANIO - 2 and h["mode"] == "READ_ONLY"  # el período sigue vencido
    r = _importa(r1_vieja)
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_REVISION_DOWNGRADE", r.text
    # Un período posterior renueva desde solo lectura: la r2 de ANIO+1 (su linaje iba por 1).
    siguiente = _emite(ANIO + 1)
    assert siguiente["revision"] == 2 and _importa(siguiente).status_code == 200
    assert _huella()["revision"] == 2 and _huella()["mode"] == "FULL_ACCESS" and _CLIENT.get("/api/v1/license/status").json()["mode"] == "FULL_ACCESS"


def test_revc_14_las_compuertas_anteriores_siguen_delante_del_orden():
    r3 = _emite(ANIO + 1)
    antes = _huella()
    cuerpo = {"payload": r3["payload"], "signature_hex": r3["signature_hex"]}
    assert _CLIENT.post(IMPORT, json=cuerpo).status_code == 401  # sin sesión
    assert _CLIENT.post(IMPORT, json=cuerpo, headers=_sesion("lector")).status_code == 403  # sin license:create
    ajena = _firmada(_anual("LIC-AJENA", ANIO + 1, instalacion="KTL-XX-OTRA", revision=9))
    r = _importa(ajena)
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_INSTALLATION_MISMATCH", r.text
    otra_autoridad = _firmada(_anual("LIC-OTRA-AUTORIDAD", ANIO + 1, revision=9), Ed25519PrivateKey.generate())
    assert _importa(otra_autoridad).json()["code"] == "LICENSE_SIGNATURE_INVALID"
    assert {k: v for k, v in _huella().items() if k != "eventos"} == {k: v for k, v in antes.items() if k != "eventos"}
    assert _importa(r3).status_code == 200 and _huella()["revision"] == 3  # con sesión y permiso, entra


# ---------------------------------------------------------------- REVC-15..18 · fronteras, esquema y registros
def test_revc_15_estado_publico_minimo_diagnostico_protegido_y_health_igual():
    publico = _CLIENT.get("/api/v1/license/status")
    assert publico.status_code == 200 and sorted(publico.json()) == ["license_url", "mode"]
    assert "revision" not in publico.text.lower()
    assert _CLIENT.get("/api/v1/system/diagnostics").status_code == 401
    diagnostico = _CLIENT.get("/api/v1/system/diagnostics", headers=_sesion("lector"))
    assert diagnostico.status_code == 200 and "revision" not in diagnostico.text.lower()
    assert _CLIENT.get("/api/v1/health/live").json() == {"status": "ok", "service": "kontrol-backend"}
    assert _CLIENT.get("/api/v1/health/ready").status_code == 200


def test_revc_16_la_revision_vive_en_el_artefacto_firmado_sin_columna_ni_migracion_nueva():
    assert "revision" not in LicenseState.__table__.columns and "revision" not in LicenseArtifact.__table__.columns
    with _FACTORY() as db:
        ultimo = db.execute(select(LicenseArtifact).order_by(LicenseArtifact.imported_at.desc(), LicenseArtifact.created_at.desc())).scalars().first()
    assert ultimo.payload["revision"] == 3 and ultimo.payload_hash == contract.payload_hash(ultimo.payload)


def test_revc_17_un_artefacto_vigente_que_no_cumple_el_contrato_cierra_la_reemision_del_periodo():
    with _FACTORY() as db:
        ultimo = db.execute(select(LicenseArtifact).order_by(LicenseArtifact.imported_at.desc(), LicenseArtifact.created_at.desc())).scalars().first()
        intacto = dict(ultimo.payload)
        ultimo.payload = {**intacto, "revision": "corrupta"}  # un artefacto guardado que nadie debería poder escribir
        db.commit()
    try:
        antes = _huella()
        r = _importa(_emite(ANIO + 1))
        assert r.status_code == 423 and r.json()["code"] == "LICENSE_CURRENT_ARTIFACT_INVALID", r.text
        assert {k: v for k, v in _huella().items() if k not in ("eventos", "revision")} == {k: v for k, v in antes.items() if k not in ("eventos", "revision")}
        assert _rechazos()[-1].detail["outcome"] == "CURRENT_ARTIFACT_INVALID"
    finally:
        with _FACTORY() as db:
            ultimo = db.execute(select(LicenseArtifact).order_by(LicenseArtifact.imported_at.desc(), LicenseArtifact.created_at.desc())).scalars().first()
            ultimo.payload = intacto
            db.commit()
    # Restaurado el artefacto, la emisión r5 del emisor (la r4 quedó emitida y rechazada) entra con normalidad.
    assert _importa(_emite(ANIO + 1)).status_code == 200 and _huella()["revision"] == 5


def test_revc_18_los_registros_no_llevan_material_de_clave_ni_firma_ni_cargas(caplog):
    with caplog.at_level(logging.INFO):
        _importa(LEGACY_A)  # LEGACY_AFTER... no: período anterior → PERIOD_DOWNGRADE; y una repetida del período vigente
        r5 = _huella()
        with _CENTRAL() as db:
            emision = central.get_issuance(db, r5["license_id"])
        _importa({"payload": {**emision["payload"], "entitlements": {"x": 1}}, "signature_hex": emision["signature_hex"]})
    texto = caplog.text
    assert "PRIVATE KEY" not in texto and _pem_publica(_PROPIETARIO).splitlines()[1] not in texto
    assert emision["signature_hex"] not in texto and "companies" not in texto


def test_revc_19_con_el_mismo_identificador_manda_el_ultimo_artefacto_aceptado_no_el_primero():
    """Un emisor puede repetir `license_id` entre revisiones (el contrato no lo prohíbe; el central no lo
    hace). El vigente es el ÚLTIMO artefacto aceptado de ese identificador: la r6 con el mismo identificador
    entra, y volver a presentar la r5 exacta —mismo identificador, misma firma— es un retroceso, no un
    «mismo artefacto»."""
    r5 = _huella()
    with _CENTRAL() as db:
        emision_r5 = central.get_issuance(db, r5["license_id"])
    r6_mismo_id = _firmada({**emision_r5["payload"], "revision": 6, "entitlements": {"companies": 2}})
    assert r6_mismo_id["payload"]["license_id"] == r5["license_id"]
    assert _importa(r6_mismo_id).status_code == 200
    assert _huella()["revision"] == 6 and _huella()["license_id"] == r5["license_id"]
    antes = _huella()
    r = _importa({"payload": emision_r5["payload"], "signature_hex": emision_r5["signature_hex"]})
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_REVISION_DOWNGRADE", r.text
    _sin_mover(antes, _huella())
    assert _rechazos()[-1].detail == {"license_id": r5["license_id"], "current_license_id": r5["license_id"], "current_revision": 6,
                                      "incoming_revision": 5, "outcome": "REVISION_DOWNGRADE"}
