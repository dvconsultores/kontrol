"""Ubicaciones físicas de expedientes de importación (T-RL-A)."""
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.modules.imports.models import ImportFile
from app.modules.inventory import location_validation
from app.modules.inventory import service as inv_service
from app.modules.inventory.models import (
    InventoryBalance,
    InventoryLocationValidation,
    InventoryMovement,
)
from app.modules.master_data.models import CatalogItem
from app.modules.organization.models import WarehouseLocation
from app.modules.purchasing.models import GoodsReceipt


def file_receipts(db: Session, file: ImportFile) -> list[GoodsReceipt]:
    if file.order_id is None:
        return []
    return list(
        db.scalars(
            select(GoodsReceipt).where(
                GoodsReceipt.order_id == file.order_id,
                GoodsReceipt.company_id == file.company_id,
            )
        ).all()
    )


def attributed_rows(
    db: Session, file: ImportFile, receipts: list[GoodsReceipt] | None = None
) -> list[dict[str, Any]]:
    codes = {r.code: r for r in (receipts if receipts is not None else file_receipts(db, file))}
    if not codes:
        return []

    ubicacion_tipo = inv_service._get_movement_type_by_code_optional(
        db, file.company_id, "UBICACION"
    )
    reubicacion_tipo = inv_service._get_movement_type_by_code_optional(
        db, file.company_id, "REUBICACION"
    )
    tipo_ids = [t.id for t in (ubicacion_tipo, reubicacion_tipo) if t is not None]
    if not tipo_ids:
        return []

    movements = list(
        db.scalars(
            select(InventoryMovement).where(
                InventoryMovement.company_id == file.company_id,
                InventoryMovement.movement_type_id.in_(tipo_ids),
                InventoryMovement.document_ref.in_(codes.keys()),
                InventoryMovement.status == "POSTED",
                InventoryMovement.reversed_by_id.is_(None),
            )
        ).all()
    )
    if not movements:
        return []

    neto: dict[tuple[str, str, str, str | None, str], Decimal] = {}
    for movement in movements:
        if movement.document_ref is None or movement.product_id is None:
            continue
        if movement.target_location_id is not None and movement.target_state is not None:
            clave = (
                movement.document_ref,
                movement.warehouse_id,
                movement.product_id,
                movement.target_state,
                movement.target_location_id,
            )
            neto[clave] = neto.get(clave, Decimal("0")) + (
                movement.base_quantity
                if movement.base_quantity is not None
                else movement.quantity or Decimal("0")
            )
        if movement.source_location_id is not None and movement.source_state is not None:
            clave = (
                movement.document_ref,
                movement.warehouse_id,
                movement.product_id,
                movement.source_state,
                movement.source_location_id,
            )
            neto[clave] = neto.get(clave, Decimal("0")) - (
                movement.base_quantity
                if movement.base_quantity is not None
                else movement.quantity or Decimal("0")
            )

    product_ids = {clave[2] for clave in neto}
    products_by_id = {
        str(product.id): product
        for product in db.scalars(
            select(CatalogItem).where(CatalogItem.id.in_(product_ids))
        )
    } if product_ids else {}

    rows: list[dict[str, Any]] = []
    for clave_neto, total in neto.items():
        if total <= 0:
            continue
        receipt_code, warehouse_id, product_id, state, ubicacion_id = clave_neto
        receipt = codes[receipt_code]
        product = products_by_id.get(product_id)
        saldo = db.scalars(
            select(InventoryBalance).where(
                InventoryBalance.company_id == file.company_id,
                InventoryBalance.warehouse_id == warehouse_id,
                InventoryBalance.product_id == product_id,
                InventoryBalance.lot_id.is_(None),
                InventoryBalance.serial_id.is_(None),
                InventoryBalance.state == state,
                InventoryBalance.location_id == ubicacion_id,
            )
        ).first()
        on_hand = (
            str(inv_service._dec(saldo.qty_on_hand))
            if saldo is not None
            else "0"
        )
        ultima = db.scalars(
            select(InventoryLocationValidation)
            .where(
                InventoryLocationValidation.import_file_id == file.id,
                InventoryLocationValidation.receipt_id == receipt.id,
                InventoryLocationValidation.product_id == product_id,
                InventoryLocationValidation.state == state,
                InventoryLocationValidation.registered_location_id == ubicacion_id,
            )
            .order_by(InventoryLocationValidation.validated_at.desc())
            .limit(1)
        ).first()
        rows.append(
            {
                "receipt_id": str(receipt.id),
                "receipt_code": receipt.code,
                "warehouse_id": warehouse_id,
                "product_id": product_id,
                "product_name": product.name if product else None,
                "state": state,
                "lot_id": None,
                "serial_id": None,
                "location": location_validation.location_ref(db, ubicacion_id),
                "quantity": str(total),
                "on_hand_at_location": on_hand,
                "last_validation": (
                    location_validation.validation_dict(db, ultima)
                    if ultima is not None
                    else None
                ),
            }
        )

    rows.sort(
        key=lambda row: (
            row["receipt_code"] or "",
            row["product_name"] or "",
            row["location"]["code"] or "",
        )
    )
    return rows


