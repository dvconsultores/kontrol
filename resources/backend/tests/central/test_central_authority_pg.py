"""CLA-PG · Lo que solo PostgreSQL puede probar de la Autoridad Central: la asignación concurrente de
`revision` y las migraciones propias (instalación limpia y actualización idempotente).

Marcador PG-only del repositorio (`test_spec004_installation_race.py`): sin `KONTROL_TEST_DB_URL`
de PostgreSQL se omite. La sincronización de la carrera es determinista: una barrera retiene a los
dos hilos tras cargar la clave y antes del bloqueo de la fila de la instalación.
"""

from __future__ import annotations

import os
import subprocess
import threading
import uuid
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from central_authority import service
from central_authority.config import Settings
from central_authority.models import Base, Issuance, PeriodLineage
from tests.central.conftest import pem_privada, pem_publica
from tests.conftest import make_engine

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif(not PG_URL.startswith("postgresql"), reason="la concurrencia y las migraciones de la autoridad se certifican en PostgreSQL")
BACKEND = Path(__file__).resolve().parents[2]
INSTALACION = "KTL-XX-SINTETICA-PG"


@pytest.fixture
def mundo():
    propietario = Ed25519PrivateKey.generate()
    ajustes = Settings(_env_file=None, environment="qa", db_url=PG_URL, signing_private_key_pem=pem_privada(propietario))
    motor = make_engine()
    Base.metadata.create_all(motor)
    factoria = sessionmaker(bind=motor, class_=Session, expire_on_commit=False)
    with factoria() as db:
        service.register_installation(db, installation_uuid=INSTALACION, public_key_pem=pem_publica(Ed25519PrivateKey.generate()),
                                      customer_id="CUS-PG", contract_id="CON-PG", company_tax_id=None, operator="ana")
    yield {"ajustes": ajustes, "factoria": factoria, "propietario": propietario}
    Base.metadata.drop_all(motor)


def _emitir(mundo, entitlements, barrera: threading.Barrier | None = None, resultados: dict | None = None, nombre: str = "") -> dict:
    inicio, fin = service.periodo_anual(2027)
    with mundo["factoria"]() as db:
        r = service.issue_license(db, settings=mundo["ajustes"], installation_uuid=INSTALACION, period_start=inicio, period_end=fin,
                                  entitlements=entitlements, minimum_version="1.0.0", operator="ana")
    if resultados is not None:
        resultados[nombre] = r
    return r


def test_clapg_01_dos_reemisiones_concurrentes_reciben_revisiones_distintas_y_consecutivas(mundo, monkeypatch):
    _emitir(mundo, {"companies": 1})  # revision 1
    for ronda in range(6):
        barrera = threading.Barrier(2, timeout=20)
        cargar = service.load_signing_key

        def cargar_y_esperar(pem, _cargar=cargar, _barrera=barrera):
            clave = _cargar(pem)
            _barrera.wait()  # los dos con la clave cargada; ahora, a por el bloqueo de la instalación
            return clave

        monkeypatch.setattr(service, "load_signing_key", cargar_y_esperar)
        resultados: dict = {}
        hilos = [threading.Thread(target=_emitir, args=(mundo, {"companies": 2 + ronda}, barrera, resultados, "R1")),
                 threading.Thread(target=_emitir, args=(mundo, {"companies": 9 + ronda}, barrera, resultados, "R2"))]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=60)
            assert not h.is_alive(), "un hilo no terminó: ¿bloqueo sin soltar?"
        monkeypatch.undo()
        revisiones = sorted(r["revision"] for r in resultados.values())
        base = 2 + 2 * ronda
        assert revisiones == [base, base + 1], (ronda, resultados)
        assert resultados["R1"]["payload"] != resultados["R2"]["payload"]
    with mundo["factoria"]() as db:
        filas = db.execute(select(Issuance).order_by(Issuance.revision)).scalars().all()
        assert [f.revision for f in filas] == list(range(1, 14))
        assert len({f.license_id for f in filas}) == 13 and len({f.payload_hash for f in filas}) == 13
        assert db.execute(select(PeriodLineage)).scalars().one().last_revision == 13


