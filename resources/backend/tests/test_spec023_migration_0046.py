"""Spec 023 · la migración `0046` y la concurrencia, sobre PostgreSQL real.

Dos cosas que solo se pueden comprobar aquí: que la tabla que produce Alembic
—la de cualquier instalación real, no la que `create_all` fabrica desde el ORM—
acepta el insert de la aplicación y clasifica el histórico sin inventarlo; y que
dos reclasificaciones simultáneas sobre el mismo origen no se llevan la misma
existencia dos veces.
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
PRE_023 = "0045_spec020_incidents"
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
    """Base sembrada **antes** de la `0046`, con movimientos de los dos signos."""
    from sqlalchemy import create_engine, text

    name = f"k023_{uuid.uuid4().hex[:8]}"
    admin = create_engine(PG_URL.rsplit("/", 1)[0] + "/postgres", future=True,
                          isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    proc = _alembic(name, PRE_023)
    assert proc.returncode == 0, proc.stderr[-3000:]

    ids = {k: str(uuid.uuid4()) for k in
           ("inst", "ten", "co", "wh", "prod", "mt", "m_in", "m_out", "m_zero")}
    _sql(name, [
        ("INSERT INTO installations (id, installation_uuid, state, created_at, updated_at) "
         "VALUES (:i, :i, 'ACTIVE', now(), now())", {"i": ids["inst"]}),
        ("INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at, updated_at) "
         "VALUES (:t, :i, 'T023', 'T', 'STANDARD', 'ACTIVE', now(), now())",
         {"t": ids["ten"], "i": ids["inst"]}),
        ("INSERT INTO companies (id, tenant_id, code, legal_name, rif, legal_type, "
         "functional_currency, status, created_at, updated_at) "
         "VALUES (:c, :t, 'C023', 'Empresa', 'J-023', 'CA', 'VED', 'ACTIVE', now(), now())",
         {"c": ids["co"], "t": ids["ten"]}),
        ("INSERT INTO warehouses (id, company_id, code, name, status, created_at, updated_at) "
         "VALUES (:w, :c, 'W023', 'Almacén', 'ACTIVE', now(), now())",
         {"w": ids["wh"], "c": ids["co"]}),
        ("INSERT INTO catalog_items (id, company_id, code, name, item_type, status, "
         "created_at, updated_at) "
         "VALUES (:p, :c, 'P023', 'Producto', 'PRODUCT', 'ACTIVE', now(), now())",
         {"p": ids["prod"], "c": ids["co"]}),
        ("INSERT INTO movement_types (id, company_id, code, name, direction, affects_balance, "
         "status, created_at, updated_at) "
         "VALUES (:mt, :c, 'ENTRADA_RECEPCION', 'Entrada', 'IN', true, 'ACTIVE', now(), now())",
         {"mt": ids["mt"], "c": ids["co"]}),
        # Una entrada y una salida: la clasificación histórica debe distinguirlas.
        ("INSERT INTO inventory_movements (id, company_id, warehouse_id, product_id, "
         "movement_type_id, quantity, base_quantity, currency, occurred_at, status, "
         "created_at, updated_at) "
         "VALUES (:m, :c, :w, :p, :mt, 30, 30, 'VED', now(), 'POSTED', now(), now())",
         {"m": ids["m_in"], "c": ids["co"], "w": ids["wh"], "p": ids["prod"], "mt": ids["mt"]}),
        ("INSERT INTO inventory_movements (id, company_id, warehouse_id, product_id, "
         "movement_type_id, quantity, base_quantity, currency, occurred_at, status, "
         "created_at, updated_at) "
         "VALUES (:m, :c, :w, :p, :mt, -12, -12, 'VED', now(), 'POSTED', now(), now())",
         {"m": ids["m_out"], "c": ids["co"], "w": ids["wh"], "p": ids["prod"], "mt": ids["mt"]}),
        # Cantidad cero: existe en el histórico —conversiones de tipo,
        # correcciones— y la primera versión de la `0046` la dejaba fuera.
        ("INSERT INTO inventory_movements (id, company_id, warehouse_id, product_id, "
         "movement_type_id, quantity, base_quantity, currency, occurred_at, status, "
         "created_at, updated_at) "
         "VALUES (:m, :c, :w, :p, :mt, 0, 0, 'VED', now(), 'POSTED', now(), now())",
         {"m": ids["m_zero"], "c": ids["co"], "w": ids["wh"], "p": ids["prod"], "mt": ids["mt"]}),
    ])

    proc = _alembic(name, "head")
    assert proc.returncode == 0, proc.stderr[-4000:]
    yield name, ids
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    admin.dispose()


def test_la_clasificacion_historica_distingue_entradas_de_salidas(base_migrada):
    """No es una suposición: hasta la `0046` el motor escribía `DISPONIBLE` fijo."""
    name, ids = base_migrada
    filas = dict(_rows(name, "SELECT id, source_state FROM inventory_movements"))
    destinos = dict(_rows(name, "SELECT id, target_state FROM inventory_movements"))
    assert destinos[ids["m_in"]] == "DISPONIBLE" and filas[ids["m_in"]] is None
    assert filas[ids["m_out"]] == "DISPONIBLE" and destinos[ids["m_out"]] is None


def test_un_movimiento_en_cero_no_deja_la_migracion_a_medias(base_migrada):
    """El caso que la primera versión de la `0046` no contemplaba.

    `record_movement` no emite ceros, pero el histórico los tiene. Con la regla
    `quantity > 0` quedaban sin clasificar, la migración abortaba —correctamente,
    porque prefiere abortar a inventar— y ninguna instalación con esas filas
    podía actualizarse. Cuentan como entrada: tocaron la fila `DISPONIBLE` como
    destino, sumándole cero.
    """
    name, ids = base_migrada
    fila = dict(_rows(name, "SELECT id, target_state FROM inventory_movements "
                            "WHERE quantity = 0"))
    assert fila.get(ids["m_zero"]) == "DISPONIBLE"


def test_ningun_movimiento_queda_sin_procedencia(base_migrada):
    name, _ = base_migrada
    huerfanos = _rows(name, "SELECT count(*) FROM inventory_movements "
                            "WHERE source_state IS NULL AND target_state IS NULL")[0][0]
    assert huerfanos == 0


def test_la_restriccion_de_procedencia_existe_y_rechaza(base_migrada):
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import IntegrityError

    name, ids = base_migrada
    checks = {r[0] for r in _rows(name, "SELECT conname FROM pg_constraint WHERE contype='c' "
                                        "AND conrelid='inventory_movements'::regclass")}
    assert "ck_inventory_movements_state_provenance" in checks, checks
    assert not any(c.startswith("ck_inventory_movements_ck_") for c in checks), "prefijo duplicado"

    engine = create_engine(_db_url(name), future=True)
    try:
        with pytest.raises(IntegrityError) as info:
            with engine.begin() as conn:
                conn.execute(text(
                    "INSERT INTO inventory_movements (id, company_id, warehouse_id, product_id, "
                    "movement_type_id, quantity, currency, occurred_at, status, created_at, updated_at) "
                    "VALUES (:m, :c, :w, :p, :mt, 5, 'VED', now(), 'POSTED', now(), now())"),
                    {"m": str(uuid.uuid4()), "c": ids["co"], "w": ids["wh"],
                     "p": ids["prod"], "mt": ids["mt"]})
        assert getattr(info.value.orig, "pgcode", "") == CHECK_VIOLATION
    finally:
        engine.dispose()


def test_la_aplicacion_puede_insertar_en_la_tabla_que_crea_la_migracion(base_migrada):
    """La lección de la Spec 020: el SQL crudo de estas pruebas no prueba el ORM."""
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
                company_id=ids["co"], warehouse_id=ids["wh"], product_id=ids["prod"],
                movement_type_id=ids["mt"], quantity=Decimal("9"), base_quantity=Decimal("9"),
                currency="VED", occurred_at=__import__("datetime").datetime.now(
                    __import__("datetime").UTC), status="POSTED",
                source_state=None, target_state="RECIBIDO")
            db.add(m)
            db.commit()
            db.refresh(m)
            assert m.created_at is not None and m.target_state == "RECIBIDO"
    finally:
        engine.dispose()


def test_bajar_y_volver_a_subir_deja_la_base_igual(base_migrada):
    name, _ = base_migrada
    assert _alembic(name, PRE_023, "downgrade").returncode == 0
    columnas = {r[0] for r in _rows(name, "SELECT column_name FROM information_schema.columns "
                                          "WHERE table_name='inventory_movements'")}
    assert "source_state" not in columnas and "target_state" not in columnas
    assert _alembic(name, "head").returncode == 0
    columnas = {r[0] for r in _rows(name, "SELECT column_name FROM information_schema.columns "
                                          "WHERE table_name='inventory_movements'")}
    assert {"source_state", "target_state"} <= columnas


def test_dos_reclasificaciones_simultaneas_no_mueven_la_misma_existencia(base_migrada):
    """Origen con 10; dos transacciones piden 8 cada una. Solo una puede ganar.

    Sin el bloqueo de fila las dos leerían 10, las dos aceptarían, y el origen
    quedaría en −6: existencia inventada por una carrera.
    """
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
                product_id=ids["prod"], lot_id=None, serial_id=None, state="RECIBIDO",
                qty_on_hand=Decimal("10"), qty_reserved=Decimal("0"), qty_available=Decimal("10")))
            db.commit()

        listo = threading.Barrier(2)
        resultados: list[str] = []

        def mover() -> None:
            db = Sesion()
            try:
                listo.wait(timeout=30)
                inv.reclassify(db, company_id=ids["co"], warehouse_id=ids["wh"],
                               product_id=ids["prod"], source_state="RECIBIDO",
                               target_state="DISPONIBLE", quantity=8, actor="qa")
                db.commit()
                resultados.append("ok")
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                resultados.append(type(exc).__name__)
            finally:
                db.close()

        hilos = [threading.Thread(target=mover) for _ in range(2)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=60)

        assert resultados.count("ok") == 1, f"ganaron {resultados.count('ok')}: {resultados}"
        with Session(engine) as db:
            saldos = {b.state: Decimal(str(b.qty_on_hand)) for b in db.execute(
                select(InventoryBalance).where(
                    InventoryBalance.product_id == ids["prod"])).scalars().all()}
        assert saldos["RECIBIDO"] == Decimal("2")
        assert saldos["DISPONIBLE"] == Decimal("8")
        assert sum(saldos.values()) == Decimal("10"), "la carrera creó o destruyó existencia"
    finally:
        engine.dispose()
