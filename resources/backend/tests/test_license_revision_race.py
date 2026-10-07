"""RREV-RACE · La comparación de `revision` ocurre bajo el bloqueo de la Fase A y por eso dos
reemisiones concurrentes del mismo período terminan siempre en la mayor (FR-010-345..347).

Mismo arnés que `test_license_import_race.py` (barrera antes del bloqueo, contador de hilos en la
sección crítica; ningún `sleep` decide nada) y el mismo motivo para correr solo en PostgreSQL. Los
artefactos revisionados los emite la Autoridad Central real sobre su propia base; los hostiles
(otra legacy, una `revision` repetida con otra carga) se firman a mano con la clave sintética.
"""

from __future__ import annotations

import os
import threading
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core import license as license_engine
from app.core import license_contract as contract
from app.core.config import get_settings
from app.core.database import Base, init_models
from app.core.errors import KontrolError
from app.modules.licensing import service as svc
from app.modules.licensing.models import LicenseArtifact, LicenseEvent, LicenseState
from app.modules.organization.models import Installation
from app.modules.setup.api import SetupRequest, initialize
from central_authority import service as central
from central_authority.config import Settings as CentralSettings
from central_authority.models import Base as CentralBase
from tests.conftest import make_engine
from tests.test_license_import_race import Vigia

pytestmark = pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="la concurrencia de la importación la gobierna PostgreSQL; SQLite no bloquea filas",
)

CARACAS = timezone(timedelta(hours=-4))
HOY = datetime.now(UTC).astimezone(CARACAS)
ANIO = HOY.year if HOY.month >= 4 else HOY.year - 1
ANCLA = "KONTROL_LICENSE_PUBLIC_KEY_PEM"
KID = "kontrol-lic-2026-01"


def _legacy(license_id: str, anio: int, instalacion: str, **extra: Any) -> dict[str, Any]:
    return {
        "issuer": "QA", "license_id": license_id, "installation_id": instalacion,
        "customer_id": "C-TEST", "contract_id": "K-TEST", "company_tax_id": "J-00000000-0",
        "period_start": f"{anio}-04-01T00:00:00-04:00", "period_end": f"{anio + 1}-03-31T23:59:59-04:00",
        "critical_warning_start": f"{anio + 1}-04-21T00:00:00-04:00", "read_only_start": f"{anio + 1}-05-01T00:00:00-04:00",
        "entitlements": {"companies": 3}, "minimum_version": "1.0.0", "kid": KID, **extra,
    }


