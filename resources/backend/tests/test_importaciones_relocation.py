# ruff: noqa: E402, F811, F401, I001
import os
import threading
import uuid
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
    rol_solo_lectura,
)

from app.core.errors import ConflictError, KontrolError
from app.modules.audit.models import AuditEvent
from app.modules.imports.models import ImportFile
from app.modules.imports.service import get_file
from app.modules.inventory import location_validation
from app.modules.inventory import service as inventory_service
from app.modules.inventory.models import (
    CostLayer,
    InventoryBalance,
    InventoryLocationValidation,
    InventoryMovement,
    MovementType,
)
from app.modules.master_data.models import CatalogItem, Party
from app.modules.organization.models import Company, Warehouse, WarehouseLocation
from app.modules.purchasing.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrderLine,
)
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
            name="Almacenista Validación",
            company_id=None,
            permissions=[
                "maestros:view",
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


def _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen, cantidad=10) -> dict:
    cab_compras, file_id, _ = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    cab = _operador(mundo, reloj_mfa, rol_almacen)
    cab["company_id"] = str(mundo.company_id)

    with mundo.factory() as db:
        file = db.get(ImportFile, file_id)
        warehouse_id = _almacen(mundo, mundo.company_id)
        locations = [
            WarehouseLocation(
                company_id=mundo.company_id,
                warehouse_id=warehouse_id,
                code=f"A-{uuid4().hex[:8]}",
                name="Rack A",
                sequence=1,
                status="ACTIVE",
            ),
            WarehouseLocation(
                company_id=mundo.company_id,
                warehouse_id=warehouse_id,
                code=f"B-{uuid4().hex[:8]}",
                name="Rack B",
                sequence=2,
                status="ACTIVE",
            ),
            WarehouseLocation(
                company_id=mundo.company_id,
                warehouse_id=warehouse_id,
                code=f"C-{uuid4().hex[:8]}",
                name="Rack C",
                sequence=3,
                status="ACTIVE",
            ),
        ]
        db.add_all(locations)
        db.flush()
        a, b, c = locations[0].id, locations[1].id, locations[2].id

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
            quantity_ordered=cantidad,
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
        )
        db.add(receipt)
        db.flush()

        line = GoodsReceiptLine(
            receipt_id=receipt.id,
            order_line_id=pol.id,
            product_id=product.id,
            quantity_received=cantidad,
            quantity_accepted=cantidad,
            quantity_rejected=0,
            counted_base_quantity=cantidad,
            damaged_quantity=0,
            overage_base_quantity=0,
            count_difference_kinds=None,
            physical_condition="BUENO",
        )
        db.add(line)

        tipo = inventory_service._get_movement_type_by_code(
            db, mundo.company_id, "ENTRADA_RECEPCION"
        )
        inventory_service.record_movement(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse_id,
            product_id=str(product.id),
            movement_type_id=str(tipo.id),
            quantity=Decimal(cantidad),
            unit_cost=Decimal("5.00"),
            currency="VED",
            document_ref=f"RECEIPT:{receipt.id}",
            actor=mundo.admin_id,
        )
        inventory_service.putaway(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse_id,
            product_id=str(product.id),
            target_location_id=str(a),
            quantity=Decimal(cantidad),
            document_ref=receipt.code,
            actor=mundo.admin_id,
        )
        db.commit()
        return {
            "cab": cab,
            "cab_compras": cab_compras,
            "company_id": str(mundo.company_id),
            "file_id": str(file_id),
            "receipt_id": str(receipt.id),
            "receipt_code": receipt.code,
            "warehouse_id": warehouse_id,
            "product_id": str(product.id),
            "a": str(a),
            "b": str(b),
            "c": str(c),
        }


def _validar(mundo, cab, u, observada, cantidad="10"):
    return mundo.client.post(
        f"{API}/importaciones/{u['file_id']}/physical-locations/validate",
        json={
            "receipt_id": u["receipt_id"],
            "product_id": u["product_id"],
            "registered_location_id": u["a"],
            "observed_location_id": observada,
            "quantity": cantidad,
            "state": "DISPONIBLE",
        },
        headers=cab,
    )


def _reubicar(mundo, cab, validation_id, cantidad="10", motivo="Error de ubicación"):
    return mundo.client.post(
        f"{API}/inventory/location-validations/{validation_id}/relocate",
        json={"quantity": cantidad, "reason": motivo},
        headers=cab,
    )


