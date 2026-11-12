import os
import pathlib
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text

from alembic import command
from alembic.config import Config


def test_el_backfill_solo_vincula_coincidencias_exactas():
    url = os.environ.get("KONTROL_TEST_DB_URL", "")
    if "postgresql" not in url:
        pytest.skip("El backfill se verifica sobre PostgreSQL")

    base, _, nombre = url.rpartition("/")
    destino = f"{nombre}_pt103"
    url_destino = f"{base}/{destino}"
    raiz = pathlib.Path(__file__).resolve().parents[1]

    admin = create_engine(f"{base}/postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{destino}"'))
        conn.execute(text(f'CREATE DATABASE "{destino}" ENCODING \'UTF8\''))
        conn.execute(text(f'ALTER DATABASE "{destino}" SET timezone TO \'UTC\''))
    admin.dispose()

    cfg = Config(str(raiz / "alembic.ini"))
    cfg.set_main_option("script_location", str(raiz / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url_destino)

    old_url = os.environ.get("KONTROL_DB_URL")
    os.environ["KONTROL_DB_URL"] = url_destino
    engine = None
    try:
        command.upgrade(cfg, "0102_gov_ctl09_actas")

        engine = create_engine(url_destino)
        instalacion = str(uuid.uuid4())
        tenant = str(uuid.uuid4())
        company_a = str(uuid.uuid4())
        company_b = str(uuid.uuid4())
        warehouse_a1 = str(uuid.uuid4())
        warehouse_a2 = str(uuid.uuid4())
        proveedor = str(uuid.uuid4())
        orden = str(uuid.uuid4())
        producto = str(uuid.uuid4())
        movimiento_tipo = str(uuid.uuid4())
        ubicacion_fisica = str(uuid.uuid4())
        receipt_ok = str(uuid.uuid4())
        receipt_dup_1 = str(uuid.uuid4())
        receipt_dup_2 = str(uuid.uuid4())
        receipt_w2 = str(uuid.uuid4())
        m1 = str(uuid.uuid4())
        m2 = str(uuid.uuid4())
        m3 = str(uuid.uuid4())
        m4 = str(uuid.uuid4())
        m5 = str(uuid.uuid4())
        m6 = str(uuid.uuid4())

        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO installations (id, installation_uuid) "
                    "VALUES (:id, :installation_uuid)"
                ),
                {"id": instalacion, "installation_uuid": str(uuid.uuid4())},
            )
            conn.execute(
                text(
                    "INSERT INTO tenants (id, code, name, installation_id) "
                    "VALUES (:id, :code, :name, :installation_id)"
                ),
                {"id": tenant, "code": "TENANT-BF", "name": "Tenant BF", "installation_id": instalacion},
            )
            conn.execute(
                text(
                    "INSERT INTO companies (id, code, legal_name, rif, tenant_id) "
                    "VALUES (:id, :code, :legal_name, :rif, :tenant_id)"
                ),
                {"id": company_a, "code": "C-A", "legal_name": "Compañía A", "rif": "J-00000001-0", "tenant_id": tenant},
            )
            conn.execute(
                text(
                    "INSERT INTO companies (id, code, legal_name, rif, tenant_id) "
                    "VALUES (:id, :code, :legal_name, :rif, :tenant_id)"
                ),
                {"id": company_b, "code": "C-B", "legal_name": "Compañía B", "rif": "J-00000002-0", "tenant_id": tenant},
            )
            conn.execute(
                text(
                    "INSERT INTO warehouses (id, company_id, code, name) "
                    "VALUES (:id, :company_id, :code, :name)"
                ),
                {"id": warehouse_a1, "company_id": company_a, "code": "W1", "name": "Almacén 1"},
            )
            conn.execute(
                text(
                    "INSERT INTO warehouses (id, company_id, code, name) "
                    "VALUES (:id, :company_id, :code, :name)"
                ),
                {"id": warehouse_a2, "company_id": company_a, "code": "W2", "name": "Almacén 2"},
            )
            conn.execute(
                text(
                    "INSERT INTO parties (id, company_id, code, name, roles) "
                    "VALUES (:id, :company_id, :code, :name, CAST(:roles AS json))"
                ),
                {"id": proveedor, "company_id": company_a, "code": "PROV-BF", "name": "Proveedor BF", "roles": '["PROVEEDOR"]'},
            )
            conn.execute(
                text(
                    "INSERT INTO purchase_orders (id, company_id, supplier_id, code) "
                    "VALUES (:id, :company_id, :supplier_id, :code)"
                ),
                {"id": orden, "company_id": company_a, "supplier_id": proveedor, "code": "PO-BF"},
            )
            conn.execute(
                text(
                    "INSERT INTO catalog_items (id, company_id, code, name, item_type) "
                    "VALUES (:id, :company_id, :code, :name, :item_type)"
                ),
                {"id": producto, "company_id": company_a, "code": "PROD-BF", "name": "Producto BF", "item_type": "PRODUCT"},
            )
            conn.execute(
                text(
                    "INSERT INTO movement_types (id, company_id, code, name, direction) "
                    "VALUES (:id, :company_id, :code, :name, :direction)"
                ),
                {
                    "id": movimiento_tipo,
                    "company_id": company_a,
                    "code": "UBICACION",
                    "name": "Colocación en ubicación (put-away)",
                    "direction": "INTERNAL",
                },
            )
            conn.execute(
                text(
                    "INSERT INTO warehouse_locations (id, company_id, warehouse_id, code) "
                    "VALUES (:id, :company_id, :warehouse_id, :code)"
                ),
                {"id": ubicacion_fisica, "company_id": company_a, "warehouse_id": warehouse_a1, "code": "LOC-BF"},
            )
            conn.execute(
                text(
                    "INSERT INTO goods_receipts (id, company_id, warehouse_id, order_id, code) "
                    "VALUES (:id, :company_id, :warehouse_id, :order_id, :code)"
                ),
                {"id": receipt_ok, "company_id": company_a, "warehouse_id": warehouse_a1, "order_id": orden, "code": "RC-OK"},
            )
            conn.execute(
                text(
                    "INSERT INTO goods_receipts (id, company_id, warehouse_id, order_id, code) "
                    "VALUES (:id, :company_id, :warehouse_id, :order_id, :code)"
                ),
                {"id": receipt_dup_1, "company_id": company_a, "warehouse_id": warehouse_a1, "order_id": orden, "code": "RC-DUP"},
            )
            conn.execute(
                text(
                    "INSERT INTO goods_receipts (id, company_id, warehouse_id, order_id, code) "
                    "VALUES (:id, :company_id, :warehouse_id, :order_id, :code)"
                ),
                {"id": receipt_dup_2, "company_id": company_a, "warehouse_id": warehouse_a1, "order_id": orden, "code": "RC-DUP"},
            )
            conn.execute(
                text(
                    "INSERT INTO goods_receipts (id, company_id, warehouse_id, order_id, code) "
                    "VALUES (:id, :company_id, :warehouse_id, :order_id, :code)"
                ),
                {"id": receipt_w2, "company_id": company_a, "warehouse_id": warehouse_a2, "order_id": orden, "code": "RC-W2"},
            )

            movimientos = [
                {
                    "id": m1,
                    "company_id": company_a,
                    "warehouse_id": warehouse_a1,
                    "product_id": producto,
                    "movement_type_id": movimiento_tipo,
                    "quantity": 7,
                    "document_ref": "RC-OK",
                    "status": "POSTED",
                    "source_location_id": None,
                    "target_state": "DISPONIBLE",
                    "base_quantity": 7,
                },
                {
                    "id": m2,
                    "company_id": company_a,
                    "warehouse_id": warehouse_a1,
                    "product_id": producto,
                    "movement_type_id": movimiento_tipo,
                    "quantity": 3,
                    "document_ref": "RC-DUP",
                    "status": "POSTED",
                    "source_location_id": None,
                    "target_state": "DISPONIBLE",
                    "base_quantity": 3,
                },
                {
                    "id": m3,
                    "company_id": company_a,
                    "warehouse_id": warehouse_a1,
                    "product_id": producto,
                    "movement_type_id": movimiento_tipo,
                    "quantity": 2,
                    "document_ref": "RC-W2",
                    "status": "POSTED",
                    "source_location_id": None,
                    "target_state": "DISPONIBLE",
                    "base_quantity": 2,
                },
                {
                    "id": m4,
                    "company_id": company_a,
                    "warehouse_id": warehouse_a1,
                    "product_id": producto,
                    "movement_type_id": movimiento_tipo,
                    "quantity": 1,
                    "document_ref": "RC-OK",
                    "status": "REVERSED",
                    "source_location_id": None,
                    "target_state": "DISPONIBLE",
                    "base_quantity": 1,
                },
                {
                    "id": m5,
                    "company_id": company_a,
                    "warehouse_id": warehouse_a1,
                    "product_id": producto,
                    "movement_type_id": movimiento_tipo,
                    "quantity": 1,
                    "document_ref": "RC-OK",
                    "status": "POSTED",
                    "source_location_id": ubicacion_fisica,
                    "target_state": "DISPONIBLE",
                    "base_quantity": 1,
                },
                {
                    "id": m6,
                    "company_id": company_a,
                    "warehouse_id": warehouse_a1,
                    "product_id": producto,
                    "movement_type_id": movimiento_tipo,
                    "quantity": 1,
                    "document_ref": "TEXTO-LIBRE",
                    "status": "POSTED",
                    "source_location_id": None,
                    "target_state": "DISPONIBLE",
                    "base_quantity": 1,
                },
            ]
            for movimiento in movimientos:
                conn.execute(
                    text(
                        "INSERT INTO inventory_movements (id, company_id, warehouse_id, product_id, "
                        "movement_type_id, quantity, occurred_at, status, reversed_by_id, "
                        "document_ref, source_location_id, target_state, base_quantity) "
                        "VALUES (:id, :company_id, :warehouse_id, :product_id, :movement_type_id, "
                        ":quantity, now(), :status, :reversed_by_id, :document_ref, :source_location_id, "
                        ":target_state, :base_quantity)"
                    ),
                    {
                        "id": movimiento["id"],
                        "company_id": movimiento["company_id"],
                        "warehouse_id": movimiento["warehouse_id"],
                        "product_id": movimiento["product_id"],
                        "movement_type_id": movimiento["movement_type_id"],
                        "quantity": movimiento["quantity"],
                        "status": movimiento["status"],
                        "reversed_by_id": None,
                        "document_ref": movimiento["document_ref"],
                        "source_location_id": movimiento["source_location_id"],
                        "target_state": movimiento["target_state"],
                        "base_quantity": movimiento["base_quantity"],
                    },
                )

        command.upgrade(cfg, "head")

        with engine.connect() as conn:
            filas = conn.execute(
                text(
                    "SELECT receipt_id, movement_id, base_quantity, company_id, warehouse_id, product_id "
                    "FROM receipt_putaways"
                )
            ).fetchall()

        assert filas == [(receipt_ok, m1, Decimal("7"), company_a, warehouse_a1, producto)]

        command.downgrade(cfg, "0102_gov_ctl09_actas")

        with engine.connect() as conn:
            existe = conn.execute(
                text("SELECT to_regclass('receipt_putaways') IS NULL")
            ).scalar()
        assert existe is True
    finally:
        if engine is not None:
            engine.dispose()
        if old_url is None:
            os.environ.pop("KONTROL_DB_URL", None)
        else:
            os.environ["KONTROL_DB_URL"] = old_url
        admin = create_engine(f"{base}/postgres", isolation_level="AUTOCOMMIT")
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{destino}"'))
        admin.dispose()
