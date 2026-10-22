"""Spec 004 · delta dirigido — la instalación no se crea dos veces.

`get_or_create_installation` leía, y si no había instalación generaba una clave,
escribía el fichero de clave privada con `O_TRUNC` e insertaba la fila. Como el
`installation_uuid` es aleatorio, dos altas simultáneas **no chocaban en ningún
índice**: quedaban dos instalaciones, y la segunda había sobrescrito la clave de la
primera. Alcanzable sin credenciales con dos `GET /license/installation-request`
contra una instalación recién desplegada.

Todo corre sobre una base temporal **migrada de cero** (P24): la carrera solo
existe cuando la instalación todavía no está.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.errors import KontrolError
from app.modules.licensing import service as svc
from app.modules.licensing.models import LicenseEvent, LicenseState
from app.modules.organization.models import Installation
from tests.alembic_orden import orden_alembic

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif(
    not PG_URL.startswith("postgresql"),
    reason="La carrera del alta solo es verificable sobre PostgreSQL (P21)",
)

BACKEND = Path(__file__).resolve().parents[1]
BASE = "kontrol_install_race"


def _url(nombre: str) -> str:
    return PG_URL.rsplit("/", 1)[0] + "/" + nombre


@pytest.fixture(scope="module")
def base_limpia():
    admin = create_engine(_url("postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f"DROP DATABASE IF EXISTS {BASE} WITH (FORCE)"))
        c.execute(text(f"CREATE DATABASE {BASE}"))
    env = {**os.environ, "KONTROL_DB_URL": _url(BASE)}
    env.pop("KONTROL_TEST_DB_URL", None)
    migra = subprocess.run(orden_alembic("upgrade", "head"),
                           cwd=BACKEND, env=env, capture_output=True, text=True, timeout=900)
    assert migra.returncode == 0, migra.stderr[-2000:]
    engine = create_engine(_url(BASE), future=True)
    try:
        yield sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    finally:
        engine.dispose()
        with admin.connect() as c:
            c.execute(text(f"DROP DATABASE IF EXISTS {BASE} WITH (FORCE)"))
        admin.dispose()


@pytest.fixture()
def factory(base_limpia, tmp_path, monkeypatch):
    with base_limpia() as db:
        for tabla in ("license_events", "license_states", "installations"):
            db.execute(text(f"DELETE FROM {tabla}"))
        db.commit()
    monkeypatch.setattr(svc, "_private_key_path", lambda: str(tmp_path / "installation_private_key.pem"))
    return base_limpia


def _contar(factory, modelo, *condiciones) -> int:
    with factory() as db:
        return db.execute(select(func.count()).select_from(modelo).where(*condiciones)).scalar()


def test_dos_altas_simultaneas_dejan_una_instalacion_y_una_sola_clave(factory, tmp_path, monkeypatch):
    """Dos llamadas **reales**; la primera queda retenida dentro del alta hasta
    ver a la segunda esperando en PostgreSQL. Si nunca espera, la prueba falla:
    no se certifica una exclusión que no ocurrió."""
    from cryptography.hazmat.primitives import serialization

    real = svc.Ed25519PrivateKey
    dentro, soltar, generadas = threading.Event(), threading.Event(), []

    class Retenida:
        @staticmethod
        def generate():
            generadas.append(1)
            if len(generadas) == 1:
                dentro.set()
                soltar.wait(20)
            return real.generate()

    monkeypatch.setattr(svc, "Ed25519PrivateKey", Retenida)
    uuids, errores, pids = {}, {}, {}

    def alta(nombre: str) -> None:
        db = factory()
        try:
            pids[nombre] = db.execute(text("SELECT pg_backend_pid()")).scalar()
            uuids[nombre] = svc.get_or_create_installation(db).installation_uuid
        except Exception as e:  # noqa: BLE001 - el resultado es la excepción
            errores[nombre] = e
        finally:
            db.close()

    primera = threading.Thread(target=alta, args=("primera",))
    primera.start()
    assert dentro.wait(20), "la primera alta nunca llegó a generar la clave"
    segunda = threading.Thread(target=alta, args=("segunda",))
    segunda.start()
    espero = False
    try:
        fin = time.monotonic() + 15
        while time.monotonic() < fin and not espero:
            if "segunda" in pids:
                with factory() as vigia:
                    espero = vigia.execute(
                        text("SELECT wait_event_type FROM pg_stat_activity WHERE pid = :p"),
                        {"p": pids["segunda"]}).scalar() == "Lock"
            time.sleep(0.05)
    finally:
        soltar.set()
    primera.join(30)
    segunda.join(30)

    assert espero, "la segunda alta nunca esperó a la primera: no hubo exclusión"
    assert not errores, f"una de las altas falló: {errores!r}"
    assert uuids["primera"] == uuids["segunda"], "cada petición se quedó con una identidad distinta"
    assert _contar(factory, Installation) == 1, "se crearon varias instalaciones"
    assert len(generadas) == 1, "se generó más de un par de claves"

    with factory() as db:
        fila = db.execute(select(Installation)).scalars().one()
    privada = serialization.load_pem_private_key(
        (tmp_path / "installation_private_key.pem").read_bytes(), password=None)
    publica = privada.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
    assert publica == fila.public_key, "la clave del volumen no corresponde a la instalación que quedó"


def test_repetir_la_peticion_no_crea_otra_identidad_ni_reescribe_la_clave(factory, tmp_path):
    with factory() as db:
        primera = svc.get_or_create_installation(db).installation_uuid
    clave = tmp_path / "installation_private_key.pem"
    antes = clave.read_bytes()
    with factory() as db:
        segunda = svc.get_or_create_installation(db).installation_uuid
    assert segunda == primera
    assert clave.read_bytes() == antes, "el reintento reescribió la clave privada"
    assert _contar(factory, Installation) == 1


def test_con_dos_filas_heredadas_todas_las_lecturas_eligen_la_mas_antigua(factory):
    """La más nueva se inserta primero en disco: un `limit(1)` sin orden la
    devolvería a ella."""
    from app.modules.setup.api import setup_status

    with factory() as db:
        db.add(Installation(installation_uuid="KTL-VE-NUEVA", public_key="b", state="PENDING",
                            created_at=datetime(2026, 1, 1, tzinfo=UTC)))
        db.commit()
        db.add(Installation(installation_uuid="KTL-VE-VIEJA", public_key="a", state="PENDING",
                            created_at=datetime(2020, 1, 1, tzinfo=UTC)))
        db.commit()
    with factory() as db:
        assert svc.get_installation(db).installation_uuid == "KTL-VE-VIEJA"
        assert svc.get_or_create_installation(db).installation_uuid == "KTL-VE-VIEJA"
        assert setup_status(db).installation == "KTL-VE-VIEJA"


def _licencia(installation_id: str) -> tuple[dict, str, str]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    autoridad = Ed25519PrivateKey.generate()
    publica = autoridad.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
    payload = {
        "issuer": "KONTROL Licensing Authority", "license_id": "LIC-RACE-01",
        "installation_id": installation_id, "customer_id": "CUS-000001",
        "contract_id": "CON-000001", "company_tax_id": "J-12345678-9",
        "period_start": "2026-04-01T00:00:00-04:00", "period_end": "2027-03-31T23:59:59-04:00",
        "critical_warning_start": "2027-04-21T00:00:00-04:00",
        "read_only_start": "2027-05-01T00:00:00-04:00",
        "entitlements": {"companies": 1, "users": 5, "modules": ["ventas"]},
        "minimum_version": "1.0.0", "kid": "kontrol-lic-2026-01",
    }
    canonico = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return payload, autoridad.sign(canonico).hex(), publica


def _importar(factory, monkeypatch, installation_id: str):
    payload, firma, publica = _licencia(installation_id)
    monkeypatch.setenv("KONTROL_LICENSE_PUBLIC_KEY_PEM", publica)
    get_settings.cache_clear()
    try:
        with factory() as db:
            return svc.import_license(db, payload=payload, signature_hex=firma, source="MANUAL")
    finally:
        monkeypatch.delenv("KONTROL_LICENSE_PUBLIC_KEY_PEM", raising=False)
        get_settings.cache_clear()


@pytest.mark.parametrize("ajena", ["KTL-VE-OTRA0000-0000", "FALSIFICADA"])
def test_una_licencia_firmada_para_otra_instalacion_se_rechaza_sin_tocar_el_estado(factory, monkeypatch, ajena):
    with factory() as db:
        svc.get_or_create_installation(db)
    with pytest.raises(KontrolError) as exc:
        _importar(factory, monkeypatch, ajena)
    assert exc.value.code == "LICENSE_INSTALLATION_MISMATCH"
    assert _contar(factory, LicenseState) == 0, "la licencia ajena dejó estado"
    assert _contar(factory, LicenseEvent, LicenseEvent.event_type == "LICENSE_INSTALLATION_MISMATCH") == 1


def test_control_positivo_la_licencia_de_esta_instalacion_si_se_acepta(factory, monkeypatch):
    """Sin esto, el rechazo de arriba podría deberse a una firma mal hecha."""
    with factory() as db:
        propia = svc.get_or_create_installation(db).installation_uuid
    _importar(factory, monkeypatch, propia)
    assert _contar(factory, LicenseState) == 1