def _saldo(db, u, ubicacion):
    saldo = db.scalars(
        select(InventoryBalance).where(
            InventoryBalance.company_id == u["company_id"],
            InventoryBalance.warehouse_id == u["warehouse_id"],
            InventoryBalance.product_id == u["product_id"],
            InventoryBalance.state == "DISPONIBLE",
            InventoryBalance.location_id == ubicacion,
            InventoryBalance.lot_id.is_(None),
            InventoryBalance.serial_id.is_(None),
        )
    ).first()
    return Decimal(saldo.qty_on_hand) if saldo is not None else Decimal("0")


def _vista(mundo, cab, file_id):
    return mundo.client.get(
        f"{API}/importaciones/{file_id}/physical-locations", headers=cab
    ).json()


def test_a_match(mundo, reloj_mfa, rol_completo, rol_almacen):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    r = _validar(mundo, u["cab"], u, u["a"])
    assert r.status_code == 200
    data = r.json()
    assert data["result"] == "MATCH"
    assert data["status"] == "CONFIRMED"
    assert data["relocation"] is None
    with mundo.factory() as db:
        movs = list(
            db.scalars(
                select(InventoryMovement).where(
                    InventoryMovement.document_ref == u["receipt_code"],
                    InventoryMovement.status == "POSTED",
                )
            ).all()
        )
        reubicaciones = [
            m
            for m in movs
            if m.movement_type_id
            == str(
                inventory_service._get_movement_type_by_code(
                    db, mundo.company_id, "REUBICACION"
                ).id
            )
        ]
        assert reubicaciones == []
        assert _saldo(db, u, u["a"]) == Decimal("10")
        assert _saldo(db, u, u["b"]) == Decimal("0")
        evento = db.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "INVENTORY_LOCATION_VALIDATED",
                AuditEvent.entity_id == data["id"],
            )
        ).first()
        assert evento is not None


def test_b_mismatch_no_mueve(mundo, reloj_mfa, rol_completo, rol_almacen):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    r = _validar(mundo, u["cab"], u, u["b"])
    assert r.status_code == 200
    data = r.json()
    assert data["result"] == "MISMATCH"
    assert data["status"] == "PENDING"
    assert data["stale"] is False
    with mundo.factory() as db:
        assert _saldo(db, u, u["a"]) == Decimal("10")
        assert _saldo(db, u, u["b"]) == Decimal("0")
        evento = db.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "INVENTORY_LOCATION_MISMATCH_DETECTED",
                AuditEvent.entity_id == data["id"],
            )
        ).first()
        assert evento is not None


def test_c_reubicacion_completa(mundo, reloj_mfa, rol_completo, rol_almacen):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    v = _validar(mundo, u["cab"], u, u["b"]).json()
    r = _reubicar(mundo, u["cab"], v["id"])
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "RELOCATED"
    assert data["relocation"]["source_location"]["code"].startswith("A-")
    assert data["relocation"]["target_location"]["code"].startswith("B-")
    with mundo.factory() as db:
        assert _saldo(db, u, u["a"]) == Decimal("0")
        assert _saldo(db, u, u["b"]) == Decimal("10")
        total_antes = Decimal("0")
        for ubicacion in (u["a"], u["b"], u["c"], None):
            saldo = db.scalars(
                select(InventoryBalance).where(
                    InventoryBalance.company_id == u["company_id"],
                    InventoryBalance.warehouse_id == u["warehouse_id"],
                    InventoryBalance.product_id == u["product_id"],
                    InventoryBalance.location_id == ubicacion,
                )
            ).first()
            if saldo is not None:
                total_antes += Decimal(saldo.qty_on_hand)
        movimiento = db.get(InventoryMovement, data["relocation"]["movement_id"])
        assert movimiento is not None
        assert movimiento.source_location_id == u["a"]
        assert movimiento.target_location_id == u["b"]
        assert movimiento.source_state == "DISPONIBLE"
        assert movimiento.target_state == "DISPONIBLE"
        assert movimiento.warehouse_id == u["warehouse_id"]
        assert movimiento.document_ref == u["receipt_code"]
        assert movimiento.unit_cost is None
        tipo = db.get(MovementType, movimiento.movement_type_id)
        assert tipo.code == "REUBICACION"
        total_despues = Decimal("0")
        for ubicacion in (u["a"], u["b"], u["c"], None):
            saldo = db.scalars(
                select(InventoryBalance).where(
                    InventoryBalance.company_id == u["company_id"],
                    InventoryBalance.warehouse_id == u["warehouse_id"],
                    InventoryBalance.product_id == u["product_id"],
                    InventoryBalance.location_id == ubicacion,
                )
            ).first()
            if saldo is not None:
                total_despues += Decimal(saldo.qty_on_hand)
        assert total_antes == total_despues
        evento = db.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "INVENTORY_RELOCATED_BY_ERROR",
                AuditEvent.entity_id == str(movimiento.id),
            )
        ).first()
        assert evento is not None
        assert evento.reason == "Error de ubicación"
    detalle = mundo.client.get(
        f"{API}/importaciones/{u['file_id']}", headers=u["cab"]
    ).json()
    logistics = detalle["logistics"]
    assert len(logistics["locations"]) == 1
    assert u["b"] not in logistics["locations"][0]["location_label"]
    assert "B-" in logistics["locations"][0]["location_label"]
    assert Decimal(logistics["locations"][0]["quantity"]) == Decimal("10")
    assert Decimal(logistics["quantities"][0]["located"]) == Decimal("10")
    vista = _vista(mundo, u["cab"], u["file_id"])
    assert len(vista["rows"]) == 1
    assert vista["rows"][0]["location"]["id"] == u["b"]
    assert len(vista["history"]) == 1
    assert vista["history"][0]["relocation"] is not None
    assert not uuid_regex.search(vista["history"][0]["validated_by_name"])