@pytest.fixture
def mundo(monkeypatch):
    """Cliente sobre PostgreSQL con la Autoridad Central real al lado; la clave sintética es a la vez
    ancla del cliente y clave de firma del emisor. Sesiones por hilo."""
    propietario = Ed25519PrivateKey.generate()
    monkeypatch.setenv(ANCLA, propietario.public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode())
    get_settings.cache_clear()
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    with factory() as db:
        initialize(db, SetupRequest(
            tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1",
            company_legal_name="Demo C.A.", company_rif="J-12345678-9",
            admin_username="admin", admin_password="Kontrol2026Segura!",
        ))
        inst = db.execute(select(Installation)).scalars().first()
        instalacion, clave_publica = inst.installation_uuid, inst.public_key
        db.commit()
    motor_central = make_engine()
    CentralBase.metadata.create_all(motor_central)
    central_factory = sessionmaker(bind=motor_central, class_=Session, expire_on_commit=False)
    ajustes = CentralSettings(_env_file=None, environment="qa", db_url="sqlite+pysqlite:///:memory:",
                              signing_private_key_pem=propietario.private_bytes(
                                  encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8,
                                  encryption_algorithm=serialization.NoEncryption()).decode(), signing_kid=KID)
    with central_factory() as db:
        central.register_installation(db, installation_uuid=instalacion, public_key_pem=clave_publica, customer_id="C-TEST",
                                      contract_id="K-TEST", company_tax_id="J-00000000-0", operator="qa")

    def emite(anio: int, **entitlements: Any) -> dict[str, Any]:
        inicio, fin = central.periodo_anual(anio)
        with central_factory() as db:
            return central.issue_license(db, settings=ajustes, installation_uuid=instalacion, period_start=inicio, period_end=fin,
                                         entitlements=entitlements or {"companies": 3}, minimum_version="1.0.0", operator="qa")

    def firmada(payload: dict[str, Any]) -> dict[str, Any]:
        return {"payload": payload, "signature_hex": contract.sign_license_payload(payload, propietario), "license_id": payload["license_id"]}

    def importa(artefacto: dict[str, Any], antes_de_confirmar=None) -> str:
        with factory() as db:
            try:
                svc.import_license(db, payload=artefacto["payload"], signature_hex=artefacto["signature_hex"], source="MANUAL")
                if antes_de_confirmar is not None:
                    antes_de_confirmar()  # aún con el bloqueo: nadie más puede estar dentro
                db.commit()
                return "ok"
            except KontrolError as exc:
                db.rollback()
                return exc.code

    def vigente() -> tuple[str, int | None]:
        with factory() as db:
            s = db.execute(select(LicenseState)).scalars().one()
            a = db.execute(select(LicenseArtifact).where(LicenseArtifact.license_id == s.license_id)
                           .order_by(LicenseArtifact.imported_at.desc(), LicenseArtifact.created_at.desc())).scalars().first()
            return s.license_id, contract.parse_revision(a.payload)

    def volver_a(artefacto: dict[str, Any]) -> None:
        """Deja vigente un artefacto ya importado sin pasar por la importación (el anti-retroceso no lo permitiría)."""
        with factory() as db:
            s = db.execute(select(LicenseState)).scalars().one()
            s.license_id = artefacto["license_id"]
            db.commit()

    def eventos(tipo: str) -> list[dict[str, Any]]:
        with factory() as db:
            return [e.detail for e in db.execute(select(LicenseEvent).where(LicenseEvent.event_type == tipo)).scalars().all()]

    yield {"instalacion": instalacion, "emite": emite, "firmada": firmada, "importa": importa, "vigente": vigente,
           "volver_a": volver_a, "eventos": eventos}
    get_settings.cache_clear()


def _concurrentes(mundo, vigia: Vigia, *artefactos: dict[str, Any]) -> dict[str, str]:
    resultados: dict[str, str] = {}

    def correr(a: dict[str, Any]) -> None:
        resultados[a["license_id"]] = mundo["importa"](a, antes_de_confirmar=vigia.salir)

    hilos = [threading.Thread(target=correr, args=(a,)) for a in artefactos]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
        assert not h.is_alive(), "un hilo no terminó: ¿bloqueo sin soltar?"
    return resultados


def test_rrev_race_01_r2_y_r3_concurrentes_terminan_siempre_en_r3(mundo, monkeypatch):
    r1, r2, r3 = mundo["emite"](ANIO), mundo["emite"](ANIO), mundo["emite"](ANIO)
    assert (r1["revision"], r2["revision"], r3["revision"]) == (1, 2, 3)
    assert mundo["importa"](r1) == "ok"
    for ronda in range(6):
        mundo["volver_a"](r1)
        vigia = Vigia(monkeypatch, 2)
        orden = (r2, r3) if ronda % 2 == 0 else (r3, r2)
        resultados = _concurrentes(mundo, vigia, *orden)
        assert mundo["vigente"]() == (r3["license_id"], 3), (ronda, resultados)
        assert resultados[r3["license_id"]] == "ok" and resultados[r2["license_id"]] in ("ok", "LICENSE_REVISION_DOWNGRADE"), resultados
        assert vigia.maximo_dentro == 1, f"ronda {ronda}: {vigia.maximo_dentro} hilos a la vez en la sección crítica"


def test_rrev_race_02_r3_confirma_primero_y_r2_relee_bajo_el_bloqueo_y_se_rechaza(mundo, monkeypatch):
    """El caso crítico: r2 ya verificó la firma cuando r3 confirma. Si comparara con lo que leyó antes
    del bloqueo (r1) entraría; relee bajo el bloqueo, ve r3 y recibe el rechazo, con su evento."""
    r1, r2, r3 = mundo["emite"](ANIO), mundo["emite"](ANIO), mundo["emite"](ANIO)
    assert mundo["importa"](r1) == "ok"
    r3_confirmada = threading.Event()
    verificar = license_engine.verify_license_signature

    def verificar_y_ceder(payload, *a, **k):
        ok = verificar(payload, *a, **k)
        if payload["license_id"] == r2["license_id"]:
            assert r3_confirmada.wait(timeout=30), "r3 no confirmó"
        return ok

    monkeypatch.setattr(license_engine, "verify_license_signature", verificar_y_ceder)
    resultados: dict[str, str] = {}
    hilo = threading.Thread(target=lambda: resultados.__setitem__("r2", mundo["importa"](r2)))
    hilo.start()
    resultados["r3"] = mundo["importa"](r3)
    r3_confirmada.set()
    hilo.join(timeout=60)
    assert not hilo.is_alive()
    assert resultados == {"r3": "ok", "r2": "LICENSE_REVISION_DOWNGRADE"}
    assert mundo["vigente"]() == (r3["license_id"], 3)
    rechazos = mundo["eventos"]("LICENSE_REISSUE_REJECTED")
    assert [(e["current_revision"], e["incoming_revision"], e["outcome"]) for e in rechazos] == [(3, 2, "REVISION_DOWNGRADE")]


