# ruff: noqa: E402, F811, F401, I001
import hashlib
import os
import threading
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from test_importaciones_seguimiento import (
    _almacen,
    _hasta_despachado,
    _operador,
    mundo,
    rol_completo,
)

from app.core.errors import ConflictError, KontrolError
from app.modules.audit.models import AuditEvent
from app.modules.imports.models import ImportFile
from app.modules.inventory import service as inventory_service
from app.modules.inventory.models import InventoryMovement, MovementType
from app.modules.master_data.models import CatalogItem
from app.modules.organization.models import Warehouse, WarehouseLocation, WarehouseZone, ZoneType
from app.modules.purchasing.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrderLine,
    ReceiptConfirmation,
)
from app.modules.storage import models as storage_models
from app.modules.storage import service as storage_service
from app.modules.storage.models import StorageLabel
from app.shared.clock import zona_de_negocio

pytest_plugins = ["mfa_apoyo"]

API = "/api/v1"


@pytest.fixture(scope="module")
def rol_almacen(mundo):
    from app.modules.identity_access import service as identity_service

    db = mundo.factory()
    try:
        rol = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"alm{uuid.uuid4().hex[:12]}",
            name="Almacenista Storage",
            company_id=None,
            permissions=[
                "maestros:view",
                "maestros:create",
                "maestros:edit",
                "organization:view",
                "organization:edit",
                "compras:view",
                "compras:create",
                "inventario:view",
                "inventario:create",
            ],
            actor=mundo.admin_id,
        )
        db.commit()
        return rol["id"]
    finally:
        db.close()


