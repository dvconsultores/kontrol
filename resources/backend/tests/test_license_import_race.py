"""RACE · Dos importaciones concurrentes pasan de una en una y la segunda compara contra lo que
la primera dejó (LICENCIA-IMPORT-SIN-BLOQUEO; FR-010-210..212).

Antes, con A vigente, B (año siguiente) y C (dos años después) concurrentes dejaban B vigente en
3 de 6 rondas: ambas leían A y ganaba la última en escribir. Ahora `import_license` bloquea la
fila de la instalación y el estado (`with_for_update`) y relee bajo el bloqueo. La autoridad de
concurrencia es PostgreSQL: en SQLite `with_for_update` no hace nada, así que este fichero solo
corre con `KONTROL_TEST_DB_URL` (el marcador que ya usa `test_spec004_installation_race.py`).

La sincronización es determinista: una barrera retiene a los dos hilos **antes** del bloqueo
(tras verificar la firma), y un contador comprueba que nunca hay dos hilos dentro de la sección
crítica a la vez. Ningún `sleep` decide nada.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core import license as license_engine
from app.core.config import get_settings
from app.core.database import Base, init_models
from app.core.errors import KontrolError
from app.modules.licensing import service as svc
from app.modules.licensing.models import LicenseEvent, LicenseState
from app.modules.organization.models import Installation
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine

pytestmark = pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="la concurrencia de la importación la gobierna PostgreSQL; SQLite no bloquea filas",
)

CARACAS = timezone(timedelta(hours=-4))
HOY = datetime.now(UTC).astimezone(CARACAS)
ANIO = HOY.year if HOY.month >= 4 else HOY.year - 1
ANCLA = "KONTROL_LICENSE_PUBLIC_KEY_PEM"


def _anual(license_id: str, anio: int, instalacion: str, **extra) -> dict:
    return {
        "issuer": "QA", "license_id": license_id, "installation_id": instalacion,
        "customer_id": "C-TEST", "contract_id": "K-TEST", "company_tax_id": "J-00000000-0",
        "period_start": f"{anio}-04-01T00:00:00-04:00", "period_end": f"{anio + 1}-03-31T23:59:59-04:00",
        "critical_warning_start": f"{anio + 1}-04-21T00:00:00-04:00", "read_only_start": f"{anio + 1}-05-01T00:00:00-04:00",
        "entitlements": {"companies": 3}, "minimum_version": "1.0.0", "kid": "kontrol-lic-2026-01", **extra,
    }


@pytest.fixture
def mundo(monkeypatch):
    """Instalación activada con A (año vigente) sobre PostgreSQL; ancla sintética; sesiones por hilo."""
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
        instalacion = db.execute(select(Installation)).scalars().first().installation_uuid
        db.commit()

    def firmada(payload: dict) -> tuple[dict, str]:
        return payload, propietario.sign(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hex()

    def importa(payload: dict, antes_de_confirmar=None) -> str:
        with factory() as db:
            try:
                p, firma = firmada(payload)
                svc.import_license(db, payload=p, signature_hex=firma, source="MANUAL")
                if antes_de_confirmar is not None:
                    antes_de_confirmar()  # aún con el bloqueo: nadie más puede estar dentro
                db.commit()
                return "ok"
            except KontrolError as exc:
                db.rollback()
                return exc.code

    def vigente() -> str:
        with factory() as db:
            return db.execute(select(LicenseState)).scalars().one().license_id

    def eventos() -> list[str]:
        with factory() as db:
            return [e.event_type for e in db.execute(select(LicenseEvent).order_by(LicenseEvent.created_at)).scalars().all()]

    assert importa(_anual("LIC-A", ANIO, instalacion)) == "ok"
    yield {"instalacion": instalacion, "importa": importa, "vigente": vigente, "eventos": eventos, "factory": factory}
    get_settings.cache_clear()


class Vigia:
    """Retiene a los hilos en una barrera antes del bloqueo y cuenta cuántos están a la vez en la
    sección crítica: entra quien recalcula el modo (ya releyó el estado bajo el bloqueo) y sale
    justo antes de confirmar, todavía con el bloqueo. Un rechazo nunca entra: se decide antes."""

    def __init__(self, monkeypatch, participantes: int) -> None:
        self.barrera = threading.Barrier(participantes, timeout=15)
        self.dentro = 0
        self.maximo_dentro = 0
        self.candado = threading.Lock()
        verificar = license_engine.verify_license_signature
        calcular = license_engine.compute_mode

        def verificar_y_esperar(*a, **k):
            ok = verificar(*a, **k)
            self.barrera.wait()  # los dos verificados; ahora, a por el bloqueo
            return ok

        def calcular_y_contar(*a, **k):  # se ejecuta tras releer el estado, antes de persistir
            with self.candado:
                self.dentro += 1
                self.maximo_dentro = max(self.maximo_dentro, self.dentro)
            return calcular(*a, **k)

        monkeypatch.setattr(license_engine, "verify_license_signature", verificar_y_esperar)
        monkeypatch.setattr(license_engine, "compute_mode", calcular_y_contar)

    def salir(self) -> None:
        with self.candado:
            self.dentro -= 1


def _concurrentes(mundo, vigia: Vigia, *payloads: dict) -> dict[str, str]:
    resultados: dict[str, str] = {}

    def correr(p: dict) -> None:
        resultados[p["license_id"]] = mundo["importa"](p, antes_de_confirmar=vigia.salir)

    hilos = [threading.Thread(target=correr, args=(p,)) for p in payloads]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
        assert not h.is_alive(), "un hilo no terminó: ¿bloqueo sin soltar?"
    return resultados


def test_race_01_b_y_c_concurrentes_terminan_siempre_en_c_y_nunca_a_la_vez_dentro(mundo, monkeypatch):
    inst = mundo["instalacion"]
    for ronda in range(8):
        with mundo["factory"]() as db:  # volver a A sin pasar por la importación
            s = db.execute(select(LicenseState)).scalars().one()
            s.license_id, s.period_start, s.period_end = "LIC-A", datetime(ANIO, 4, 1, tzinfo=CARACAS), datetime(ANIO + 1, 3, 31, 23, 59, 59, tzinfo=CARACAS)
            db.commit()
        vigia = Vigia(monkeypatch, 2)
        orden = (_anual("LIC-B", ANIO + 1, inst), _anual("LIC-C", ANIO + 2, inst)) if ronda % 2 == 0 else (_anual("LIC-C", ANIO + 2, inst), _anual("LIC-B", ANIO + 1, inst))
        resultados = _concurrentes(mundo, vigia, *orden)
        assert mundo["vigente"]() == "LIC-C", (ronda, resultados)
        assert resultados["LIC-C"] == "ok" and resultados["LIC-B"] in ("ok", "LICENSE_PERIOD_DOWNGRADE"), resultados
        assert vigia.maximo_dentro == 1, f"ronda {ronda}: {vigia.maximo_dentro} hilos a la vez en la sección crítica"


def test_race_03_c_confirma_primero_y_b_relee_bajo_bloqueo_y_se_rechaza(mundo, monkeypatch):
    """El caso crítico: B ya verificó la firma cuando C confirma. Si B comparara con lo que leyó
    antes del bloqueo (A), entraría; relee bajo el bloqueo, ve C y recibe el rechazo."""
    inst = mundo["instalacion"]
    c_confirmada = threading.Event()
    verificar = license_engine.verify_license_signature

    def verificar_y_ceder(payload, *a, **k):
        ok = verificar(payload, *a, **k)
        if payload["license_id"] == "LIC-B":
            assert c_confirmada.wait(timeout=30), "C no confirmó"
        return ok

    monkeypatch.setattr(license_engine, "verify_license_signature", verificar_y_ceder)
    resultados: dict[str, str] = {}

    def b() -> None:
        resultados["LIC-B"] = mundo["importa"](_anual("LIC-B", ANIO + 1, inst))

    hilo_b = threading.Thread(target=b)
    hilo_b.start()
    resultados["LIC-C"] = mundo["importa"](_anual("LIC-C", ANIO + 2, inst))
    c_confirmada.set()
    hilo_b.join(timeout=60)
    assert not hilo_b.is_alive()
    assert resultados == {"LIC-C": "ok", "LIC-B": "LICENSE_PERIOD_DOWNGRADE"}
    assert mundo["vigente"]() == "LIC-C"
    # `created_at` es la hora de inicio de la transacción (`now()` de PostgreSQL) y B empezó antes
    # de que C confirmara: el orden por fecha no dice quién ganó; los tipos y la cuenta, sí.
    tipos = mundo["eventos"]()
    assert tipos.count("LICENSE_IMPORTED") == 2 and tipos.count("LICENSE_PERIOD_DOWNGRADE_REJECTED") == 1  # A, C y el rechazo de B


def test_race_04_dos_legacy_distintas_del_mismo_periodo_concurrentes_se_rechazan_las_dos(mundo, monkeypatch):
    """Cerrado LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN (FR-010-330): con A legacy vigente, otras dos legacy
    del mismo período no entran, en ningún orden; el orden dentro del período lo da la `revision` del emisor
    (`test_license_revision_race.py`). Un rechazo nunca entra en la sección crítica."""
    inst = mundo["instalacion"]
    vigia = Vigia(monkeypatch, 2)
    resultados = _concurrentes(mundo, vigia, _anual("LIC-A-X", ANIO, inst, entitlements={"companies": 1}), _anual("LIC-A-Y", ANIO, inst, entitlements={"companies": 9}))
    assert resultados == {"LIC-A-X": "LICENSE_LEGACY_REISSUE_REQUIRES_REVISION", "LIC-A-Y": "LICENSE_LEGACY_REISSUE_REQUIRES_REVISION"}
    assert mundo["vigente"]() == "LIC-A"
    assert vigia.maximo_dentro == 0


def test_race_05_tras_un_rechazo_la_sesion_queda_limpia_y_la_siguiente_importacion_entra(mundo):
    inst = mundo["instalacion"]
    assert mundo["importa"](_anual("LIC-C", ANIO + 2, inst)) == "ok"
    assert mundo["importa"](_anual("LIC-B", ANIO + 1, inst)) == "LICENSE_PERIOD_DOWNGRADE"
    assert mundo["vigente"]() == "LIC-C"
    assert mundo["importa"](_anual("LIC-D", ANIO + 3, inst)) == "ok"
    assert mundo["vigente"]() == "LIC-D"
