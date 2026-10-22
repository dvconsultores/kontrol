"""Los seis casos de la migración `0018` (Spec 008, Control 1).

Cada caso siembra una base **anterior a 008**, aplica la cadena completa y
comprueba qué hizo la migración con cada referencia. Se ejecuta contra
PostgreSQL real: es el único motor que impone las claves foráneas, y el modo
offline (`--sql`) no puede clasificar porque no lee datos.

Estas pruebas buscan defectos: el caso 4 exige que la migración **falle**.
"""

from __future__ import annotations

import os
import subprocess
import uuid

import pytest

from tests.alembic_orden import orden_alembic

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif(
    "postgresql" not in PG_URL,
    reason="La clasificación de huérfanas solo es verificable sobre PostgreSQL (P21)",
)

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRE_008 = "0016_approvals_backfill"


def _admin_url() -> str:
    return PG_URL.rsplit("/", 1)[0] + "/postgres"


def _db_url(name: str) -> str:
    return PG_URL.rsplit("/", 1)[0] + "/" + name


def _alembic(db_name: str, target: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "KONTROL_DB_URL": _db_url(db_name)}
    env.pop("KONTROL_TEST_DB_URL", None)
    return subprocess.run(
        orden_alembic("upgrade", target),
        cwd=BACKEND, env=env, capture_output=True, text=True, timeout=600,
    )


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


def _fresh_pre008(name: str) -> str:
    """Base con el esquema anterior a 008 y la cadena organizativa mínima."""
    from sqlalchemy import create_engine, text

    engine = create_engine(_admin_url(), future=True, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{name}" ENCODING \'UTF8\''))
    engine.dispose()
    # La base tiene dueño: se suelta al terminar el ámbito —la prueba o el módulo— que la creó.
    from pg_harness import registrar_base

    registrar_base(name)

    result = _alembic(name, PRE_008)
    assert result.returncode == 0, result.stderr[-2000:]

    _sql(name, [
        "INSERT INTO installations (id, installation_uuid, state, created_at, updated_at) "
        "VALUES ('inst-1','uuid-1','ACTIVE',now(),now())",
        "INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at, updated_at) "
        "VALUES ('ten-1','inst-1','DEMO','Demo','MONO_COMPANY','ACTIVE',now(),now())",
        "INSERT INTO companies (id, tenant_id, code, legal_name, rif, legal_type, "
        "  functional_currency, status, created_at, updated_at) "
        "VALUES ('co-1','ten-1','D1','Demo CA','J-1','CA','VED','ACTIVE',now(),now())",
        "INSERT INTO warehouses (id, company_id, code, name, warehouse_type, status, "
        "  created_at, updated_at) "
        "VALUES ('wh-1','co-1','ALM-01','Central','PHYSICAL','ACTIVE',now(),now())",
        # Texto libre legado: es exactamente lo que NO debe convertirse en jerarquía.
        "INSERT INTO locations (id, warehouse_id, code, zone, aisle, rack, status, "
        "  created_at, updated_at) "
        "VALUES ('loc-1','wh-1','A-01','A ','P3','R1','ACTIVE',now(),now())",
        "INSERT INTO locations (id, warehouse_id, code, zone, status, created_at, updated_at) "
        "VALUES ('loc-2','wh-1','A-02','Zona A','ACTIVE',now(),now())",
        "INSERT INTO catalog_items (id, company_id, code, name, item_type, status, "
        "  created_at, updated_at) "
        "VALUES ('item-1','co-1','P-1','Producto','PRODUCT','ACTIVE',now(),now())",
        "INSERT INTO movement_types (id, code, name, direction, affects_balance, status, "
        "  created_at, updated_at) "
        "VALUES ('mt-1','ENT','Entrada','IN',true,'ACTIVE',now(),now())",
    ])
    return name


def _balance(location_id: str | None, qty: float, row_id: str | None = None) -> str:
    row_id = row_id or f"bal-{uuid.uuid4().hex[:8]}"
    value = f"'{location_id}'" if location_id else "NULL"
    _sql(_CURRENT[0], [
        f"INSERT INTO inventory_balances (id, company_id, warehouse_id, location_id, product_id, "
        f"  state, qty_on_hand, qty_reserved, qty_available, created_at, updated_at) "
        f"VALUES ('{row_id}','co-1','wh-1',{value},'item-1','DISPONIBLE',{qty},0,{qty},now(),now())"
    ])
    return row_id


_CURRENT: list[str] = [""]


def _setup(name: str) -> str:
    _CURRENT[0] = _fresh_pre008(name)
    return _CURRENT[0]


# ---------------------------------------------------------------- AC-008-25
def test_caso_1_todas_las_referencias_validas():
    db = _setup("k008_c1")
    _balance("loc-1", 25.0, row_id="bal-a")
    _balance("loc-2", 0.0, row_id="bal-b")

    result = _alembic(db, "head")
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-2000:]
    out = result.stdout
    assert '"total_rows_checked": 2' in out
    assert '"valid_references": 2' in out
    assert '"orphan_references": 0' in out
    assert '"migration_blocked": false' in out

    # Ninguna fila modificada.
    rows = _query(db, "SELECT location_id, legacy_location_id FROM inventory_balances ORDER BY id")
    assert [(r[0], r[1]) for r in rows] == [("loc-1", None), ("loc-2", None)]


