"""KR · La referencia de la clave de la instalación no depende de la ruta del volumen (INSTALACION-KEY-REFERENCE-120, A3).

Contrato ratificado el 2026-10-13: `Installation.key_reference` guarda, para las altas nuevas, una referencia
RELATIVA al volumen (`installation_private_key.pem`); las filas históricas con ruta absoluta siguen valiendo tal
cual; `None` → ruta canónica por configuración; nunca el directorio de trabajo; nunca material de clave en la
base. Sin migración: la columna sigue siendo `String(120)`. PostgreSQL es la autoridad del largo (SQLite no hace
cumplir `VARCHAR`); ambos motores comparten la semántica. Claves: sintéticas, generadas en un temporal.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy import String, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core import license_contract
from app.core import sync_auth_contract as sync_auth
from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.core.errors import KontrolError
from app.modules.licensing import service as svc
from app.modules.organization.models import Installation
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine
from tests.test_system_access import PASSWORD

PG = os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql")
CANONICA = "installation_private_key.pem"
#: Un volumen «largo»: la ruta absoluta del fichero supera 120 caracteres, el caso que rompía el alta.
SEGMENTO_LARGO = "despliegues/cliente-con-un-nombre-largo/instalacion-principal/volumenes/estado-de-licencia-kontrol-produccion"


def _volumen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, forma: str) -> str:
    ruta = {"corto": tmp_path / "v", "medio": tmp_path / "despliegues" / "cliente" / "licencia", "largo": tmp_path / SEGMENTO_LARGO}[forma]
    ruta.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("KONTROL_INSTALLATION_VOLUME_PATH", str(ruta))
    get_settings.cache_clear()
    return str(ruta)


@pytest.fixture
def sesion() -> Iterator[sessionmaker]:
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    engine.dispose()


def _alta(factory: sessionmaker) -> Installation:
    with factory() as db:
        initialize(db, SetupRequest(tenant_code="DEMO", tenant_name="Demo", company_code="D1", company_legal_name="Demo C.A.",
                                    company_rif="J-12345678-9", admin_username="admin", admin_password=PASSWORD))
        return db.execute(select(Installation)).scalars().one()


def _clave_sintetica(ruta: Path) -> Ed25519PrivateKey:
    clave = Ed25519PrivateKey.generate()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(clave.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    ruta.chmod(0o600)
    return clave


# ----------------------------------------------------------------------------- KR-01/02/03/04 · el alta con cualquier volumen
@pytest.mark.parametrize("forma", ["corto", "medio", "largo"])
def test_kr_01_04_el_alta_persiste_la_referencia_canonica_sea_cual_sea_el_largo_del_volumen(forma: str, tmp_path, monkeypatch, sesion):
    volumen = _volumen(tmp_path, monkeypatch, forma)
    if forma == "largo":
        assert len(os.path.join(volumen, CANONICA)) > 120, "el escenario debe superar el límite que rompía el alta"
    instalacion = _alta(sesion)
    assert instalacion.key_reference == CANONICA
    assert len(instalacion.key_reference) == len(CANONICA) <= 120
    assert os.path.isfile(os.path.join(volumen, CANONICA)), "la clave sigue en el volumen configurado"
    assert (os.stat(os.path.join(volumen, CANONICA)).st_mode & 0o777) == 0o600


@pytest.mark.skipif(not PG, reason="PostgreSQL es la autoridad del largo de la columna (KR-01/KR-25)")
def test_kr_25_en_postgresql_el_volumen_largo_que_rompia_el_alta_ya_no_lo_rompe(tmp_path, monkeypatch, sesion):
    volumen = _volumen(tmp_path, monkeypatch, "largo")
    assert len(volumen) > 100
    instalacion = _alta(sesion)
    with sesion() as db:
        assert db.execute(text("select key_reference from installations")).scalar_one() == CANONICA
    assert instalacion.installation_uuid.startswith("KTL-VE-")


# ----------------------------------------------------------------------------- KR-05/06/15 · la fila histórica absoluta
def test_kr_05_06_15_una_referencia_absoluta_historica_se_usa_tal_cual_y_no_se_reescribe(tmp_path, monkeypatch, sesion):
    _volumen(tmp_path, monkeypatch, "corto")
    legado = str(tmp_path / "legado" / "otro-volumen" / CANONICA)
    with sesion() as db:
        db.add(Installation(installation_uuid="KTL-VE-LEGADO01-0001", public_key="-----BEGIN PUBLIC KEY-----\nAA==\n-----END PUBLIC KEY-----\n",
                            state="ACTIVE", key_reference=legado))
        db.commit()
    assert svc.resolve_key_reference(legado) == legado
    with sesion() as db:
        # Un ciclo completo de «alta» devuelve la instalación existente y no toca la fila.
        assert svc.get_or_create_installation(db).key_reference == legado
        db.commit()
        assert db.execute(text("select key_reference from installations")).scalar_one() == legado


# ----------------------------------------------------------------------------- KR-07/13 · la relativa y None
def test_kr_07_13_la_relativa_se_resuelve_contra_el_volumen_configurado_y_none_contra_la_ruta_canonica(tmp_path, monkeypatch):
    volumen = _volumen(tmp_path, monkeypatch, "medio")
    assert svc.resolve_key_reference(CANONICA) == os.path.join(volumen, CANONICA)
    assert svc.resolve_key_reference(None) == svc._private_key_path() == os.path.join(volumen, CANONICA)
    # Si el volumen se reubica, la misma referencia relativa sigue al volumen; nunca al directorio de trabajo.
    otro = _volumen(tmp_path, monkeypatch, "largo")
    assert svc.resolve_key_reference(CANONICA) == os.path.join(otro, CANONICA)
    assert not svc.resolve_key_reference(CANONICA).startswith(os.getcwd()) or os.getcwd() in otro


# ----------------------------------------------------------------------------- KR-16 · seguridad: nada sale del volumen
@pytest.mark.parametrize("maliciosa", ["../installation_private_key.pem", "..", ".", "", "claves/otra.pem", "sub/../x.pem", "a\\b.pem" if os.altsep else "x/y"])
def test_kr_16_una_referencia_relativa_fuera_del_contrato_se_rechaza(maliciosa: str, tmp_path, monkeypatch):
    _volumen(tmp_path, monkeypatch, "corto")
    with pytest.raises(KontrolError) as exc:
        svc.resolve_key_reference(maliciosa)
    assert exc.value.code == "INSTALLATION_KEY_REFERENCE_INVALID"


# ----------------------------------------------------------------------------- KR-08/09/10/11 · la clave carga y firma por ambas vías
@pytest.mark.parametrize("formato", ["absoluta", "relativa"])
def test_kr_08_11_la_clave_sintetica_carga_y_firma_el_desafio_con_referencia_absoluta_o_relativa(formato: str, tmp_path, monkeypatch):
    volumen = _volumen(tmp_path, monkeypatch, "largo")
    clave = _clave_sintetica(Path(volumen) / CANONICA)
    referencia = os.path.join(volumen, CANONICA) if formato == "absoluta" else CANONICA
    with open(svc.resolve_key_reference(referencia), encoding="utf-8") as fh:
        cargada = license_contract.load_private_key(fh.read())
    publica = clave.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    sobre = {"protocol_version": 1, "installation_id": "KTL-VE-SINTETICA-0001", "challenge_id": "c-1", "nonce": "n-1",
             "method": "POST", "target": sync_auth.SYNC_TARGET, "body_sha256": "0" * 64}
    firma = sync_auth.sign_envelope(sobre, cargada)
    assert sync_auth.verify_envelope(sobre, firma, publica)
    # El cargador canónico del sync (por configuración) lee la misma clave.
    assert svc._installation_private_key().public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode() == publica


# ----------------------------------------------------------------------------- KR-12 · identidad de arranque con ambas referencias
@pytest.mark.parametrize("referencia", ["absoluta", CANONICA, None])
def test_kr_12_la_identidad_de_la_instalacion_no_depende_del_formato_de_la_referencia(referencia, tmp_path, monkeypatch, sesion):
    volumen = _volumen(tmp_path, monkeypatch, "corto")
    valor = os.path.join(volumen, CANONICA) if referencia == "absoluta" else referencia
    with sesion() as db:
        db.add(Installation(installation_uuid="KTL-VE-IDENTIDA-0002", public_key="-----BEGIN PUBLIC KEY-----\nAA==\n-----END PUBLIC KEY-----\n", state="ACTIVE", key_reference=valor))
        db.commit()
        instalacion = svc.get_installation(db)
        assert instalacion.installation_uuid == "KTL-VE-IDENTIDA-0002"
        carga = svc.installation_request_payload(instalacion)
        assert carga["installation_id"] == "KTL-VE-IDENTIDA-0002" and "key_reference" not in carga


# ----------------------------------------------------------------------------- KR-18/19 · la columna intacta; cabeza declarada (0064, GOV-0-02)
def test_kr_18_19_la_columna_sigue_siendo_string_120_y_la_cabeza_de_alembic_no_cambia():
    columna = Installation.__table__.c.key_reference
    assert isinstance(columna.type, String) and columna.type.length == 120 and columna.nullable is True
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    raiz = Path(__file__).resolve().parents[1]
    cfg = Config(str(raiz / "alembic.ini"))
    cfg.set_main_option("script_location", str(raiz / "alembic"))
    assert ScriptDirectory.from_config(cfg).get_heads() == ["0076_gov_org04_ocupacion"]


# ----------------------------------------------------------------------------- KR-21 · el diagnóstico no expone la referencia
def test_kr_21_el_diagnostico_con_permiso_no_expone_la_referencia_ni_la_ruta(tmp_path, monkeypatch):
    _volumen(tmp_path, monkeypatch, "corto")
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    import app.core.database as dm

    dm._engine, dm._SessionLocal = engine, factory  # type: ignore[attr-defined]
    with factory() as db:
        initialize(db, SetupRequest(tenant_code="DEMO", tenant_name="Demo", company_code="D1", company_legal_name="Demo C.A.",
                                    company_rif="J-12345678-9", admin_username="admin", admin_password=PASSWORD))
        db.commit()
    from app.main import create_app

    app = create_app()

    def _db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _db
    cliente = TestClient(app)
    token = login_completo(cliente, "/api/v1/auth/login", json={"tenant_code": "DEMO", "username": "admin", "password": PASSWORD}).json()["access_token"]
    r = cliente.get("/api/v1/system/diagnostics", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert "key_reference" not in r.text and CANONICA not in r.text and str(tmp_path) not in r.text
    engine.dispose()