def _pendiente(
    mundo,
    reloj_mfa,
    rol_completo,
    rol_almacen,
    mode="ENFORCED",
    on_no_rule="BLOCK",
    label_policy="REQUIRED",
    con_regla=True,
) -> dict:
    cab_compras, file_id, _ = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    cab = _operador(mundo, reloj_mfa, rol_almacen)
    cab["company_id"] = str(mundo.company_id)

    with mundo.factory() as db:
        file = db.get(ImportFile, file_id)
        warehouse_id = _almacen(mundo, mundo.company_id)

        zt1 = ZoneType(company_id=mundo.company_id, code=f"ZT-{uuid4().hex[:8]}", name="Zona Frágil", status="ACTIVE")
        zt2 = ZoneType(company_id=mundo.company_id, code=f"ZT-{uuid4().hex[:8]}", name="Zona Normal", status="ACTIVE")
        db.add_all([zt1, zt2])
        db.flush()

        z1 = WarehouseZone(
            company_id=mundo.company_id,
            warehouse_id=warehouse_id,
            zone_type_id=zt1.id,
            code=f"Z-{uuid4().hex[:8]}",
            name="Z1 Frágil",
            status="ACTIVE",
        )
        z2 = WarehouseZone(
            company_id=mundo.company_id,
            warehouse_id=warehouse_id,
            zone_type_id=zt2.id,
            code=f"Z-{uuid4().hex[:8]}",
            name="Z2 Normal",
            status="ACTIVE",
        )
        db.add_all([z1, z2])
        db.flush()

        l1 = WarehouseLocation(
            company_id=mundo.company_id,
            warehouse_id=warehouse_id,
            zone_id=z1.id,
            code=f"L-{uuid4().hex[:8]}",
            name="Ubicación L1",
            sequence=1,
            status="ACTIVE",
        )
        l2 = WarehouseLocation(
            company_id=mundo.company_id,
            warehouse_id=warehouse_id,
            zone_id=z2.id,
            code=f"L-{uuid4().hex[:8]}",
            name="Ubicación L2",
            sequence=2,
            status="ACTIVE",
        )
        db.add_all([l1, l2])
        db.flush()

        product = CatalogItem(
            company_id=mundo.company_id,
            item_type="PRODUCT",
            code=f"PROD-{uuid4().hex[:8]}",
            name=f"producto-{uuid4().hex[:8]}",
            created_by=mundo.admin_id,
            status="ACTIVE",
        )
        db.add(product)
        db.flush()

        pol = PurchaseOrderLine(
            order_id=file.order_id,
            product_id=product.id,
            quantity_ordered=10,
            unit_price=1,
        )
        db.add(pol)
        db.flush()

        receipt = GoodsReceipt(
            company_id=mundo.company_id,
            code=f"REC-{uuid4().hex[:8]}",
            order_id=file.order_id,
            warehouse_id=warehouse_id,
            status="ACCEPTED",
            quality_status="APPROVED",
            arrival_at=datetime.now(UTC),
            confirmation_status="CONFIRMADA",
        )
        db.add(receipt)
        db.flush()

        line = GoodsReceiptLine(
            receipt_id=receipt.id,
            order_line_id=pol.id,
            product_id=product.id,
            quantity_received=10,
            quantity_accepted=10,
            quantity_rejected=0,
            counted_base_quantity=10,
            damaged_quantity=0,
            overage_base_quantity=0,
            count_difference_kinds=None,
            physical_condition="BUENO",
        )
        db.add(line)
        db.flush()

        confirmation = ReceiptConfirmation(
            company_id=mundo.company_id,
            receipt_id=receipt.id,
            receipt_line_id=line.id,
            source_state="RECIBIDO",
            target_state="DISPONIBLE",
            base_quantity=Decimal("10"),
            created_by=mundo.admin_id,
        )
        db.add(confirmation)

        tipo = inventory_service._get_movement_type_by_code(
            db, mundo.company_id, "ENTRADA_RECEPCION"
        )
        inventory_service.record_movement(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse_id,
            product_id=str(product.id),
            movement_type_id=str(tipo.id),
            quantity=Decimal(10),
            unit_cost=Decimal("5.00"),
            currency="VED",
            document_ref=f"RECEIPT:{receipt.id}",
            actor=mundo.admin_id,
        )

        condition = storage_service.create_condition(
            db,
            company_id=mundo.company_id,
            code=f"FRAGIL-{uuid4().hex[:8]}",
            name="Frágil",
            description=None,
            actor_id=mundo.admin_id,
        )
        storage_service.save_profile(
            db,
            company_id=mundo.company_id,
            item_id=str(product.id),
            weight_value=None,
            weight_unit_id=None,
            volume_value=None,
            volume_unit_id=None,
            size_class_id=None,
            condition_ids=[str(condition.id)],
            expected_version=None,
            actor_id=mundo.admin_id,
        )

        rule_id = None
        if con_regla:
            rule = storage_service.create_rule(
                db,
                company_id=mundo.company_id,
                data={
                    "code": f"R-{uuid4().hex[:8]}",
                    "name": "Regla Frágil",
                    "priority": 1,
                    "warehouse_id": warehouse_id,
                    "condition_id": str(condition.id),
                    "target_zone_id": str(z1.id),
                    "label_policy": label_policy,
                },
                actor_id=mundo.admin_id,
            )
            rule_id = str(rule.id)

        storage_service.save_policy(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse_id,
            mode=mode,
            on_no_rule=on_no_rule,
            expected_version=None,
            actor_id=mundo.admin_id,
        )

        db.commit()
        return {
            "cab": cab,
            "cab_compras": cab_compras,
            "file_id": str(file_id),
            "receipt_id": str(receipt.id),
            "receipt_code": receipt.code,
            "warehouse_id": warehouse_id,
            "product_id": str(product.id),
            "z1": str(z1.id),
            "z2": str(z2.id),
            "l1": str(l1.id),
            "l1_code": l1.code,
            "l2": str(l2.id),
            "rule_id": rule_id,
        }