# ---------------------------------------------------------------- AC-008-27
def test_caso_3_no_reconstruible_con_nulo_legitimo():
    """Sin saldo vivo y sin candidata: se anula, pero conservando el original
    y dejando la incidencia registrada."""
    db = _setup("k008_c3")
    _balance("loc-1", 10.0)
    _balance("fantasma-1", 0.0, row_id="bal-orphan")

    result = _alembic(db, "head")
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-2000:]
    out = result.stdout
    assert '"orphan_references": 1' in out
    assert '"nulled_with_justification": 1' in out
    assert '"critical_orphans": 0' in out
    assert "NON_RECONSTRUCTIBLE_BUT_NULL_ALLOWED" in out

    row = _query(db, "SELECT location_id, legacy_location_id FROM inventory_balances "
                     "WHERE id = 'bal-orphan'")[0]
    assert row[0] is None
    # El valor original **nunca** se pierde.
    assert row[1] == "fantasma-1"


# ---------------------------------------------------------------- AC-008-26
def test_caso_2_huerfana_reconstruible_se_repara():
    """Con una única candidata determinista desde `inventory_movements`."""
    db = _setup("k008_c2")
    _sql(db, [
        "INSERT INTO inventory_movements (id, company_id, warehouse_id, location_id, product_id, "
        "  movement_type_id, quantity, currency, occurred_at, created_at, updated_at) "
        "VALUES ('mov-1','co-1','wh-1','loc-1','item-1','mt-1',5,'VED',now(),now(),now())",
    ])
    _balance("fantasma-2", 0.0, row_id="bal-rec")

    result = _alembic(db, "head")
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-2000:]
    out = result.stdout
    assert '"reconstructed_references": 1' in out
    assert "RECONSTRUCTIBLE_ORPHAN" in out

    row = _query(db, "SELECT location_id, legacy_location_id FROM inventory_balances "
                     "WHERE id = 'bal-rec'")[0]
    assert row[0] == "loc-1"
    assert row[1] == "fantasma-2"


def test_reconstruccion_ambigua_no_adivina():
    """Dos candidatas degradan la fila a crítica: no se elige «la más
    probable» (R-008-4)."""
    db = _setup("k008_amb")
    _sql(db, [
        "INSERT INTO inventory_movements (id, company_id, warehouse_id, location_id, product_id, "
        "  movement_type_id, quantity, currency, occurred_at, created_at, updated_at) "
        "VALUES ('mov-1','co-1','wh-1','loc-1','item-1','mt-1',5,'VED',now(),now(),now())",
        "INSERT INTO inventory_movements (id, company_id, warehouse_id, location_id, product_id, "
        "  movement_type_id, quantity, currency, occurred_at, created_at, updated_at) "
        "VALUES ('mov-2','co-1','wh-1','loc-2','item-1','mt-1',5,'VED',now(),now(),now())",
    ])
    _balance("fantasma-3", 0.0, row_id="bal-amb")

    result = _alembic(db, "head")
    assert result.returncode != 0, "una reconstrucción ambigua no puede resolverse sola"
    assert "Reconstrucción ambigua" in result.stdout
    assert '"migration_blocked": true' in result.stdout


