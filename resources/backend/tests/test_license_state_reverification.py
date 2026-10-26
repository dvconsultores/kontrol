"""REVST · El artefacto de licencia vigente y persistido se reverifica con la política de confianza
de HOY al arrancar y antes de cada escritura (LICENCIA-ESTADO-SIN-REVERIFICAR; DOC-07 §10.1, §14.5,
§15.1, §16.2; FR-010-488..537).

«Reiniciar» aquí es crear la aplicación de nuevo y abrirla con su `lifespan` (`with TestClient(app)`);
«restaurar» es copiar el estado y el artefacto a una base nueva. Los hostiles escriben directamente en
las tablas (manipulación fuera del flujo normal) con claves sintéticas. Un fallo deja SECURITY_SUSPENSION:
las escrituras de negocio se bloquean, la sesión y la lectura siguen, y una licencia válida importada o
sincronizada (con la Autoridad Central real en proceso) recupera la operación. Nada real.
"""

from __future__ import annotations

import json
import os

# `central_authority.main` construye su app al importarse y lee `Settings` del entorno: aquí una base en
# memoria y entorno `qa`; los ajustes reales de la autoridad en proceso se inyectan en cada prueba.
os.environ.setdefault("KONTROL_CENTRAL_DB_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("KONTROL_CENTRAL_ENVIRONMENT", "qa")
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
from app.core import license_reverification as nucleo
from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.licensing import reverification
from app.modules.licensing import service as svc
from app.modules.licensing.models import LicenseArtifact, LicenseEvent, LicenseState
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.setup.api import SetupRequest, initialize
from central_authority import database as central_db
from central_authority import main as central_main
from central_authority import service as central
from central_authority.config import Settings as CentralSettings
from central_authority.models import Base as CentralBase
from tests.central.conftest import pem_privada, pem_publica
from tests.conftest import make_engine
from tests.test_license_revision_client import _usuario
from tests.test_license_sync_client import TransporteReal

PASSWORD = "Kontrol2026Segura!"
IMPORT = "/api/v1/license/import"
ESCRITURA = ("/api/v1/licensing/central-config", {"server_url": "http://127.0.0.1:8010", "public_key": None, "sync_policy": {"mode": "MANUAL"}, "grace_days": 7, "enabled": True})
CARACAS = timezone(timedelta(hours=-4))
HOY = datetime.now(UTC).astimezone(CARACAS)
ANIO = HOY.year if HOY.month >= 4 else HOY.year - 1
KID_A, KID_B = "kid-a-2026", "kid-b-2027"
VARS = ("KONTROL_LICENSE_PUBLIC_KEY_PEM", "KONTROL_LICENSE_PUBLIC_KEY_KID", "KONTROL_LICENSE_TRUST_KEYS")

_FACTORY: sessionmaker
_CENTRAL: sessionmaker
_INSTALACION: str
A: Ed25519PrivateKey
B: Ed25519PrivateKey


def _confiar(**kids: Ed25519PrivateKey) -> None:
    for v in VARS:
        os.environ.pop(v, None)
    os.environ["KONTROL_LICENSE_TRUST_KEYS"] = json.dumps({k: pem_publica(c) for k, c in kids.items()})
    get_settings.cache_clear()


def _autoridad(activo: str) -> CentralSettings:
    return CentralSettings(_env_file=None, environment="qa", db_url="sqlite+pysqlite:///:memory:", signing_kid=activo,
                           signing_keys=json.dumps({KID_A: pem_privada(A), KID_B: pem_privada(B)}))


def _arranca() -> TestClient:
    """Un «proceso» nuevo: aplicación nueva y su `lifespan` (reverificación de arranque)."""
    from app.main import create_app

    app = create_app()

    def _db():
        d = _FACTORY()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _db
    cliente = TestClient(app, raise_server_exceptions=False)
    cliente.__enter__()
    return cliente


@pytest.fixture(scope="module", autouse=True)
def _mundo() -> Iterator[None]:
    global _FACTORY, _CENTRAL, _INSTALACION, A, B
    A, B = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    anteriores = {v: os.environ.get(v) for v in VARS}
    _confiar(**{KID_A: A, KID_B: B})
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    _FACTORY = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    dm._engine = engine  # type: ignore[attr-defined]
    dm._SessionLocal = _FACTORY  # type: ignore[attr-defined]
    with _FACTORY() as db:
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
    try:
        yield
    finally:
        for v, valor in anteriores.items():
            if valor is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = valor
        get_settings.cache_clear()


def _sesion(c: TestClient, username: str = "admin") -> dict[str, str]:
    r = login_completo(c, "/api/v1/auth/login", json={"tenant_code": "DEMO", "username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _emite(activo: str, anio: int) -> dict[str, Any]:
    inicio, fin = central.periodo_anual(anio)
    with _CENTRAL() as db:
        return central.issue_license(db, settings=_autoridad(activo), installation_uuid=_INSTALACION, period_start=inicio, period_end=fin,
                                     entitlements={"companies": 3}, minimum_version="1.0.0", operator="qa")


def _importa(c: TestClient, artefacto: dict[str, Any]):
    return c.post(IMPORT, json={"payload": artefacto["payload"], "signature_hex": artefacto["signature_hex"]}, headers=_sesion(c))


def _vigente() -> tuple[LicenseState, LicenseArtifact]:
    with _FACTORY() as db:
        s = db.execute(select(LicenseState)).scalars().one()
        a = reverification.artefacto_vigente(db, s)
        assert a is not None
        return s, a


def _eventos_fallo() -> list[LicenseEvent]:
    with _FACTORY() as db:
        return list(db.execute(select(LicenseEvent).where(LicenseEvent.event_type == reverification.EVENTO_FALLO)
                               .order_by(LicenseEvent.created_at)).scalars().all())


def _estado_de(c: TestClient) -> dict[str, Any]:
    return c.get("/api/v1/license/status").json()


def _escritura(c: TestClient):
    ruta, cuerpo = ESCRITURA
    return c.put(ruta, json=cuerpo, headers=_sesion(c))


def _restaurar_artefacto(payload: dict[str, Any], firma: str, huella: str) -> None:
    with _FACTORY() as db:
        s = db.execute(select(LicenseState)).scalars().one()
        a = reverification.artefacto_vigente(db, s)
        a.payload, a.signature_hex, a.payload_hash = payload, firma, huella
        db.commit()


# ---------------------------------------------------------------- REVST-01..03 · sin licencia, válida, válida pero vencida
def test_revst_01_sin_licencia_vigente_el_arranque_es_pending_y_el_setup_y_la_sesion_siguen():
    c = _arranca()
    assert reverification.ultimo_arranque is not None and reverification.ultimo_arranque.status == nucleo.NO_CURRENT_LICENSE
    assert _estado_de(c) == {"mode": "PENDING", "license_url": "/mi-licencia"}
    assert _sesion(c)  # la sesión del administrador existe antes que la licencia (setup)
    diagnostico = c.get("/api/v1/system/diagnostics", headers=_sesion(c, "lector")).json()
    assert diagnostico["license"]["verification"] == "NO_CURRENT_LICENSE"


def test_revst_02_con_una_licencia_valida_el_arranque_la_reverifica_y_las_escrituras_estan_autorizadas():
    c = _arranca()
    r1 = _emite(KID_A, ANIO)
    assert _importa(c, r1).status_code == 200
    c = _arranca()  # reinicio
    assert reverification.ultimo_arranque.status == nucleo.VALID and reverification.ultimo_arranque.kid == KID_A
    assert _estado_de(c)["mode"] == "FULL_ACCESS"
    assert _escritura(c).status_code == 200
    assert c.get("/api/v1/license/detail", headers=_sesion(c)).json()["verification"] == "VALID"
    assert _eventos_fallo() == []


def test_revst_03_una_licencia_valida_vencida_es_read_only_por_fechas_no_firma_invalida():
    with _FACTORY() as db:  # el tiempo pasa: el estado derivado envejece (como hacen las suites de licencia); el artefacto es el mismo
        s = db.execute(select(LicenseState)).scalars().one()
        ahora = datetime.now(UTC)
        originales = (s.period_start, s.period_end, s.critical_warning_start, s.read_only_start)
        s.period_start, s.period_end = ahora - timedelta(days=400), ahora - timedelta(days=40)
        s.critical_warning_start, s.read_only_start = ahora - timedelta(days=20), ahora - timedelta(days=10)
        db.commit()
    try:
        c = _arranca()
        assert reverification.ultimo_arranque.status == nucleo.VALID
        assert _estado_de(c)["mode"] == "READ_ONLY"
        assert _escritura(c).json()["code"] == "LICENSE_READ_ONLY"
        assert _eventos_fallo() == []
    finally:
        with _FACTORY() as db:
            s = db.execute(select(LicenseState)).scalars().one()
            s.period_start, s.period_end, s.critical_warning_start, s.read_only_start = originales
            db.commit()


# ---------------------------------------------------------------- REVST-04..07 · hostiles sobre el artefacto persistido
def test_revst_04_una_firma_manipulada_en_la_base_se_detecta_al_reiniciar_y_suspende_sin_romper_sesion_ni_lectura():
    _, a = _vigente()
    original = (dict(a.payload), a.signature_hex, a.payload_hash)
    _restaurar_artefacto(a.payload, "00" * 64, a.payload_hash)
    c = _arranca()
    assert reverification.ultimo_arranque.status == nucleo.SIGNATURE_INVALID
    assert _estado_de(c) == {"mode": "SECURITY_SUSPENSION", "license_url": "/mi-licencia"}
    r = _escritura(c)
    assert r.status_code == 423 and r.json()["code"] == "LICENSE_SECURITY_SUSPENSION"
    assert "signature" not in r.text and "kid" not in r.text and "BEGIN" not in r.text
    assert c.get("/api/v1/license/detail", headers=_sesion(c)).status_code == 200  # sesión y lectura siguen
    eventos = _eventos_fallo()
    assert eventos[-1].detail == {"license_id": a.license_id, "kid": KID_A, "status": "SIGNATURE_INVALID", "reason": "owner_signature"}
    assert eventos[-1].user_id is None and eventos[-1].source == "SYSTEM"
    assert set(eventos[-1].detail) == {"license_id", "kid", "status", "reason"}  # sin material: ni firma, ni carga, ni claves
    assert "00" * 64 not in json.dumps(eventos[-1].detail) and "BEGIN" not in json.dumps(eventos[-1].detail)
    _, sigue = _vigente()
    assert sigue.signature_hex == "00" * 64  # el artefacto no se borra ni se repara en silencio
    _restaurar_artefacto(*original)
    c = _arranca()
    assert reverification.ultimo_arranque.status == nucleo.VALID and _estado_de(c)["mode"] == "FULL_ACCESS"


def test_revst_05_reinicios_repetidos_con_el_mismo_fallo_anotan_un_solo_evento():
    _, a = _vigente()
    original = (dict(a.payload), a.signature_hex, a.payload_hash)
    _restaurar_artefacto(a.payload, "00" * 64, a.payload_hash)
    antes = len(_eventos_fallo())
    for _ in range(3):
        c = _arranca()
        _estado_de(c)
        _escritura(c)
    assert len(_eventos_fallo()) == antes  # el mismo fallo ya estaba anotado (REVST-04): no se repite
    _restaurar_artefacto(*original)


def test_revst_06_una_carga_alterada_con_hash_y_firma_intactos_es_una_rotura_de_integridad():
    _, a = _vigente()
    original = (dict(a.payload), a.signature_hex, a.payload_hash)
    _restaurar_artefacto({**a.payload, "entitlements": {"companies": 999}}, a.signature_hex, a.payload_hash)
    c = _arranca()
    assert reverification.ultimo_arranque.status == nucleo.ARTIFACT_STATE_MISMATCH and reverification.ultimo_arranque.reason == "payload_hash"
    assert _estado_de(c)["mode"] == "SECURITY_SUSPENSION"
    _restaurar_artefacto(*original)


def test_revst_07_un_artefacto_de_otra_instalacion_bien_firmado_no_vale_aqui():
    _, a = _vigente()
    original = (dict(a.payload), a.signature_hex, a.payload_hash)
    ajeno = {**a.payload, "installation_id": "KTL-XX-OTRA"}
    firma = contract.sign_license_payload(ajeno, A)
    _restaurar_artefacto(ajeno, firma, contract.payload_hash(ajeno))
    c = _arranca()
    assert reverification.ultimo_arranque.status == nucleo.INSTALLATION_MISMATCH
    assert _estado_de(c)["mode"] == "SECURITY_SUSPENSION"
    _restaurar_artefacto(*original)


def test_revst_08_un_estado_que_senala_una_licencia_sin_artefacto_es_rotura_de_vinculo():
    with _FACTORY() as db:
        s = db.execute(select(LicenseState)).scalars().one()
        original = s.license_id
        s.license_id = "LIC-SIN-ARTEFACTO"
        db.commit()
    c = _arranca()
    assert reverification.ultimo_arranque.status == nucleo.ARTIFACT_STATE_MISMATCH and reverification.ultimo_arranque.reason == "artifact_missing"
    assert _estado_de(c)["mode"] == "SECURITY_SUSPENSION"
    with _FACTORY() as db:
        s = db.execute(select(LicenseState)).scalars().one()
        s.license_id = original
        db.commit()


# ---------------------------------------------------------------- REVST-09..11 · retiro de clave, restauración y recuperación
def test_revst_09_retirada_la_clave_a_el_vigente_firmado_con_a_deja_de_estar_verificado_al_arrancar():
    _confiar(**{KID_B: B})  # T1: el operador retira A; T2: reinicio
    c = _arranca()
    assert reverification.ultimo_arranque.status == nucleo.KID_UNKNOWN and reverification.ultimo_arranque.kid == KID_A
    assert _estado_de(c)["mode"] == "SECURITY_SUSPENSION"
    assert _escritura(c).json()["code"] == "LICENSE_SECURITY_SUSPENSION"
    assert _eventos_fallo()[-1].detail["status"] == "KID_UNKNOWN"


def test_revst_10_la_recuperacion_es_el_sync_autenticado_con_la_autoridad_que_ya_firma_con_b():
    c = _arranca()
    assert _estado_de(c)["mode"] == "SECURITY_SUSPENSION"
    _emite(KID_B, ANIO + 1)  # la autoridad (activo B) tiene una licencia nueva para esta instalación
    monkey = svc.UrllibSyncTransport
    central_main.get_settings = lambda: _autoridad(KID_B)  # type: ignore[assignment]
    app_central = central_main.create_app()

    def _db_central():
        d = _CENTRAL()
        try:
            yield d
        finally:
            d.close()

    app_central.dependency_overrides[central_db.get_db] = _db_central
    svc.UrllibSyncTransport = lambda: TransporteReal(TestClient(app_central))  # type: ignore[assignment,misc]
    try:
        assert _escritura(c).status_code == 423  # la configuración central es escritura de negocio: sigue bloqueada
        with _FACTORY() as db:  # configurar la autoridad es escritura bloqueada; el operador la tenía configurada de antes
            svc.upsert_central_config(db, server_url="http://127.0.0.1:8010", public_key=None, sync_policy={"mode": "MANUAL"}, grace_days=7, enabled=True, actor="admin")
        r = c.post("/api/v1/licensing/sync", headers=_sesion(c))  # exenta del bloqueo: es la vía de recuperación
        assert r.status_code == 200, r.text
    finally:
        svc.UrllibSyncTransport = monkey  # type: ignore[misc]
    assert _estado_de(c)["mode"] == "FULL_ACCESS"
    assert _vigente()[1].kid == KID_B
    c = _arranca()
    assert reverification.ultimo_arranque.status == nucleo.VALID and _escritura(c).status_code == 200


def test_revst_11_una_restauracion_en_otra_base_se_reverifica_igual_que_un_arranque():
    global _FACTORY
    s0, a0 = _vigente()
    anterior = _FACTORY
    motor = make_engine()
    Base.metadata.create_all(motor)
    _FACTORY = sessionmaker(bind=motor, class_=Session, expire_on_commit=False)
    dm._engine, dm._SessionLocal = motor, _FACTORY  # type: ignore[attr-defined]
    try:
        with anterior() as origen, _FACTORY() as destino:  # «restaurar»: copiar la instalación, el estado y el artefacto
            inst = origen.execute(select(Installation)).scalars().one()
            destino.add(Installation(installation_uuid=inst.installation_uuid, public_key=inst.public_key, state=inst.state, key_reference=inst.key_reference))
            destino.add(LicenseState(**{c.name: getattr(s0, c.name) for c in LicenseState.__table__.columns if c.name not in ("id", "created_at", "updated_at")}))
            destino.add(LicenseArtifact(**{c.name: getattr(a0, c.name) for c in LicenseArtifact.__table__.columns if c.name not in ("id", "created_at", "updated_at")}))
            destino.commit()
        _confiar(**{KID_A: A})  # el entorno restaurado solo confía en A: el vigente (B) ya no verifica
        with _FACTORY() as db:
            inst = db.execute(select(Installation)).scalars().one()
            s = db.execute(select(LicenseState)).scalars().one()
            assert reverification.reverificar_vigente(db, inst, s).status == nucleo.KID_UNKNOWN
        _confiar(**{KID_A: A, KID_B: B})  # con la confianza correcta, la restauración verifica
        with _FACTORY() as db:
            inst = db.execute(select(Installation)).scalars().one()
            s = db.execute(select(LicenseState)).scalars().one()
            assert reverification.reverificar_vigente(db, inst, s).status == nucleo.VALID
    finally:
        _FACTORY = anterior
        dm._engine, dm._SessionLocal = anterior.kw["bind"], anterior  # type: ignore[attr-defined]


# ---------------------------------------------------------------- REVST-12..14 · arranque sin base, determinismo, fronteras
def test_revst_12_si_la_base_no_responde_al_arrancar_el_proceso_no_cae_y_el_gate_decide_por_peticion():
    def rota():
        raise RuntimeError("base no disponible")

    assert reverification.reverificar_al_arrancar(rota) is None and reverification.ultimo_arranque is None
    c = _arranca()  # con la base, el arranque y las peticiones vuelven a decidir
    assert reverification.ultimo_arranque.status == nucleo.VALID and _estado_de(c)["mode"] == "FULL_ACCESS"


def test_revst_13_la_reverificacion_es_determinista_idempotente_y_no_toca_el_artefacto():
    with _FACTORY() as db:
        inst = db.execute(select(Installation)).scalars().one()
        s = db.execute(select(LicenseState)).scalars().one()
        a = reverification.artefacto_vigente(db, s)
        antes = (dict(a.payload), a.signature_hex, a.payload_hash, a.imported_at)
        resultados = {reverification.reverificar_vigente(db, inst, s) for _ in range(5)}
        db.refresh(a)
        despues = (dict(a.payload), a.signature_hex, a.payload_hash, a.imported_at)
    assert len(resultados) == 1 and next(iter(resultados)).status == nucleo.VALID and antes == despues
    assert len({r.status for r in [reverification.ultimo_arranque]}) == 1


def test_revst_14_status_publico_minimo_health_igual_diagnostico_sin_material_y_esquema_cero():
    c = _arranca()
    assert sorted(_estado_de(c)) == ["license_url", "mode"]
    assert c.get("/api/v1/health/live").json() == {"status": "ok", "service": "kontrol-backend"}
    assert "verification" not in c.get("/api/v1/health/ready").text
    assert c.get("/api/v1/system/diagnostics").status_code == 401
    diagnostico = c.get("/api/v1/system/diagnostics", headers=_sesion(c, "lector"))
    assert diagnostico.json()["license"]["verification"] == "VALID" and "BEGIN" not in diagnostico.text and "signature" not in diagnostico.text
    assert "verification" not in LicenseState.__table__.columns and "verification" not in LicenseArtifact.__table__.columns


def test_revst_15_un_conjunto_de_confianza_roto_deja_al_vigente_sin_autoridad_y_lo_dice_como_clase():
    os.environ["KONTROL_LICENSE_TRUST_KEYS"] = "{esto no es json"
    get_settings.cache_clear()
    try:
        c = _arranca()
        assert reverification.ultimo_arranque.status == nucleo.TRUST_SET_INVALID
        assert _estado_de(c)["mode"] == "SECURITY_SUSPENSION"
        assert _escritura(c).json()["code"] == "LICENSE_SECURITY_SUSPENSION"
        assert _eventos_fallo()[-1].detail["status"] == "TRUST_SET_INVALID"
        assert "json" not in c.get("/api/v1/license/status").text  # la clase, nunca el porqué, en lo público
    finally:
        _confiar(**{KID_A: A, KID_B: B})
    c = _arranca()
    assert reverification.ultimo_arranque.status == nucleo.VALID and _estado_de(c)["mode"] == "FULL_ACCESS"
