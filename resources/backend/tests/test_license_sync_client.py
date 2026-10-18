"""CSYNC · El cliente sincroniza con la Autoridad Central AUTENTICANDO a la instalación (desafío-respuesta
Ed25519) y trata lo recibido como un artefacto más que pasa por todas sus compuertas (FR-010-400..415).

La autoridad es la real, en proceso: su app FastAPI (`TestClient`) sobre su propia base es el
transporte del cliente. La clave sintética del propietario firma licencias y es el ancla del
cliente; la clave de identidad de la instalación es la que el propio cliente generó al activarse
(volumen de pruebas) y el vendor la vincula en la autoridad desde la base del cliente. Un transporte
hostil, aparte, prueba la defensa en profundidad. Nada real.

Cada prueba aísla sus datos: las aplicaciones y las claves se comparten a nivel de módulo, pero las
bases de cliente y autoridad se crean nuevas en cada prueba.
"""

from __future__ import annotations

import json
import os

# `central_authority.main` construye su app al importarse y lee `Settings` del entorno: aquí una base en
# memoria y entorno `qa` (como en `tests/central/conftest.py`); la prueba la sustituye por la suya.
os.environ.setdefault("KONTROL_CENTRAL_DB_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("KONTROL_CENTRAL_ENVIRONMENT", "qa")
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

import app.core.database as dm
from app.core import license_contract as contract
from app.core import sync_auth_contract as sa
from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.licensing import service as svc
from app.modules.licensing.models import LicenseEvent, LicenseState, LicenseSyncRun
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

PASSWORD = "Kontrol2026Segura!"
SYNC = "/api/v1/licensing/sync"
CONFIG = "/api/v1/licensing/central-config"
ANCLA = "KONTROL_LICENSE_PUBLIC_KEY_PEM"
CARACAS = timezone(timedelta(hours=-4))
HOY = datetime.now(UTC).astimezone(CARACAS)
ANIO = HOY.year if HOY.month >= 4 else HOY.year - 1

_CLIENT: TestClient
_FACTORY: sessionmaker
_CENTRAL: sessionmaker
_AJUSTES: CentralSettings
_PROPIETARIO: Ed25519PrivateKey
_INSTALACION: str
_CENTRAL_APP: TestClient


class TransporteReal:
    """La autoridad real en proceso: cada llamada del cliente se registra para afirmar qué viajó y qué no."""

    def __init__(self, central_client: TestClient) -> None:
        self.c = central_client
        self.llamadas: list[tuple[str, Any]] = []

    def _post(self, ruta: str, body: bytes, headers: dict[str, str]) -> dict[str, Any]:
        r = self.c.post(ruta, content=body, headers={"Content-Type": "application/json", **headers})
        if 400 <= r.status_code < 500:
            raise svc.CentralSyncRejected(r.json().get("code", "HTTP"), r.status_code, r.json().get("message", ""))
        r.raise_for_status()
        return r.json()

    def challenge(self, server_url: str, installation_id: str) -> dict[str, Any]:
        self.llamadas.append(("challenge", installation_id))
        return self._post(sa.CHALLENGE_TARGET, sa.canonical_body({"installation_id": installation_id}), {})

    def sync(self, server_url: str, body: bytes, headers: dict[str, str]) -> dict[str, Any]:
        self.llamadas.append(("sync", (body, headers)))
        return self._post(sa.SYNC_TARGET, body, headers)


@pytest.fixture(scope="module", autouse=True)
def _aplicaciones():
    global _CLIENT, _AJUSTES, _PROPIETARIO, _CENTRAL_APP
    _PROPIETARIO = Ed25519PrivateKey.generate()
    anterior = os.environ.get(ANCLA)
    os.environ[ANCLA] = pem_publica(_PROPIETARIO)
    get_settings.cache_clear()
    _AJUSTES = CentralSettings(_env_file=None, environment="qa", db_url="sqlite+pysqlite:///:memory:",
                               signing_private_key_pem=pem_privada(_PROPIETARIO), signing_kid="kontrol-lic-2026-01")
    central_main.get_settings = lambda: _AJUSTES  # type: ignore[assignment]
    app_central = central_main.create_app()

    def _db_central():
        d = _CENTRAL()
        try:
            yield d
        finally:
            d.close()

    app_central.dependency_overrides[central_db.get_db] = _db_central
    _CENTRAL_APP = TestClient(app_central)

    from app.main import create_app

    app = create_app()

    def _db():
        d = _FACTORY()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _db
    _CLIENT = TestClient(app, raise_server_exceptions=False)
    # La ruta HTTP del cliente usa el transporte por defecto: aquí, la autoridad real en proceso.
    transporte_original = svc.UrllibSyncTransport
    svc.UrllibSyncTransport = lambda: TransporteReal(_CENTRAL_APP)  # type: ignore[assignment,misc]
    try:
        yield
    finally:
        svc.UrllibSyncTransport = transporte_original  # type: ignore[misc]
        if anterior is None:
            os.environ.pop(ANCLA, None)
        else:
            os.environ[ANCLA] = anterior
        get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _mundo(_aplicaciones):
    global _FACTORY, _CENTRAL, _INSTALACION
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
    with _CENTRAL() as db:  # el vendor vincula la clave pública que el cliente guarda (enrolamiento fuera de banda)
        central.register_installation(db, installation_uuid=_INSTALACION, public_key_pem=clave_publica, customer_id="C-TEST", contract_id="K-TEST",
                                      company_tax_id="J-00000000-0", operator="qa")
    _FACTORY = factory
    try:
        yield
    finally:
        engine.dispose()
        motor_central.dispose()


def _sesion(username: str) -> dict[str, str]:
    r = _CLIENT.post("/api/v1/auth/login", json={"tenant_code": "DEMO", "username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _emite(anio: int, **entitlements: Any) -> dict[str, Any]:
    inicio, fin = central.periodo_anual(anio)
    with _CENTRAL() as db:
        return central.issue_license(db, settings=_AJUSTES, installation_uuid=_INSTALACION, period_start=inicio, period_end=fin,
                                     entitlements=entitlements or {"companies": 3, "modules": {"ventas": True, "compras": False}},
                                     minimum_version="1.0.0", operator="qa")


def _estado() -> LicenseState | None:
    with _FACTORY() as db:
        return db.execute(select(LicenseState)).scalars().first()


def _corridas() -> list[LicenseSyncRun]:
    with _FACTORY() as db:
        return list(db.execute(select(LicenseSyncRun).order_by(LicenseSyncRun.ran_at)).scalars().all())


def _eventos(tipo: str) -> list[LicenseEvent]:
    with _FACTORY() as db:
        return list(db.execute(select(LicenseEvent).where(LicenseEvent.event_type == tipo).order_by(LicenseEvent.created_at)).scalars().all())


def _sincroniza(transporte: Any, actor: str = "admin") -> dict[str, Any]:
    with _FACTORY() as db:
        return svc.sync_license(db, transport=transporte, actor=actor)


def _olvida_idempotencia() -> None:
    """Las pruebas encadenan varios intentos el mismo día: se retira la marca de éxito anterior."""
    with _FACTORY() as db:
        for r in db.execute(select(LicenseSyncRun)).scalars().all():
            r.idempotency_key = f"usada-{r.id}"
        db.commit()


def _configura_autoridad() -> None:
    """Guarda en el cliente la configuración MANUAL de la autoridad para las pruebas que la requieren."""
    r = _CLIENT.put(CONFIG, json={"server_url": "http://127.0.0.1:8010", "public_key": None, "sync_policy": {"mode": "MANUAL"}, "grace_days": 7, "enabled": True},
                    headers=_sesion("admin"))
    assert r.status_code == 200, r.text


def _importa_licencia(anio: int = ANIO) -> dict[str, Any]:
    """Configura la autoridad, emite una licencia y la importa en el cliente vía SYNC como admin."""
    _configura_autoridad()
    licencia = _emite(anio)
    r = _CLIENT.post(SYNC, headers=_sesion("admin"))
    assert r.status_code == 200, r.text
    assert r.json()["response"]["status"] == "LICENSE"
    return licencia


def _sincronizacion_previa() -> None:
    """Precondición de idempotencia: la autoridad configurada y una sincronización con éxito hoy sobre el estado actual."""
    _configura_autoridad()
    assert _sincroniza(TransporteReal(_CENTRAL_APP))["status"] == "SUCCESS"


# ---------------------------------------------------------------- CSYNC-01..04 · configuración y camino bueno
def test_csync_01_configurar_la_autoridad_por_http_local_en_qa_y_sin_licencia_el_sync_responde_no_license():
    r = _CLIENT.put(CONFIG, json={"server_url": "http://127.0.0.1:8010", "public_key": None, "sync_policy": {"mode": "MANUAL"}, "grace_days": 7, "enabled": True},
                    headers=_sesion("admin"))
    assert r.status_code == 200, r.text
    transporte = TransporteReal(_CENTRAL_APP)
    resultado = _sincroniza(transporte)
    assert resultado["status"] == "SUCCESS" and resultado["response"]["status"] == "NO_LICENSE"
    assert [n for n, _ in transporte.llamadas] == ["challenge", "sync"]
    assert _estado() is None and _eventos("LICENSE_SYNCED")[-1].detail["status"] == "NO_LICENSE"


def test_csync_02_la_licencia_emitida_por_la_autoridad_llega_autenticada_y_pasa_por_la_importacion():
    _configura_autoridad()
    _olvida_idempotencia()
    r1 = _emite(ANIO)
    r = _CLIENT.post(SYNC, headers=_sesion("admin"))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "SUCCESS" and r.json()["response"]["license_id"] == r1["license_id"]
    estado = _estado()
    assert estado is not None and estado.license_id == r1["license_id"] and estado.mode == "FULL_ACCESS"
    assert _eventos("LICENSE_IMPORTED")[-1].detail["revision"] == 1 and _eventos("LICENSE_SYNCED")[-1].detail["revision"] == 1
    assert _corridas()[-1].status == "SUCCESS"
    # La matriz de módulos sale del paquete firmado.
    assert svc.module_entitled(_FACTORY(), "ventas") is True and svc.module_entitled(_FACTORY(), "compras") is False


def test_csync_03_lo_que_viaja_son_los_bytes_hasheados_y_ninguna_clave_privada():
    _configura_autoridad()
    _olvida_idempotencia()
    transporte = TransporteReal(_CENTRAL_APP)
    _sincroniza(transporte)
    (_, instalacion), (_, (body, headers)) = transporte.llamadas
    assert instalacion == _INSTALACION
    assert json.loads(body)["installation_id"] == _INSTALACION and b" " not in body.split(b'"license_jws"')[0]  # serializado una vez, canónico
    assert set(headers) == {sa.HEADER_PROTOCOL, sa.HEADER_INSTALLATION, sa.HEADER_CHALLENGE, sa.HEADER_NONCE, sa.HEADER_SIGNATURE}
    todo = body.decode() + json.dumps(headers)
    assert "PRIVATE KEY" not in todo and "BEGIN PUBLIC KEY" not in todo
    with open(svc._private_key_path(), encoding="utf-8") as fh:
        privada = fh.read()
    assert privada.splitlines()[1] not in todo
    # El sobre que firmó el cliente es el que la autoridad verificó: la petición idéntica ya no vale (desafío consumido).
    with pytest.raises(svc.CentralSyncRejected) as exc:
        transporte.sync("", body, headers)
    assert exc.value.code == "SYNC_CHALLENGE_USED"


def test_csync_04_la_sincronizacion_es_idempotente_por_dia_sin_contactar_de_nuevo():
    _sincronizacion_previa()
    transporte = TransporteReal(_CENTRAL_APP)
    resultado = _sincroniza(transporte)
    assert resultado["idempotent"] is True and transporte.llamadas == []


# ---------------------------------------------------------------- CSYNC-05..08 · fallos: sin retroceso, sin reintentos ocultos
def test_csync_05_si_el_transporte_falla_no_hay_retroceso_a_un_sync_anonimo_y_el_siguiente_intento_pide_otro_desafio():
    _configura_autoridad()
    _olvida_idempotencia()

    class Caido(TransporteReal):
        def sync(self, server_url: str, body: bytes, headers: dict[str, str]) -> dict[str, Any]:
            self.llamadas.append(("sync", (body, headers)))
            raise ConnectionError("servidor caído")

    caido = Caido(_CENTRAL_APP)
    with _FACTORY() as db, pytest.raises(svc.KontrolError) as exc:
        svc.sync_license(db, transport=caido, actor="admin")
    assert exc.value.code == "CENTRAL_UNREACHABLE" and exc.value.status_code == 503
    assert [n for n, _ in caido.llamadas] == ["challenge", "sync"]  # un intento lógico: ni segundo envío ni ruta antigua
    assert _corridas()[-1].status == "FAILED" and _corridas()[-1].error == "servidor caído"
    primer_desafio = caido.llamadas[1][1][1][sa.HEADER_CHALLENGE]
    bueno = TransporteReal(_CENTRAL_APP)
    assert _sincroniza(bueno)["status"] == "SUCCESS"
    assert bueno.llamadas[1][1][1][sa.HEADER_CHALLENGE] != primer_desafio  # desafío nuevo por intento


def test_csync_06_si_la_autoridad_rechaza_la_prueba_el_cliente_lo_anota_y_no_toca_el_estado():
    _importa_licencia()
    _olvida_idempotencia()
    antes = _estado().license_id

    class Suplantador(TransporteReal):
        def sync(self, server_url: str, body: bytes, headers: dict[str, str]) -> dict[str, Any]:
            headers = {**headers, sa.HEADER_SIGNATURE: "00" * 64}  # la prueba llega rota a la autoridad
            return super().sync(server_url, body, headers)

    with _FACTORY() as db, pytest.raises(svc.KontrolError) as exc:
        svc.sync_license(db, transport=Suplantador(_CENTRAL_APP), actor="admin")
    assert exc.value.code == "CENTRAL_SYNC_REJECTED" and exc.value.status_code == 502 and exc.value.details == {"central_code": "SYNC_AUTH_INVALID"}
    assert _corridas()[-1].status == "FAILED" and _corridas()[-1].error == "SYNC_AUTH_INVALID"
    assert _eventos("LICENSE_SYNC_REJECTED")[-1].detail == {"central_code": "SYNC_AUTH_INVALID"} and _estado().license_id == antes


def test_csync_07_un_artefacto_de_otra_instalacion_o_manipulado_no_entra_aunque_llegue_autenticado():
    _importa_licencia()
    _olvida_idempotencia()
    antes = _estado().license_id
    ajeno = contract.sign_license_payload  # firmado por el propietario, pero para otra instalación

    class ServidorHostil(TransporteReal):
        def __init__(self, c: TestClient, licencia: dict[str, Any]) -> None:
            super().__init__(c)
            self.licencia = licencia

        def sync(self, server_url: str, body: bytes, headers: dict[str, str]) -> dict[str, Any]:
            real = super().sync(server_url, body, headers)
            return {**real, "status": "LICENSE", "license": self.licencia}

    payload_ajeno = {**_emite(ANIO + 1)["payload"], "installation_id": "KTL-XX-OTRA"}
    hostil = ServidorHostil(_CENTRAL_APP, {"payload": payload_ajeno, "signature_hex": ajeno(payload_ajeno, _PROPIETARIO)})
    with _FACTORY() as db, pytest.raises(svc.KontrolError) as exc:
        svc.sync_license(db, transport=hostil, actor="admin")
    assert exc.value.code == "LICENSE_INSTALLATION_MISMATCH"
    _olvida_idempotencia()
    with _CENTRAL() as db:
        emision = central.select_current_issuance(db, central.get_installation(db, _INSTALACION))
        manipulada = {"payload": {**emision.payload, "entitlements": {"companies": 999}}, "signature_hex": emision.signature_hex}
    with _FACTORY() as db, pytest.raises(svc.KontrolError) as exc:
        svc.sync_license(db, transport=ServidorHostil(_CENTRAL_APP, manipulada), actor="admin")
    assert exc.value.code == "LICENSE_SIGNATURE_INVALID"
    assert _estado().license_id == antes and _corridas()[-1].status == "FAILED"


def test_csync_08_una_respuesta_fuera_de_contrato_se_rechaza():
    _importa_licencia()
    _olvida_idempotencia()

    class Raro(TransporteReal):
        def sync(self, server_url: str, body: bytes, headers: dict[str, str]) -> dict[str, Any]:
            super().sync(server_url, body, headers)
            return {"status": "FULL_ACCESS", "entitlements": {"ventas": True}}  # el contrato anónimo de antes

    with _FACTORY() as db, pytest.raises(svc.KontrolError) as exc:
        svc.sync_license(db, transport=Raro(_CENTRAL_APP), actor="admin")
    assert exc.value.code == "CENTRAL_RESPONSE_INVALID" and exc.value.status_code == 502
    assert _estado().mode == "FULL_ACCESS" and svc.module_entitled(_FACTORY(), "compras") is False  # nada se aplicó del servidor


# ---------------------------------------------------------------- CSYNC-09..12 · compuertas locales, READ_ONLY, HTTPS, clave
def test_csync_09_la_ruta_local_sigue_exigiendo_sesion_y_license_create():
    assert _CLIENT.post(SYNC).status_code == 401
    assert _CLIENT.post(SYNC, headers=_sesion("lector")).status_code == 403


def test_csync_10_en_solo_lectura_la_renovacion_por_sync_sigue_siendo_posible():
    _importa_licencia()
    _olvida_idempotencia()
    with _FACTORY() as db:
        estado = db.execute(select(LicenseState)).scalars().one()
        ahora = datetime.now(UTC)
        estado.period_start, estado.period_end = ahora - timedelta(days=400), ahora - timedelta(days=40)
        estado.critical_warning_start, estado.read_only_start = ahora - timedelta(days=20), ahora - timedelta(days=10)
        db.commit()
    assert _CLIENT.get("/api/v1/license/status").json()["mode"] == "READ_ONLY"
    nueva = _emite(ANIO + 1)  # la autoridad ya tiene un período posterior (r2 de ANIO+1)
    r = _CLIENT.post(SYNC, headers=_sesion("admin"))
    assert r.status_code == 200, r.text
    assert _estado().license_id == nueva["license_id"] and _CLIENT.get("/api/v1/license/status").json()["mode"] == "FULL_ACCESS"


def test_csync_11_en_produccion_la_autoridad_debe_ir_por_https():
    _configura_autoridad()
    produccion = get_settings().model_copy(update={"environment": "prod"})
    original = svc.get_settings
    svc.get_settings = lambda: produccion  # type: ignore[assignment]
    try:
        r = _CLIENT.put(CONFIG, json={"server_url": "http://central.example", "public_key": None, "sync_policy": {"mode": "MANUAL"}, "grace_days": 7, "enabled": True},
                        headers=_sesion("admin"))
        assert r.status_code == 422 and r.json()["code"] == "CENTRAL_URL_INSECURE", r.text
        _olvida_idempotencia()
        transporte = TransporteReal(_CENTRAL_APP)
        with _FACTORY() as db, pytest.raises(svc.KontrolError) as exc:
            svc.sync_license(db, transport=transporte, actor="admin")  # la configuración guardada es http://
        assert exc.value.code == "CENTRAL_URL_INSECURE" and transporte.llamadas == []
    finally:
        svc.get_settings = original  # type: ignore[assignment]
    r = _CLIENT.put(CONFIG, json={"server_url": "https://central.example", "public_key": None, "sync_policy": {"mode": "MANUAL"}, "grace_days": 7, "enabled": True},
                    headers=_sesion("admin"))
    assert r.status_code == 200


def test_csync_12_sin_clave_privada_de_instalacion_el_sync_falla_cerrado_antes_de_contactar():
    _configura_autoridad()
    _olvida_idempotencia()
    ruta = svc._private_key_path()
    os.rename(ruta, ruta + ".fuera")
    try:
        transporte = TransporteReal(_CENTRAL_APP)
        with _FACTORY() as db, pytest.raises(svc.KontrolError) as exc:
            svc.sync_license(db, transport=transporte, actor="admin")
        assert exc.value.code == "INSTALLATION_KEY_UNAVAILABLE" and exc.value.status_code == 503 and transporte.llamadas == []
        assert _corridas()[-1].status == "FAILED"
    finally:
        os.rename(ruta + ".fuera", ruta)


def test_csync_13_el_ayudante_local_exporta_solo_la_clave_publica_de_la_instalacion(capsys):
    from scripts import clave_publica_instalacion as ayudante

    assert ayudante.main(["--huella"]) == 0
    salida = capsys.readouterr().out
    with _FACTORY() as db:
        publica = db.execute(select(Installation)).scalars().first().public_key
    assert salida.startswith("-----BEGIN PUBLIC KEY-----") and publica.strip() in salida
    assert f"huella sha256: {sa.public_key_fingerprint(publica)}" in salida
    assert "PRIVATE" not in salida