# ---------------------------------------------------------------- AC-008-28
def test_caso_4_huerfana_critica_bloquea_la_migracion():
    """Saldo vivo irrecuperable: la migración aborta **antes** de escribir."""
    db = _setup("k008_c4")
    _balance("loc-1", 10.0)
    _balance("fantasma-critica", 99.0, row_id="bal-crit")

    result = _alembic(db, "head")
    assert result.returncode != 0, "la migración debía bloquearse"
    out = result.stdout
    assert '"critical_orphans": 1' in out
    assert '"migration_blocked": true' in out
    assert "CRITICAL_NON_RECONSTRUCTIBLE" in out
    assert "Saldo vivo" in out

    # --- Cero escrituras aplicadas: se verifica el estado de la base, no el
    # --- código de salida.
    version = _query(db, "SELECT version_num FROM alembic_version")[0][0]
    assert version == PRE_008, f"la migración avanzó pese al bloqueo: {version}"
    assert _query(db, "SELECT to_regclass('public.warehouse_locations')")[0][0] is None
    assert _query(db, "SELECT to_regclass('public.warehouse_zones')")[0][0] is None
    fks = _query(db, "SELECT count(*) FROM information_schema.table_constraints "
                     "WHERE constraint_name = 'fk_inventory_balances_location'")[0][0]
    assert fks == 0
    # La referencia crítica sigue intacta.
    assert _query(db, "SELECT location_id FROM inventory_balances "
                      "WHERE id = 'bal-crit'")[0][0] == "fantasma-critica"


# ------------------------------------------------------ AC-008-29 / AC-008-30
def test_caso_5_y_6_idempotencia_y_upgrade_desde_base_real():
    db = _setup("k008_c56")
    _balance("loc-1", 42.0)
    _balance("loc-2", 7.0)
    before = _query(db, "SELECT count(*) FROM locations")[0][0]

    first = _alembic(db, "head")
    assert first.returncode == 0, first.stdout[-3000:] + first.stderr[-2000:]

    # Caso 6: la cadena aplica y los datos se conservan.
    assert _query(db, "SELECT count(*) FROM warehouse_locations")[0][0] == before
    assert _query(db, "SELECT count(*) FROM inventory_balances")[0][0] == 2

    # `legacy_path` conserva el texto original, incluido el espacio de 'A '.
    paths = dict(_query(db, "SELECT id, legacy_path FROM warehouse_locations ORDER BY id"))
    assert paths["loc-1"] == "A  / P3 / R1", repr(paths["loc-1"])
    assert paths["loc-2"] == "Zona A"

    # Ninguna zona, pasillo ni rack se creó automáticamente.
    for table in ("warehouse_zones", "warehouse_aisles", "warehouse_racks", "warehouse_levels"):
        assert _query(db, f"SELECT count(*) FROM {table}")[0][0] == 0, table

    # Caso 5: reejecutar es inocuo.
    second = _alembic(db, "head")
    assert second.returncode == 0, second.stderr[-2000:]
    assert _query(db, "SELECT count(*) FROM warehouse_locations")[0][0] == before
    assert _query(db, "SELECT count(*) FROM inventory_balances")[0][0] == 2


def test_permisos_de_008_los_concede_la_migracion():
    db = _setup("k008_perm")
    _sql(db, [
        "INSERT INTO roles (id, code, name, protected, status, created_at, updated_at) "
        "VALUES ('role-admin','ADMIN','Administrador',true,'ACTIVE',now(),now())",
    ])
    result = _alembic(db, "head")
    assert result.returncode == 0, result.stderr[-2000:]
    actions = {row[0] for row in _query(
        db, "SELECT action FROM permissions WHERE resource = 'organization'")}
    assert {"delete", "manage_structure"} <= actions
    granted = {row[0] for row in _query(
        db, "SELECT p.action FROM permissions p "
            "JOIN role_permissions rp ON rp.permission_id = p.id "
            "WHERE rp.role_id = 'role-admin' AND p.resource = 'organization'")}
    assert {"delete", "manage_structure"} <= granted
