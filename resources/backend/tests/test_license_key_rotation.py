"""KEYROT · El cliente elige la clave pública del propietario EXACTAMENTE por el `kid` firmado y la
autoridad firma con el `kid` activo de su conjunto: rotación A → B con solapamiento y retiro
(LICENCIA-SIN-ROTACION-DE-CLAVE; FR-010-437..487).

Mundo sintético: dos claves del propietario (A, B), la autoridad real en proceso con su conjunto de
firma, el cliente con su conjunto de confianza configurado desde fuera (par de una clave + JSON).
Hostiles firmados a mano con claves sintéticas: `kid` desconocido, `kid` ausente, `kid` A con firma de
B, licencia que «trae» una clave pública. Nada real. Corre en SQLite y PostgreSQL. El retiro de A no
revalida el estado ya persistido: eso sigue siendo `LICENCIA-ESTADO-SIN-REVERIFICAR`.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

import app.core.database as dm
from app.core import license_contract as contract
from app.core.config import Settings as ClientSettings
from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.licensing.models import LicenseArtifact, LicenseEvent, LicenseState
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.setup.api import SetupRequest, initialize
from central_authority import service as central
from central_authority.config import Settings as CentralSettings
from central_authority.config import SigningKeyError, load_signing_key_set
from central_authority.models import Base as CentralBase
from central_authority.models import Issuance
from tests.central.conftest import pem_privada, pem_publica
from tests.conftest import make_engine
from tests.test_license_revision_client import _usuario

PASSWORD = "Kontrol2026Segura!"
IMPORT = "/api/v1/license/import"
CARACAS = timezone(timedelta(hours=-4))
HOY = datetime.now(UTC).astimezone(CARACAS)
ANIO = HOY.year if HOY.month >= 4 else HOY.year - 1
KID_A, KID_B, KID_C = "kid-a-2026", "kid-b-2027", "kid-c-desconocido"
VARS = ("KONTROL_LICENSE_PUBLIC_KEY_PEM", "KONTROL_LICENSE_PUBLIC_KEY_KID", "KONTROL_LICENSE_TRUST_KEYS")

_CLIENT: TestClient
_FACTORY: sessionmaker
_CENTRAL: sessionmaker
_INSTALACION: str
A: Ed25519PrivateKey
B: Ed25519PrivateKey


def _confiar(*, legacy: tuple[str, Ed25519PrivateKey] | None, json_keys: dict[str, Ed25519PrivateKey] | None) -> None:
    """La configuración de confianza del cliente, como la desplegaría el operador (reinicio = `cache_clear`)."""
    for v in VARS:
        os.environ.pop(v, None)
    if legacy is not None:
        os.environ["KONTROL_LICENSE_PUBLIC_KEY_KID"], os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = legacy[0], pem_publica(legacy[1])
    if json_keys is not None:
        os.environ["KONTROL_LICENSE_TRUST_KEYS"] = json.dumps({k: pem_publica(c) for k, c in json_keys.items()})
    get_settings.cache_clear()


def _ajustes_centrales(activo: str, **claves: Ed25519PrivateKey) -> CentralSettings:
    return CentralSettings(_env_file=None, environment="qa", db_url="sqlite+pysqlite:///:memory:", signing_kid=activo,
                           signing_keys=json.dumps({k: pem_privada(c) for k, c in claves.items()}))


@pytest.fixture(scope="module", autouse=True)
def _mundo() -> Iterator[None]:
    global _CLIENT, _FACTORY, _CENTRAL, _INSTALACION, A, B
    A, B = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    anteriores = {v: os.environ.get(v) for v in VARS}
    _confiar(legacy=(KID_A, A), json_keys=None)  # R0: un despliegue de una sola clave, tal como existen hoy
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    dm._engine = engine  # type: ignore[attr-defined]
    dm._SessionLocal = factory  # type: ignore[attr-defined]
    with factory() as db:
        initialize(db, SetupRequest(tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1", company_legal_name="Demo C.A.",
                                    company_rif="J-12345678-9", admin_username="admin", admin_password=PASSWORD))
        tenant = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().one()
        empresa = db.execute(select(Company).where(Company.tenant_id == tenant.id)).scalars().one()
        _usuario(db, str(tenant.id), str(empresa.id), "lector", sin={"license:create"})
        inst = db.execute(select(Installation)).scalars().first()
        _INSTALACION, clave_publica = inst.installation_uuid, inst.public_key
        db.commit()
    motor_central = make_engine()
    CentralBase.metadata.create_all(motor_central)
    _CENTRAL = sessionmaker(bind=motor_central, class_=Session, expire_on_commit=False)
    with _CENTRAL() as db:
        central.register_installation(db, installation_uuid=_INSTALACION, public_key_pem=clave_publica, customer_id="C-TEST", contract_id="K-TEST",
                                      company_tax_id=None, operator="qa")
    from app.main import create_app

    app = create_app()

    def _db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _db
    _CLIENT, _FACTORY = TestClient(app, raise_server_exceptions=False), factory
    try:
        yield
    finally:
        for v, valor in anteriores.items():
            if valor is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = valor
        get_settings.cache_clear()


def _sesion(username: str = "admin") -> dict[str, str]:
    r = login_completo(_CLIENT, "/api/v1/auth/login", json={"tenant_code": "DEMO", "username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _emite(ajustes: CentralSettings, anio: int, **entitlements: Any) -> dict[str, Any]:
    inicio, fin = central.periodo_anual(anio)
    with _CENTRAL() as db:
        return central.issue_license(db, settings=ajustes, installation_uuid=_INSTALACION, period_start=inicio, period_end=fin,
                                     entitlements=entitlements or {"companies": 3}, minimum_version="1.0.0", operator="qa")


def _sintetica(license_id: str, anio: int, clave: Ed25519PrivateKey, *, kid: str | None, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "issuer": "QA", "license_id": license_id, "installation_id": _INSTALACION, "customer_id": "C-TEST", "contract_id": "K-TEST",
        "company_tax_id": "J-00000000-0", "period_start": f"{anio}-04-01T00:00:00-04:00", "period_end": f"{anio + 1}-03-31T23:59:59-04:00",
        "critical_warning_start": f"{anio + 1}-04-21T00:00:00-04:00", "read_only_start": f"{anio + 1}-05-01T00:00:00-04:00",
        "entitlements": {"companies": 3}, "minimum_version": "1.0.0", **extra,
    }
    if kid is not None:
        payload["kid"] = kid
    return {"payload": payload, "signature_hex": contract.sign_license_payload(payload, clave)}


def _importa(artefacto: dict[str, Any], quien: str = "admin"):
    return _CLIENT.post(IMPORT, json={"payload": artefacto["payload"], "signature_hex": artefacto["signature_hex"]}, headers=_sesion(quien))


def _huella() -> dict[str, Any]:
    with _FACTORY() as db:
        s = db.execute(select(LicenseState)).scalars().first()
        ultimo = db.execute(select(LicenseArtifact).order_by(LicenseArtifact.imported_at.desc(), LicenseArtifact.created_at.desc())).scalars().first()
        return {"license_id": s.license_id if s else None, "kid": s.kid if s else None, "mode": s.mode if s else None,
                "period": (s.period_start, s.period_end) if s else None, "entitlements": s.entitlements if s else None,
                "artefacto": ultimo.payload_hash if ultimo else None, "revision": ultimo.payload.get("revision") if ultimo else None,
                "eventos": db.execute(select(LicenseEvent)).scalars().all().__len__()}


def _rechazos() -> list[LicenseEvent]:
    with _FACTORY() as db:
        return list(db.execute(select(LicenseEvent).where(LicenseEvent.event_type == "LICENSE_SIGNING_KEY_REJECTED")
                               .order_by(LicenseEvent.created_at)).scalars().all())


def _sin_mover(antes: dict[str, Any], despues: dict[str, Any], eventos_mas: int = 1) -> None:
    assert {k: v for k, v in despues.items() if k != "eventos"} == {k: v for k, v in antes.items() if k != "eventos"}
    assert despues["eventos"] == antes["eventos"] + eventos_mas


# ---------------------------------------------------------------- R0 · una sola clave, como hoy
def test_keyrot_01_el_despliegue_de_una_clave_es_un_conjunto_de_una_entrada_y_su_kid_la_identifica():
    r1 = _emite(_ajustes_centrales(KID_A, **{KID_A: A}), ANIO)
    assert r1["payload"]["kid"] == KID_A
    r = _importa(r1)
    assert r.status_code == 200, r.text
    assert _huella()["kid"] == KID_A and _huella()["revision"] == 1


def test_keyrot_02_con_una_sola_clave_un_kid_desconocido_se_rechaza_aunque_la_firma_fuera_de_esa_clave():
    antes = _huella()
    hostil = _sintetica("LIC-KID-C", ANIO + 1, A, kid=KID_C)  # firma válida de A, pero el kid dice otra cosa
    r = _importa(hostil)
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_SIGNING_KID_UNKNOWN", r.text
    _sin_mover(antes, _huella())
    assert _rechazos()[-1].detail == {"license_id": "LIC-KID-C", "kid": KID_C, "reason": "unknown_kid"}
    assert "BEGIN" not in r.text and KID_A not in r.text  # no se dice qué claves hay ni cuál verificaría


def test_keyrot_03_un_paquete_sin_kid_esta_fuera_de_contrato_y_se_rechaza():
    antes = _huella()
    for kid in (None, "", "   "):
        r = _importa(_sintetica("LIC-SIN-KID", ANIO + 1, A, kid=kid) if kid is not None else _sintetica("LIC-SIN-KID", ANIO + 1, A, kid=None))
        assert r.status_code == 423 and r.json()["code"] == "LICENSE_SIGNING_KID_MISSING", r.text
    _sin_mover(antes, _huella(), eventos_mas=3)
    assert _rechazos()[-1].detail["reason"] == "kid_missing"


def test_keyrot_04_antes_del_pre_stage_una_licencia_firmada_con_b_no_entra():
    antes = _huella()
    r = _importa(_sintetica("LIC-B-TEMPRANA", ANIO + 1, B, kid=KID_B))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_SIGNING_KID_UNKNOWN", r.text
    _sin_mover(antes, _huella())


# ---------------------------------------------------------------- R1 · pre-stage: confianza A + B
def test_keyrot_05_en_pre_stage_a_sigue_entrando_y_b_ya_entra_cada_una_por_su_kid():
    _confiar(legacy=(KID_A, A), json_keys={KID_B: B})
    autoridad_a = _ajustes_centrales(KID_A, **{KID_A: A, KID_B: B})  # la autoridad ya tiene B cargada, pero el activo sigue siendo A
    r2 = _emite(autoridad_a, ANIO)
    assert r2["payload"]["kid"] == KID_A and r2["revision"] == 2
    assert _importa(r2).status_code == 200 and _huella()["kid"] == KID_A
    sintetica_b = _sintetica("LIC-B-SINTETICA", ANIO + 1, B, kid=KID_B)  # R5 del runbook: una B sintética verifica en QA
    assert _importa(sintetica_b).status_code == 200 and _huella()["kid"] == KID_B and _huella()["period"][0].year == ANIO + 1


def test_keyrot_06_kid_a_con_firma_de_b_se_rechaza_aunque_b_sea_de_confianza_y_nunca_se_prueban_todas():
    antes = _huella()
    confusa = _sintetica("LIC-CONFUSA", ANIO + 2, B, kid=KID_A)  # B firma, pero el kid señala a A
    r = _importa(confusa)
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_SIGNATURE_INVALID", r.text
    assert KID_B not in r.text  # sin decir que «la otra» verificaría
    _sin_mover(antes, _huella())
    with _FACTORY() as db:
        firmas = db.execute(select(LicenseEvent).where(LicenseEvent.event_type == "LICENSE_SIGNATURE_INVALID")).scalars().all()
    assert any(e.detail.get("license_id") == "LIC-CONFUSA" for e in firmas)  # el evento es el de firma, no uno de clave


def test_keyrot_07_una_licencia_que_trae_su_propia_clave_publica_no_se_vuelve_de_confianza():
    antes = _huella()
    intrusa = Ed25519PrivateKey.generate()
    r = _importa(_sintetica("LIC-TRAE-CLAVE", ANIO + 2, intrusa, kid="kid-intrusa", public_key=pem_publica(intrusa)))
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_SIGNING_KID_UNKNOWN", r.text
    _sin_mover(antes, _huella())


# ---------------------------------------------------------------- R2/R3 · la autoridad activa B y reemite
def test_keyrot_08_la_autoridad_con_b_activa_firma_con_b_y_la_reemision_del_mismo_periodo_recibe_revision_nueva():
    _confiar(legacy=(KID_A, A), json_keys={KID_B: B})
    autoridad_b = _ajustes_centrales(KID_B, **{KID_A: A, KID_B: B})
    r2_b = _emite(autoridad_b, ANIO + 1)  # el linaje de ANIO+1 en la autoridad iba por 0: esta es su r1... (la sintética B no pasó por el emisor)
    assert r2_b["payload"]["kid"] == KID_B
    assert contract.verify_license_signature(r2_b["payload"], r2_b["signature_hex"], pem_publica(B))
    assert not contract.verify_license_signature(r2_b["payload"], r2_b["signature_hex"], pem_publica(A))
    # El cliente tiene vigente la sintética B (sin revisión → legacy) del mismo período: la revisionada B entra y fija el linaje.
    assert _importa(r2_b).status_code == 200 and _huella()["kid"] == KID_B and _huella()["revision"] == 1
    r3_b = _emite(autoridad_b, ANIO + 1, companies=9)
    assert r3_b["revision"] == 2 and _importa(r3_b).status_code == 200 and _huella()["revision"] == 2


def test_keyrot_09_la_rotacion_no_reabre_el_anti_retroceso_ni_kid_ordena():
    antes = _huella()  # vigente: ANIO+1 / r2 / kid B
    autoridad_a = _ajustes_centrales(KID_A, **{KID_A: A, KID_B: B})
    with _CENTRAL() as db:
        r1_b = db.execute(select(Issuance).where(Issuance.revision == 1, Issuance.period_start >= central.periodo_anual(ANIO + 1)[0])).scalars().first()
    r = _importa({"payload": r1_b.payload, "signature_hex": r1_b.signature_hex})  # r1/B es anterior a r2/B: retroceso
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_REVISION_DOWNGRADE"
    r3_a = _emite(autoridad_a, ANIO + 1)  # r3 firmada con A (A sigue activa en otra autoridad): kid no ordena, la revisión sí
    assert r3_a["revision"] == 3 and r3_a["payload"]["kid"] == KID_A
    assert _importa(r3_a).status_code == 200 and _huella()["kid"] == KID_A and _huella()["revision"] == 3
    r = _importa({"payload": r1_b.payload, "signature_hex": r1_b.signature_hex})
    assert r.json()["code"] == "LICENSE_REVISION_DOWNGRADE"  # «kid B» no vale más que «kid A»
    vieja_a = _sintetica("LIC-VIEJA-A", ANIO, A, kid=KID_A, revision=999)
    assert _importa(vieja_a).json()["code"] == "LICENSE_PERIOD_DOWNGRADE"  # el período sigue primero
    assert _huella()["revision"] == 3 and _huella()["eventos"] > antes["eventos"]


def test_keyrot_10_entre_periodos_b_entra_con_revision_1_si_b_es_de_confianza():
    autoridad_b = _ajustes_centrales(KID_B, **{KID_A: A, KID_B: B})
    siguiente = _emite(autoridad_b, ANIO + 2)
    assert siguiente["revision"] == 1 and siguiente["payload"]["kid"] == KID_B
    assert _importa(siguiente).status_code == 200 and _huella()["period"][0].year == ANIO + 2 and _huella()["kid"] == KID_B


def test_keyrot_11_el_libro_no_se_reescribe_al_rotar():
    with _CENTRAL() as db:
        filas = db.execute(select(Issuance).order_by(Issuance.issued_at)).scalars().all()
    kids = [f.kid for f in filas]
    assert KID_A in kids and KID_B in kids  # las emisiones A siguen siendo A; las B, B
    for f in filas:
        assert f.payload["kid"] == f.kid and contract.payload_hash(f.payload) == f.payload_hash
        clave = pem_publica(A) if f.kid == KID_A else pem_publica(B)
        assert contract.verify_license_signature(f.payload, f.signature_hex, clave)


# ---------------------------------------------------------------- R4 · retirar A
def test_keyrot_12_retirada_a_una_importacion_nueva_con_kid_a_se_rechaza_y_el_estado_persistido_no_se_toca():
    _confiar(legacy=None, json_keys={KID_B: B})  # solo B
    antes = _huella()
    autoridad_a = _ajustes_centrales(KID_A, **{KID_A: A, KID_B: B})
    con_a = _emite(autoridad_a, ANIO + 2)  # r2 de ANIO+2 firmada con A: ya no se acepta
    assert con_a["revision"] == 2
    r = _importa(con_a)
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_SIGNING_KID_UNKNOWN", r.text
    _sin_mover(antes, _huella())
    assert _huella() == {**antes, "eventos": antes["eventos"] + 1}  # el vigente (ANIO+2/r1/B) sigue; nada se revalida aquí
    autoridad_b = _ajustes_centrales(KID_B, **{KID_B: B})
    con_b = _emite(autoridad_b, ANIO + 2)
    assert con_b["revision"] == 3 and _importa(con_b).status_code == 200 and _huella()["revision"] == 3


def test_keyrot_13_el_estado_vigente_firmado_con_a_sigue_persistido_tras_retirar_a_sin_revalidacion_en_este_ciclo():
    """Documenta la frontera: retirar A no revalida lo ya persistido (`LICENCIA-ESTADO-SIN-REVERIFICAR`, OPEN)."""
    with _FACTORY() as db:
        anteriores = [a for a in db.execute(select(LicenseArtifact)).scalars().all() if a.kid == KID_A]
    assert anteriores, "hubo artefactos A aceptados durante el solapamiento"
    assert _CLIENT.get("/api/v1/license/status").json()["mode"] == "FULL_ACCESS"  # el estado vigente (B) sigue operando


# ---------------------------------------------------------------- configuración: duplicados, vacío, prod
def test_keyrot_14_un_kid_con_dos_claves_distintas_falla_cerrado_antes_de_mirar_el_artefacto():
    _confiar(legacy=(KID_B, A), json_keys={KID_B: B})  # el mismo kid para A y para B
    antes = _huella()
    r = _importa(_sintetica("LIC-X", ANIO + 3, B, kid=KID_B))
    assert r.status_code == 503 and r.json()["code"] == "LICENSE_TRUST_ANCHOR_DUPLICATE_KID", r.text
    assert _huella() == antes  # ni evento: la instalación no puede verificar nada


def test_keyrot_15_la_misma_clave_bajo_dos_kid_falla_cerrado_el_contrato_no_define_alias():
    _confiar(legacy=(KID_A, B), json_keys={KID_B: B})
    r = _importa(_sintetica("LIC-X", ANIO + 3, B, kid=KID_B))
    assert r.status_code == 503 and r.json()["code"] == "LICENSE_TRUST_ANCHOR_DUPLICATE_KEY", r.text


def test_keyrot_16_sin_conjunto_o_con_json_roto_se_falla_cerrado_con_los_codigos_de_siempre():
    _confiar(legacy=None, json_keys=None)
    r = _importa(_sintetica("LIC-X", ANIO + 3, B, kid=KID_B))
    assert r.status_code == 503 and r.json()["code"] == "LICENSE_TRUST_ANCHOR_MISSING"
    os.environ["KONTROL_LICENSE_TRUST_KEYS"] = "{no es json"
    get_settings.cache_clear()
    r = _importa(_sintetica("LIC-X", ANIO + 3, B, kid=KID_B))
    assert r.status_code == 503 and r.json()["code"] == "LICENSE_TRUST_ANCHOR_INVALID"
    _confiar(legacy=(KID_A, A), json_keys={KID_B: B})


def test_keyrot_17_en_prod_el_cliente_no_arranca_sin_conjunto_valido_ni_con_duplicados_y_si_con_el_par_de_una_clave():
    base = {"_env_file": None, "environment": "prod", "secret_key": "x" * 48, "db_url": "postgresql+psycopg2://u:p@h/db"}
    with pytest.raises(ValueError) as exc:
        ClientSettings(**base, license_public_key_pem=None, license_trust_keys=None)
    assert "ancla missing" in str(exc.value) and "BEGIN" not in str(exc.value)
    with pytest.raises(ValueError) as exc:
        ClientSettings(**base, license_public_key_pem=pem_publica(A), license_public_key_kid=KID_B, license_trust_keys=json.dumps({KID_B: pem_publica(B)}))
    assert "duplicate_kid" in str(exc.value)
    assert ClientSettings(**base, license_public_key_pem=pem_publica(A), license_public_key_kid=KID_A, license_trust_keys=None).license_public_key_kid == KID_A
    solo_json = ClientSettings(**base, license_public_key_pem=None, license_trust_keys=json.dumps({KID_A: pem_publica(A), KID_B: pem_publica(B)}))
    assert solo_json.license_public_key_pem is None and KID_B in solo_json.license_trust_keys


def test_keyrot_18_la_autoridad_falla_cerrada_si_el_kid_activo_no_tiene_clave_y_no_elige_la_primera():
    with _CENTRAL() as db, pytest.raises(central.CentralError) as exc:
        central.issue_license(db, settings=_ajustes_centrales("kid-sin-clave", **{KID_A: A, KID_B: B}), installation_uuid=_INSTALACION,
                              period_start=central.periodo_anual(ANIO + 3)[0], period_end=central.periodo_anual(ANIO + 3)[1],
                              entitlements={}, minimum_version="1.0.0", operator="qa")
    assert exc.value.code == "SIGNING_KEY_ACTIVE_KID_MISSING"
    with pytest.raises(SigningKeyError) as exc2:
        load_signing_key_set(CentralSettings(_env_file=None, environment="qa", db_url="sqlite://", signing_kid=KID_A,
                                             signing_keys=json.dumps({KID_A: pem_privada(A), "kid-alias": pem_privada(A)})))
    assert exc2.value.reason == "duplicate_key"


# ---------------------------------------------------------------- fronteras que no cambian
def test_keyrot_19_sesion_permiso_identidad_status_diagnostico_y_health_siguen_igual():
    _confiar(legacy=(KID_A, A), json_keys={KID_B: B})
    cuerpo = _sintetica("LIC-X", ANIO + 3, B, kid=KID_B)
    assert _CLIENT.post(IMPORT, json=cuerpo).status_code == 401
    assert _CLIENT.post(IMPORT, json=cuerpo, headers=_sesion("lector")).status_code == 403
    ajena = _sintetica("LIC-AJENA", ANIO + 3, B, kid=KID_B)
    ajena["payload"]["installation_id"] = "KTL-XX-OTRA"
    ajena["signature_hex"] = contract.sign_license_payload(ajena["payload"], B)
    assert _importa(ajena).json()["code"] == "LICENSE_INSTALLATION_MISMATCH"
    publico = _CLIENT.get("/api/v1/license/status")
    assert sorted(publico.json()) == ["license_url", "mode"] and "kid" not in publico.text
    diagnostico = _CLIENT.get("/api/v1/system/diagnostics", headers=_sesion("lector"))
    assert diagnostico.status_code == 200 and "BEGIN PUBLIC KEY" not in diagnostico.text and "TRUST" not in diagnostico.text
    assert _CLIENT.get("/api/v1/health/live").json() == {"status": "ok", "service": "kontrol-backend"}
    assert "kid" not in _CLIENT.get("/api/v1/health/ready").text
    assert "revision" not in LicenseState.__table__.columns and "trust" not in str(LicenseState.__table__.columns)  # esquema 0
