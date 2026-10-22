"""Spec 022 · la migración `0048` y las carreras, sobre PostgreSQL real.

Dos cosas que solo se comprueban aquí: que el histórico se clasifique sin
inventar dirección, y que dos operaciones simultáneas no se lleven la misma
existencia ni pierdan una reserva.
"""

from __future__ import annotations

import os
import subprocess
import threading
import uuid
from decimal import Decimal

import pytest

from tests.alembic_orden import orden_alembic

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif(not PG_URL.startswith("postgresql"),
                                reason="La integridad solo se verifica sobre PostgreSQL (P21)")
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRE_022 = "0047_spec021_confirm"
CHECK_VIOLATION = "23514"


def _db_url(name: str) -> str:
    return PG_URL.rsplit("/", 1)[0] + "/" + name


def _alembic(db_name: str, target: str, comando: str = "upgrade") -> subprocess.CompletedProcess:
    env = {**os.environ, "KONTROL_DB_URL": _db_url(db_name)}
    env.pop("KONTROL_TEST_DB_URL", None)
    return subprocess.run(orden_alembic(comando, target),
                          cwd=BACKEND, env=env, capture_output=True, text=True, timeout=900)


def _sql(db_name: str, statements: list[tuple[str, dict]]) -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(_db_url(db_name), future=True)
    with engine.begin() as conn:
        for statement, params in statements:
            conn.execute(text(statement), params)
    engine.dispose()


def _rows(db_name: str, statement: str, **params):
    from sqlalchemy import create_engine, text

    engine = create_engine(_db_url(db_name), future=True)
    try:
        with engine.connect() as conn:
            return conn.execute(text(statement), params).fetchall()
    finally:
        engine.dispose()