def file_physical_locations(db: Session, file: ImportFile) -> dict[str, Any]:
    rows = attributed_rows(db, file)
    history = [
        location_validation.validation_dict(db, v)
        for v in db.scalars(
            select(InventoryLocationValidation)
            .where(InventoryLocationValidation.import_file_id == file.id)
            .order_by(InventoryLocationValidation.validated_at.desc())
        ).all()
    ]
    warehouse_ids = {row["warehouse_id"] for row in rows}
    locations_by_warehouse: dict[str, list[dict]] = {}
    if warehouse_ids:
        ubicaciones = list(
            db.scalars(
                select(WarehouseLocation)
                .where(
                    WarehouseLocation.company_id == file.company_id,
                    WarehouseLocation.warehouse_id.in_(warehouse_ids),
                    WarehouseLocation.status == "ACTIVE",
                )
                .order_by(WarehouseLocation.sequence, WarehouseLocation.code)
            ).all()
        )
        for warehouse_id in warehouse_ids:
            locations_by_warehouse[warehouse_id] = [
                location_validation.location_ref(db, str(location.id))
                for location in ubicaciones
                if location.warehouse_id == warehouse_id
            ]
    return {
        "rows": rows,
        "history": history,
        "locations_by_warehouse": locations_by_warehouse,
    }


def validate_for_file(
    db: Session,
    *,
    file: ImportFile,
    receipt_id: str,
    product_id: str,
    state: str,
    registered_location_id: str,
    observed_location_id: str,
    quantity: Any,
    actor_id: str,
) -> InventoryLocationValidation:
    receipts = file_receipts(db, file)
    receipt = next((r for r in receipts if str(r.id) == receipt_id), None)
    if receipt is None:
        raise NotFoundError(
            code="IMPORT_RECEIPT_NOT_IN_FILE",
            message="La recepción no pertenece a este expediente",
        )
    rows = attributed_rows(db, file, receipts)
    fila = next(
        (
            row
            for row in rows
            if row["receipt_id"] == receipt_id
            and row["product_id"] == product_id
            and row["state"] == state
            and row["location"]["id"] == registered_location_id
        ),
        None,
    )
    if fila is None or Decimal(fila["quantity"]) < Decimal(str(quantity)):
        raise ConflictError(
            code="IMPORT_LOCATION_NOT_ATTRIBUTED",
            message="Esa cantidad no está atribuida a esta recepción en esa ubicación.",
        )
    return location_validation.validate_location(
        db,
        company_id=file.company_id,
        warehouse_id=str(receipt.warehouse_id),
        product_id=product_id,
        registered_location_id=registered_location_id,
        observed_location_id=observed_location_id,
        quantity=quantity,
        state=state,
        actor_id=actor_id,
        import_file_id=str(file.id),
        receipt_id=str(receipt.id),
        document_ref=receipt.code,
    )
