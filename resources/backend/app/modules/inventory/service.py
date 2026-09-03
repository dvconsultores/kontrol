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
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.approvals import integration as approvals_integration
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
from app.modules.master_data import uom as uom_engine
from app.modules.organization.models import Warehouse
from app.modules.organization.service import warehouse_belongs_to
from app.shared import audit as audit_service


def _audit(db: Session, *, action: str, entity_type: str, entity_id: str,
           company_id: str, actor: str | None = None, **kw: Any) -> None:
    """Registra un evento de auditoría de negocio (KAUD-001 → FR-009-022)."""
    audit_service.record_audit(
        db, action=action, entity_type=entity_type, entity_id=entity_id,
        company_id=company_id, user_id=actor, source="API", **kw,
    )

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


def _dec(value: Any, places: int = 6) -> Decimal:
    """Coerción a `Decimal` en la frontera del servicio.

    Desde la Spec 011 las cantidades son `NUMERIC` en la base y `Decimal` en el
    ORM, pero la API sigue recibiendo números. La conversión ocurre **una vez,
    aquí**: mezclar `float` y `Decimal` en aritmética es el defecto `KQA-100`
    que rompió factura, pago, cobro y notas.
    """
    if value is None:
        return Decimal(0)
    if isinstance(value, Decimal):
        return value.quantize(Decimal(1).scaleb(-places))
    return Decimal(str(value)).quantize(Decimal(1).scaleb(-places))


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
            qty_on_hand=Decimal(0),
            qty_reserved=Decimal(0),
            qty_available=Decimal(0),
        )
        db.add(balance)
        db.flush()
    return balance