uuid_regex = __import__("re").compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)


def test_d_costo_neutral(mundo, reloj_mfa, rol_completo, rol_almacen):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    with mundo.factory() as db:
        valuacion_antes = inventory_service.valuation(
            db, company_id=mundo.company_id, product_id=u["product_id"], warehouse_id=u["warehouse_id"]
        )
        capas_antes = list(
            db.scalars(
                select(CostLayer).where(
                    CostLayer.product_id == u["product_id"],
                    CostLayer.company_id == mundo.company_id,
                )
            ).all()
        )
        snapshot_antes = [
            (str(c.id), Decimal(c.quantity_remaining), c.unit_cost, c.landed_cost)
            for c in capas_antes
        ]
    v = _validar(mundo, u["cab"], u, u["b"]).json()
    _reubicar(mundo, u["cab"], v["id"])
    with mundo.factory() as db:
        valuacion_despues = inventory_service.valuation(
            db, company_id=mundo.company_id, product_id=u["product_id"], warehouse_id=u["warehouse_id"]
        )
        assert valuacion_antes == valuacion_despues
        capas_despues = list(
            db.scalars(
                select(CostLayer).where(
                    CostLayer.product_id == u["product_id"],
                    CostLayer.company_id == mundo.company_id,
                )
            ).all()
        )
        snapshot_despues = [
            (str(c.id), Decimal(c.quantity_remaining), c.unit_cost, c.landed_cost)
            for c in capas_despues
        ]
        assert snapshot_antes == snapshot_despues


def test_e_reservas_preservadas(mundo, reloj_mfa, rol_completo, rol_almacen):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    with mundo.factory() as db:
        inventory_service.reserve(
            db,
            company_id=mundo.company_id,
            source_document="OV-RL",
            product_id=u["product_id"],
            warehouse_id=u["warehouse_id"],
            quantity=Decimal("3"),
            actor=mundo.admin_id,
        )
        db.commit()
    v = _validar(mundo, u["cab"], u, u["b"]).json()
    _reubicar(mundo, u["cab"], v["id"])
    with mundo.factory() as db:
        ancla = db.scalars(
            select(InventoryBalance).where(
                InventoryBalance.company_id == u["company_id"],
                InventoryBalance.warehouse_id == u["warehouse_id"],
                InventoryBalance.product_id == u["product_id"],
                InventoryBalance.location_id.is_(None),
                InventoryBalance.state == "DISPONIBLE",
            )
        ).first()
        assert ancla is not None
        assert Decimal(ancla.qty_reserved) == Decimal("3")
        for ubicacion in (u["a"], u["b"]):
            saldo = db.scalars(
                select(InventoryBalance).where(
                    InventoryBalance.company_id == u["company_id"],
                    InventoryBalance.warehouse_id == u["warehouse_id"],
                    InventoryBalance.product_id == u["product_id"],
                    InventoryBalance.location_id == ubicacion,
                    InventoryBalance.state == "DISPONIBLE",
                )
            ).first()
            assert saldo is not None
            assert Decimal(saldo.qty_reserved) == Decimal("0")


