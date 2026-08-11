"""Servicios de inventario y logística (003-inventario-logistica).

Motor de movimientos balanceados e inmutables, saldos reconstruibles, reservas
atómicas, FEFO, transferencias, conteos/ajustes y valoración por capas.

Invariantes clave:
- `InventoryMovement` es la única fuente de saldos (DOC-03 §5).
- Los movimientos no se editan ni eliminan; toda corrección es un reverso
  vinculado (Constitución P5).
- `available = on_hand − reserved`; las reservas no superan el disponible salvo
  política aprobada (DOC-03 §12).
- Método de costeo versionado (AVERAGE/FIFO), no hardcodeado (P8).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
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
from app.modules.organization.models import Warehouse
from app.modules.organization.service import warehouse_in_tenant_scope

# Tipos de movimiento operativos base (se auto-configuran si faltan, FR-003-023).
BASE_MOVEMENT_TYPES: dict[str, tuple[str, str]] = {
    "ENTRADA_RECEPCION": ("Entrada por recepción", "IN"),
    "SALIDA_DESPACHO": ("Salida por despacho", "OUT"),
    "TRANSFERENCIA_SALIDA": ("Salida por transferencia", "OUT"),
    "TRANSFERENCIA_ENTRADA": ("Entrada por transferencia", "IN"),
    "CONTEO": ("Ajuste por conteo", "INTERNAL"),
    "AJUSTE_POSITIVO": ("Ajuste positivo", "IN"),
    "AJUSTE_NEGATIVO": ("Ajuste negativo", "OUT"),
    "REVERSO": ("Reverso de movimiento", "INTERNAL"),
}


# --------------------------------------------------------------------------- #
# Transiciones permitidas (máquinas de estado, DOC-03 §13)
# --------------------------------------------------------------------------- #
TRANSFER_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"SUBMITTED", "CANCELLED"},
    "SUBMITTED": {"APPROVED", "REJECTED"},
    "APPROVED": {"PICKING", "CANCELLED"},
    "PICKING": {"IN_TRANSIT"},
    "IN_TRANSIT": {"PARTIALLY_RECEIVED", "RECEIVED"},
    "PARTIALLY_RECEIVED": {"RECEIVED"},
    "RECEIVED": {"CLOSED"},
    "CLOSED": set(),
    "CANCELLED": set(),
    "REJECTED": set(),
}

COUNT_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"FROZEN", "CANCELLED"},
    "FROZEN": {"COUNTING", "CANCELLED"},
    "COUNTING": {"SUBMITTED", "CANCELLED"},
    "SUBMITTED": {"APPROVED", "REJECTED"},
    "APPROVED": {"CLOSED"},
    "CLOSED": set(),
    "CANCELLED": set(),
    "REJECTED": set(),
}

ADJUSTMENT_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"SUBMITTED", "CANCELLED"},
    "SUBMITTED": {"APPROVED", "REJECTED"},
    "APPROVED": {"APPLIED"},
    "APPLIED": set(),
    "REJECTED": set(),
    "CANCELLED": set(),
}

LOT_SERIAL_TRANSITIONS: dict[str, set[str]] = {
    "DISPONIBLE": {"RESERVADO", "TRANSITO", "CUARENTENA"},
    "RESERVADO": {"DISPONIBLE", "TRANSITO", "VENDIDO"},
    "TRANSITO": {"DISPONIBLE", "CUARENTENA", "RECHAZADO"},
    "CUARENTENA": {"DISPONIBLE", "RECHAZADO", "DESECHO"},
    "VENCIDO": {"DESECHO"},
    "RECHAZADO": {"DESECHO"},
    "DESECHO": set(),
    "VENDIDO": set(),
}


def _assert_transition(current: str, target: str, transitions: dict[str, set[str]], what: str) -> None:
    if target not in transitions.get(current, set()):
        raise ConflictError(
            code="INVALID_STATE_TRANSITION",
            message=f"No se permite pasar {what} de {current} a {target}.",
        )


def _company(company_id: str | None, *, obj: str) -> str:
    if not company_id:
        raise KontrolError(code="COMPANY_REQUIRED", message="Se requiere la empresa para esta operación", status_code=422)
    return company_id


# --------------------------------------------------------------------------- #
# allowed_actions
# --------------------------------------------------------------------------- #
def movement_allowed_actions(movement: InventoryMovement) -> dict[str, bool]:
    return {"view": True, "reverse": movement.reversed_by_id is None, "audit": True}


def lot_allowed_actions(lot: InventoryLot) -> dict[str, bool]:
    return {"view": True, "transition": True, "deactivate": lot.status not in ("DESECHO",), "audit": True}


def transfer_allowed_actions(status: str) -> dict[str, bool]:
    return {"view": True, "submit": status == "DRAFT", "approve": status == "SUBMITTED", "reject": status == "SUBMITTED",
            "confirm_ship": status in ("APPROVED", "PICKING"), "confirm_receipt": status in ("IN_TRANSIT", "PARTIALLY_RECEIVED"),
            "close": status == "RECEIVED", "cancel": status in ("DRAFT", "APPROVED")}


def count_allowed_actions(status: str) -> dict[str, bool]:
    return {"view": True, "freeze": status == "DRAFT", "submit": status in ("FROZEN", "COUNTING"),
            "approve": status == "SUBMITTED", "close": status == "APPROVED", "cancel": status in ("DRAFT", "FROZEN", "COUNTING")}


def adjustment_allowed_actions(status: str) -> dict[str, bool]:
    return {"view": True, "submit": status == "DRAFT", "approve": status == "SUBMITTED",
            "reject": status == "SUBMITTED", "cancel": status == "DRAFT"}


# --------------------------------------------------------------------------- #
# Saldos (cache reconstruible) — FR-003-010/011/012/013
# --------------------------------------------------------------------------- #
def _balance_key(*, warehouse_id: str, location_id: str | None, product_id: str, lot_id: str | None,
                 serial_id: str | None, state: str) -> tuple[str | None, ...]:
    return (warehouse_id, location_id, product_id, lot_id, serial_id, state)


def _get_balance(
    db: Session,
    *,
    company_id: str,
    warehouse_id: str,
    location_id: str | None,
    product_id: str,
    lot_id: str | None,
    serial_id: str | None,
    state: str,
) -> InventoryBalance:
    balance = (
        db.execute(
            select(InventoryBalance).where(
                InventoryBalance.company_id == company_id,
                InventoryBalance.warehouse_id == warehouse_id,
                InventoryBalance.location_id.is_(None) if location_id is None else InventoryBalance.location_id == location_id,
                InventoryBalance.product_id == product_id,
                InventoryBalance.lot_id.is_(None) if lot_id is None else InventoryBalance.lot_id == lot_id,
                InventoryBalance.serial_id.is_(None) if serial_id is None else InventoryBalance.serial_id == serial_id,
                InventoryBalance.state == state,
            )
        )
        .scalars()
        .first()
    )
    if balance is None:
        balance = InventoryBalance(
            company_id=company_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            product_id=product_id,
            lot_id=lot_id,
            serial_id=serial_id,
            state=state,
            qty_on_hand=0.0,
            qty_reserved=0.0,
            qty_available=0.0,
        )
        db.add(balance)
        db.flush()
    return balance


def _refresh_available(balance: InventoryBalance) -> None:
    balance.qty_available = round(balance.qty_on_hand - balance.qty_reserved, 6)


def recompute_balances(db: Session, *, company_id: str, warehouse_id: str | None = None) -> int:
    """Reconstruye el cache desde movimientos y reservas (FR-003-010/011).

    Fuente de verdad: `inventory_movements` (+ reservas activas).
    Devuelve el número de filas de balance reconstruidas.
    """
    mov_query = select(InventoryMovement).where(InventoryMovement.company_id == company_id)
    bal_query = select(InventoryBalance).where(InventoryBalance.company_id == company_id)
    if warehouse_id:
        mov_query = mov_query.where(InventoryMovement.warehouse_id == warehouse_id)
        bal_query = bal_query.where(InventoryBalance.warehouse_id == warehouse_id)

    movements = db.execute(mov_query).scalars().all()
    existing = db.execute(bal_query).scalars().all()
    for b in existing:
        db.delete(b)
    db.flush()

    rows: dict[tuple[str | None, ...], InventoryBalance] = {}
    for m in movements:
        key = _balance_key(
            warehouse_id=m.warehouse_id, location_id=m.location_id, product_id=m.product_id,
            lot_id=None, serial_id=None, state="DISPONIBLE",
        )
        bal = rows.setdefault(
            key,
            InventoryBalance(
                company_id=company_id, warehouse_id=m.warehouse_id, location_id=m.location_id,
                product_id=m.product_id, lot_id=None, serial_id=None, state="DISPONIBLE",
                qty_on_hand=0.0, qty_reserved=0.0, qty_available=0.0,
            ),
        )
        bal.qty_on_hand = round(bal.qty_on_hand + m.quantity, 6)

    # 2. Aplicar reservas activas
    reservations = db.execute(select(Reservation).where(Reservation.company_id == company_id, Reservation.status == "ACTIVE")).scalars().all()
    for r in reservations:
        key = _balance_key(
            warehouse_id=r.warehouse_id, location_id=None, product_id=r.product_id,
            lot_id=r.lot_id, serial_id=r.serial_id, state="DISPONIBLE",
        )
        bal = rows.setdefault(
            key,
            InventoryBalance(
                company_id=company_id, warehouse_id=r.warehouse_id, location_id=None,
                product_id=r.product_id, lot_id=r.lot_id, serial_id=r.serial_id, state="DISPONIBLE",
                qty_on_hand=0.0, qty_reserved=0.0, qty_available=0.0,
            ),
        )
        bal.qty_reserved = round(bal.qty_reserved + r.quantity, 6)

    now = datetime.now(UTC)
    for bal in rows.values():
        _refresh_available(bal)
        bal.last_rebuilt_at = now
        db.add(bal)
    db.flush()
    return len(rows)


def get_available(
    db: Session,
    *,
    company_id: str,
    product_id: str,
    warehouse_id: str,
    location_id: str | None = None,
    lot_id: str | None = None,
    serial_id: str | None = None,
) -> float:
    """Disponible = físico − reservas (FR-003-013)."""
    balance = (
        db.execute(
            select(InventoryBalance).where(
                InventoryBalance.company_id == company_id,
                InventoryBalance.warehouse_id == warehouse_id,
                InventoryBalance.product_id == product_id,
                InventoryBalance.location_id.is_(None) if location_id is None else InventoryBalance.location_id == location_id,
                InventoryBalance.lot_id.is_(None) if lot_id is None else InventoryBalance.lot_id == lot_id,
                InventoryBalance.serial_id.is_(None) if serial_id is None else InventoryBalance.serial_id == serial_id,
                InventoryBalance.state == "DISPONIBLE",
            )
        )
        .scalars()
        .first()
    )
    if balance is None:
        return 0.0
    return balance.qty_available


# --------------------------------------------------------------------------- #
# Movimientos (FR-003-020..024)
# --------------------------------------------------------------------------- #
def _require_warehouse(db: Session, company_id: str, warehouse_id: str) -> Warehouse:
    warehouse = db.get(Warehouse, warehouse_id)
    if not warehouse or not warehouse_in_tenant_scope(db, company_id, warehouse):
        raise NotFoundError(code="WAREHOUSE_NOT_FOUND", message="Almacén no encontrado")
    return warehouse


def _require_product(db: Session, company_id: str, product_id: str) -> None:
    from app.modules.master_data.models import CatalogItem

    item = db.get(CatalogItem, product_id)
    if not item or item.company_id != company_id or item.item_type != "PRODUCT":
        raise NotFoundError(code="PRODUCT_NOT_FOUND", message="Producto no encontrado")


def _allow_negative(warehouse: Warehouse) -> bool:
    """Política del almacén (JSON gobernado, P8): permitir existencias negativas."""
    return bool((warehouse.policies or {}).get("allow_negative", False))


def record_movement(
    db: Session,
    *,
    company_id: str,
    warehouse_id: str,
    product_id: str,
    movement_type_id: str,
    quantity: float,
    unit_cost: float | None = None,
    currency: str = "VED",
    fiscal_rate: float | None = None,
    document_ref: str | None = None,
    location_id: str | None = None,
    actor: str | None = None,
    occurred_at: datetime | None = None,
    idempotency_key: str | None = None,
) -> InventoryMovement:
    """Registra un movimiento balanceado e inmutable (FR-003-020/021/022)."""
    company_id = _company(company_id, obj="movimiento")
    if quantity == 0:
        raise KontrolError(code="ZERO_QUANTITY", message="La cantidad del movimiento no puede ser cero", status_code=422)

    if idempotency_key:
        existing = db.execute(select(InventoryMovement).where(InventoryMovement.idempotency_key == idempotency_key)).scalars().first()
        if existing:
            return existing

    warehouse = _require_warehouse(db, company_id, warehouse_id)
    _require_product(db, company_id, product_id)
    mtype = db.get(MovementType, movement_type_id)
    if not mtype:
        raise NotFoundError(code="MOVEMENT_TYPE_NOT_FOUND", message="Tipo de movimiento no encontrado")

    signed = quantity
    if mtype.direction == "OUT":
        if quantity > 0:
            raise KontrolError(code="INVALID_SIGN", message="Un movimiento de salida debe tener cantidad negativa", status_code=422)
    elif mtype.direction == "IN":
        if quantity < 0:
            raise KontrolError(code="INVALID_SIGN", message="Un movimiento de entrada debe tener cantidad positiva", status_code=422)
    # direction == INTERNAL: se permite cualquier signo (p. ej. reversos).

    if signed < 0:
        available = get_available(db, company_id=company_id, product_id=product_id, warehouse_id=warehouse_id, location_id=location_id)
        if -signed > available and not _allow_negative(warehouse):
            raise ConflictError(
                code="INSUFFICIENT_STOCK",
                message=f"No hay existencias disponibles suficientes (disponible: {available}).",
            )

    movement = InventoryMovement(
        company_id=company_id,
        warehouse_id=warehouse_id,
        location_id=location_id,
        product_id=product_id,
        movement_type_id=movement_type_id,
        quantity=signed,
        unit_id=None,
        unit_cost=unit_cost,
        currency=currency,
        fiscal_rate=fiscal_rate,
        document_ref=document_ref,
        occurred_at=occurred_at or datetime.now(UTC),
        status="POSTED",
        created_by=actor,
        idempotency_key=idempotency_key,
    )
    db.add(movement)
    db.flush()

    # Costing: entrada crea capa; salida consume capas y fija el costo unitario
    if signed > 0:
        if unit_cost is not None:
            _apply_cost_in(db, company_id=company_id, product_id=product_id, warehouse_id=warehouse_id,
                           receipt_ref=document_ref, quantity=signed, unit_cost=unit_cost, currency=currency, fiscal_rate=fiscal_rate)
    else:
        cost = _consume_cost(db, company_id=company_id, product_id=product_id, warehouse_id=warehouse_id, quantity=-signed)
        movement.unit_cost = cost

    # Balance (cache)
    balance = _get_balance(db, company_id=company_id, warehouse_id=warehouse_id, location_id=location_id,
                           product_id=product_id, lot_id=None, serial_id=None, state="DISPONIBLE")
    balance.qty_on_hand = round(balance.qty_on_hand + signed, 6)
    _refresh_available(balance)
    db.flush()
    return movement


def reverse_movement(db: Session, *, movement: InventoryMovement, actor: str | None = None,
                     occurred_at: datetime | None = None) -> InventoryMovement:
    """Crea un movimiento reverso vinculado (FR-003-022, P5). Nunca borra el original."""
    if movement.reversed_by_id is not None:
        raise ConflictError(code="ALREADY_REVERSED", message="El movimiento ya fue revertido.")
    mtype = _get_movement_type_by_code_optional(db, "REVERSO")
    if mtype is None:
        mtype = MovementType(company_id=None, code="REVERSO", name="Reverso de movimiento",
                             direction="INTERNAL", affects_balance=True, status="ACTIVE", created_by=actor)
        db.add(mtype)
        db.flush()
    reverse = record_movement(
        db,
        company_id=movement.company_id,
        warehouse_id=movement.warehouse_id,
        product_id=movement.product_id,
        movement_type_id=str(mtype.id),
        quantity=-movement.quantity,
        unit_cost=movement.unit_cost,
        currency=movement.currency,
        fiscal_rate=movement.fiscal_rate,
        document_ref=f"REVERSO:{movement.id}",
        location_id=movement.location_id,
        actor=actor,
        occurred_at=occurred_at or datetime.now(UTC),
    )
    reverse.reversed_by_id = str(movement.id)
    movement.reversed_by_id = str(reverse.id)
    db.flush()
    return reverse


# --------------------------------------------------------------------------- #
# Costos por capas (FR-003-080..083)
# --------------------------------------------------------------------------- #
def _costing_method(db: Session, company_id: str, product_id: str) -> str:
    profile = (
        db.execute(
            select(CostingProfile)
            .where(
                CostingProfile.status == "ACTIVE",
                ((CostingProfile.company_id == company_id) | (CostingProfile.company_id.is_(None))),
                (CostingProfile.product_id == product_id) | (CostingProfile.product_id.is_(None)),
            )
            .order_by(CostingProfile.product_id.isnot(None).desc(), CostingProfile.company_id.isnot(None).desc())
        )
        .scalars()
        .first()
    )
    return profile.method if profile else "AVERAGE"


def _apply_cost_in(db: Session, *, company_id: str, product_id: str, warehouse_id: str,
                   receipt_ref: str | None, quantity: float, unit_cost: float, currency: str,
                   fiscal_rate: float | None) -> CostLayer:
    layer = CostLayer(
        company_id=company_id, product_id=product_id, warehouse_id=warehouse_id,
        receipt_ref=receipt_ref, quantity_in=quantity, quantity_remaining=quantity,
        unit_cost=unit_cost, currency=currency, fiscal_rate=fiscal_rate, landed_cost=0.0, status="OPEN",
    )
    db.add(layer)
    db.flush()
    return layer


def _consume_cost(db: Session, *, company_id: str, product_id: str, warehouse_id: str, quantity: float) -> float | None:
    """Consume capas de costo (FIFO o promedio) y devuelve el costo unitario de salida."""
    method = _costing_method(db, company_id, product_id)
    layers = (
        db.execute(
            select(CostLayer)
            .where(CostLayer.company_id == company_id, CostLayer.product_id == product_id,
                   CostLayer.warehouse_id == warehouse_id, CostLayer.quantity_remaining > 0)
            .order_by(CostLayer.created_at.asc())
        )
        .scalars()
        .all()
    )
    remaining = quantity
    if method == "FIFO":
        total_cost = 0.0
        for layer in layers:
            take = min(layer.quantity_remaining, remaining)
            total_cost += float(take) * float(layer.unit_cost or 0)
            layer.quantity_remaining = round(layer.quantity_remaining - take, 6)
            remaining -= take
            if layer.quantity_remaining <= 0:
                layer.status = "CLOSED"
            if remaining <= 0:
                break
        if remaining > 0:
            raise ConflictError(code="NO_COST_LAYER", message="No hay capas de costo suficientes para valorar la salida.")
        return round(total_cost / quantity, 6)
    # Promedio ponderado
    total_qty = sum(layer.quantity_remaining for layer in layers)
    total_value = sum(float(layer.quantity_remaining) * float(layer.unit_cost or 0) for layer in layers)
    if total_qty <= 0:
        return None
    avg = total_value / total_qty
    for layer in layers:
        share = remaining * (layer.quantity_remaining / total_qty)
        layer.quantity_remaining = round(layer.quantity_remaining - share, 6)
        if layer.quantity_remaining <= 0:
            layer.status = "CLOSED"
    return round(avg, 6)


def valuation(db: Session, *, company_id: str, product_id: str | None = None, warehouse_id: str | None = None) -> float:
    """Valoración del inventario según capas (FR-003-081)."""
    query = select(CostLayer).where(CostLayer.company_id == company_id, CostLayer.quantity_remaining > 0)
    if product_id:
        query = query.where(CostLayer.product_id == product_id)
    if warehouse_id:
        query = query.where(CostLayer.warehouse_id == warehouse_id)
    layers = db.execute(query).scalars().all()
    return round(sum(float(layer.quantity_remaining) * float(layer.unit_cost or 0) for layer in layers), 6)


# --------------------------------------------------------------------------- #
# Lotes y seriales (FR-003-030..036)
# --------------------------------------------------------------------------- #
def create_lot(db: Session, *, company_id: str, product_id: str, lot_number: str,
               manufacture_date=None, expiry_date=None, supplier_id: str | None = None,
               receipt_ref: str | None = None, actor: str | None = None) -> InventoryLot:
    company_id = _company(company_id, obj="lote")
    _require_product(db, company_id, product_id)
    if manufacture_date and expiry_date and manufacture_date > expiry_date:
        raise KontrolError(code="INVALID_EXPIRY", message="La fecha de fabricación no puede ser posterior al vencimiento", status_code=422)
    dup = (
        db.execute(
            select(InventoryLot).where(InventoryLot.company_id == company_id,
                                       InventoryLot.product_id == product_id,
                                       InventoryLot.lot_number == lot_number)
        )
        .scalars()
        .first()
    )
    if dup:
        raise ConflictError(code="LOT_DUPLICATE", message="Ya existe un lote con ese número para el producto.")
    lot = InventoryLot(company_id=company_id, product_id=product_id, lot_number=lot_number,
                       manufacture_date=manufacture_date, expiry_date=expiry_date,
                       supplier_id=supplier_id, receipt_ref=receipt_ref, status="DISPONIBLE", created_by=actor)
    db.add(lot)
    db.flush()
    return lot


def create_serial(db: Session, *, company_id: str, product_id: str, serial: str,
                  imei1: str | None = None, imei2: str | None = None, mac: str | None = None,
                  lot_id: str | None = None, warehouse_id: str | None = None,
                  actor: str | None = None) -> ProductSerial:
    company_id = _company(company_id, obj="serial")
    _require_product(db, company_id, product_id)
    dup = db.execute(select(ProductSerial).where(ProductSerial.company_id == company_id, ProductSerial.serial == serial)).scalars().first()
    if dup:
        raise ConflictError(code="SERIAL_DUPLICATE", message="Ya existe un serial con ese valor.")
    ps = ProductSerial(company_id=company_id, product_id=product_id, serial=serial, imei1=imei1, imei2=imei2,
                       mac=mac, lot_id=lot_id, warehouse_id=warehouse_id, status="DISPONIBLE", created_by=actor)
    db.add(ps)
    db.flush()
    return ps


def fefo_pick_lots(db: Session, *, company_id: str, product_id: str, quantity: float) -> list[InventoryLot]:
    """Selecciona lotes por FEFO (primero en expirar) para una salida (FR-003-034)."""
    return list(
        db.execute(
            select(InventoryLot)
            .where(InventoryLot.company_id == company_id, InventoryLot.product_id == product_id,
                   InventoryLot.status.in_(["DISPONIBLE"]))
            .order_by(InventoryLot.expiry_date.asc().nulls_last())
        )
        .scalars()
        .all()
    )


def transition_lot(db: Session, *, lot: InventoryLot, target: str, actor: str | None = None) -> InventoryLot:
    _assert_transition(lot.status, target, LOT_SERIAL_TRANSITIONS, "el lote")
    lot.status = target
    lot.updated_at = datetime.now(UTC)
    db.flush()
    return lot


def transition_serial(db: Session, *, serial: ProductSerial, target: str) -> ProductSerial:
    _assert_transition(serial.status, target, LOT_SERIAL_TRANSITIONS, "el serial")
    serial.status = target
    serial.updated_at = datetime.now(UTC)
    db.flush()
    return serial


# --------------------------------------------------------------------------- #
# Reservas (FR-003-040..043)
# --------------------------------------------------------------------------- #
def reserve(db: Session, *, company_id: str, source_document: str | None, product_id: str,
            warehouse_id: str, quantity: float, lot_id: str | None = None, serial_id: str | None = None,
            expires_in_days: int | None = None, actor: str | None = None) -> Reservation:
    company_id = _company(company_id, obj="reserva")
    if quantity <= 0:
        raise KontrolError(code="INVALID_QUANTITY", message="La cantidad reservada debe ser positiva", status_code=422)
    warehouse = _require_warehouse(db, company_id, warehouse_id)
    _require_product(db, company_id, product_id)
    available = get_available(db, company_id=company_id, product_id=product_id, warehouse_id=warehouse_id,
                              location_id=None, lot_id=lot_id, serial_id=serial_id)
    if quantity > available and not _allow_negative(warehouse):
        raise ConflictError(code="INSUFFICIENT_AVAILABLE", message=f"No hay disponible suficiente (disponible: {available}).")

    reservation = Reservation(
        company_id=company_id, source_document=source_document, product_id=product_id,
        warehouse_id=warehouse_id, lot_id=lot_id, serial_id=serial_id, quantity=quantity,
        status="ACTIVE", created_by=actor,
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days) if expires_in_days else None,
    )
    db.add(reservation)
    db.flush()
    balance = _get_balance(db, company_id=company_id, warehouse_id=warehouse_id, location_id=None,
                           product_id=product_id, lot_id=lot_id, serial_id=serial_id, state="DISPONIBLE")
    balance.qty_reserved = round(balance.qty_reserved + quantity, 6)
    _refresh_available(balance)
    db.flush()
    return reservation


def release_reservation(db: Session, *, reservation: Reservation, actor: str | None = None) -> Reservation:
    if reservation.status != "ACTIVE":
        raise ConflictError(code="RESERVATION_NOT_ACTIVE", message="La reserva no está activa.")
    reservation.status = "RELEASED"
    balance = _get_balance(db, company_id=reservation.company_id, warehouse_id=reservation.warehouse_id,
                           location_id=None, product_id=reservation.product_id, lot_id=reservation.lot_id,
                           serial_id=reservation.serial_id, state="DISPONIBLE")
    balance.qty_reserved = round(max(balance.qty_reserved - reservation.quantity, 0.0), 6)
    _refresh_available(balance)
    db.flush()
    return reservation


def expire_reservations(db: Session, *, company_id: str) -> int:
    now = datetime.now(UTC)
    active = db.execute(
        select(Reservation).where(Reservation.company_id == company_id, Reservation.status == "ACTIVE",
                                  Reservation.expires_at.isnot(None), Reservation.expires_at < now)
    ).scalars().all()
    for r in active:
        r.status = "EXPIRED"
        balance = _get_balance(db, company_id=r.company_id, warehouse_id=r.warehouse_id, location_id=None,
                               product_id=r.product_id, lot_id=r.lot_id, serial_id=r.serial_id, state="DISPONIBLE")
        balance.qty_reserved = round(max(balance.qty_reserved - r.quantity, 0.0), 6)
        _refresh_available(balance)
    db.flush()
    return len(active)


# --------------------------------------------------------------------------- #
# Transferencias (FR-003-060..062)
# --------------------------------------------------------------------------- #
def transition_transfer(db: Session, *, transfer: Transfer, target: str, actor: str | None = None) -> Transfer:
    _assert_transition(transfer.status, target, TRANSFER_TRANSITIONS, "la transferencia")
    transfer.status = target
    transfer.updated_at = datetime.now(UTC)
    db.flush()
    return transfer


def confirm_transfer_ship(db: Session, *, transfer: Transfer, shipment_ref: str | None = None,
                          actor: str | None = None) -> Transfer:
    """Confirmación de envío: genera salidas de origen y pasa a IN_TRANSIT.

    Permitido desde APPROVED o PICKING (DOC-03 §13: APPROVED → PICKING → IN_TRANSIT).
    """
    if transfer.status not in ("APPROVED", "PICKING"):
        raise ConflictError(code="INVALID_STATE", message="La transferencia debe estar aprobada o en picking para enviarse.")
    lines = db.execute(select(TransferLine).where(TransferLine.transfer_id == transfer.id)).scalars().all()
    out_type = _get_movement_type_by_code(db, transfer.company_id, "TRANSFERENCIA_SALIDA")
    for line in lines:
        record_movement(
            db, company_id=transfer.company_id, warehouse_id=transfer.origin_warehouse_id,
            product_id=line.product_id, movement_type_id=str(out_type.id), quantity=-line.quantity_sent,
            document_ref=f"TRANSFER:{transfer.id}", actor=actor,
        )
    transfer.shipment_ref = shipment_ref or transfer.shipment_ref
    transfer.status = "IN_TRANSIT"
    transfer.updated_at = datetime.now(UTC)
    db.flush()
    return transfer


def confirm_transfer_receipt(db: Session, *, transfer: Transfer, receipt_ref: str | None = None,
                             received: dict[str, float] | None = None, actor: str | None = None) -> Transfer:
    """Confirmación de recepción: entradas en destino y diferencias (FR-003-062)."""
    if transfer.status not in ("IN_TRANSIT", "PARTIALLY_RECEIVED"):
        raise ConflictError(code="INVALID_STATE", message="La transferencia debe estar en tránsito para recibirse.")
    lines = db.execute(select(TransferLine).where(TransferLine.transfer_id == transfer.id)).scalars().all()
    in_type = _get_movement_type_by_code(db, transfer.company_id, "TRANSFERENCIA_ENTRADA")
    received = received or {}
    any_partial = False
    for line in lines:
        qty = received.get(str(line.id), line.quantity_sent)
        qty = min(qty, line.quantity_sent)
        line.quantity_received = qty
        line.difference = round(line.quantity_sent - qty, 6)
        if line.difference and line.difference > 0:
            line.destination_state = "CUARENTENA"
        if qty > 0:
            record_movement(
                db, company_id=transfer.company_id, warehouse_id=transfer.destination_warehouse_id,
                product_id=line.product_id, movement_type_id=str(in_type.id), quantity=qty,
                document_ref=f"TRANSFER:{transfer.id}", actor=actor,
            )
        if line.difference and line.difference > 0:
            any_partial = True
    transfer.receipt_ref = receipt_ref or transfer.receipt_ref
    transfer.status = "PARTIALLY_RECEIVED" if any_partial else "RECEIVED"
    transfer.updated_at = datetime.now(UTC)
    db.flush()
    return transfer


# --------------------------------------------------------------------------- #
# Conteos (FR-003-070/071)
# --------------------------------------------------------------------------- #
def transition_count(db: Session, *, count: StockCount, target: str, actor: str | None = None) -> StockCount:
    _assert_transition(count.status, target, COUNT_TRANSITIONS, "el conteo")
    count.status = target
    count.updated_at = datetime.now(UTC)
    db.flush()
    return count


def record_count_line(db: Session, *, count_id: str, product_id: str, expected_qty: float,
                      counted_qty: float | None = None, location_id: str | None = None,
                      lot_id: str | None = None) -> StockCountLine:
    line = StockCountLine(count_id=count_id, product_id=product_id, location_id=location_id, lot_id=lot_id,
                          expected_qty=expected_qty, counted_qty=counted_qty,
                          variance=round((counted_qty or 0.0) - expected_qty, 6))
    db.add(line)
    db.flush()
    return line


def approve_count(db: Session, *, count: StockCount, actor: str | None = None) -> StockCount:
    """Aprueba el conteo y genera los ajustes/movimientos por diferencia (FR-003-071)."""
    _assert_transition(count.status, "APPROVED", COUNT_TRANSITIONS, "el conteo")
    lines = db.execute(select(StockCountLine).where(StockCountLine.count_id == count.id)).scalars().all()
    adj_type = _get_movement_type_by_code(db, count.company_id, "CONTEO")
    for line in lines:
        variance = (line.counted_qty or 0.0) - line.expected_qty
        if abs(variance) < 1e-9:
            continue
        record_movement(
            db, company_id=count.company_id, warehouse_id=count.warehouse_id,
            product_id=line.product_id, movement_type_id=str(adj_type.id), quantity=round(variance, 6),
            document_ref=f"COUNT:{count.id}", actor=actor,
        )
    count.status = "APPROVED"
    count.updated_at = datetime.now(UTC)
    db.flush()
    return count


# --------------------------------------------------------------------------- #
# Ajustes (FR-003-072/073)
# --------------------------------------------------------------------------- #
def create_adjustment(db: Session, *, company_id: str, warehouse_id: str, product_id: str, quantity: float,
                      reason: str, evidence_ref: str | None = None, unit_cost: float | None = None,
                      currency: str = "VED", actor: str | None = None) -> InventoryAdjustment:
    company_id = _company(company_id, obj="ajuste")
    _require_warehouse(db, company_id, warehouse_id)
    _require_product(db, company_id, product_id)
    if quantity == 0:
        raise KontrolError(code="ZERO_QUANTITY", message="La cantidad del ajuste no puede ser cero", status_code=422)
    adjustment = InventoryAdjustment(company_id=company_id, warehouse_id=warehouse_id, product_id=product_id,
                                     quantity=quantity, reason=reason, evidence_ref=evidence_ref,
                                     unit_cost=unit_cost, currency=currency, status="DRAFT", created_by=actor)
    db.add(adjustment)
    db.flush()
    return adjustment


def transition_adjustment(db: Session, *, adjustment: InventoryAdjustment, target: str,
                          actor: str | None = None) -> InventoryAdjustment:
    _assert_transition(adjustment.status, target, ADJUSTMENT_TRANSITIONS, "el ajuste")
    adjustment.status = target
    adjustment.updated_at = datetime.now(UTC)
    if target in ("APPROVED", "REJECTED"):
        adjustment.approver_id = actor
    db.flush()
    return adjustment


def apply_adjustment(db: Session, *, adjustment: InventoryAdjustment, actor: str | None = None) -> InventoryAdjustment:
    """Aplica el ajuste aprobado generando el movimiento (nunca edita el saldo)."""
    _assert_transition(adjustment.status, "APPLIED", ADJUSTMENT_TRANSITIONS, "el ajuste")
    adj_type = _get_movement_type_by_code(db, adjustment.company_id, "AJUSTE_POSITIVO" if adjustment.quantity > 0 else "AJUSTE_NEGATIVO")
    record_movement(
        db, company_id=adjustment.company_id, warehouse_id=adjustment.warehouse_id,
        product_id=adjustment.product_id, movement_type_id=str(adj_type.id), quantity=adjustment.quantity,
        unit_cost=adjustment.unit_cost, currency=adjustment.currency,
        document_ref=f"ADJUSTMENT:{adjustment.id}", actor=actor,
    )
    adjustment.status = "APPLIED"
    adjustment.updated_at = datetime.now(UTC)
    db.flush()
    return adjustment


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def _get_movement_type_by_code(db: Session, company_id: str, code: str) -> MovementType:
    mtype = _get_movement_type_by_code_optional(db, code)
    if not mtype and code in BASE_MOVEMENT_TYPES:
        # Auto-configuración idempotente (instalaciones frescas y existentes).
        name, direction = BASE_MOVEMENT_TYPES[code]
        mtype = MovementType(company_id=None, code=code, name=name, direction=direction,
                             affects_balance=True, status="ACTIVE", created_by=None)
        db.add(mtype)
        db.flush()
    if not mtype:
        raise NotFoundError(code="MOVEMENT_TYPE_NOT_FOUND", message=f"Tipo de movimiento '{code}' no configurado.")
    return mtype


def _get_movement_type_by_code_optional(db: Session, code: str) -> MovementType | None:
    return (
        db.execute(select(MovementType).where(MovementType.code == code))
        .scalars()
        .first()
    )


def balance_dict(balance: InventoryBalance) -> dict:
    return {
        "id": balance.id,
        "company_id": balance.company_id,
        "warehouse_id": balance.warehouse_id,
        "location_id": balance.location_id,
        "product_id": balance.product_id,
        "lot_id": balance.lot_id,
        "serial_id": balance.serial_id,
        "state": balance.state,
        "qty_on_hand": balance.qty_on_hand,
        "qty_reserved": balance.qty_reserved,
        "qty_available": balance.qty_available,
        "last_rebuilt_at": balance.last_rebuilt_at.isoformat() if balance.last_rebuilt_at else None,
    }


def movement_dict(movement: InventoryMovement) -> dict:
    return {
        "id": movement.id,
        "company_id": movement.company_id,
        "warehouse_id": movement.warehouse_id,
        "location_id": movement.location_id,
        "product_id": movement.product_id,
        "movement_type_id": movement.movement_type_id,
        "quantity": movement.quantity,
        "unit_cost": movement.unit_cost,
        "currency": movement.currency,
        "document_ref": movement.document_ref,
        "occurred_at": movement.occurred_at.isoformat() if movement.occurred_at else None,
        "reversed_by_id": movement.reversed_by_id,
        "status": movement.status,
        "allowed_actions": movement_allowed_actions(movement),
    }
