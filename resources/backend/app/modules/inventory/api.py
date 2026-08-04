"""API de inventario y logística (003-inventario-logistica).

Endpoints REST `/inventory/*` + API de integración v1 para 004/005
(`/operations/*`). Convenciones heredadas de 001 (DOC-03 §14): errores
uniformes, `allowed_actions` en backend, transiciones explícitas.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, require_write_allowed
from app.core.errors import NotFoundError
from app.modules.identity_access.models import User
from app.modules.inventory import service as inv_service
from app.modules.inventory.models import (
    CostingProfile,
    CostLayer,
    InventoryAdjustment,
    InventoryBalance,
    InventoryLot,
    InventoryMovement,
    MovementType,
    ProductSerial,
    Reservation,
    StockCount,
    StockCountLine,
    Transfer,
    TransferLine,
)

router = APIRouter(prefix="/inventory", tags=["inventario"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class MovementTypeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    direction: str = Field(pattern="^(IN|OUT|INTERNAL)$")
    global_scope: bool = False


class MovementCreate(BaseModel):
    warehouse_id: str
    product_id: str
    movement_type_id: str
    quantity: float
    unit_cost: float | None = None
    currency: str = "VED"
    fiscal_rate: float | None = None
    document_ref: str | None = None
    location_id: str | None = None
    idempotency_key: str | None = None


class ReverseBody(BaseModel):
    movement_id: str
    reason: str | None = None


class LotCreate(BaseModel):
    product_id: str
    lot_number: str = Field(min_length=1, max_length=120)
    manufacture_date: date | None = None
    expiry_date: date | None = None
    supplier_id: str | None = None
    receipt_ref: str | None = None


class SerialCreate(BaseModel):
    product_id: str
    serial: str = Field(min_length=1, max_length=120)
    imei1: str | None = None
    imei2: str | None = None
    mac: str | None = None
    lot_id: str | None = None
    warehouse_id: str | None = None


class TransitionBody(BaseModel):
    target: str


class ReserveBody(BaseModel):
    source_document: str | None = None
    product_id: str
    warehouse_id: str
    quantity: float = Field(gt=0)
    lot_id: str | None = None
    serial_id: str | None = None
    expires_in_days: int | None = None


class TransferLineCreate(BaseModel):
    product_id: str
    quantity_sent: float = Field(gt=0)
    lot_id: str | None = None
    serial_id: str | None = None


class TransferCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    origin_warehouse_id: str
    destination_warehouse_id: str
    request_ref: str | None = None
    lines: list[TransferLineCreate] = Field(min_length=1)


class ReceiptBody(BaseModel):
    receipt_ref: str | None = None
    received: dict[str, float] | None = None


class CountCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    warehouse_id: str
    plan_ref: str | None = None
    scope: list = Field(default_factory=list)
    freeze_policy: str = "PER_PRODUCT"


class CountLineCreate(BaseModel):
    product_id: str
    expected_qty: float
    counted_qty: float | None = None
    location_id: str | None = None
    lot_id: str | None = None


class AdjustmentCreate(BaseModel):
    warehouse_id: str
    product_id: str
    quantity: float
    reason: str = Field(min_length=3, max_length=2000)
    evidence_ref: str | None = None
    unit_cost: float | None = None
    currency: str = "VED"


class CostingProfileCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    method: str = Field(pattern="^(AVERAGE|FIFO)$")
    currency: str = "VED"
    product_id: str | None = None
    global_scope: bool = False
    effective_from: date | None = None
    effective_to: date | None = None


# --------------------------------------------------------------------------- #
# Almacenes y ubicaciones
# --------------------------------------------------------------------------- #
# NOTA: Almacenes y ubicaciones (maestros de custodia) los expone el módulo
# organization (001): /organization/warehouses y /organization/locations.
# El módulo de inventario los REUTILIZA (CL-003-02) y no duplica endpoints.
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
# Tipos de movimiento
# --------------------------------------------------------------------------- #
@router.get("/movement-types")
def list_movement_types(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.execute(
        select(MovementType).where((MovementType.company_id == user.tenant_id) | (MovementType.company_id.is_(None)))
    ).scalars().all()
    return {"items": [_mtype_dict(m) for m in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/movement-types", dependencies=[Depends(require_write_allowed)])
def create_movement_type(body: MovementTypeCreate, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("inventario", "create"))):
    company_id = None if body.global_scope else actor.tenant_id
    dup = db.execute(select(MovementType).where(MovementType.company_id == company_id, MovementType.code == body.code)).scalars().first()
    if dup:
        from app.core.errors import ConflictError

        raise ConflictError(code="MOVEMENT_TYPE_DUPLICATE", message="Ya existe un tipo de movimiento con ese código.")
    mtype = MovementType(company_id=company_id, code=body.code, name=body.name, direction=body.direction,
                         affects_balance=True, status="ACTIVE", created_by=str(actor.id))
    db.add(mtype)
    db.commit()
    db.refresh(mtype)
    return _mtype_dict(mtype)


# --------------------------------------------------------------------------- #
# Existencias y kardex
# --------------------------------------------------------------------------- #
@router.get("/balances")
def list_balances(product_id: str | None = None, warehouse_id: str | None = None,
                  location_id: str | None = None, lot_id: str | None = None, serial_id: str | None = None,
                  state: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(InventoryBalance).where(InventoryBalance.company_id == user.tenant_id)
    if product_id:
        query = query.where(InventoryBalance.product_id == product_id)
    if warehouse_id:
        query = query.where(InventoryBalance.warehouse_id == warehouse_id)
    if location_id:
        query = query.where(InventoryBalance.location_id == location_id)
    if lot_id:
        query = query.where(InventoryBalance.lot_id == lot_id)
    if serial_id:
        query = query.where(InventoryBalance.serial_id == serial_id)
    if state:
        query = query.where(InventoryBalance.state == state)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = db.execute(query.order_by(InventoryBalance.product_id).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [inv_service.balance_dict(b) for b in items], "total": total, "page": page, "page_size": page_size}


@router.get("/balances/{balance_id}")
def get_balance(balance_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    b = _get_owned(db, InventoryBalance, balance_id, user.tenant_id, "BALANCE_NOT_FOUND", "Balance no encontrado")
    return inv_service.balance_dict(b)


@router.post("/balances/recompute", dependencies=[Depends(require_write_allowed)])
def recompute_balances_endpoint(warehouse_id: str | None = None, db: Session = Depends(get_db),
                                user: User = Depends(get_current_user)):
    count = inv_service.recompute_balances(db, company_id=user.tenant_id, warehouse_id=warehouse_id)
    db.commit()
    return {"rebuilt": count, "company_id": user.tenant_id}


@router.get("/movements")
def list_movements(product_id: str | None = None, warehouse_id: str | None = None,
                   q: str = "", page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Kardex: historial de movimientos con paginación (FR-003-090)."""
    query = select(InventoryMovement).where(InventoryMovement.company_id == user.tenant_id)
    if product_id:
        query = query.where(InventoryMovement.product_id == product_id)
    if warehouse_id:
        query = query.where(InventoryMovement.warehouse_id == warehouse_id)
    if q:
        like = f"%{q}%"
        query = query.where((InventoryMovement.document_ref.ilike(like)) | (InventoryMovement.id.ilike(like)))
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = db.execute(query.order_by(InventoryMovement.occurred_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [inv_service.movement_dict(m) for m in items], "total": total, "page": page, "page_size": page_size}


@router.get("/movements/{movement_id}")
def get_movement(movement_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    m = _get_owned(db, InventoryMovement, movement_id, user.tenant_id, "MOVEMENT_NOT_FOUND", "Movimiento no encontrado")
    return inv_service.movement_dict(m)


@router.post("/movements", dependencies=[Depends(require_write_allowed)])
def create_movement(body: MovementCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("inventario", "create"))):
    movement = inv_service.record_movement(
        db, company_id=actor.tenant_id, warehouse_id=body.warehouse_id, product_id=body.product_id,
        movement_type_id=body.movement_type_id, quantity=body.quantity, unit_cost=body.unit_cost,
        currency=body.currency, fiscal_rate=body.fiscal_rate, document_ref=body.document_ref,
        location_id=body.location_id, actor=str(actor.id), idempotency_key=body.idempotency_key,
    )
    db.commit()
    db.refresh(movement)
    return inv_service.movement_dict(movement)


@router.post("/movements/reverse", dependencies=[Depends(require_write_allowed)])
def reverse_movement_endpoint(body: ReverseBody, db: Session = Depends(get_db),
                              actor: User = Depends(require_permission("inventario", "create"))):
    movement = _get_owned(db, InventoryMovement, body.movement_id, actor.tenant_id, "MOVEMENT_NOT_FOUND", "Movimiento no encontrado")
    reverse = inv_service.reverse_movement(db, movement=movement, actor=str(actor.id))
    db.commit()
    db.refresh(reverse)
    return inv_service.movement_dict(reverse)


# --------------------------------------------------------------------------- #
# Lotes y seriales
# --------------------------------------------------------------------------- #
@router.get("/lots")
def list_lots(product_id: str | None = None, status: str | None = None, expiry_before: date | None = None,
              page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
              db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(InventoryLot).where(InventoryLot.company_id == user.tenant_id)
    if product_id:
        query = query.where(InventoryLot.product_id == product_id)
    if status:
        query = query.where(InventoryLot.status == status)
    if expiry_before:
        query = query.where(InventoryLot.expiry_date.isnot(None), InventoryLot.expiry_date <= expiry_before)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = db.execute(query.order_by(InventoryLot.expiry_date.asc().nulls_last()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [_lot_dict(lot) for lot in items], "total": total, "page": page, "page_size": page_size}


@router.post("/lots", dependencies=[Depends(require_write_allowed)])
def create_lot(body: LotCreate, db: Session = Depends(get_db),
               actor: User = Depends(require_permission("inventario", "create"))):
    lot = inv_service.create_lot(db, company_id=actor.tenant_id, product_id=body.product_id, lot_number=body.lot_number,
                                 manufacture_date=body.manufacture_date, expiry_date=body.expiry_date,
                                 supplier_id=body.supplier_id, receipt_ref=body.receipt_ref, actor=str(actor.id))
    db.commit()
    db.refresh(lot)
    return _lot_dict(lot)


@router.post("/lots/{lot_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_lot(lot_id: str, body: TransitionBody, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("inventario", "transition"))):
    lot = _get_owned(db, InventoryLot, lot_id, actor.tenant_id, "LOT_NOT_FOUND", "Lote no encontrado")
    inv_service.transition_lot(db, lot=lot, target=body.target, actor=str(actor.id))
    db.commit()
    db.refresh(lot)
    return _lot_dict(lot)


@router.get("/serials")
def list_serials(product_id: str | None = None, status: str | None = None, q: str = "",
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(ProductSerial).where(ProductSerial.company_id == user.tenant_id)
    if product_id:
        query = query.where(ProductSerial.product_id == product_id)
    if status:
        query = query.where(ProductSerial.status == status)
    if q:
        like = f"%{q}%"
        query = query.where((ProductSerial.serial.ilike(like)) | (ProductSerial.imei1.ilike(like)))
    items = db.execute(query.order_by(ProductSerial.created_at)).scalars().all()
    return {"items": [_serial_dict(s) for s in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/serials", dependencies=[Depends(require_write_allowed)])
def create_serial(body: SerialCreate, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("inventario", "create"))):
    ps = inv_service.create_serial(db, company_id=actor.tenant_id, product_id=body.product_id, serial=body.serial,
                                   imei1=body.imei1, imei2=body.imei2, mac=body.mac, lot_id=body.lot_id,
                                   warehouse_id=body.warehouse_id, actor=str(actor.id))
    db.commit()
    db.refresh(ps)
    return _serial_dict(ps)


# --------------------------------------------------------------------------- #
# Reservas
# --------------------------------------------------------------------------- #
@router.post("/reservations", dependencies=[Depends(require_write_allowed)])
def create_reservation(body: ReserveBody, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("inventario", "reserve"))):
    reservation = inv_service.reserve(db, company_id=actor.tenant_id, source_document=body.source_document,
                                      product_id=body.product_id, warehouse_id=body.warehouse_id, quantity=body.quantity,
                                      lot_id=body.lot_id, serial_id=body.serial_id, expires_in_days=body.expires_in_days,
                                      actor=str(actor.id))
    db.commit()
    db.refresh(reservation)
    return _reservation_dict(reservation)


@router.get("/reservations")
def list_reservations(status: str | None = None, product_id: str | None = None,
                      db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(Reservation).where(Reservation.company_id == user.tenant_id)
    if status:
        query = query.where(Reservation.status == status)
    if product_id:
        query = query.where(Reservation.product_id == product_id)
    items = db.execute(query.order_by(Reservation.created_at.desc())).scalars().all()
    return {"items": [_reservation_dict(r) for r in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/reservations/{reservation_id}/release", dependencies=[Depends(require_write_allowed)])
def release_reservation(reservation_id: str, db: Session = Depends(get_db),
                        actor: User = Depends(require_permission("inventario", "reserve"))):
    reservation = _get_owned(db, Reservation, reservation_id, actor.tenant_id, "RESERVATION_NOT_FOUND", "Reserva no encontrada")
    inv_service.release_reservation(db, reservation=reservation, actor=str(actor.id))
    db.commit()
    db.refresh(reservation)
    return _reservation_dict(reservation)


@router.post("/reservations/expire", dependencies=[Depends(require_write_allowed)])
def expire_reservations(db: Session = Depends(get_db), actor: User = Depends(require_permission("inventario", "reserve"))):
    count = inv_service.expire_reservations(db, company_id=actor.tenant_id)
    db.commit()
    return {"expired": count}


# --------------------------------------------------------------------------- #
# Transferencias
# --------------------------------------------------------------------------- #
@router.post("/transfers", dependencies=[Depends(require_write_allowed)])
def create_transfer(body: TransferCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("inventario", "create"))):
    inv_service._require_warehouse(db, actor.tenant_id, body.origin_warehouse_id)
    inv_service._require_warehouse(db, actor.tenant_id, body.destination_warehouse_id)
    transfer = Transfer(company_id=actor.tenant_id, code=body.code, origin_warehouse_id=body.origin_warehouse_id,
                        destination_warehouse_id=body.destination_warehouse_id, request_ref=body.request_ref,
                        status="DRAFT", created_by=str(actor.id))
    db.add(transfer)
    db.flush()
    for line in body.lines:
        db.add(TransferLine(transfer_id=str(transfer.id), product_id=line.product_id, lot_id=line.lot_id,
                            serial_id=line.serial_id, quantity_sent=line.quantity_sent))
    db.commit()
    db.refresh(transfer)
    return _transfer_dict(db, transfer)


@router.get("/transfers")
def list_transfers(status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(Transfer).where(Transfer.company_id == user.tenant_id)
    if status:
        query = query.where(Transfer.status == status)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = db.execute(query.order_by(Transfer.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [_transfer_dict(db, t) for t in items], "total": total, "page": page, "page_size": page_size}


@router.post("/transfers/{transfer_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_transfer(transfer_id: str, body: TransitionBody, db: Session = Depends(get_db),
                        actor: User = Depends(require_permission("inventario", "transition"))):
    transfer = _get_owned(db, Transfer, transfer_id, actor.tenant_id, "TRANSFER_NOT_FOUND", "Transferencia no encontrada")
    if body.target == "IN_TRANSIT":
        inv_service.confirm_transfer_ship(db, transfer=transfer, actor=str(actor.id))
    elif body.target in ("RECEIVED", "PARTIALLY_RECEIVED"):
        inv_service.confirm_transfer_receipt(db, transfer=transfer, actor=str(actor.id))
    else:
        inv_service.transition_transfer(db, transfer=transfer, target=body.target, actor=str(actor.id))
    db.commit()
    db.refresh(transfer)
    return _transfer_dict(db, transfer)


# --------------------------------------------------------------------------- #
# Conteos
# --------------------------------------------------------------------------- #
@router.post("/counts", dependencies=[Depends(require_write_allowed)])
def create_count(body: CountCreate, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("inventario", "create"))):
    inv_service._require_warehouse(db, actor.tenant_id, body.warehouse_id)
    count = StockCount(company_id=actor.tenant_id, code=body.code, warehouse_id=body.warehouse_id,
                       plan_ref=body.plan_ref, scope=body.scope, freeze_policy=body.freeze_policy,
                       status="DRAFT", created_by=str(actor.id))
    db.add(count)
    db.commit()
    db.refresh(count)
    return _count_dict(count)


@router.get("/counts")
def list_counts(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(StockCount).where(StockCount.company_id == user.tenant_id)
    if status:
        query = query.where(StockCount.status == status)
    items = db.execute(query.order_by(StockCount.created_at.desc())).scalars().all()
    return {"items": [_count_dict(c) for c in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/counts/{count_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_count_line(count_id: str, body: CountLineCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("inventario", "create"))):
    count = _get_owned(db, StockCount, count_id, actor.tenant_id, "COUNT_NOT_FOUND", "Conteo no encontrado")
    line = inv_service.record_count_line(db, count_id=str(count.id), product_id=body.product_id,
                                         expected_qty=body.expected_qty, counted_qty=body.counted_qty,
                                         location_id=body.location_id, lot_id=body.lot_id)
    db.commit()
    db.refresh(line)
    return _count_line_dict(line)


@router.post("/counts/{count_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_count(count_id: str, body: TransitionBody, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("inventario", "transition"))):
    count = _get_owned(db, StockCount, count_id, actor.tenant_id, "COUNT_NOT_FOUND", "Conteo no encontrado")
    if body.target == "APPROVED":
        inv_service.approve_count(db, count=count, actor=str(actor.id))
    else:
        inv_service.transition_count(db, count=count, target=body.target, actor=str(actor.id))
    db.commit()
    db.refresh(count)
    return _count_dict(count)


# --------------------------------------------------------------------------- #
# Ajustes
# --------------------------------------------------------------------------- #
@router.post("/adjustments", dependencies=[Depends(require_write_allowed)])
def create_adjustment(body: AdjustmentCreate, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("inventario", "create"))):
    adjustment = inv_service.create_adjustment(db, company_id=actor.tenant_id, warehouse_id=body.warehouse_id,
                                               product_id=body.product_id, quantity=body.quantity, reason=body.reason,
                                               evidence_ref=body.evidence_ref, unit_cost=body.unit_cost,
                                               currency=body.currency, actor=str(actor.id))
    db.commit()
    db.refresh(adjustment)
    return _adjustment_dict(adjustment)


@router.get("/adjustments")
def list_adjustments(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(InventoryAdjustment).where(InventoryAdjustment.company_id == user.tenant_id)
    if status:
        query = query.where(InventoryAdjustment.status == status)
    items = db.execute(query.order_by(InventoryAdjustment.created_at.desc())).scalars().all()
    return {"items": [_adjustment_dict(a) for a in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/adjustments/{adjustment_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_adjustment(adjustment_id: str, body: TransitionBody, db: Session = Depends(get_db),
                          actor: User = Depends(require_permission("inventario", "approve"))):
    adjustment = _get_owned(db, InventoryAdjustment, adjustment_id, actor.tenant_id, "ADJUSTMENT_NOT_FOUND", "Ajuste no encontrado")
    if body.target == "APPLIED":
        inv_service.apply_adjustment(db, adjustment=adjustment, actor=str(actor.id))
    else:
        inv_service.transition_adjustment(db, adjustment=adjustment, target=body.target, actor=str(actor.id))
    db.commit()
    db.refresh(adjustment)
    return _adjustment_dict(adjustment)


# --------------------------------------------------------------------------- #
# Costos
# --------------------------------------------------------------------------- #
@router.get("/cost-layers")
def list_cost_layers(product_id: str | None = None, warehouse_id: str | None = None,
                     db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(CostLayer).where(CostLayer.company_id == user.tenant_id)
    if product_id:
        query = query.where(CostLayer.product_id == product_id)
    if warehouse_id:
        query = query.where(CostLayer.warehouse_id == warehouse_id)
    items = db.execute(query.order_by(CostLayer.created_at)).scalars().all()
    return {"items": [_cost_layer_dict(c) for c in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.get("/valuation")
def get_valuation(product_id: str | None = None, warehouse_id: str | None = None,
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    value = inv_service.valuation(db, company_id=user.tenant_id, product_id=product_id, warehouse_id=warehouse_id)
    return {"valuation": value, "currency": "VED"}


@router.get("/costing-profiles")
def list_costing_profiles(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.execute(
        select(CostingProfile).where((CostingProfile.company_id == user.tenant_id) | (CostingProfile.company_id.is_(None)))
    ).scalars().all()
    return {"items": [_costing_profile_dict(c) for c in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/costing-profiles", dependencies=[Depends(require_write_allowed)])
def create_costing_profile(body: CostingProfileCreate, db: Session = Depends(get_db),
                           actor: User = Depends(require_permission("inventario", "create"))):
    profile = CostingProfile(company_id=None if body.global_scope else actor.tenant_id, code=body.code, method=body.method,
                             currency=body.currency, product_id=body.product_id, effective_from=body.effective_from,
                             effective_to=body.effective_to, status="ACTIVE", created_by=str(actor.id))
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _costing_profile_dict(profile)


# --------------------------------------------------------------------------- #
# Integración v1 (para 004/005)
# --------------------------------------------------------------------------- #
class OperationReceive(BaseModel):
    warehouse_id: str
    product_id: str
    quantity: float = Field(gt=0)
    unit_cost: float
    currency: str = "VED"
    fiscal_rate: float | None = None
    document_ref: str | None = None
    lot_number: str | None = None
    expiry_date: date | None = None
    serials: list[str] = Field(default_factory=list)
    idempotency_key: str | None = None


@router.post("/operations/receive", dependencies=[Depends(require_write_allowed)])
def operation_receive(body: OperationReceive, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("inventario", "create"))):
    """Entrada por recepción (origen: GoodsReceipt 004). Crea lotes/seriales y capas."""
    lot_id = None
    if body.lot_number:
        lot = inv_service.create_lot(db, company_id=actor.tenant_id, product_id=body.product_id, lot_number=body.lot_number,
                                     expiry_date=body.expiry_date, receipt_ref=body.document_ref, actor=str(actor.id))
        lot_id = str(lot.id)
    for serial in body.serials:
        inv_service.create_serial(db, company_id=actor.tenant_id, product_id=body.product_id, serial=serial,
                                  lot_id=lot_id, warehouse_id=body.warehouse_id, actor=str(actor.id))
    mtype = inv_service._get_movement_type_by_code(db, actor.tenant_id, "ENTRADA_RECEPCION")
    movement = inv_service.record_movement(db, company_id=actor.tenant_id, warehouse_id=body.warehouse_id,
                                           product_id=body.product_id, movement_type_id=str(mtype.id), quantity=body.quantity,
                                           unit_cost=body.unit_cost, currency=body.currency, fiscal_rate=body.fiscal_rate,
                                           document_ref=body.document_ref, actor=str(actor.id), idempotency_key=body.idempotency_key)
    db.commit()
    db.refresh(movement)
    return {"movement_id": str(movement.id), "lot_id": lot_id, "serial_ids": []}


class OperationShip(BaseModel):
    warehouse_id: str
    product_id: str
    quantity: float = Field(gt=0)
    document_ref: str | None = None
    lot_ids: list[str] = Field(default_factory=list)
    idempotency_key: str | None = None


@router.post("/operations/ship", dependencies=[Depends(require_write_allowed)])
def operation_ship(body: OperationShip, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("inventario", "create"))):
    """Salida (origen: Shipment 005): valida FEFO/bloqueos y calcula costo de salida."""
    mtype = inv_service._get_movement_type_by_code(db, actor.tenant_id, "SALIDA_DESPACHO")
    movement = inv_service.record_movement(db, company_id=actor.tenant_id, warehouse_id=body.warehouse_id,
                                           product_id=body.product_id, movement_type_id=str(mtype.id), quantity=-body.quantity,
                                           document_ref=body.document_ref, actor=str(actor.id), idempotency_key=body.idempotency_key)
    db.commit()
    db.refresh(movement)
    return {"movement_id": str(movement.id), "unit_cost": movement.unit_cost}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _get_owned(db: Session, model, obj_id: str, tenant: str, code: str, message: str):
    obj = db.get(model, obj_id)
    if not obj or getattr(obj, "company_id", tenant) != tenant:
        raise NotFoundError(code=code, message=message)
    return obj


def _mtype_dict(m: MovementType) -> dict:
    return {"id": m.id, "code": m.code, "name": m.name, "direction": m.direction, "version": m.version, "status": m.status}


def _lot_dict(lot: InventoryLot) -> dict:
    return {"id": lot.id, "product_id": lot.product_id, "lot_number": lot.lot_number,
            "manufacture_date": lot.manufacture_date.isoformat() if lot.manufacture_date else None,
            "expiry_date": lot.expiry_date.isoformat() if lot.expiry_date else None,
            "supplier_id": lot.supplier_id, "receipt_ref": lot.receipt_ref, "status": lot.status,
            "allowed_actions": inv_service.lot_allowed_actions(lot)}


def _serial_dict(s: ProductSerial) -> dict:
    return {"id": s.id, "product_id": s.product_id, "serial": s.serial, "imei1": s.imei1, "imei2": s.imei2,
            "mac": s.mac, "lot_id": s.lot_id, "status": s.status, "warehouse_id": s.warehouse_id,
            "warranty_until": s.warranty_until.isoformat() if s.warranty_until else None}


def _reservation_dict(r: Reservation) -> dict:
    return {"id": r.id, "source_document": r.source_document, "product_id": r.product_id, "warehouse_id": r.warehouse_id,
            "lot_id": r.lot_id, "serial_id": r.serial_id, "quantity": r.quantity, "status": r.status,
            "expires_at": r.expires_at.isoformat() if r.expires_at else None}


def _transfer_dict(db: Session, t: Transfer) -> dict:
    lines = db.execute(select(TransferLine).where(TransferLine.transfer_id == t.id)).scalars().all()
    return {"id": t.id, "code": t.code, "origin_warehouse_id": t.origin_warehouse_id,
            "destination_warehouse_id": t.destination_warehouse_id, "request_ref": t.request_ref,
            "shipment_ref": t.shipment_ref, "receipt_ref": t.receipt_ref, "status": t.status,
            "allowed_actions": inv_service.transfer_allowed_actions(t.status),
            "lines": [{"id": line.id, "product_id": line.product_id, "quantity_sent": line.quantity_sent,
                       "quantity_received": line.quantity_received, "difference": line.difference,
                       "destination_state": line.destination_state} for line in lines]}


def _count_dict(c: StockCount) -> dict:
    return {"id": c.id, "code": c.code, "warehouse_id": c.warehouse_id, "plan_ref": c.plan_ref, "scope": c.scope,
            "freeze_policy": c.freeze_policy, "status": c.status, "allowed_actions": inv_service.count_allowed_actions(c.status)}


def _count_line_dict(line: StockCountLine) -> dict:
    return {"id": line.id, "count_id": line.count_id, "product_id": line.product_id, "location_id": line.location_id,
            "lot_id": line.lot_id, "expected_qty": line.expected_qty, "counted_qty": line.counted_qty, "variance": line.variance}


def _adjustment_dict(a: InventoryAdjustment) -> dict:
    return {"id": a.id, "warehouse_id": a.warehouse_id, "product_id": a.product_id, "quantity": a.quantity,
            "reason": a.reason, "evidence_ref": a.evidence_ref, "unit_cost": a.unit_cost, "currency": a.currency,
            "status": a.status, "allowed_actions": inv_service.adjustment_allowed_actions(a.status)}


def _cost_layer_dict(c: CostLayer) -> dict:
    return {"id": c.id, "product_id": c.product_id, "warehouse_id": c.warehouse_id, "receipt_ref": c.receipt_ref,
            "quantity_in": c.quantity_in, "quantity_remaining": c.quantity_remaining, "unit_cost": c.unit_cost,
            "currency": c.currency, "fiscal_rate": c.fiscal_rate, "landed_cost": c.landed_cost, "status": c.status}


def _costing_profile_dict(c: CostingProfile) -> dict:
    return {"id": c.id, "code": c.code, "method": c.method, "currency": c.currency, "product_id": c.product_id,
            "effective_from": c.effective_from.isoformat() if c.effective_from else None,
            "effective_to": c.effective_to.isoformat() if c.effective_to else None, "version": c.version, "status": c.status}