def test_vista_y_clasificacion(mundo, reloj_mfa, rol_completo, rol_almacen):
    datos = _pendiente(mundo, reloj_mfa, rol_completo, rol_almacen)
    cab = datos["cab"]
    file_id = datos["file_id"]

    r = mundo.client.get(f"{API}/importaciones/{file_id}/storage", headers=cab)
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert len(rows) == 1
    assert rows[0]["product_id"] == datos["product_id"]
    assert rows[0]["classification"] is None
    assert rows[0]["can_putaway"] is False
    assert rows[0]["blocking_reason"] == "Clasifique la mercancía antes de ubicar"

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/classify",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
        },
        headers=cab,
    )
    assert r.status_code == 200
    assert r.json()["result"] == "CLASSIFIED"
    assert "Z1" in r.json()["target_label"]

    r = mundo.client.get(f"{API}/importaciones/{file_id}/storage", headers=cab)
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert len(rows) == 1
    assert [c["id"] for c in rows[0]["candidates"]] == [datos["l1"]]
    assert rows[0]["label_required"] is True
    assert rows[0]["can_putaway"] is False
    assert rows[0]["blocking_reason"] == "Genere la etiqueta antes de ubicar"


def test_etiqueta_y_putaway(mundo, reloj_mfa, rol_completo, rol_almacen):
    datos = _pendiente(mundo, reloj_mfa, rol_completo, rol_almacen)
    cab = datos["cab"]
    file_id = datos["file_id"]

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/classify",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
        },
        headers=cab,
    )
    assert r.status_code == 200
    classification_id = r.json()["id"]

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/putaway",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
            "target_location_id": datos["l1"],
            "quantity": "10",
        },
        headers=cab,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "STORAGE_LABEL_REQUIRED"

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/labels",
        json={"classification_id": classification_id},
        headers=cab,
    )
    assert r.status_code == 200
    label = r.json()
    assert label["reference"].startswith("ETQ-")
    import re
    assert re.match(r"^ETQ-\d{6}$", label["reference"])

    r = mundo.client.get(
        f"{API}/importaciones/{file_id}/storage/labels/{label['id']}/pdf",
        headers=cab,
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    body = r.content
    assert body.startswith(b"%PDF-")
    with mundo.factory() as db2:
        assert hashlib.sha256(body).hexdigest() == db2.get(StorageLabel, label["id"]).file_sha256

    r = mundo.client.get(
        f"{API}/importaciones/{file_id}/storage/labels/{label['id']}/pdf?inline=true",
        headers=cab,
    )
    assert r.status_code == 200
    assert r.headers["content-disposition"].startswith("inline")

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/putaway",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
            "target_location_id": datos["l2"],
            "quantity": "10",
        },
        headers=cab,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "LOCATION_OUTSIDE_DETERMINED_ZONE"

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/putaway",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
            "target_location_id": datos["l1"],
            "quantity": "10",
        },
        headers=cab,
    )
    assert r.status_code == 200
    assert r.json()["movement_id"]

    r = mundo.client.get(
        f"{API}/importaciones/{file_id}",
        headers=datos["cab_compras"],
    )
    assert r.status_code == 200
    logistics = r.json().get("logistics") or {}
    assert any(datos["l1_code"] in loc.get("location_label", "") for loc in logistics.get("locations", []))

    r = mundo.client.get(f"{API}/importaciones/{file_id}/storage", headers=cab)
    assert r.status_code == 200
    assert r.json()["rows"] == []


def test_sin_etiqueta(mundo, reloj_mfa, rol_completo, rol_almacen):
    datos = _pendiente(
        mundo, reloj_mfa, rol_completo, rol_almacen, label_policy="NOT_REQUIRED"
    )
    cab = datos["cab"]
    file_id = datos["file_id"]

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/classify",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
        },
        headers=cab,
    )
    assert r.status_code == 200
    classification_id = r.json()["id"]

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/putaway",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
            "target_location_id": datos["l1"],
            "quantity": "10",
        },
        headers=cab,
    )
    assert r.status_code == 200

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/labels",
        json={"classification_id": classification_id},
        headers=cab,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "STORAGE_LABEL_NOT_REQUIRED"


