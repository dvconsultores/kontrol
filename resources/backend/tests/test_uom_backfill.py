"""Backfill clasificado de la Spec 011 — casos §32 a §37.

Cada caso siembra una base **anterior a 011**, aplica la cadena y comprueba qué
hizo la migración con cada línea. Sobre PostgreSQL real: el modo offline no lee
datos y no puede clasificar.

Estas pruebas buscan defectos: el caso crítico exige que la migración **falle**
y que no quede ni una escritura aplicada.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from tests.alembic_orden import orden_alembic

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif(
    "postgresql" not in PG_URL,
    reason="La clasificación del backfill solo es verificable sobre PostgreSQL (P21)")

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRE_011 = "0018_location_fk_and_legacy"


def _db_url(name: str) -> str:
    return PG_URL.rsplit("/", 1)[0] + "/" + name


def _alembic(db_name: str, target: str, env_extra: dict | None = None):
    env = {**os.environ, "KONTROL_DB_URL": _db_url(db_name)}
    env.pop("KONTROL_TEST_DB_URL", None)
    env.update(env_extra or {})
    return subprocess.run(orden_alembic("upgrade", target),
                          cwd=BACKEND, env=env, capture_output=True, text=True, timeout=900)


def _sql(db_name: str, statements: list[str]) -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(_db_url(db_name), future=True)
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
    engine.dispose()


def _query(db_name: str, statement: str):
    from sqlalchemy import create_engine, text

    engine = create_engine(_db_url(db_name), future=True)
    with engine.connect() as conn:
        rows = conn.execute(text(statement)).fetchall()
    engine.dispose()
    return rows


def _fresh(name: str) -> str:
    """Base con el esquema anterior a 011 y la cadena organizativa mínima."""
    from sqlalchemy import create_engine, text

    engine = create_engine(PG_URL.rsplit("/", 1)[0] + "/postgres", future=True,
                           isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{name}" ENCODING \'UTF8\''))
    engine.dispose()
    # La base tiene dueño: se suelta al terminar el ámbito —la prueba o el módulo— que la creó.
    from pg_harness import registrar_base

    registrar_base(name)

    result = _alembic(name, PRE_011)
    assert result.returncode == 0, result.stderr[-2000:]

    _sql(name, [
        "INSERT INTO installations (id, installation_uuid, state, created_at, updated_at) "
        "VALUES ('inst-1','uuid-1','ACTIVE',now(),now())",
        "INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at, updated_at) "
        "VALUES ('ten-1','inst-1','DEMO','Demo','MONO_COMPANY','ACTIVE',now(),now())",
        "INSERT INTO companies (id, tenant_id, code, legal_name, rif, legal_type, "
        "  functional_currency, status, created_at, updated_at) "
        "VALUES ('co-1','ten-1','D1','Demo CA','J-1','CA','VED','ACTIVE',now(),now())",
        "INSERT INTO units_of_measure (id, company_id, code, name, symbol, dimension, "
        "  decimals, status, created_at, updated_at) "
        "VALUES ('u-und','co-1','UND','Unidad','und','CANTIDAD',0,'ACTIVE',now(),now())",
        "INSERT INTO units_of_measure (id, company_id, code, name, symbol, dimension, "
        "  decimals, status, created_at, updated_at) "
        "VALUES ('u-kg','co-1','KG','Kilo','kg','PESO',3,'ACTIVE',now(),now())",
        # Producto CON unidad base -> clase A
        "INSERT INTO catalog_items (id, company_id, code, name, item_type, status, "
        "  base_unit_id, created_at, updated_at) "
        "VALUES ('it-a','co-1','P-A','Con base','PRODUCT','ACTIVE','u-und',now(),now())",
        # Producto SIN unidad base -> clase B o C según evidencia
        "INSERT INTO catalog_items (id, company_id, code, name, item_type, status, "
        "  created_at, updated_at) "
        "VALUES ('it-b','co-1','P-B','Sin base','PRODUCT','ACTIVE',now(),now())",
        "INSERT INTO catalog_items (id, company_id, code, name, item_type, status, "
        "  created_at, updated_at) "
        "VALUES ('it-c','co-1','P-C','Ambiguo','PRODUCT','ACTIVE',now(),now())",
        "INSERT INTO movement_types (id, code, name, direction, affects_balance, status, "
        "  created_at, updated_at) "
        "VALUES ('mt-1','ENT','Entrada','IN',true,'ACTIVE',now(),now())",
        "INSERT INTO warehouses (id, company_id, code, name, warehouse_type, status, "
        "  created_at, updated_at) "
        "VALUES ('wh-1','co-1','ALM','Central','PHYSICAL','ACTIVE',now(),now())",
    ])
    return name


def _movement(db: str, row_id: str, product: str, qty: str, unit: str | None) -> None:
    unit_sql = f"'{unit}'" if unit else "NULL"
    _sql(db, [
        f"INSERT INTO inventory_movements (id, company_id, warehouse_id, product_id, "
        f"  movement_type_id, quantity, unit_id, currency, occurred_at, status, "
        f"  created_at, updated_at) "
        f"VALUES ('{row_id}','co-1','wh-1','{product}','mt-1',{qty},{unit_sql},'VED',"
        f"  now(),'POSTED',now(),now())"])


def _invoice_line(db: str, row_id: str, product: str, qty: str) -> None:
    _sql(db, [
        "INSERT INTO parties (id, company_id, code, name, legal_name, tax_id, status, "
        "  person_type, roles, created_at, updated_at) "
        "VALUES ('pt-1','co-1','CLI','Cliente','Cliente CA','J-9','ACTIVE','JURIDICA',"
        "  '[\"CLIENTE\"]',now(),now()) ON CONFLICT DO NOTHING",
        "INSERT INTO sales_invoices (id, company_id, customer_id, invoice_number, status, "
        "  base_fiscal_currency, base_fiscal, tax_total, total, created_at, updated_at) "
        f"VALUES ('inv-{row_id}','co-1','pt-1','F-{row_id}','ISSUED','VED',0,0,0,now(),now()) "
        "ON CONFLICT DO NOTHING",
        f"INSERT INTO sales_invoice_lines (id, invoice_id, product_id, quantity, unit_price, "
        f"  tax_amount, base_fiscal, total, created_at, updated_at) "
        f"VALUES ('{row_id}','inv-{row_id}','{product}',{qty},10,0,0,0,now(),now())"])


# ---------------------------------------------------- §34 · CASO D (clase A)
def test_backfill_deterministico():
    db = _fresh("k011_det")
    _movement(db, "mv-1", "it-a", "25", None)

    result = _alembic(db, "head")
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-2000:]
    assert '"deterministic": 1' in result.stdout
    assert '"migration_blocked": false' in result.stdout

    row = _query(db, "SELECT quantity, uom_id, base_quantity, conversion_factor_snapshot, "
                     "uom_source FROM inventory_movements WHERE id='mv-1'")[0]
    assert row[0] == 25, "la cantidad original nunca se modifica"
    assert row[1] == "u-und"
    assert row[2] == 25
    assert row[3] == 1
    assert row[4] == "LEGACY_ASSUMED_BASE"


# ---------------------------------------------------- §35 · CASO E (clase B)
def test_backfill_reconstruible_con_candidata_unica():
    db = _fresh("k011_rec")
    # El producto no declara unidad base, pero sus movimientos solo usaron KG.
    _movement(db, "mv-1", "it-b", "10", "u-kg")
    _movement(db, "mv-2", "it-b", "5", None)

    result = _alembic(db, "head")
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-2000:]
    assert '"reconstructed": 2' in result.stdout
    assert "RECONSTRUCTIBLE_WITH_EVIDENCE" in result.stdout

    rows = dict(_query(db, "SELECT id, uom_id FROM inventory_movements"))
    assert rows["mv-1"] == "u-kg" and rows["mv-2"] == "u-kg"
    sources = {r[0] for r in _query(db, "SELECT DISTINCT uom_source FROM inventory_movements")}
    assert sources == {"LEGACY_RECONSTRUCTED"}


# ---------------------------------------------------- §36 · CASO F (clase C)
def test_backfill_ambiguo_no_adivina():
    db = _fresh("k011_amb")
    # Dos unidades distintas en la evidencia: no se elige la más frecuente.
    _movement(db, "mv-1", "it-c", "10", "u-und")
    _movement(db, "mv-2", "it-c", "5", "u-kg")
    _movement(db, "mv-3", "it-c", "7", "u-und")

    result = _alembic(db, "head")
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-2000:]
    assert '"ambiguous": 3' in result.stdout
    assert "AMBIGUOUS" in result.stdout
    assert "no se elige la más probable" in result.stdout

    rows = _query(db, "SELECT quantity, uom_id, base_quantity, uom_source "
                      "FROM inventory_movements ORDER BY id")
    for quantity, unit, base, source in rows:
        assert unit is None, "no se asigna una unidad supuesta"
        assert base is None, "sin unidad no hay cantidad base"
        assert source == "LEGACY_UNRESOLVED"
        assert quantity is not None, "la cantidad original se conserva"


# ------------------------------------ §33 · CASO C · ABORTO CRÍTICO (clase D)
def test_linea_fiscal_irreconstruible_aborta_sin_escribir():
    """ESC-011-01 con el default: una sola línea crítica bloquea."""
    db = _fresh("k011_crit")
    _movement(db, "mv-1", "it-a", "25", None)          # clase A, se perdería
    _movement(db, "mv-2", "it-c", "10", "u-und")
    _movement(db, "mv-3", "it-c", "5", "u-kg")         # hace ambiguo a it-c
    _invoice_line(db, "ln-crit", "it-c", "3")          # fiscal + ambiguo = clase D

    result = _alembic(db, "head")
    assert result.returncode != 0, "la migración debía bloquearse"
    assert '"fiscal_critical": 1' in result.stdout
    assert '"migration_blocked": true' in result.stdout
    assert "NON_RECONSTRUCTIBLE_FISCAL" in result.stdout
    assert '"max_critical_allowed": 0' in result.stdout

    # --- Cero escrituras aplicadas: se inspecciona la base, no el código de
    # --- salida. La versión de Alembic **nunca** queda marcada como si el
    # --- backfill hubiera corrido.
    version = _query(db, "SELECT version_num FROM alembic_version")[0][0]
    assert version != "0022_uom_backfill", f"la versión avanzó indebidamente a {version}"
    # PostgreSQL ejecuta la cadena en una transacción: el aborto revierte también
    # las migraciones de esquema que la acompañaban. Es más seguro de lo mínimo
    # exigido y por eso se acepta cualquier estado anterior al backfill.
    assert version in ("0018_location_fk_and_legacy", "0021_line_uom_columns"), version

    # Las cantidades originales permanecen intactas en todos los casos.
    rows = _query(db, "SELECT quantity FROM inventory_movements ORDER BY id")
    assert [r[0] for r in rows] == [25, 10, 5]
    assert _query(db, "SELECT quantity FROM sales_invoice_lines")[0][0] == 3

    # Si el esquema sobrevivió al aborto, ninguna columna de 011 fue escrita.
    if version == "0021_line_uom_columns":
        for quantity, unit, base, source in _query(
                db, "SELECT quantity, uom_id, base_quantity, uom_source "
                    "FROM inventory_movements ORDER BY id"):
            assert unit is None and base is None and source is None, \
                "el backfill escribió pese al bloqueo"
            assert quantity is not None


def test_umbral_configurable_permite_continuar_deliberadamente():
    """El umbral se puede subir, pero es una acción explícita y auditable."""
    db = _fresh("k011_thr")
    _movement(db, "mv-2", "it-c", "10", "u-und")
    _movement(db, "mv-3", "it-c", "5", "u-kg")
    _invoice_line(db, "ln-crit", "it-c", "3")

    result = _alembic(db, "head", {"KONTROL_UOM_BACKFILL_MAX_CRITICAL": "1"})
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-2000:]
    assert '"max_critical_allowed": 1' in result.stdout
    assert '"threshold_source": "ENV:KONTROL_UOM_BACKFILL_MAX_CRITICAL"' in result.stdout
    assert '"migration_blocked": false' in result.stdout

    # La línea fiscal sigue sin tocarse: solo se marca.
    fiscal = _query(db, "SELECT quantity, uom_id, base_quantity, uom_source "
                        "FROM sales_invoice_lines")[0]
    assert fiscal[0] == 3 and fiscal[1] is None and fiscal[2] is None
    assert fiscal[3] == "LEGACY_UNVERSIONED"


# ---------------------------------------------------- §27 · Float -> Numeric
def test_conversion_de_tipo_conserva_los_valores():
    db = _fresh("k011_num")
    for index, value in enumerate(("0", "1", "0.1", "0.01", "1.234567", "-3.5", "999999.5"), 1):
        _movement(db, f"mv-{index}", "it-a", value, None)
    _sql(db, ["INSERT INTO inventory_movements (id, company_id, warehouse_id, product_id, "
              "  movement_type_id, quantity, currency, occurred_at, status, created_at, updated_at) "
              "VALUES ('mv-null','co-1','wh-1','it-a','mt-1',2,'VED',now(),'POSTED',now(),now())"])

    before = {r[0]: float(r[1]) for r in _query(db, "SELECT id, quantity FROM inventory_movements")}
    result = _alembic(db, "head")
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-2000:]
    assert '"total_columns_migrated": 30' in result.stdout

    after = {r[0]: float(r[1]) for r in _query(db, "SELECT id, quantity FROM inventory_movements")}
    assert before == after, "la conversión de tipo alteró valores"

    kind = _query(db, "SELECT data_type FROM information_schema.columns "
                      "WHERE table_name='inventory_movements' AND column_name='quantity'")[0][0]
    assert kind == "numeric"


# ---------------------------------------------------- §32 · idempotencia
def test_reejecucion_es_idempotente():
    db = _fresh("k011_idem")
    _movement(db, "mv-1", "it-a", "25", None)
    first = _alembic(db, "head")
    assert first.returncode == 0, first.stderr[-2000:]
    snapshot = _query(db, "SELECT id, quantity, uom_id, base_quantity FROM inventory_movements")

    second = _alembic(db, "head")
    assert second.returncode == 0, second.stderr[-2000:]
    assert _query(db, "SELECT id, quantity, uom_id, base_quantity FROM inventory_movements") == snapshot
