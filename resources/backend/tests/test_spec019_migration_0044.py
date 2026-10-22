"""La migración `0044` frente a recepciones anteriores a la Spec 019.

Siembra una base en `0043` con una recepción aceptada y su línea, aplica `0044`
y comprueba que **no se inventa nada**: el arribo, los bultos y la observación
física de una recepción pasada no son reconstruibles y quedan nulos. Solo sobre
PostgreSQL: es el motor que impone las restricciones.
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
PRE_019 = "0043_spec030_reservation"


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

    name = f"k019_{uuid.uuid4().hex[:8]}"
    admin = create_engine(PG_URL.rsplit("/", 1)[0] + "/postgres", future=True, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    proc = _alembic(name, PRE_019)
    assert proc.returncode == 0, proc.stderr[-3000:]

    ids = {k: str(uuid.uuid4()) for k in ("inst", "ten", "co", "wh", "prod", "party", "po", "pol", "rec", "line")}
    _sql(name, [
        ("INSERT INTO installations (id, installation_uuid, state, created_at, updated_at) "
         "VALUES (:i, :u, 'ACTIVE', now(), now())", {"i": ids["inst"], "u": "u-" + ids["inst"][:8]}),
        ("INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at, updated_at) "
         "VALUES (:i, :inst, 'T', 'T', 'MULTI_COMPANY', 'ACTIVE', now(), now())", {"i": ids["ten"], "inst": ids["inst"]}),
        ("INSERT INTO companies (id, tenant_id, code, legal_name, rif, legal_type, functional_currency, status, created_at, updated_at) "
         "VALUES (:i, :t, 'C', 'C', 'J-1', 'JURIDICA', 'VED', 'ACTIVE', now(), now())", {"i": ids["co"], "t": ids["ten"]}),
        ("INSERT INTO warehouses (id, company_id, code, name, status, created_at, updated_at) "
         "VALUES (:i, :c, 'W', 'W', 'ACTIVE', now(), now())", {"i": ids["wh"], "c": ids["co"]}),
        ("INSERT INTO catalog_items (id, company_id, code, name, item_type, status, created_at, updated_at) "
         "VALUES (:i, :c, 'P', 'P', 'PRODUCT', 'ACTIVE', now(), now())", {"i": ids["prod"], "c": ids["co"]}),
        ("INSERT INTO parties (id, company_id, code, name, person_type, roles, status, created_at, updated_at) "
         "VALUES (:i, :c, 'PRV', 'Proveedor', 'JURIDICA', CAST(:r AS JSON), 'ACTIVE', now(), now())",
         {"i": ids["party"], "c": ids["co"], "r": '["PROVEEDOR"]'}),
        ("INSERT INTO purchase_orders (id, company_id, code, supplier_id, currency, status, created_at, updated_at) "
         "VALUES (:i, :c, 'OC', :s, 'VED', 'APPROVED', now(), now())",
         {"i": ids["po"], "c": ids["co"], "s": ids["party"]}),
        ("INSERT INTO purchase_order_lines (id, order_id, product_id, quantity_ordered, quantity_received, "
         "unit_price, discount, needs_inventory, created_at, updated_at) "
         "VALUES (:i, :o, :p, 10, 10, 5, 0, true, now(), now())",
         {"i": ids["pol"], "o": ids["po"], "p": ids["prod"]}),
        ("INSERT INTO goods_receipts (id, company_id, code, order_id, warehouse_id, status, quality_status, created_at, updated_at) "
         "VALUES (:i, :c, 'REC-VIEJA', :o, :w, 'ACCEPTED', 'APPROVED', now(), now())",
         {"i": ids["rec"], "c": ids["co"], "o": ids["po"], "w": ids["wh"]}),
        ("INSERT INTO goods_receipt_lines (id, receipt_id, order_line_id, product_id, quantity_received, "
         "quantity_accepted, quantity_rejected, quality, created_at, updated_at) "
         "VALUES (:i, :r, :ol, :p, 10, 10, 0, 'APPROVED', now(), now())",
         {"i": ids["line"], "r": ids["rec"], "ol": ids["pol"], "p": ids["prod"]}),
    ])
    proc = _alembic(name, "head")
    assert proc.returncode == 0, proc.stderr[-3000:]
    ids["log"] = proc.stdout + proc.stderr
    yield name, ids
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
    admin.dispose()


def test_la_recepcion_pasada_no_recibe_un_arribo_inventado(base_migrada):
    """`P23` al revés: lo que no se capturó entonces no se fabrica ahora."""
    name, ids = base_migrada
    (row,) = _rows(name, "SELECT arrival_at, packages_declared, packages_received, inspected_at, "
                         "record_issued_at, packing_list_ref FROM goods_receipts WHERE id = :i", i=ids["rec"])
    assert all(v is None for v in row), f"la migración inventó datos físicos: {row}"


def test_la_linea_pasada_no_recibe_una_observacion_inventada(base_migrada):
    name, ids = base_migrada
    (row,) = _rows(name, "SELECT physical_condition, damaged_quantity, damage_notes, identification_ok, "
                         "reference_ok, overage_base_quantity FROM goods_receipt_lines WHERE id = :i", i=ids["line"])
    assert all(v is None for v in row), f"la migración inventó una observación física: {row}"


def test_no_se_añadio_un_veredicto_de_conformidad_duplicado(base_migrada):
    name, _ = base_migrada
    cols = {r[0] for r in _rows(name, "SELECT column_name FROM information_schema.columns "
                                      "WHERE table_name = 'goods_receipts'")}
    assert "conformity" not in cols, "volvió el segundo veredicto"
    assert "quality_status" in cols


def test_las_restricciones_existen_con_el_nombre_del_orm(base_migrada):
    name, _ = base_migrada
    checks = {r[0] for r in _rows(name, "SELECT conname FROM pg_constraint WHERE contype = 'c'")}
    assert {"ck_goods_receipts_packages_nonneg", "ck_goods_receipt_lines_damage_nonneg"} <= checks
    assert not any(c.startswith("ck_goods_receipts_ck_") for c in checks), "nombre duplicado por la convención"


def test_la_restriccion_de_bultos_rechaza_un_negativo(base_migrada):
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import IntegrityError

    name, ids = base_migrada
    engine = create_engine(_db_url(name), future=True)
    try:
        with pytest.raises(IntegrityError) as info:
            with engine.begin() as conn:
                conn.execute(text("UPDATE goods_receipts SET packages_received = -1 WHERE id = :i"), {"i": ids["rec"]})
        estado = getattr(info.value.orig, "pgcode", None)
        assert estado == "23514", f"SQLSTATE inesperado: {estado}"
    finally:
        engine.dispose()


def test_la_migracion_declara_lo_que_encontro(base_migrada):
    _, ids = base_migrada
    assert "recepciones existentes: 1" in ids["log"], ids["log"][-1500:]
    assert "no son reconstruibles" in ids["log"]