def test_f_parcial(mundo, reloj_mfa, rol_completo, rol_almacen):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    v = _validar(mundo, u["cab"], u, u["b"], cantidad="4").json()
    r = _reubicar(mundo, u["cab"], v["id"], cantidad="4")
    assert r.status_code == 200
    with mundo.factory() as db:
        assert _saldo(db, u, u["a"]) == Decimal("6")
        assert _saldo(db, u, u["b"]) == Decimal("4")


def test_g_cantidades_invalidas(mundo, reloj_mfa, rol_completo, rol_almacen):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    r = _validar(mundo, u["cab"], u, u["b"], cantidad="11")
    assert r.status_code == 409
    assert r.json()["code"] == "IMPORT_LOCATION_NOT_ATTRIBUTED"
    r = mundo.client.post(
        f"{API}/inventory/location-validations",
        json={
            "warehouse_id": u["warehouse_id"],
            "product_id": u["product_id"],
            "registered_location_id": u["a"],
            "observed_location_id": u["b"],
            "quantity": "11",
            "state": "DISPONIBLE",
        },
        headers=u["cab"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "INSUFFICIENT_LOCATION_QUANTITY"
    r = _validar(mundo, u["cab"], u, u["b"], cantidad="0")
    assert r.status_code == 422
    assert r.json()["code"] == "INVALID_QUANTITY"
    v = _validar(mundo, u["cab"], u, u["b"], cantidad="4").json()
    r = _reubicar(mundo, u["cab"], v["id"], cantidad="5")
    assert r.status_code == 409
    assert r.json()["code"] == "RELOCATION_QUANTITY_EXCEEDS_VALIDATION"


def test_h_validacion_vencida(mundo, reloj_mfa, rol_completo, rol_almacen):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    v = _validar(mundo, u["cab"], u, u["b"]).json()
    with mundo.factory() as db:
        inventory_service.putaway(
            db,
            company_id=mundo.company_id,
            warehouse_id=u["warehouse_id"],
            product_id=u["product_id"],
            source_location_id=u["a"],
            target_location_id=u["c"],
            quantity=Decimal("2"),
            document_ref=u["receipt_code"],
            actor=mundo.admin_id,
        )
        db.commit()
    r = _reubicar(mundo, u["cab"], v["id"])
    assert r.status_code == 409
    assert r.json()["code"] == "LOCATION_VALIDATION_STALE"
    with mundo.factory() as db:
        assert _saldo(db, u, u["a"]) == Decimal("8")
        assert _saldo(db, u, u["b"]) == Decimal("0")
        assert _saldo(db, u, u["c"]) == Decimal("2")
    nueva = _validar(mundo, u["cab"], u, u["b"], cantidad="8").json()
    assert nueva["status"] == "PENDING"
    with mundo.factory() as db:
        anterior = db.get(InventoryLocationValidation, v["id"])
        assert anterior.status == "SUPERSEDED"
    r = _reubicar(mundo, u["cab"], v["id"])
    assert r.status_code == 409
    assert r.json()["code"] == "LOCATION_VALIDATION_SUPERSEDED"


def test_i_doble_reubicacion(mundo, reloj_mfa, rol_completo, rol_almacen):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    v = _validar(mundo, u["cab"], u, u["b"]).json()
    r1 = _reubicar(mundo, u["cab"], v["id"])
    assert r1.status_code == 200
    r2 = _reubicar(mundo, u["cab"], v["id"])
    assert r2.status_code == 409
    assert r2.json()["code"] == "LOCATION_VALIDATION_ALREADY_RELOCATED"
    with mundo.factory() as db:
        assert _saldo(db, u, u["a"]) == Decimal("0")
        assert _saldo(db, u, u["b"]) == Decimal("10")


def test_j_reubicar_match_es_rechazado(mundo, reloj_mfa, rol_completo, rol_almacen):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    v = _validar(mundo, u["cab"], u, u["a"]).json()
    r = _reubicar(mundo, u["cab"], v["id"])
    assert r.status_code == 409
    assert r.json()["code"] == "LOCATION_VALIDATION_NOT_MISMATCH"


def test_k_motivo_obligatorio(mundo, reloj_mfa, rol_completo, rol_almacen):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    v = _validar(mundo, u["cab"], u, u["b"]).json()
    r = _reubicar(mundo, u["cab"], v["id"], motivo="   ")
    assert r.status_code == 422
    assert r.json()["code"] == "RELOCATION_REASON_REQUIRED"
    with mundo.factory() as db:
        validacion = db.get(InventoryLocationValidation, v["id"])
        assert validacion.status == "PENDING"


def test_l_permisos(mundo, reloj_mfa, rol_completo, rol_almacen, rol_solo_lectura):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    r = mundo.client.get(
        f"{API}/importaciones/{u['file_id']}/physical-locations",
        headers=u["cab_compras"],
    )
    assert r.status_code == 200
    r = _validar(mundo, u["cab_compras"], u, u["b"])
    assert r.status_code == 403
    v = _validar(mundo, u["cab"], u, u["b"]).json()
    r = _reubicar(mundo, u["cab_compras"], v["id"])
    assert r.status_code == 403
    cab_lectura = _operador(mundo, reloj_mfa, rol_solo_lectura)
    r = _validar(mundo, cab_lectura, u, u["b"])
    assert r.status_code == 403


def test_m_ubicaciones_invalidas(mundo, reloj_mfa, rol_completo, rol_almacen):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    inexistente = str(uuid4())
    r = _validar(mundo, u["cab"], u, inexistente)
    assert r.status_code == 404
    with mundo.factory() as db:
        otro_almacen = Warehouse(
            company_id=mundo.company_id,
            code=f"WH-{uuid4().hex[:8]}",
            name="Otro almacén",
            status="ACTIVE",
        )
        db.add(otro_almacen)
        db.flush()
        ubicacion_otro_almacen = WarehouseLocation(
            company_id=mundo.company_id,
            warehouse_id=str(otro_almacen.id),
            code=f"X-{uuid4().hex[:8]}",
            name="X",
            sequence=1,
            status="ACTIVE",
        )
        db.add(ubicacion_otro_almacen)
        db.flush()
        ubicacion_otro_almacen_id = str(ubicacion_otro_almacen.id)
        inactiva = WarehouseLocation(
            company_id=mundo.company_id,
            warehouse_id=u["warehouse_id"],
            code=f"I-{uuid4().hex[:8]}",
            name="Inactiva",
            sequence=4,
            status="INACTIVE",
        )
        db.add(inactiva)
        db.flush()
        inactiva_id = str(inactiva.id)
        db.commit()
    r = _validar(mundo, u["cab"], u, ubicacion_otro_almacen_id)
    assert r.status_code == 409
    assert r.json()["code"] == "LOCATION_OTHER_WAREHOUSE"
    r = _validar(mundo, u["cab"], u, inactiva_id)
    assert r.status_code == 409
    assert r.json()["code"] == "LOCATION_NOT_ELIGIBLE"
    with mundo.factory() as db:
        other_company_id = db.scalar(
            select(Company.id).where(Company.tenant_id == mundo.tenant_b_id)
        )
        almacen_b = Warehouse(
            company_id=other_company_id,
            code=f"WHB-{uuid4().hex[:8]}",
            name="Almacén B",
            status="ACTIVE",
        )
        db.add(almacen_b)
        db.flush()
        ubicacion_b = WarehouseLocation(
            company_id=other_company_id,
            warehouse_id=str(almacen_b.id),
            code=f"B-{uuid4().hex[:8]}",
            name="Ubicación B",
            sequence=1,
            status="ACTIVE",
        )
        db.add(ubicacion_b)
        db.commit()
        ubicacion_b_id = str(ubicacion_b.id)
    r = _validar(mundo, u["cab"], u, ubicacion_b_id)
    assert r.status_code == 404
    with mundo.factory() as db:
        assert _saldo(db, u, u["a"]) == Decimal("10")
        assert _saldo(db, u, u["b"]) == Decimal("0")
        total = db.scalar(
            select(InventoryLocationValidation.id).where(
                InventoryLocationValidation.product_id == u["product_id"]
            )
        )
        assert total is None


def test_n_aislamiento(mundo, reloj_mfa, rol_completo, rol_almacen):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    r = _reubicar(mundo, u["cab"], str(uuid4()))
    assert r.status_code == 404
    assert r.json()["code"] == "LOCATION_VALIDATION_NOT_FOUND"
    u2 = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    r = mundo.client.post(
        f"{API}/importaciones/{u['file_id']}/physical-locations/validate",
        json={
            "receipt_id": u2["receipt_id"],
            "product_id": u2["product_id"],
            "registered_location_id": u2["a"],
            "observed_location_id": u2["b"],
            "quantity": "10",
            "state": "DISPONIBLE",
        },
        headers=u["cab"],
    )
    assert r.status_code == 404
    assert r.json()["code"] == "IMPORT_RECEIPT_NOT_IN_FILE"
    with mundo.factory() as db:
        other_company_id = db.scalar(
            select(Company.id).where(Company.tenant_id == mundo.tenant_b_id)
        )
        proveedor_externo = Party(
            company_id=other_company_id,
            code=f"PROV-{uuid4().hex[:8]}",
            name="Proveedor externo",
            person_type="JURIDICA",
            roles=["SUPPLIER"],
        )
        db.add(proveedor_externo)
        db.flush()
        file_externo = ImportFile(
            company_id=other_company_id,
            code=f"IMP-{uuid4().hex[:12]}",
            supplier_id=str(proveedor_externo.id),
            currency="VED",
            status="NEGOTIATING",
        )
        db.add(file_externo)
        db.commit()
        file_externo_id = str(file_externo.id)
    r = mundo.client.get(
        f"{API}/importaciones/{file_externo_id}/physical-locations",
        headers=u["cab"],
    )
    assert r.status_code == 404
    assert r.json()["code"] == "IMPORT_NOT_FOUND"


def test_o_no_atribuida(mundo, reloj_mfa, rol_completo, rol_almacen):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    r = mundo.client.post(
        f"{API}/importaciones/{u['file_id']}/physical-locations/validate",
        json={
            "receipt_id": u["receipt_id"],
            "product_id": u["product_id"],
            "registered_location_id": u["b"],
            "observed_location_id": u["a"],
            "quantity": "10",
            "state": "DISPONIBLE",
        },
        headers=u["cab"],
    )
    assert r.status_code == 409
    assert r.json()["code"] == "IMPORT_LOCATION_NOT_ATTRIBUTED"


def test_p_serie_indivisible(mundo, reloj_mfa, rol_completo, rol_almacen):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    serial = str(uuid4())
    with mundo.factory() as db:
        saldo = inventory_service.lock_balance(
            db,
            company_id=mundo.company_id,
            warehouse_id=u["warehouse_id"],
            product_id=u["product_id"],
            serial_id=serial,
            state="DISPONIBLE",
            location_id=u["a"],
        )
        saldo.qty_on_hand = Decimal("1")
        saldo.qty_available = Decimal("1")
        db.commit()
        try:
            location_validation.validate_location(
                db,
                company_id=mundo.company_id,
                warehouse_id=u["warehouse_id"],
                product_id=u["product_id"],
                registered_location_id=u["a"],
                observed_location_id=u["a"],
                quantity=Decimal("0.5"),
                actor_id=mundo.admin_id,
                serial_id=serial,
            )
            raise AssertionError("Se esperaba KontrolError")
        except KontrolError as e:
            assert e.code == "SERIAL_INDIVISIBLE"


def test_q_recompute_reproduce(mundo, reloj_mfa, rol_completo, rol_almacen):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    v = _validar(mundo, u["cab"], u, u["b"]).json()
    _reubicar(mundo, u["cab"], v["id"])
    with mundo.factory() as db:
        inventory_service.recompute_balances(db, company_id=mundo.company_id)
        db.commit()
        assert _saldo(db, u, u["a"]) == Decimal("0")
        assert _saldo(db, u, u["b"]) == Decimal("10")


@pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="Concurrencia solo verificable en PostgreSQL",
)
def test_r_concurrencia(mundo, reloj_mfa, rol_completo, rol_almacen):
    u = _ubicado(mundo, reloj_mfa, rol_completo, rol_almacen)
    v = _validar(mundo, u["cab"], u, u["b"]).json()

    resultados = []
    lock = threading.Lock()

    def _trabajador():
        with mundo.factory() as db:
            try:
                location_validation.relocate_by_error(
                    db,
                    company_id=mundo.company_id,
                    validation_id=v["id"],
                    quantity=Decimal("10"),
                    reason="Error de ubicación",
                    actor_id=mundo.admin_id,
                )
                db.commit()
                with lock:
                    resultados.append(("ok",))
            except ConflictError as e:
                db.rollback()
                with lock:
                    resultados.append(("conflict", e.code))

    hilos = [threading.Thread(target=_trabajador) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    assert len(resultados) == 2
    assert sorted(resultado[0] for resultado in resultados) == ["conflict", "ok"]
    conflictos = [r for r in resultados if r[0] == "conflict"]
    assert conflictos[0][1] == "LOCATION_VALIDATION_ALREADY_RELOCATED"
    with mundo.factory() as db:
        assert _saldo(db, u, u["a"]) == Decimal("0")
        assert _saldo(db, u, u["b"]) == Decimal("10")