@pytest.mark.parametrize("primero", ["revisionada", "legacy"])
def test_rrev_race_03_una_legacy_concurrente_no_pisa_el_linaje_revisionado(mundo, monkeypatch, primero):
    """Legacy A vigente; concurren otra legacy B y la r1 del emisor, en los dos órdenes posibles.
    Final: r1. B se rechaza por la regla que toque: tras r1, `LEGACY_AFTER_REVISION`; antes, por ser
    otra legacy del período, `LEGACY_REISSUE_REQUIRES_REVISION`."""
    inst = mundo["instalacion"]
    legacy_a = mundo["firmada"](_legacy("LIC-LEGACY-A", ANIO, inst))
    legacy_b = mundo["firmada"](_legacy("LIC-LEGACY-B", ANIO, inst, entitlements={"companies": 9}))
    r1 = mundo["emite"](ANIO)
    assert mundo["importa"](legacy_a) == "ok"
    confirmado = threading.Event()
    verificar = license_engine.verify_license_signature
    espera = legacy_b["license_id"] if primero == "revisionada" else r1["license_id"]

    def verificar_y_ceder(payload, *a, **k):
        ok = verificar(payload, *a, **k)
        if payload["license_id"] == espera:
            assert confirmado.wait(timeout=30), "el primero no confirmó"
        return ok

    monkeypatch.setattr(license_engine, "verify_license_signature", verificar_y_ceder)
    resultados: dict[str, str] = {}
    segundo = legacy_b if primero == "revisionada" else r1
    primero_art = r1 if primero == "revisionada" else legacy_b
    hilo = threading.Thread(target=lambda: resultados.__setitem__("segundo", mundo["importa"](segundo)))
    hilo.start()
    resultados["primero"] = mundo["importa"](primero_art)
    confirmado.set()
    hilo.join(timeout=60)
    assert not hilo.is_alive()
    if primero == "revisionada":
        assert resultados == {"primero": "ok", "segundo": "LICENSE_LEGACY_AFTER_REVISION"}
    else:
        assert resultados == {"primero": "LICENSE_LEGACY_REISSUE_REQUIRES_REVISION", "segundo": "ok"}
    assert mundo["vigente"]() == (r1["license_id"], 1)


def test_rrev_race_04_dos_artefactos_distintos_con_la_misma_revision_nunca_entran_los_dos(mundo, monkeypatch):
    """Un emisor correcto nunca lo emite; el cliente hostil lo comprueba igual: a lo sumo uno entra y el otro
    es conflicto. La sección crítica sigue siendo de uno en uno."""
    inst = mundo["instalacion"]
    r1, r2 = mundo["emite"](ANIO), mundo["emite"](ANIO)
    r2_bis = mundo["firmada"](_legacy("LIC-R2-BIS", ANIO, inst, revision=2, entitlements={"companies": 777}))
    assert mundo["importa"](r1) == "ok"
    for ronda in range(4):
        mundo["volver_a"](r1)
        vigia = Vigia(monkeypatch, 2)
        orden = (r2, r2_bis) if ronda % 2 == 0 else (r2_bis, r2)
        resultados = _concurrentes(mundo, vigia, *orden)
        assert sorted(resultados.values()) == ["LICENSE_REVISION_CONFLICT", "ok"], (ronda, resultados)
        ganador = next(k for k, v in resultados.items() if v == "ok")
        assert mundo["vigente"]() == (ganador, 2)
        assert vigia.maximo_dentro == 1
