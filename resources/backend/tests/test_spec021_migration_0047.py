"""Spec 021 · la migración `0047` sobre PostgreSQL real.

Dos cosas que solo se ven aquí: que el histórico no se reinterprete —una
recepción ya aceptada tiene su mercancía disponible y decir que está sin
confirmar sería mentir en la otra dirección— y que el permiso nuevo llegue a las
instalaciones que ya existen, porque un endpoint que nadie puede invocar no
está entregado.
"""

from __future__ import annotations

import os
import subprocess
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from tests.alembic_orden import orden_alembic

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif(not PG_URL.startswith("postgresql"),
                                reason="La integridad solo se verifica sobre PostgreSQL (P21)")
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRE_021 = "0046_spec023_state"
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

    name = f"k021_{uuid.uuid4().hex[:8]}"
    admin = create_engine(PG_URL.rsplit("/", 1)[0] + "/postgres", future=True,
                          isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    assert _alembic(name, PRE_021).returncode == 0

    ids = {k: str(uuid.uuid4()) for k in
           ("inst", "ten", "co", "wh", "prod", "party", "po", "pol",
            "rec_ok", "rec_draft", "line", "rol", "perm_approve")}
    _sql(name, [
        ("INSERT INTO installations (id, installation_uuid, state, created_at, updated_at) "
         "VALUES (:i, :i, 'ACTIVE', now(), now())", {"i": ids["inst"]}),
        ("INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at, updated_at) "
         "VALUES (:t, :i, 'T021', 'T', 'STANDARD', 'ACTIVE', now(), now())",
         {"t": ids["ten"], "i": ids["inst"]}),
        ("INSERT INTO companies (id, tenant_id, code, legal_name, rif, legal_type, "
         "functional_currency, status, created_at, updated_at) "
         "VALUES (:c, :t, 'C021', 'Empresa', 'J-021', 'CA', 'VED', 'ACTIVE', now(), now())",
         {"c": ids["co"], "t": ids["ten"]}),
        ("INSERT INTO warehouses (id, company_id, code, name, status, created_at, updated_at) "
         "VALUES (:w, :c, 'W021', 'Almacén', 'ACTIVE', now(), now())",
         {"w": ids["wh"], "c": ids["co"]}),
        ("INSERT INTO catalog_items (id, company_id, code, name, item_type, status, "
         "created_at, updated_at) VALUES (:p, :c, 'P021', 'Prod', 'PRODUCT', 'ACTIVE', now(), now())",
         {"p": ids["prod"], "c": ids["co"]}),
        ("INSERT INTO parties (id, company_id, code, name, person_type, roles, status, "
         "created_at, updated_at) "
         "VALUES (:p, :c, 'PRV021', 'Prov', 'JURIDICA', '[\"PROVEEDOR\"]', 'ACTIVE', now(), now())",
         {"p": ids["party"], "c": ids["co"]}),
        ("INSERT INTO purchase_orders (id, company_id, code, supplier_id, currency, status, "
         "created_at, updated_at) VALUES (:o, :c, 'OC021', :s, 'VED', 'APPROVED', now(), now())",
         {"o": ids["po"], "c": ids["co"], "s": ids["party"]}),
        # Una recepción ya aceptada y otra en borrador: el backfill debe distinguirlas.
        ("INSERT INTO goods_receipts (id, company_id, code, order_id, warehouse_id, status, "
         "quality_status, created_at, updated_at) "
         "VALUES (:r, :c, 'RC-OK', :o, :w, 'ACCEPTED', 'APPROVED', now(), now())",
         {"r": ids["rec_ok"], "c": ids["co"], "o": ids["po"], "w": ids["wh"]}),
        ("INSERT INTO goods_receipts (id, company_id, code, order_id, warehouse_id, status, "
         "quality_status, created_at, updated_at) "
         "VALUES (:r, :c, 'RC-DRAFT', :o, :w, 'DRAFT', 'PENDING', now(), now())",
         {"r": ids["rec_draft"], "c": ids["co"], "o": ids["po"], "w": ids["wh"]}),
        # Un rol con `inventario:approve`: debe heredar `inventario:confirm`.
        ("INSERT INTO permissions (id, resource, action, scope_type, created_at, updated_at) "
         "VALUES (:p, 'inventario', 'approve', 'COMPANY', now(), now())",
         {"p": ids["perm_approve"]}),
        ("INSERT INTO roles (id, company_id, code, name, status, created_at, updated_at) "
         "VALUES (:r, :c, 'ALM021', 'Almacén 021', 'ACTIVE', now(), now())",
         {"r": ids["rol"], "c": ids["co"]}),
        ("INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at) "
         "VALUES (:i, :r, :p, now(), now())",
         {"i": str(uuid.uuid4()), "r": ids["rol"], "p": ids["perm_approve"]}),
    ])

    proc = _alembic(name, "head")
    assert proc.returncode == 0, proc.stdout[-2500:] + proc.stderr[-2500:]
    yield name, ids
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    admin.dispose()


def test_lo_ya_aceptado_queda_confirmado_y_lo_demas_pendiente(base_migrada):
    """No se reinterpreta el histórico en ninguna de las dos direcciones.

    Una recepción aceptada antes de esta Spec tiene su mercancía en `DISPONIBLE`
    bajo la regla que regía entonces. Dejarla `PENDIENTE` afirmaría que hay stock
    a la venta sin confirmar, que es justo lo que la Spec impide hacia adelante.
    """
    name, ids = base_migrada
    estados = dict(_rows(name, "SELECT id, confirmation_status FROM goods_receipts"))
    assert estados[ids["rec_ok"]] == "CONFIRMADA"
    assert estados[ids["rec_draft"]] == "PENDIENTE"


def test_el_permiso_nuevo_llega_a_quien_ya_podia_aprobar(base_migrada):
    name, ids = base_migrada
    filas = _rows(name,
                  "SELECT count(*) FROM role_permissions rp JOIN permissions p "
                  "ON p.id = rp.permission_id WHERE p.resource = 'inventario' "
                  "AND p.action = 'confirm' AND rp.role_id = :r", r=ids["rol"])
    assert filas[0][0] == 1, "el rol que aprobaba inventario no puede confirmar"


def test_el_permiso_no_se_duplica_al_reaplicar(base_migrada):
    """La migración es idempotente en lo que otorga."""
    name, ids = base_migrada
    assert _alembic(name, PRE_021, "downgrade").returncode == 0
    assert _alembic(name, "head").returncode == 0
    filas = _rows(name, "SELECT count(*) FROM permissions WHERE resource = 'inventario' "
                        "AND action = 'confirm'")
    assert filas[0][0] == 1


def test_la_tabla_de_confirmaciones_rechaza_lo_imposible(base_migrada):
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import IntegrityError

    name, ids = base_migrada
    checks = {r[0] for r in _rows(name, "SELECT conname FROM pg_constraint WHERE contype='c' "
                                        "AND conrelid='receipt_confirmations'::regclass")}
    assert {"ck_receipt_confirmations_quantity_positive",
            "ck_receipt_confirmations_target_state",
            "ck_receipt_confirmations_source_state"} <= checks, checks
    assert not any(c.startswith("ck_receipt_confirmations_ck_") for c in checks), "prefijo duplicado"

    # Una línea real para poder probar el destino inventado sin chocar antes con la FK.
    _sql(name, [
        ("INSERT INTO purchase_order_lines (id, order_id, product_id, quantity_ordered, "
         "quantity_received, unit_price, discount, needs_inventory, created_at, updated_at) "
         "VALUES (:l, :o, :p, 10, 0, 1, 0, true, now(), now())",
         {"l": ids["pol"], "o": ids["po"], "p": ids["prod"]}),
        ("INSERT INTO goods_receipt_lines (id, receipt_id, order_line_id, product_id, "
         "quantity_received, quantity_accepted, quantity_rejected, quality, created_at, updated_at) "
         "VALUES (:l, :r, :ol, :p, 10, 10, 0, 'PENDING', now(), now())",
         {"l": ids["line"], "r": ids["rec_ok"], "ol": ids["pol"], "p": ids["prod"]}),
    ])

    engine = create_engine(_db_url(name), future=True)
    try:
        for destino, motivo in (("DESECHO", "destino fuera de las cuatro transiciones"),
                                ("DISPONIBLE", "cantidad no positiva")):
            with pytest.raises(IntegrityError) as info:
                with engine.begin() as conn:
                    conn.execute(text(
                        "INSERT INTO receipt_confirmations (id, company_id, receipt_id, "
                        "receipt_line_id, source_state, target_state, base_quantity, "
                        "created_at, updated_at) "
                        "VALUES (:i, :c, :r, :l, 'RECIBIDO', :t, :q, now(), now())"),
                        {"i": str(uuid.uuid4()), "c": ids["co"], "r": ids["rec_ok"],
                         "l": ids["line"], "t": destino,
                         "q": 0 if destino == "DISPONIBLE" else 5})
            assert getattr(info.value.orig, "pgcode", "") == CHECK_VIOLATION, motivo
    finally:
        engine.dispose()


def test_la_aplicacion_puede_insertar_en_la_tabla_que_crea_la_migracion(base_migrada):
    """La lección de la Spec 020: el SQL crudo de estas pruebas no prueba el ORM."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.database import init_models
    from app.modules.purchasing.models import ReceiptConfirmation

    init_models()
    name, ids = base_migrada
    engine = create_engine(_db_url(name), future=True)
    try:
        with Session(engine) as db:
            fila = ReceiptConfirmation(
                company_id=ids["co"], receipt_id=ids["rec_ok"], receipt_line_id=ids["line"],
                source_state="RECIBIDO", target_state="DISPONIBLE",
                base_quantity=Decimal("10"), created_by="qa")
            db.add(fila)
            db.commit()
            db.refresh(fila)
            assert fila.created_at is not None
            assert fila.created_at <= datetime.now(UTC)
    finally:
        engine.dispose()


def test_bajar_y_subir_deja_la_base_igual(base_migrada):
    name, _ = base_migrada
    assert _alembic(name, PRE_021, "downgrade").returncode == 0
    tablas = {r[0] for r in _rows(name, "SELECT table_name FROM information_schema.tables "
                                        "WHERE table_schema = 'public'")}
    assert "receipt_confirmations" not in tablas
    assert _alembic(name, "head").returncode == 0
    columnas = {r[0] for r in _rows(name, "SELECT column_name FROM information_schema.columns "
                                          "WHERE table_name = 'goods_receipts'")}
    assert {"confirmation_status", "confirmed_at", "confirmed_by"} <= columnas