def test_sin_regla_bloquea(mundo, reloj_mfa, rol_completo, rol_almacen):
    datos = _pendiente(mundo, reloj_mfa, rol_completo, rol_almacen, con_regla=False)
    cab = datos["cab"]
    file_id = datos["file_id"]

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/classify",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
        },
        headers=cab,
    )
    assert r.status_code == 200
    assert r.json()["result"] == "NO_RULE"

    r = mundo.client.get(f"{API}/importaciones/{file_id}/storage", headers=cab)
    row = r.json()["rows"][0]
    assert row["candidates"] == []
    assert "No existe una regla de almacenamiento aplicable" in row["blocking_reason"]

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/putaway",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
            "target_location_id": datos["l1"],
            "quantity": "10",
        },
        headers=cab,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "STORAGE_NO_RULE_BLOCKED"


def test_sin_regla_permite(mundo, reloj_mfa, rol_completo, rol_almacen):
    datos = _pendiente(
        mundo,
        reloj_mfa,
        rol_completo,
        rol_almacen,
        on_no_rule="ALLOW_ANY",
        con_regla=False,
    )
    cab = datos["cab"]
    file_id = datos["file_id"]

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/classify",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
        },
        headers=cab,
    )
    assert r.status_code == 200

    r = mundo.client.get(f"{API}/importaciones/{file_id}/storage", headers=cab)
    row = r.json()["rows"][0]
    assert {datos["l1"], datos["l2"]}.issubset({c["id"] for c in row["candidates"]})

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/putaway",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
            "target_location_id": datos["l2"],
            "quantity": "10",
        },
        headers=cab,
    )
    assert r.status_code == 200


def test_almacen_simple(mundo, reloj_mfa, rol_completo, rol_almacen):
    datos = _pendiente(mundo, reloj_mfa, rol_completo, rol_almacen, mode="DISABLED")
    cab = datos["cab"]
    file_id = datos["file_id"]

    r = mundo.client.get(f"{API}/importaciones/{file_id}/storage", headers=cab)
    row = r.json()["rows"][0]
    assert {datos["l1"], datos["l2"]}.issubset({c["id"] for c in row["candidates"]})
    assert row["can_putaway"] is True

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/putaway",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
            "target_location_id": datos["l2"],
            "quantity": "10",
        },
        headers=cab,
    )
    assert r.status_code == 200


def test_regla_vencida(mundo, reloj_mfa, rol_completo, rol_almacen):
    datos = _pendiente(mundo, reloj_mfa, rol_completo, rol_almacen)
    cab = datos["cab"]
    file_id = datos["file_id"]

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/classify",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
        },
        headers=cab,
    )
    assert r.status_code == 200

    with mundo.factory() as db:
        storage_service.update_rule(
            db,
            company_id=mundo.company_id,
            rule_id=datos["rule_id"],
            expected_version=1,
            data={"name": "Otra"},
            actor_id=mundo.admin_id,
        )
        db.commit()

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/putaway",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
            "target_location_id": datos["l1"],
            "quantity": "10",
        },
        headers=cab,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "STORAGE_CLASSIFICATION_STALE"

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/classify",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
        },
        headers=cab,
    )
    assert r.status_code == 200
    classification_id = r.json()["id"]

    with mundo.factory() as db:
        superseeded = db.scalars(
            select(storage_models.StorageClassification).where(
                storage_models.StorageClassification.status == "SUPERSEDED",
                storage_models.StorageClassification.warehouse_id == datos["warehouse_id"],
                storage_models.StorageClassification.item_id == datos["product_id"],
            )
        ).all()
        assert len(superseeded) >= 1

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/labels",
        json={"classification_id": classification_id},
        headers=cab,
    )
    assert r.status_code == 200

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/putaway",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
            "target_location_id": datos["l1"],
            "quantity": "10",
        },
        headers=cab,
    )
    assert r.status_code == 200