@pytest.fixture(scope="module")
def base_migrada():
    from sqlalchemy import create_engine, text

    name = f"k022_{uuid.uuid4().hex[:8]}"
    admin = create_engine(PG_URL.rsplit("/", 1)[0] + "/postgres", future=True,
                          isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    assert _alembic(name, PRE_022).returncode == 0

    ids = {k: str(uuid.uuid4()) for k in
           ("inst", "ten", "co", "wh", "loc", "prod", "mt", "m_in", "m_out", "m_sin")}
    _sql(name, [
        ("INSERT INTO installations (id, installation_uuid, state, created_at, updated_at) "
         "VALUES (:i, :i, 'ACTIVE', now(), now())", {"i": ids["inst"]}),
        ("INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at, updated_at) "
         "VALUES (:t, :i, 'T022', 'T', 'STANDARD', 'ACTIVE', now(), now())",
         {"t": ids["ten"], "i": ids["inst"]}),
        ("INSERT INTO companies (id, tenant_id, code, legal_name, rif, legal_type, "
         "functional_currency, status, created_at, updated_at) "
         "VALUES (:c, :t, 'C022', 'Empresa', 'J-022', 'CA', 'VED', 'ACTIVE', now(), now())",
         {"c": ids["co"], "t": ids["ten"]}),
        ("INSERT INTO warehouses (id, company_id, code, name, status, created_at, updated_at) "
         "VALUES (:w, :c, 'W022', 'Almacén', 'ACTIVE', now(), now())",
         {"w": ids["wh"], "c": ids["co"]}),
        ("INSERT INTO warehouse_locations (id, company_id, warehouse_id, code, sequence, "
         "status, version, created_at, updated_at) "
         "VALUES (:l, :c, :w, 'L022', 1, 'ACTIVE', 1, now(), now())",
         {"l": ids["loc"], "c": ids["co"], "w": ids["wh"]}),
        ("INSERT INTO catalog_items (id, company_id, code, name, item_type, status, "
         "created_at, updated_at) VALUES (:p, :c, 'P022', 'Prod', 'PRODUCT', 'ACTIVE', now(), now())",
         {"p": ids["prod"], "c": ids["co"]}),
        ("INSERT INTO movement_types (id, company_id, code, name, direction, affects_balance, "
         "status, created_at, updated_at) "
         "VALUES (:mt, :c, 'ENTRADA_RECEPCION', 'Entrada', 'IN', true, 'ACTIVE', now(), now())",
         {"mt": ids["mt"], "c": ids["co"]}),
        # Entrada, salida y un movimiento sin ubicación: los tres se clasifican distinto.
        ("INSERT INTO inventory_movements (id, company_id, warehouse_id, location_id, product_id, "
         "movement_type_id, quantity, base_quantity, currency, occurred_at, status, "
         "target_state, created_at, updated_at) "
         "VALUES (:m, :c, :w, :l, :p, :mt, 30, 30, 'VED', now(), 'POSTED', 'DISPONIBLE', now(), now())",
         {"m": ids["m_in"], "c": ids["co"], "w": ids["wh"], "l": ids["loc"],
          "p": ids["prod"], "mt": ids["mt"]}),
        ("INSERT INTO inventory_movements (id, company_id, warehouse_id, location_id, product_id, "
         "movement_type_id, quantity, base_quantity, currency, occurred_at, status, "
         "source_state, created_at, updated_at) "
         "VALUES (:m, :c, :w, :l, :p, :mt, -12, -12, 'VED', now(), 'POSTED', 'DISPONIBLE', now(), now())",
         {"m": ids["m_out"], "c": ids["co"], "w": ids["wh"], "l": ids["loc"],
          "p": ids["prod"], "mt": ids["mt"]}),
        ("INSERT INTO inventory_movements (id, company_id, warehouse_id, product_id, "
         "movement_type_id, quantity, base_quantity, currency, occurred_at, status, "
         "target_state, created_at, updated_at) "
         "VALUES (:m, :c, :w, :p, :mt, 7, 7, 'VED', now(), 'POSTED', 'DISPONIBLE', now(), now())",
         {"m": ids["m_sin"], "c": ids["co"], "w": ids["wh"], "p": ids["prod"], "mt": ids["mt"]}),
    ])

    proc = _alembic(name, "head")
    assert proc.returncode == 0, proc.stdout[-2500:] + proc.stderr[-2500:]
    yield name, ids
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    admin.dispose()


def test_la_direccion_historica_la_da_el_signo_no_una_suposicion(base_migrada):
    name, ids = base_migrada
    filas = {r[0]: (r[1], r[2]) for r in _rows(
        name, "SELECT id, source_location_id, target_location_id FROM inventory_movements")}
    assert filas[ids["m_in"]] == (None, ids["loc"]), "una entrada tuvo esa ubicación por destino"
    assert filas[ids["m_out"]] == (ids["loc"], None), "una salida tuvo esa ubicación por origen"


def test_un_movimiento_sin_ubicacion_no_se_le_inventa_una(base_migrada):
    name, ids = base_migrada
    fila = {r[0]: (r[1], r[2]) for r in _rows(
        name, "SELECT id, source_location_id, target_location_id FROM inventory_movements "
              "WHERE location_id IS NULL")}
    assert fila[ids["m_sin"]] == (None, None)


def test_la_restriccion_rechaza_un_traslado_sin_procedencia(base_migrada):
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import IntegrityError

    name, ids = base_migrada
    checks = {r[0] for r in _rows(name, "SELECT conname FROM pg_constraint WHERE contype='c' "
                                        "AND conrelid='inventory_movements'::regclass")}
    assert "ck_inventory_movements_location_provenance" in checks, checks
    assert not any(c.startswith("ck_inventory_movements_ck_") for c in checks), "prefijo duplicado"

    engine = create_engine(_db_url(name), future=True)
    try:
        with pytest.raises(IntegrityError) as info:
            with engine.begin() as conn:
                conn.execute(text(
                    "INSERT INTO inventory_movements (id, company_id, warehouse_id, location_id, "
                    "product_id, movement_type_id, quantity, currency, occurred_at, status, "
                    "target_state, created_at, updated_at) "
                    "VALUES (:m, :c, :w, :l, :p, :mt, 5, 'VED', now(), 'POSTED', 'DISPONIBLE', "
                    "now(), now())"),
                    {"m": str(uuid.uuid4()), "c": ids["co"], "w": ids["wh"], "l": ids["loc"],
                     "p": ids["prod"], "mt": ids["mt"]})
        assert getattr(info.value.orig, "pgcode", "") == CHECK_VIOLATION
    finally:
        engine.dispose()


def test_la_aplicacion_puede_insertar_en_la_tabla_que_crea_la_migracion(base_migrada):
    from datetime import UTC, datetime

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.database import init_models
    from app.modules.inventory.models import InventoryMovement

    init_models()
    name, ids = base_migrada
    engine = create_engine(_db_url(name), future=True)
    try:
        with Session(engine) as db:
            m = InventoryMovement(
                company_id=ids["co"], warehouse_id=ids["wh"], location_id=ids["loc"],
                product_id=ids["prod"], movement_type_id=ids["mt"], quantity=Decimal("4"),
                base_quantity=Decimal("4"), currency="VED", occurred_at=datetime.now(UTC),
                status="POSTED", source_state="DISPONIBLE", target_state="DISPONIBLE",
                source_location_id=None, target_location_id=ids["loc"])
            db.add(m)
            db.commit()
            db.refresh(m)
            assert m.target_location_id == ids["loc"]
    finally:
        engine.dispose()


def test_bajar_y_subir_deja_la_base_igual(base_migrada):
    name, _ = base_migrada
    assert _alembic(name, PRE_022, "downgrade").returncode == 0
    columnas = {r[0] for r in _rows(name, "SELECT column_name FROM information_schema.columns "
                                          "WHERE table_name = 'inventory_movements'")}
    assert "source_location_id" not in columnas and "target_location_id" not in columnas
    assert _alembic(name, "head").returncode == 0
    columnas = {r[0] for r in _rows(name, "SELECT column_name FROM information_schema.columns "
                                          "WHERE table_name = 'inventory_movements'")}
    assert {"source_location_id", "target_location_id"} <= columnas


def test_dos_colocaciones_simultaneas_no_ubican_la_misma_existencia(base_migrada):
    """Origen con 100; dos transacciones piden 60 cada una. No pueden colocar 120."""
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session, sessionmaker

    from app.core.database import init_models
    from app.modules.inventory import service as inv
    from app.modules.inventory.models import InventoryBalance

    init_models()
    name, ids = base_migrada
    engine = create_engine(_db_url(name), future=True, pool_size=6)
    Sesion = sessionmaker(bind=engine)
    try:
        with Session(engine) as db:
            db.add(InventoryBalance(
                company_id=ids["co"], warehouse_id=ids["wh"], location_id=None,
                product_id=ids["prod"], lot_id=None, serial_id=None, state="DISPONIBLE",
                qty_on_hand=Decimal("100"), qty_reserved=Decimal("0"),
                qty_available=Decimal("100")))
            db.commit()

        listo = threading.Barrier(2)
        resultados: list[str] = []

        def colocar() -> None:
            db = Sesion()
            try:
                listo.wait(timeout=30)
                inv.putaway(db, company_id=ids["co"], warehouse_id=ids["wh"],
                            product_id=ids["prod"], target_location_id=ids["loc"],
                            quantity=60, actor="qa")
                db.commit()
                resultados.append("ok")
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                resultados.append(type(exc).__name__)
            finally:
                db.close()

        hilos = [threading.Thread(target=colocar) for _ in range(2)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=60)

        assert resultados.count("ok") == 1, f"ganaron {resultados.count('ok')}: {resultados}"
        with Session(engine) as db:
            saldos = {b.location_id: Decimal(str(b.qty_on_hand)) for b in db.execute(
                select(InventoryBalance).where(
                    InventoryBalance.product_id == ids["prod"])).scalars().all()}
        assert saldos[None] == Decimal("40")
        assert saldos[ids["loc"]] == Decimal("60")
        assert sum(saldos.values()) == Decimal("100"), "la carrera creó o destruyó existencia"
    finally:
        engine.dispose()


def test_reservar_y_ubicar_a_la_vez_no_pierde_el_compromiso(base_migrada):
    """`R-D0-14-2` bajo carrera: la reserva sobrevive y el disponible cuadra."""
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session, sessionmaker

    from app.core.database import init_models
    from app.modules.inventory import service as inv
    from app.modules.inventory.models import InventoryBalance, Reservation

    init_models()
    name, ids = base_migrada
    engine = create_engine(_db_url(name), future=True, pool_size=6)
    Sesion = sessionmaker(bind=engine)
    try:
        with Session(engine) as db:
            db.execute(InventoryBalance.__table__.delete().where(
                InventoryBalance.product_id == ids["prod"]))
            db.add(InventoryBalance(
                company_id=ids["co"], warehouse_id=ids["wh"], location_id=None,
                product_id=ids["prod"], lot_id=None, serial_id=None, state="DISPONIBLE",
                qty_on_hand=Decimal("100"), qty_reserved=Decimal("0"),
                qty_available=Decimal("100")))
            db.commit()

        listo = threading.Barrier(2)
        resultados: list[str] = []

        def reservar() -> None:
            db = Sesion()
            try:
                listo.wait(timeout=30)
                inv.reserve(db, company_id=ids["co"], source_document="OV-CARRERA",
                            product_id=ids["prod"], warehouse_id=ids["wh"], quantity=30,
                            actor="qa")
                db.commit()
                resultados.append("reserva")
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                resultados.append(f"reserva:{type(exc).__name__}")
            finally:
                db.close()

        def colocar() -> None:
            db = Sesion()
            try:
                listo.wait(timeout=30)
                inv.putaway(db, company_id=ids["co"], warehouse_id=ids["wh"],
                            product_id=ids["prod"], target_location_id=ids["loc"],
                            quantity=100, actor="qa")
                db.commit()
                resultados.append("ubicacion")
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                resultados.append(f"ubicacion:{type(exc).__name__}")
            finally:
                db.close()

        hilos = [threading.Thread(target=reservar), threading.Thread(target=colocar)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=60)

        assert "reserva" in resultados, f"la reserva no sobrevivió: {resultados}"
        assert "ubicacion" in resultados, f"la colocación no sobrevivió: {resultados}"

        with Session(engine) as db:
            filas = db.execute(select(InventoryBalance).where(
                InventoryBalance.product_id == ids["prod"])).scalars().all()
            fisico = sum(Decimal(str(b.qty_on_hand)) for b in filas)
            reservado = sum(Decimal(str(b.qty_reserved)) for b in filas)
            activas = db.execute(select(Reservation).where(
                Reservation.product_id == ids["prod"],
                Reservation.status == "ACTIVE")).scalars().all()
        assert fisico == Decimal("100"), "la carrera creó o destruyó existencia"
        assert reservado == Decimal("30"), "el compromiso se perdió o se duplicó"
        assert len(activas) == 1
    finally:
        engine.dispose()
