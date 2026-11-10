"""Validación física de ubicación y reubicación por error (T-RL-A)."""
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.identity_access.models import User
from app.modules.inventory import service as inv_service
from app.modules.inventory import states as state_authority
from app.modules.inventory.models import (
    InventoryBalance,
    InventoryLocationValidation,
    InventoryMovement,
)
from app.modules.master_data import uom as uom_engine
from app.modules.master_data.models import CatalogItem
from app.modules.organization.models import WarehouseLocation
from app.modules.organization.structure import display_path


def location_ref(db: Session, location_id: str) -> dict:
    location = db.get(WarehouseLocation, location_id)
    if location is None:
        raise NotFoundError(code="LOCATION_NOT_FOUND", message="Ubicación no encontrada")
    return {
        "id": str(location.id),
        "code": location.code,
        "name": location.name,
        "path": display_path(db, location),
    }


def validate_location(
    db: Session,
    *,
    company_id: str,
    warehouse_id: str,
    product_id: str,
    registered_location_id: str,
    observed_location_id: str,
    quantity: Any,
    actor_id: str,
    state: str | None = None,
    lot_id: str | None = None,
    serial_id: str | None = None,
    import_file_id: str | None = None,
    receipt_id: str | None = None,
    document_ref: str | None = None,
) -> InventoryLocationValidation:
    estado = state_authority.assert_valid_state(state or state_authority.DEFAULT_STATE)
    cantidad = inv_service._dec(quantity)
    if cantidad <= 0:
        raise KontrolError(
            code="INVALID_QUANTITY",
            status_code=422,
            message="La cantidad validada debe ser mayor que cero.",
        )

    inv_service._require_warehouse(db, company_id, warehouse_id)
    inv_service._require_product(db, company_id, product_id)

    registrada = inv_service._require_location(db, company_id, registered_location_id)
    if registrada.warehouse_id != warehouse_id:
        raise ConflictError(
            code="LOCATION_OTHER_WAREHOUSE",
            message="La ubicación registrada pertenece a otro almacén.",
            details={
                "warehouse_id": warehouse_id,
                "location_warehouse_id": registrada.warehouse_id,
            },
        )

    inv_service.location_in_warehouse(
        db,
        company_id=company_id,
        warehouse_id=warehouse_id,
        location_id=observed_location_id,
    )

    # Bloqueo SIEMPRE en este orden (validaciones → saldo) para no abrazarse
    # con relocate_by_error.
    pendientes = db.scalars(
        select(InventoryLocationValidation)
        .where(
            InventoryLocationValidation.company_id == company_id,
            InventoryLocationValidation.warehouse_id == warehouse_id,
            InventoryLocationValidation.product_id == product_id,
            InventoryLocationValidation.lot_id.is_(None)
            if lot_id is None
            else InventoryLocationValidation.lot_id == lot_id,
            InventoryLocationValidation.serial_id.is_(None)
            if serial_id is None
            else InventoryLocationValidation.serial_id == serial_id,
            InventoryLocationValidation.state == estado,
            InventoryLocationValidation.registered_location_id == registered_location_id,
            InventoryLocationValidation.status == "PENDING",
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()
    for pendiente in pendientes:
        pendiente.status = "SUPERSEDED"

    saldo = inv_service.lock_balance(
        db,
        company_id=company_id,
        warehouse_id=warehouse_id,
        product_id=product_id,
        lot_id=lot_id,
        serial_id=serial_id,
        state=estado,
        location_id=registered_location_id,
    )

    existencia = inv_service._dec(saldo.qty_on_hand)
    if existencia <= 0:
        raise ConflictError(code="LOCATION_VALIDATION_NO_STOCK")
    if cantidad > existencia:
        raise ConflictError(
            code="INSUFFICIENT_LOCATION_QUANTITY",
            details={"requested": str(cantidad), "available": str(existencia)},
        )
    if serial_id is not None and cantidad != existencia:
        raise KontrolError(
            code="SERIAL_INDIVISIBLE",
            message="El artículo con serie solo puede reubicarse en cantidad indivisible",
            status_code=422,
        )

    result = "MATCH" if observed_location_id == registered_location_id else "MISMATCH"
    status = "CONFIRMED" if result == "MATCH" else "PENDING"
    validacion = InventoryLocationValidation(
        created_by=actor_id,
        company_id=company_id,
        warehouse_id=warehouse_id,
        product_id=product_id,
        lot_id=lot_id,
        serial_id=serial_id,
        state=estado,
        quantity=cantidad,
        registered_qty_snapshot=existencia,
        registered_location_id=registered_location_id,
        observed_location_id=observed_location_id,
        result=result,
        status=status,
        validated_at=datetime.now(UTC),
        validated_by=actor_id,
        import_file_id=import_file_id,
        receipt_id=receipt_id,
        document_ref=document_ref,
    )
    db.add(validacion)
    db.flush()

    action = (
        "INVENTORY_LOCATION_VALIDATED"
        if result == "MATCH"
        else "INVENTORY_LOCATION_MISMATCH_DETECTED"
    )
    inv_service._audit(
        db,
        action=action,
        entity_type="InventoryLocationValidation",
        entity_id=str(validacion.id),
        company_id=company_id,
        actor=actor_id,
        after={
            "validation_id": str(validacion.id),
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "registered_location_id": registered_location_id,
            "observed_location_id": observed_location_id,
            "quantity": str(cantidad),
            "state": estado,
            "import_file_id": import_file_id,
            "receipt_id": receipt_id,
        },
    )
    return validacion


def relocate_by_error(
    db: Session,
    *,
    company_id: str,
    validation_id: str,
    quantity: Any,
    reason: str,
    actor_id: str,
) -> InventoryLocationValidation:
    v = db.scalars(
        select(InventoryLocationValidation)
        .where(
            InventoryLocationValidation.id == validation_id,
            InventoryLocationValidation.company_id == company_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if v is None:
        raise NotFoundError(code="LOCATION_VALIDATION_NOT_FOUND", message="Validación no encontrada")
    if v.result != "MISMATCH":
        raise ConflictError(code="LOCATION_VALIDATION_NOT_MISMATCH")
    if v.status == "RELOCATED":
        raise ConflictError(code="LOCATION_VALIDATION_ALREADY_RELOCATED")
    if v.status == "SUPERSEDED":
        raise ConflictError(code="LOCATION_VALIDATION_SUPERSEDED")

    motivo = (reason or "").strip()
    if not motivo:
        raise KontrolError(
            code="RELOCATION_REASON_REQUIRED",
            message="El motivo de la reubicación es obligatorio",
            status_code=422,
        )
    cantidad = inv_service._dec(quantity)
    if cantidad <= 0:
        raise KontrolError(
            code="INVALID_QUANTITY",
            message="La cantidad a reubicar debe ser mayor que cero",
            status_code=422,
        )
    if cantidad > inv_service._dec(v.quantity):
        raise ConflictError(code="RELOCATION_QUANTITY_EXCEEDS_VALIDATION")

    inv_service.location_in_warehouse(
        db,
        company_id=company_id,
        warehouse_id=v.warehouse_id,
        location_id=v.observed_location_id,
    )

    claves = sorted(
        {v.registered_location_id, v.observed_location_id},
        key=lambda x: (x is not None, x or ""),
    )
    saldos = {
        clave: inv_service.lock_balance(
            db,
            company_id=company_id,
            warehouse_id=v.warehouse_id,
            product_id=v.product_id,
            lot_id=v.lot_id,
            serial_id=v.serial_id,
            state=v.state,
            location_id=clave,
        )
        for clave in claves
    }
    origen = saldos[v.registered_location_id]
    destino = saldos[v.observed_location_id]

    existencia = inv_service._dec(origen.qty_on_hand)
    if existencia != inv_service._dec(v.registered_qty_snapshot):
        raise ConflictError(
            code="LOCATION_VALIDATION_STALE",
            message="La existencia en la ubicación registrada cambió después de la validación; valide de nuevo.",
            details={
                "snapshot": str(v.registered_qty_snapshot),
                "current": str(existencia),
            },
        )
    if cantidad > existencia:
        raise ConflictError(
            code="INSUFFICIENT_LOCATION_QUANTITY",
            details={"requested": str(cantidad), "available": str(existencia)},
        )
    if v.serial_id is not None and cantidad != existencia:
        raise KontrolError(
            code="SERIAL_INDIVISIBLE",
            message="El artículo con serie solo puede reubicarse en cantidad indivisible",
            status_code=422,
        )

    tipo = inv_service._get_movement_type_by_code(db, company_id, "REUBICACION")
    movimiento = InventoryMovement(
        company_id=company_id,
        warehouse_id=v.warehouse_id,
        location_id=v.observed_location_id,
        product_id=v.product_id,
        movement_type_id=str(tipo.id),
        quantity=cantidad,
        base_quantity=cantidad,
        currency="VED",
        document_ref=v.document_ref,
        occurred_at=datetime.now(UTC),
        status="POSTED",
        created_by=actor_id,
        source_state=v.state,
        target_state=v.state,
        source_location_id=v.registered_location_id,
        target_location_id=v.observed_location_id,
        uom_source=uom_engine.SOURCE_CAPTURED,
    )
    db.add(movimiento)

    origen.qty_on_hand = existencia - cantidad
    destino.qty_on_hand = inv_service._dec(destino.qty_on_hand) + cantidad
    inv_service._refresh_available(origen)
    inv_service._refresh_available(destino)
    db.flush()

    v.status = "RELOCATED"
    v.movement_id = str(movimiento.id)
    v.relocated_quantity = cantidad
    v.relocation_reason = motivo
    v.relocated_at = datetime.now(UTC)
    v.relocated_by = actor_id
    db.flush()

    inv_service._audit(
        db,
        action="INVENTORY_RELOCATED_BY_ERROR",
        entity_type="InventoryMovement",
        entity_id=str(movimiento.id),
        company_id=company_id,
        actor=actor_id,
        before={"location_id": v.registered_location_id, "qty": str(existencia)},
        after={
            "validation_id": str(v.id),
            "product_id": v.product_id,
            "warehouse_id": v.warehouse_id,
            "source_location_id": v.registered_location_id,
            "target_location_id": v.observed_location_id,
            "quantity": str(cantidad),
            "state": v.state,
            "import_file_id": v.import_file_id,
            "receipt_id": v.receipt_id,
        },
        reason=motivo,
    )
    return v


def is_stale(db: Session, v: InventoryLocationValidation) -> bool:
    if v.status != "PENDING":
        return False
    saldo = db.scalars(
        select(InventoryBalance).where(
            InventoryBalance.company_id == v.company_id,
            InventoryBalance.warehouse_id == v.warehouse_id,
            InventoryBalance.product_id == v.product_id,
            InventoryBalance.lot_id.is_(None) if v.lot_id is None else InventoryBalance.lot_id == v.lot_id,
            InventoryBalance.serial_id.is_(None)
            if v.serial_id is None
            else InventoryBalance.serial_id == v.serial_id,
            InventoryBalance.state == v.state,
            InventoryBalance.location_id == v.registered_location_id,
        )
    ).first()
    existencia = inv_service._dec(saldo.qty_on_hand) if saldo is not None else Decimal("0")
    return existencia != inv_service._dec(v.registered_qty_snapshot)


def validation_dict(db: Session, v: InventoryLocationValidation) -> dict:
    producto = db.get(CatalogItem, v.product_id)
    usuario = db.get(User, v.validated_by) if v.validated_by else None
    relocation = None
    if v.movement_id is not None:
        reubicador = db.get(User, v.relocated_by) if v.relocated_by else None
        relocation = {
            "movement_id": v.movement_id,
            "quantity": str(v.relocated_quantity),
            "reason": v.relocation_reason,
            "relocated_at": v.relocated_at.isoformat() if v.relocated_at else None,
            "relocated_by_name": reubicador.username if reubicador else None,
            "source_location": location_ref(db, v.registered_location_id),
            "target_location": location_ref(db, v.observed_location_id),
        }
    return {
        "id": str(v.id),
        "result": v.result,
        "status": v.status,
        "stale": is_stale(db, v),
        "warehouse_id": v.warehouse_id,
        "product_id": v.product_id,
        "product_name": producto.name if producto else None,
        "state": v.state,
        "lot_id": v.lot_id,
        "serial_id": v.serial_id,
        "quantity": str(v.quantity),
        "registered_location": location_ref(db, v.registered_location_id),
        "observed_location": location_ref(db, v.observed_location_id),
        "validated_at": v.validated_at.isoformat() if v.validated_at else None,
        "validated_by_name": usuario.username if usuario else None,
        "import_file_id": v.import_file_id,
        "receipt_id": v.receipt_id,
        "receipt_code": v.document_ref,
        "relocation": relocation,
    }


def list_validations(
    db: Session,
    *,
    company_id: str,
    warehouse_id: str | None = None,
    product_id: str | None = None,
    location_id: str | None = None,
) -> list[InventoryLocationValidation]:
    query = select(InventoryLocationValidation).where(
        InventoryLocationValidation.company_id == company_id
    )
    if warehouse_id is not None:
        query = query.where(InventoryLocationValidation.warehouse_id == warehouse_id)
    if product_id is not None:
        query = query.where(InventoryLocationValidation.product_id == product_id)
    if location_id is not None:
        query = query.where(
            or_(
                InventoryLocationValidation.registered_location_id == location_id,
                InventoryLocationValidation.observed_location_id == location_id,
            )
        )
    return list(
        db.scalars(
            query.order_by(InventoryLocationValidation.validated_at.desc())
        ).all()
    )