def _refresh_available(balance: InventoryBalance) -> None:
    balance.qty_available = _dec(balance.qty_on_hand) - _dec(balance.qty_reserved)


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
                qty_on_hand=Decimal(0), qty_reserved=Decimal(0), qty_available=Decimal(0),
            ),
        )
        bal.qty_on_hand = _dec(bal.qty_on_hand) + _dec(m.quantity)

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
                qty_on_hand=Decimal(0), qty_reserved=Decimal(0), qty_available=Decimal(0),
            ),
        )
        bal.qty_reserved = _dec(bal.qty_reserved) + _dec(r.quantity)

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
    if not warehouse or not warehouse_belongs_to(company_id, warehouse):
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
    presentation_id: str | None = None,
    actor: str | None = None,
    occurred_at: datetime | None = None,
    idempotency_key: str | None = None,
) -> InventoryMovement:
    """Registra un movimiento balanceado e inmutable (FR-003-020/021/022).

    Desde la Spec 011 el movimiento **captura su semántica de unidad**: la
    cantidad se registra tal como se expresó, y su equivalente en unidad base se
    calcula con el motor único de conversión y se congela (R-D0-09-1/2). Un
    movimiento nace congelado: no tiene borrador.
    """
    company_id = _company(company_id, obj="movimiento")
    if quantity == 0:
        raise KontrolError(code="ZERO_QUANTITY", message="La cantidad del movimiento no puede ser cero", status_code=422)

    if idempotency_key:
        existing = db.execute(
            select(InventoryMovement).where(InventoryMovement.idempotency_key == idempotency_key,
                                            InventoryMovement.company_id == company_id)).scalars().first()
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

    # Semántica de unidad (Spec 011): se resuelve **antes** de escribir. El
    # signo se conserva: la conversión opera sobre la magnitud.
    conversion = uom_engine.to_base(db, abs(signed), product_id, presentation_id, occurred_at)
    base_signed = conversion.base_quantity if signed > 0 else -conversion.base_quantity
    base_unit = uom_engine.base_unit_of(db, product_id)
    base_unit_id = base_unit.id if base_unit is not None else None

    movement = InventoryMovement(
        company_id=company_id,
        warehouse_id=warehouse_id,
        location_id=location_id,
        product_id=product_id,
        movement_type_id=movement_type_id,
        quantity=signed,
        unit_id=base_unit_id,
        uom_id=base_unit_id,
        presentation_id=presentation_id,
        conversion_factor_snapshot=conversion.factor,
        base_quantity=base_signed,
        uom_source=uom_engine.SOURCE_CAPTURED,
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

    # El primer movimiento hace inmutable la unidad base del producto: a partir
    # de aquí, cambiarla reinterpretaría este movimiento (R-011-3).
    uom_engine.lock_base_unit(db, product_id)

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
    balance.qty_on_hand = _dec(balance.qty_on_hand) + _dec(signed)
    _refresh_available(balance)
    db.flush()
    _audit(db, action="INVENTORY_MOVEMENT", entity_type="InventoryMovement", entity_id=str(movement.id),
           company_id=company_id, actor=actor,
           after={"product_id": product_id, "quantity": float(signed), "document_ref": document_ref})
    return movement


def reverse_movement(db: Session, *, movement: InventoryMovement, actor: str | None = None,
                     occurred_at: datetime | None = None) -> InventoryMovement:
    """Crea un movimiento reverso vinculado (FR-003-022, P5). Nunca borra el original."""
    if movement.reversed_by_id is not None:
        raise ConflictError(code="ALREADY_REVERSED", message="El movimiento ya fue revertido.")
    mtype = _get_movement_type_by_code_optional(db, movement.company_id, "REVERSO")
    if mtype is None:
        mtype = MovementType(company_id=movement.company_id, code="REVERSO",
                             name="Reverso de movimiento",
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
    _audit(db, action="INVENTORY_MOVEMENT_REVERSED", entity_type="InventoryMovement", entity_id=str(movement.id),
           company_id=movement.company_id, actor=actor, after={"reverse_id": str(reverse.id)})
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


def _consume_cost(db: Session, *, company_id: str, product_id: str, warehouse_id: str,
                  quantity: float | Decimal) -> Decimal | None:
    """Consume capas de costo (FIFO o promedio) y devuelve el costo unitario.

    Íntegramente en `Decimal`: desde la Spec 011 las cantidades son `NUMERIC` y
    el costo también. Mezclar aquí un `float` reintroduciría `KQA-100`.
    """
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
    demand = _dec(quantity)
    remaining = demand
    if method == "FIFO":
        total_cost = Decimal(0)
        for layer in layers:
            take = min(_dec(layer.quantity_remaining), remaining)
            total_cost += take * _dec(layer.unit_cost or 0)
            layer.quantity_remaining = _dec(layer.quantity_remaining) - take
            remaining -= take
            if layer.quantity_remaining <= 0:
                layer.status = "CLOSED"
            if remaining <= 0:
                break
        if remaining > 0:
            raise ConflictError(code="NO_COST_LAYER",
                                message="No hay capas de costo suficientes para valorar la salida.")
        if demand == 0:
            return None
        return _dec(total_cost / demand)

    # Promedio ponderado
    total_qty = sum((_dec(layer.quantity_remaining) for layer in layers), Decimal(0))
    total_value = sum((_dec(layer.quantity_remaining) * _dec(layer.unit_cost or 0)
                       for layer in layers), Decimal(0))
    if total_qty <= 0:
        return None
    average = _dec(total_value / total_qty)
    for layer in layers:
        share = remaining * (_dec(layer.quantity_remaining) / total_qty)
        layer.quantity_remaining = _dec(layer.quantity_remaining) - _dec(share)
        if layer.quantity_remaining <= 0:
            layer.status = "CLOSED"
    return average



def valuation(db: Session, *, company_id: str, product_id: str | None = None, warehouse_id: str | None = None) -> float:
    """Valoración del inventario según capas (FR-003-081)."""
    query = select(CostLayer).where(CostLayer.company_id == company_id, CostLayer.quantity_remaining > 0)
    if product_id:
        query = query.where(CostLayer.product_id == product_id)
    if warehouse_id:
        query = query.where(CostLayer.warehouse_id == warehouse_id)
    layers = db.execute(query).scalars().all()
    return float(sum((_dec(layer.quantity_remaining) * _dec(layer.unit_cost or 0)
                      for layer in layers), Decimal(0)))


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
# Reservas (FR-003-040..043 · Spec 030 · ADR-D0-003 v2)
# --------------------------------------------------------------------------- #
#: Estados terminales de una reserva y el motivo con el que se cierran.
RESERVATION_TRIGGER_ORDER = "ORDER_CONFIRMATION"
RESERVATION_TRIGGER_MANUAL = "MANUAL"
RESERVATION_SOURCE_ORDER = "SALES_ORDER"
RESERVATION_SOURCE_MANUAL = "MANUAL"


def _base_qty(reservation: Reservation) -> Decimal:
    """Lo que la reserva compromete en unidad base.

    Las filas anteriores a la Spec 030 no tenían `base_quantity`: el motor
    siempre trató `quantity` como base, y la migración 0043 lo dejó escrito.
    """
    return _dec(reservation.base_quantity if reservation.base_quantity is not None else reservation.quantity)


def _audit_reservation(db: Session, *, action: str, reservation: Reservation, actor: str | None,
                       before_status: str | None, extra: dict[str, Any] | None = None) -> None:
    """Contrato de auditoría de D0-03 §7: quién, qué pedido y línea, cuánto en
    tecleado y en base, con qué disparador y por qué motivo."""
    after = {
        "status": reservation.status,
        "source_type": reservation.source_type,
        "source_order_id": reservation.source_order_id,
        "source_line_id": reservation.source_line_id,
        "warehouse_id": reservation.warehouse_id,
        "product_id": reservation.product_id,
        "lot_id": reservation.lot_id,
        "serial_id": reservation.serial_id,
        "quantity": str(reservation.quantity),
        "base_quantity": str(_base_qty(reservation)),
        "uom_id": reservation.uom_id,
        "presentation_id": reservation.presentation_id,
        "conversion_factor_snapshot": (str(reservation.conversion_factor_snapshot)
                                       if reservation.conversion_factor_snapshot is not None else None),
        "trigger": reservation.trigger,
        "oversell": bool(reservation.oversell),
        "release_reason": reservation.release_reason,
        "expires_at": reservation.expires_at.isoformat() if reservation.expires_at else None,
    }
    if extra:
        after.update(extra)
    audit_service.record_audit(
        db, action=action, entity_type="Reservation", entity_id=str(reservation.id),
        company_id=reservation.company_id, user_id=actor, source="API",
        before={"status": before_status} if before_status else None, after=after,
        reason=reservation.release_reason)


def lock_balance(db: Session, *, company_id: str, warehouse_id: str, product_id: str,
                 lot_id: str | None = None, serial_id: str | None = None,
                 state: str = "DISPONIBLE") -> InventoryBalance:
    """La fila de saldo **bloqueada** (`SELECT … FOR UPDATE`) dentro de la
    transacción actual (R-D0-03-3, IMP-030-021).

    Si no existe, se crea bajo un savepoint: dos transacciones que llegan a la
    vez al mismo producto sin saldo previo compiten en el índice único
    `uq_inventory_balances_key`; la que pierde relee y se bloquea sobre la fila
    de la que ganó. En SQLite `FOR UPDATE` no existe y se omite: por eso la
    prueba de carrera solo vale sobre PostgreSQL (P21).

    `populate_existing`: sin él, si el saldo ya estaba en el mapa de identidad de
    esta sesión, SQLAlchemy devolvería el objeto con los valores que leyó
    **antes** del bloqueo. La espera habría servido de nada: se decidiría sobre
    un disponible viejo. Con él, la fila bloqueada sobrescribe los atributos.
    """
    def _stmt():
        return (
            select(InventoryBalance).where(
                InventoryBalance.company_id == company_id,
                InventoryBalance.warehouse_id == warehouse_id,
                InventoryBalance.location_id.is_(None),
                InventoryBalance.product_id == product_id,
                InventoryBalance.lot_id.is_(None) if lot_id is None else InventoryBalance.lot_id == lot_id,
                InventoryBalance.serial_id.is_(None) if serial_id is None else InventoryBalance.serial_id == serial_id,
                InventoryBalance.state == state,
            ).with_for_update().execution_options(populate_existing=True)
        )

    balance = db.execute(_stmt()).scalars().first()
    if balance is not None:
        return balance
    try:
        with db.begin_nested():
            balance = InventoryBalance(
                company_id=company_id, warehouse_id=warehouse_id, location_id=None,
                product_id=product_id, lot_id=lot_id, serial_id=serial_id, state=state,
                qty_on_hand=Decimal(0), qty_reserved=Decimal(0), qty_available=Decimal(0))
            db.add(balance)
            db.flush()
    except IntegrityError:
        balance = None
    locked = db.execute(_stmt()).scalars().first()
    if locked is None:  # pragma: no cover - imposible tras insertar o perder la carrera
        raise ConflictError(code="BALANCE_LOCK_FAILED", message="No fue posible bloquear el saldo.")
    return locked


def available_under_lock(balance: InventoryBalance) -> Decimal:
    """Disponible leído **después** del bloqueo, que es el único que vale."""
    return _dec(balance.qty_on_hand) - _dec(balance.qty_reserved)


def reserve(db: Session, *, company_id: str, source_document: str | None, product_id: str,
            warehouse_id: str, quantity: float, lot_id: str | None = None, serial_id: str | None = None,
            expires_in_days: int | None = None, actor: str | None = None,
            source_type: str | None = None, source_order_id: str | None = None,
            source_line_id: str | None = None, trigger: str | None = None,
            uom_id: str | None = None, presentation_id: str | None = None,
            conversion_factor_snapshot: Decimal | None = None, base_quantity: Decimal | float | None = None,
            uom_source: str | None = None, expires_at: datetime | None = None) -> Reservation:
    """Compromete inventario sin moverlo (FR-003-041).

    La disponibilidad se lee con la fila de saldo bloqueada: leerla antes y
    bloquear después deja exactamente la ventana que dos vendedores necesitan
    para comprometer la misma unidad (D0-03, análisis de concurrencia §1).
    `quantity` es la cantidad tecleada y `base_quantity` la que compromete el
    saldo; sin presentación son la misma.
    """
    company_id = _company(company_id, obj="reserva")
    qty = _dec(quantity)
    if qty <= 0:
        raise KontrolError(code="INVALID_QUANTITY", message="La cantidad reservada debe ser positiva", status_code=422)
    base = _dec(base_quantity) if base_quantity is not None else qty
    if base <= 0:
        raise KontrolError(code="INVALID_QUANTITY", message="La cantidad base reservada debe ser positiva", status_code=422)
    warehouse = _require_warehouse(db, company_id, warehouse_id)
    _require_product(db, company_id, product_id)

    balance = lock_balance(db, company_id=company_id, warehouse_id=warehouse_id, product_id=product_id,
                           lot_id=lot_id, serial_id=serial_id)
    available = available_under_lock(balance)
    oversell = False
    if base > available:
        if not _allow_negative(warehouse):
            raise ConflictError(
                code="INSUFFICIENT_AVAILABLE",
                message=f"No hay disponible suficiente (disponible: {available}).",
                details={"product_id": product_id, "warehouse_id": warehouse_id,
                         "requested_base": str(base), "available_base": str(available)})
        oversell = True

    if source_type is None:
        source_type = RESERVATION_SOURCE_ORDER if source_order_id else RESERVATION_SOURCE_MANUAL
    if trigger is None:
        trigger = RESERVATION_TRIGGER_ORDER if source_type == RESERVATION_SOURCE_ORDER else RESERVATION_TRIGGER_MANUAL
    if expires_at is None and expires_in_days:
        expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)
    if uom_id is None and presentation_id is None:
        base_unit = uom_engine.base_unit_of(db, product_id)
        uom_id = str(base_unit.id) if base_unit is not None else None
        uom_source = uom_source or uom_engine.SOURCE_CAPTURED
        conversion_factor_snapshot = conversion_factor_snapshot if conversion_factor_snapshot is not None else Decimal(1)

    reservation = Reservation(
        company_id=company_id, source_document=source_document, product_id=product_id,
        warehouse_id=warehouse_id, lot_id=lot_id, serial_id=serial_id, quantity=qty,
        status="ACTIVE", created_by=actor, expires_at=expires_at,
        source_type=source_type, source_order_id=source_order_id, source_line_id=source_line_id,
        trigger=trigger, oversell=oversell,
        uom_id=uom_id, presentation_id=presentation_id,
        conversion_factor_snapshot=conversion_factor_snapshot, base_quantity=base, uom_source=uom_source,
    )
    db.add(reservation)
    db.flush()
    balance.qty_reserved = _dec(balance.qty_reserved) + base
    _refresh_available(balance)
    db.flush()
    _audit_reservation(db, action="RESERVATION_CREATED", reservation=reservation, actor=actor,
                       before_status=None,
                       extra={"available_before": str(available), "available_after": str(available - base)})
    return reservation


def _close_reservation(db: Session, *, reservation: Reservation, status: str, reason: str | None,
                       actor: str | None, action: str) -> Reservation:
    """Cierra una reserva ACTIVE devolviendo (o consumiendo) lo comprometido.

    El saldo se bloquea antes de restar: liberar y reservar el mismo producto a
    la vez no puede dejar el contador con un valor que ninguna de las dos
    transacciones escribió.
    """
    before = reservation.status
    balance = lock_balance(db, company_id=reservation.company_id, warehouse_id=reservation.warehouse_id,
                           product_id=reservation.product_id, lot_id=reservation.lot_id,
                           serial_id=reservation.serial_id)
    reservation.status = status
    reservation.released_at = datetime.now(UTC)
    reservation.released_by = actor
    reservation.release_reason = reason
    reservation.updated_at = datetime.now(UTC)
    balance.qty_reserved = max(_dec(balance.qty_reserved) - _base_qty(reservation), Decimal(0))
    _refresh_available(balance)
    db.flush()
    _audit_reservation(db, action=action, reservation=reservation, actor=actor, before_status=before)
    return reservation


def release_reservation(db: Session, *, reservation: Reservation, actor: str | None = None,
                        reason: str | None = None) -> Reservation:
    """Libera: lo comprometido vuelve al disponible. Exige que esté ACTIVE."""
    if reservation.status != "ACTIVE":
        raise ConflictError(code="RESERVATION_NOT_ACTIVE", message="La reserva no está activa.")
    return _close_reservation(db, reservation=reservation, status="RELEASED", reason=reason,
                              actor=actor, action="RESERVATION_RELEASED")


def release_if_active(db: Session, *, reservation: Reservation, actor: str | None = None,
                      reason: str | None = None) -> bool:
    """Liberación idempotente para los flujos del pedido (IMP-030-020): una
    reserva que ya no está ACTIVE no vuelve a restar nada."""
    if reservation.status != "ACTIVE":
        return False
    _close_reservation(db, reservation=reservation, status="RELEASED", reason=reason,
                       actor=actor, action="RESERVATION_RELEASED")
    return True


def expire_if_active(db: Session, *, reservation: Reservation, actor: str | None = None) -> bool:
    """Vence una reserva concreta si sigue ACTIVE (flujo de expiración del pedido)."""
    if reservation.status != "ACTIVE":
        return False
    _close_reservation(db, reservation=reservation, status="EXPIRED", reason="EXPIRED",
                       actor=actor, action="RESERVATION_EXPIRED")
    return True


def fulfill_reservation(db: Session, *, reservation: Reservation, actor: str | None = None) -> bool:
    """Consume: la mercancía salió físicamente (R-D0-03-7). No es una liberación."""
    if reservation.status != "ACTIVE":
        return False
    _close_reservation(db, reservation=reservation, status="FULFILLED", reason="DISPATCHED",
                       actor=actor, action="RESERVATION_FULFILLED")
    return True


def reservations_for_orders(db: Session, *, company_id: str,
                            order_ids: list[str]) -> list[Reservation]:
    """Las reservas de varios pedidos en **una** consulta.

    El listado de pedidos serializa N pedidos: pedirlas de una en una convertiría
    una pantalla en N consultas.
    """
    if not order_ids:
        return []
    return list(db.execute(
        select(Reservation).where(Reservation.company_id == company_id,
                                  Reservation.source_order_id.in_(order_ids))
        .order_by(Reservation.created_at)).scalars().all())


def order_reservations(db: Session, *, company_id: str, order_id: str,
                       only_active: bool = True) -> list[Reservation]:
    stmt = select(Reservation).where(Reservation.company_id == company_id,
                                     Reservation.source_order_id == order_id)
    if only_active:
        stmt = stmt.where(Reservation.status == "ACTIVE")
    return list(db.execute(stmt.order_by(Reservation.created_at)).scalars().all())


def expire_due_reservations(db: Session, *, company_id: str, source_type: str | None,
                            now: datetime | None = None, actor: str | None = None) -> list[Reservation]:
    """Vence las reservas ACTIVE cuyo `expires_at` ya pasó, para un tipo de origen.

    Las de pedido (`SALES_ORDER`) las vence el flujo del pedido, que además
    cierra el pedido: nunca queda un pedido vivo sin reserva (R-D0-03-8).
    Idempotente: una segunda pasada no encuentra nada.
    """
    momento = now or datetime.now(UTC)
    stmt = select(Reservation).where(
        Reservation.company_id == company_id, Reservation.status == "ACTIVE",
        Reservation.expires_at.isnot(None), Reservation.expires_at < momento)
    if source_type == RESERVATION_SOURCE_ORDER:
        stmt = stmt.where(Reservation.source_type == RESERVATION_SOURCE_ORDER)
    else:
        stmt = stmt.where((Reservation.source_type.is_(None)) | (Reservation.source_type != RESERVATION_SOURCE_ORDER))
    vencidas = list(db.execute(stmt).scalars().all())
    for r in vencidas:
        _close_reservation(db, reservation=r, status="EXPIRED", reason="EXPIRED", actor=actor,
                           action="RESERVATION_EXPIRED")
    return vencidas


def expire_reservations(db: Session, *, company_id: str, actor: str | None = None) -> int:
    """Expiración de las reservas **manuales** (endpoint de inventario).

    Las reservas de pedido no se tocan desde aquí: su expiración es una
    transición del pedido (`sales.expirar_reservas_de_pedidos`).
    """
    return len(expire_due_reservations(db, company_id=company_id, source_type=None, actor=actor))


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
    """Transición del conteo, gobernada por el motor de aprobaciones (Spec 045)."""
    _assert_transition(count.status, target, COUNT_TRANSITIONS, "el conteo")
    if target in ("SUBMITTED", "REVIEWED"):
        approvals_integration.require_for_document(
            db, company_id=count.company_id,
            process_type=approvals_integration.PROCESS_INVENTORY_COUNT,
            document_type="StockCount", document_id=str(count.id),
            context=_count_context(db, count), actor=actor)
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


def _count_context(db: Session, count: StockCount) -> dict[str, Any]:
    """Contexto plano del conteo para el motor de aprobaciones (Spec 045)."""
    lines = db.execute(select(StockCountLine).where(
        StockCountLine.count_id == count.id)).scalars().all()
    variance = sum(abs(float(line.variance or 0.0)) for line in lines)
    return {"variance_total": variance, "line_count": len(lines),
            "warehouse_id": count.warehouse_id}


def approve_count(db: Session, *, count: StockCount, actor: str | None = None) -> StockCount:
    """Aprueba el conteo y genera los ajustes/movimientos por diferencia (FR-003-071)."""
    _assert_transition(count.status, "APPROVED", COUNT_TRANSITIONS, "el conteo")
    approvals_integration.ensure_approved(
        db, company_id=count.company_id, document_type="StockCount",
        document_id=str(count.id), what="el conteo")
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
    """Transición del ajuste, gobernada por el motor de aprobaciones (Spec 045).

    La segregación deja de estar codificada aquí: la decide la política de la
    empresa (`ADR-D0-002` R-D0-02-5). Sin política, el comportamiento no cambia.
    """
    _assert_transition(adjustment.status, target, ADJUSTMENT_TRANSITIONS, "el ajuste")
    if target in ("SUBMITTED", "PENDING_APPROVAL"):
        approvals_integration.require_for_document(
            db, company_id=adjustment.company_id,
            process_type=approvals_integration.PROCESS_INVENTORY_ADJUSTMENT,
            document_type="InventoryAdjustment", document_id=str(adjustment.id),
            context={"quantity": float(adjustment.quantity or 0),
                     "amount": float(adjustment.unit_cost or 0) * abs(float(adjustment.quantity or 0)),
                     "currency": getattr(adjustment, "currency", "VED") or "VED",
                     "warehouse_id": adjustment.warehouse_id,
                     "reason": adjustment.reason},
            actor=actor)
    if target == "APPROVED":
        approvals_integration.ensure_approved(
            db, company_id=adjustment.company_id, document_type="InventoryAdjustment",
            document_id=str(adjustment.id), what="el ajuste")
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
    mtype = _get_movement_type_by_code_optional(db, company_id, code)
    if not mtype and code in BASE_MOVEMENT_TYPES:
        # Auto-configuración idempotente, **por empresa**: cada una necesita su
        # propio catálogo de tipos, igual que su propio almacén.
        name, direction = BASE_MOVEMENT_TYPES[code]
        mtype = MovementType(company_id=company_id, code=code, name=name, direction=direction,
                             affects_balance=True, status="ACTIVE", created_by=None)
        db.add(mtype)
        db.flush()
    if not mtype:
        raise NotFoundError(code="MOVEMENT_TYPE_NOT_FOUND", message=f"Tipo de movimiento '{code}' no configurado.")
    return mtype


def _get_movement_type_by_code_optional(db: Session, company_id: str,
                                        code: str) -> MovementType | None:
    """El tipo de movimiento de esta empresa, o el global si lo hay.

    Antes buscaba **solo por código**, así que el tipo «ENTRADA» que creara una
    empresa lo consumía la siguiente que moviera existencias: el parámetro
    `company_id` llegaba hasta aquí y no se usaba.

    El alcance global sí existe y es deliberado —la API lo expone como
    `global_scope`, para instalaciones que quieren un catálogo común—, así que
    se admite, pero el propio de la empresa tiene preferencia.
    """
    candidatos = db.execute(select(MovementType).where(
        MovementType.code == code,
        MovementType.company_id.in_([company_id, None]),
    )).scalars().all()
    propios = [m for m in candidatos if m.company_id == company_id]
    return propios[0] if propios else (candidatos[0] if candidatos else None)


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
