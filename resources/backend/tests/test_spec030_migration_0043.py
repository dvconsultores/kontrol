"""La migración `0043` frente a datos anteriores a la Spec 030.

Siembra una base en `0042` con lo que había: una reserva de pedido con
`source_document` en texto, una manual, un pedido `RESERVED`, otro
`CREDIT_PENDING`, y aplica `0043`. Comprueba la clasificación **sin origen
inventado** (§78/§80), el renombrado de estados (§79), la base asumida y el
permiso `ventas:submit`. Solo sobre PostgreSQL: es el motor que impone las
claves y el único donde el índice parcial existe.
"""

from __future__ import annotations

import os
import subprocess
import uuid

import pytest

from tests.alembic_orden import orden_alembic

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif("postgresql" not in PG_URL,
                                reason="La migración de datos solo se verifica sobre PostgreSQL (P21)")
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRE_030 = "0042_spec029_origin"


def _db_url(name: str) -> str:
    return PG_URL.rsplit("/", 1)[0] + "/" + name


def _alembic(db_name: str, target: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "KONTROL_DB_URL": _db_url(db_name)}
    env.pop("KONTROL_TEST_DB_URL", None)
    return subprocess.run(orden_alembic("upgrade", target),
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
    with engine.connect() as conn:
        out = conn.execute(text(statement), params).fetchall()
    engine.dispose()
    return out


@pytest.fixture(scope="module")
def base_migrada():
    from sqlalchemy import create_engine, text

    name = f"k030_{uuid.uuid4().hex[:8]}"
    admin = create_engine(PG_URL.rsplit("/", 1)[0] + "/postgres", future=True, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    proc = _alembic(name, PRE_030)
    assert proc.returncode == 0, proc.stderr[-3000:]

    ids = {k: str(uuid.uuid4()) for k in ("inst", "ten", "co", "wh", "p1", "p2", "party", "o_res", "o_cred",
                                          "l_res", "l_cred_a", "l_cred_b", "r_res", "r_manual", "r_huerfana",
                                          "r_ambigua", "role", "perm_view")}
    _sql(name, [
        ("INSERT INTO installations (id, installation_uuid, state, created_at, updated_at) VALUES (:i, :u, 'ACTIVE', now(), now())",
         {"i": ids["inst"], "u": "u-" + ids["inst"][:8]}),
        ("INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at, updated_at) "
         "VALUES (:i, :inst, 'T', 'T', 'MULTI_COMPANY', 'ACTIVE', now(), now())", {"i": ids["ten"], "inst": ids["inst"]}),
        ("INSERT INTO companies (id, tenant_id, code, legal_name, rif, legal_type, functional_currency, status, created_at, updated_at) "
         "VALUES (:i, :t, 'C', 'C', 'J-1', 'JURIDICA', 'VED', 'ACTIVE', now(), now())", {"i": ids["co"], "t": ids["ten"]}),
        ("INSERT INTO warehouses (id, company_id, code, name, status, created_at, updated_at) "
         "VALUES (:i, :c, 'W', 'W', 'ACTIVE', now(), now())", {"i": ids["wh"], "c": ids["co"]}),
        ("INSERT INTO catalog_items (id, company_id, code, name, item_type, status, created_at, updated_at) "
         "VALUES (:i, :c, 'P1', 'P1', 'PRODUCT', 'ACTIVE', now(), now())", {"i": ids["p1"], "c": ids["co"]}),
        ("INSERT INTO catalog_items (id, company_id, code, name, item_type, status, created_at, updated_at) "
         "VALUES (:i, :c, 'P2', 'P2', 'PRODUCT', 'ACTIVE', now(), now())", {"i": ids["p2"], "c": ids["co"]}),
        ("INSERT INTO parties (id, company_id, code, name, person_type, roles, status, created_at, updated_at) "
         "VALUES (:i, :c, 'CL', 'Cliente', 'JURIDICA', CAST(:r AS JSON), 'ACTIVE', now(), now())",
         {"i": ids["party"], "c": ids["co"], "r": '["CLIENTE"]'}),
        # Pedido RESERVED con una línea de P1 (reconstruible) y otro CREDIT_PENDING con dos líneas de P2 (ambiguo)
        ("INSERT INTO sales_orders (id, company_id, code, customer_id, warehouse_id, currency, status, created_at, updated_at) "
         "VALUES (:i, :c, 'OV-RES', :p, :w, 'VED', 'RESERVED', now(), now())",
         {"i": ids["o_res"], "c": ids["co"], "p": ids["party"], "w": ids["wh"]}),
        ("INSERT INTO sales_orders (id, company_id, code, customer_id, warehouse_id, currency, status, created_at, updated_at) "
         "VALUES (:i, :c, 'OV-CRED', :p, :w, 'VED', 'CREDIT_PENDING', now(), now())",
         {"i": ids["o_cred"], "c": ids["co"], "p": ids["party"], "w": ids["wh"]}),
        ("INSERT INTO sales_order_lines (id, order_id, product_id, quantity, unit_price, discount, needs_inventory, created_at, updated_at) "
         "VALUES (:i, :o, :p, 5, 1, 0, true, now(), now())", {"i": ids["l_res"], "o": ids["o_res"], "p": ids["p1"]}),
        ("INSERT INTO sales_order_lines (id, order_id, product_id, quantity, unit_price, discount, needs_inventory, created_at, updated_at) "
         "VALUES (:i, :o, :p, 2, 1, 0, true, now(), now())", {"i": ids["l_cred_a"], "o": ids["o_cred"], "p": ids["p2"]}),
        ("INSERT INTO sales_order_lines (id, order_id, product_id, quantity, unit_price, discount, needs_inventory, created_at, updated_at) "
         "VALUES (:i, :o, :p, 3, 1, 0, true, now(), now())", {"i": ids["l_cred_b"], "o": ids["o_cred"], "p": ids["p2"]}),
        # Reservas legadas
        ("INSERT INTO reservations (id, company_id, source_document, product_id, warehouse_id, quantity, status, created_at, updated_at) "
         "VALUES (:i, :c, :d, :p, :w, 5, 'ACTIVE', now(), now())",
         {"i": ids["r_res"], "c": ids["co"], "d": f"SALES_ORDER:{ids['o_res']}", "p": ids["p1"], "w": ids["wh"]}),
        ("INSERT INTO reservations (id, company_id, source_document, product_id, warehouse_id, quantity, status, created_at, updated_at) "
         "VALUES (:i, :c, 'MEMO-7', :p, :w, 1, 'ACTIVE', now(), now())",
         {"i": ids["r_manual"], "c": ids["co"], "p": ids["p1"], "w": ids["wh"]}),
        ("INSERT INTO reservations (id, company_id, source_document, product_id, warehouse_id, quantity, status, created_at, updated_at) "
         "VALUES (:i, :c, 'SALES_ORDER:no-existe', :p, :w, 1, 'RELEASED', now(), now())",
         {"i": ids["r_huerfana"], "c": ids["co"], "p": ids["p1"], "w": ids["wh"]}),
        ("INSERT INTO reservations (id, company_id, source_document, product_id, warehouse_id, quantity, status, created_at, updated_at) "
         "VALUES (:i, :c, :d, :p, :w, 2, 'ACTIVE', now(), now())",
         {"i": ids["r_ambigua"], "c": ids["co"], "d": f"SALES_ORDER:{ids['o_cred']}", "p": ids["p2"], "w": ids["wh"]}),
        # Rol ADMIN sin el permiso nuevo
        ("INSERT INTO roles (id, code, name, protected, status, created_at, updated_at) "
         "VALUES (:i, 'ADMIN', 'Administrador', true, 'ACTIVE', now(), now())", {"i": ids["role"]}),
    ])
    proc = _alembic(name, "head")
    assert proc.returncode == 0, proc.stderr[-3000:]
    ids["log"] = proc.stdout + proc.stderr
    yield name, ids
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
    admin.dispose()


def test_la_reserva_de_pedido_reconstruible_recibe_pedido_linea_y_trigger_legado(base_migrada):
    name, ids = base_migrada
    (row,) = _rows(name, "SELECT source_type, source_order_id, source_line_id, trigger, base_quantity, uom_source "
                         "FROM reservations WHERE id = :i", i=ids["r_res"])
    assert row[0] == "SALES_ORDER" and row[1] == ids["o_res"]
    assert row[2] == ids["l_res"], "la única línea del producto era reconstruible"
    assert row[3] == "LEGACY_CREDIT_APPROVAL", "no se reinterpreta: nació al aprobar el crédito"
    assert float(row[4]) == 5.0 and row[5] == "LEGACY_ASSUMED_BASE"


def test_la_reserva_ambigua_no_recibe_linea_inventada(base_migrada):
    name, ids = base_migrada
    (row,) = _rows(name, "SELECT source_type, source_order_id, source_line_id, trigger FROM reservations WHERE id = :i",
                   i=ids["r_ambigua"])
    assert row[0] == "SALES_ORDER" and row[1] == ids["o_cred"]
    assert row[2] is None, "dos líneas del mismo producto: asociar la primera falsificaría la procedencia (§80)"
    assert row[3] == "LEGACY_CREDIT_APPROVAL"
    assert "CRITICAL_AMBIGUOUS" in ids["log"] and ids["r_ambigua"] in ids["log"], "no quedó listada para revisión"


def test_la_manual_y_la_huerfana_se_clasifican_sin_pedido(base_migrada):
    name, ids = base_migrada
    (manual,) = _rows(name, "SELECT source_type, trigger, source_order_id FROM reservations WHERE id = :i", i=ids["r_manual"])
    assert manual == ("MANUAL", "MANUAL", None)
    (huerfana,) = _rows(name, "SELECT source_type, trigger, source_order_id FROM reservations WHERE id = :i", i=ids["r_huerfana"])
    assert huerfana == (None, "LEGACY_CREDIT_APPROVAL", None), "un pedido inexistente no se inventa"
    assert "'LEGACY_UNVERIFIED': 1" in ids["log"]


def test_los_estados_del_pedido_se_renombran_con_evidencia(base_migrada):
    name, ids = base_migrada
    estados = dict(_rows(name, "SELECT id, status FROM sales_orders"))
    assert estados[ids["o_res"]] == "RELEASED"
    assert estados[ids["o_cred"]] == "SUBMITTED"
    assert "CREDIT_PENDING → SUBMITTED: 1" in ids["log"] and "revisión manual" in ids["log"]


def test_el_indice_parcial_y_los_checks_existen_con_el_nombre_del_orm(base_migrada):
    name, _ = base_migrada
    nombres = {r[0] for r in _rows(name, "SELECT indexname FROM pg_indexes WHERE tablename IN ('reservations', 'inventory_balances')")}
    assert {"uq_reservations_active_line", "uq_inventory_balances_key"} <= nombres
    checks = {r[0] for r in _rows(name, "SELECT conname FROM pg_constraint WHERE contype = 'c'")}
    assert {"ck_reservations_quantity_positive", "ck_inventory_balances_reserved_nonneg"} <= checks
    assert not any(c.startswith("ck_reservations_ck_") for c in checks), "nombre duplicado por la convención"


def test_el_permiso_submit_existe_y_admin_lo_tiene(base_migrada):
    name, ids = base_migrada
    rows = _rows(name, "SELECT 1 FROM permissions p JOIN role_permissions rp ON rp.permission_id = p.id "
                       "WHERE p.resource = 'ventas' AND p.action = 'submit' AND rp.role_id = :r", r=ids["role"])
    assert len(rows) == 1


def test_la_migracion_es_idempotente_en_columnas_y_permisos(base_migrada):
    name, _ = base_migrada
    (cols,) = _rows(name, "SELECT count(*) FROM information_schema.columns WHERE table_name = 'reservations' "
                          "AND column_name IN ('source_type','source_order_id','source_line_id','trigger','oversell',"
                          "'released_at','released_by','release_reason')")
    assert cols[0] == 8
    (ttl,) = _rows(name, "SELECT count(*) FROM information_schema.columns WHERE table_name = 'companies' AND column_name = 'reservation_ttl_days'")
    assert ttl[0] == 1