def test_clapg_02_la_unicidad_de_revision_la_impone_la_base(mundo):
    """Aunque alguien saltara el bloqueo, `UNIQUE(lineage_id, revision)` impide dos paquetes con la misma revisión."""
    _emitir(mundo, {})
    with mundo["factoria"]() as db:
        fila = db.execute(select(Issuance)).scalars().one()
        duplicado = Issuance(installation_id=fila.installation_id, lineage_id=fila.lineage_id, license_id="LIC-DUP", revision=fila.revision,
                             period_start=fila.period_start, period_end=fila.period_end, kid=fila.kid, payload={"x": 1}, payload_hash="0" * 64,
                             signature_hex="00", issued_by="ana")
        db.add(duplicado)
        with pytest.raises(Exception) as e:
            db.commit()
        assert "uq_cla_issuance_lineage_revision" in str(e.value) or "unique" in str(e.value).lower()
        db.rollback()


def _url(nombre: str) -> str:
    return PG_URL.rsplit("/", 1)[0] + "/" + nombre


@pytest.fixture
def base_central_limpia():
    nombre = f"kontrol_central_test_{uuid.uuid4().hex[:8]}"
    admin = create_engine(_url("postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f'CREATE DATABASE "{nombre}"'))
    try:
        yield _url(nombre)
    finally:
        with admin.connect() as c:
            c.execute(text(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{nombre}' AND pid <> pg_backend_pid()"))
            c.execute(text(f'DROP DATABASE IF EXISTS "{nombre}"'))
        admin.dispose()


def _alembic(url: str, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "KONTROL_CENTRAL_DB_URL": url, "KONTROL_CENTRAL_ENVIRONMENT": "qa"}
    env.pop("KONTROL_CENTRAL_SIGNING_PRIVATE_KEY_PEM", None)
    return subprocess.run([str(BACKEND / ".venv" / "bin" / "alembic"), "-c", "central_authority/alembic.ini", *args],
                          cwd=BACKEND, env=env, capture_output=True, text=True, timeout=300)


def test_clapg_03_instalacion_limpia_de_las_migraciones_de_la_autoridad(base_central_limpia):
    r = _alembic(base_central_limpia, "upgrade", "head")
    assert r.returncode == 0, r.stderr[-800:]
    motor = create_engine(base_central_limpia, future=True)
    insp = inspect(motor)
    tablas = set(insp.get_table_names())
    assert {"cla_installations", "cla_period_lineages", "cla_issuances", "cla_audit_events", "cla_sync_challenges", "cla_alembic_version"} <= tablas
    assert not any(t.startswith(("license_", "users", "tenants", "companies")) for t in tablas)  # ni una tabla del cliente
    unicos = {u["name"] for u in insp.get_unique_constraints("cla_issuances")}
    assert "uq_cla_issuance_lineage_revision" in unicos and "uq_cla_issuances_license_id" in unicos
    assert "uq_cla_lineage_installation_period" in {u["name"] for u in insp.get_unique_constraints("cla_period_lineages")}
    indices = {i["name"] for i in insp.get_indexes("cla_installations")}
    assert "ix_cla_installations_installation_uuid" in indices
    with motor.connect() as c:
        assert c.execute(text("select version_num from cla_alembic_version")).scalar_one() == "0002_cla_sync_auth"  # una sola cabeza
    # La actualización es idempotente y el esquema coincide con los modelos (P26).
    r2 = _alembic(base_central_limpia, "upgrade", "head")
    assert r2.returncode == 0
    assert {t for t in Base.metadata.tables} <= set(insp.get_table_names())
    for tabla in Base.metadata.tables.values():
        columnas = {c["name"] for c in inspect(motor).get_columns(tabla.name)}
        assert {c.name for c in tabla.columns} == columnas, tabla.name
    r3 = _alembic(base_central_limpia, "downgrade", "base")
    assert r3.returncode == 0 and not {t for t in inspect(motor).get_table_names() if t.startswith("cla_") and t != "cla_alembic_version"}
    motor.dispose()