def test_permisos(mundo, reloj_mfa, rol_completo, rol_almacen):
    datos = _pendiente(mundo, reloj_mfa, rol_completo, rol_almacen)
    file_id = datos["file_id"]
    cab_compras = datos["cab_compras"]

    r = mundo.client.get(f"{API}/importaciones/{file_id}/storage", headers=cab_compras)
    assert r.status_code == 200

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/classify",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
        },
        headers=cab_compras,
    )
    assert r.status_code == 403

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/labels",
        json={"classification_id": "x"},
        headers=cab_compras,
    )
    assert r.status_code == 403

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/putaway",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
            "target_location_id": datos["l1"],
            "quantity": "10",
        },
        headers=cab_compras,
    )
    assert r.status_code == 403


def test_aislamiento(mundo, reloj_mfa, rol_completo, rol_almacen):
    datos1 = _pendiente(mundo, reloj_mfa, rol_completo, rol_almacen)
    datos2 = _pendiente(mundo, reloj_mfa, rol_completo, rol_almacen)
    cab = datos1["cab"]
    file1 = datos1["file_id"]
    file2 = datos2["file_id"]

    r = mundo.client.post(
        f"{API}/importaciones/{file1}/storage/classify",
        json={
            "receipt_id": datos2["receipt_id"],
            "product_id": datos2["product_id"],
            "state": "DISPONIBLE",
        },
        headers=cab,
    )
    assert r.status_code == 404
    assert r.json()["code"] == "IMPORT_RECEIPT_NOT_IN_FILE"

    r = mundo.client.post(
        f"{API}/importaciones/{file2}/storage/classify",
        json={
            "receipt_id": datos2["receipt_id"],
            "product_id": datos2["product_id"],
            "state": "DISPONIBLE",
        },
        headers=datos2["cab"],
    )
    assert r.status_code == 200
    classification_id = r.json()["id"]

    r = mundo.client.post(
        f"{API}/importaciones/{file2}/storage/labels",
        json={"classification_id": classification_id},
        headers=datos2["cab"],
    )
    assert r.status_code == 200
    label_id = r.json()["id"]

    r = mundo.client.get(
        f"{API}/importaciones/{file1}/storage/labels/{label_id}/pdf",
        headers=cab,
    )
    assert r.status_code == 404
    assert r.json()["code"] == "STORAGE_LABEL_NOT_FOUND"


def test_nada_pendiente(mundo, reloj_mfa, rol_completo, rol_almacen):
    datos = _pendiente(mundo, reloj_mfa, rol_completo, rol_almacen)
    cab = datos["cab"]
    file_id = datos["file_id"]

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/classify",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
        },
        headers=cab,
    )
    assert r.status_code == 200
    classification_id = r.json()["id"]

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/labels",
        json={"classification_id": classification_id},
        headers=cab,
    )
    assert r.status_code == 200

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/putaway",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
            "target_location_id": datos["l1"],
            "quantity": "10",
        },
        headers=cab,
    )
    assert r.status_code == 200

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/classify",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
        },
        headers=cab,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "STORAGE_NOTHING_PENDING"


def test_auditoria_etiqueta(mundo, reloj_mfa, rol_completo, rol_almacen):
    datos = _pendiente(mundo, reloj_mfa, rol_completo, rol_almacen)
    cab = datos["cab"]
    file_id = datos["file_id"]

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/classify",
        json={
            "receipt_id": datos["receipt_id"],
            "product_id": datos["product_id"],
            "state": "DISPONIBLE",
        },
        headers=cab,
    )
    assert r.status_code == 200
    classification_id = r.json()["id"]

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/storage/labels",
        json={"classification_id": classification_id},
        headers=cab,
    )
    assert r.status_code == 200
    label_id = r.json()["id"]

    with mundo.factory() as db:
        event = db.scalar(
            select(AuditEvent).where(
                AuditEvent.action == "STORAGE_LABEL_GENERATED",
                AuditEvent.entity_id == label_id,
            )
        )
        assert event is not None
