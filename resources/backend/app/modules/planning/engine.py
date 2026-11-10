from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.inventory import models as inventory_models
from app.modules.inventory import service as inventory_service
from app.modules.master_data.models import CatalogItem
from app.modules.planning import service as planning_service
from app.modules.planning.models import PlanningPolicy, RotationBand
from app.shared.clock import ahora_de_negocio, hoy_de_negocio, inicio_del_dia_de_negocio

_Q = Decimal("0.000001")


def _q(value: Decimal | int | float | str | None) -> str | None:
    if value is None:
        return None
    return str(Decimal(str(value)).quantize(_Q))


def _quantize(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(_Q)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def compute_plan(
    db: Session,
    *,
    company_id: str,
    warehouse_id: str,
    product_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    # 0. Validaciones
    planning_service._warehouse(db, company_id, warehouse_id)
    product = db.scalars(
        select(CatalogItem).where(
            CatalogItem.id == product_id,
            CatalogItem.company_id == company_id,
            CatalogItem.item_type == "PRODUCT",
        )
    ).first()
    if product is None:
        from app.core.errors import NotFoundError

        raise NotFoundError(code="PRODUCT_NOT_FOUND", message="Producto no encontrado")

    hoy = hoy_de_negocio(now)
    calculated_at = ahora_de_negocio(now)

    # 1. Posición
    on_hand_decimal = inventory_service.warehouse_sellable_on_hand(
        db, company_id=company_id, warehouse_id=warehouse_id, product_id=product_id
    )
    reserved_decimal = Decimal("0")
    balance_anchor = db.scalars(
        select(inventory_models.InventoryBalance).where(
            inventory_models.InventoryBalance.company_id == company_id,
            inventory_models.InventoryBalance.warehouse_id == warehouse_id,
            inventory_models.InventoryBalance.product_id == product_id,
            inventory_models.InventoryBalance.location_id.is_(None),
            inventory_models.InventoryBalance.lot_id.is_(None),
            inventory_models.InventoryBalance.serial_id.is_(None),
            inventory_models.InventoryBalance.state == "DISPONIBLE",
        )
    ).first()
    if balance_anchor is not None and balance_anchor.qty_reserved is not None:
        reserved_decimal = Decimal(str(balance_anchor.qty_reserved))
    available_decimal = on_hand_decimal - reserved_decimal

    result_base: dict[str, Any] = {
        "status": "OK",
        "method": planning_service.METHOD,
        "policy": None,
        "demand_source": None,
        "window_start": None,
        "window_end": None,
        "lookback_days": None,
        "horizon_days": None,
        "lead_time_days": None,
        "safety_mode": None,
        "safety_value": None,
        "history_partial": None,
        "observed_history_days": None,
        "gross_demand": None,
        "returned_quantity": None,
        "net_demand": None,
        "demand_events": None,
        "demand_days": None,
        "first_demand_at": None,
        "last_demand_at": None,
        "avg_daily_demand": None,
        "projected_demand": None,
        "safety_stock": None,
        "reorder_point": None,
        "on_hand": _q(on_hand_decimal),
        "reserved": _q(reserved_decimal),
        "available": _q(available_decimal),
        "open_supply": None,
        "open_supply_available": False,
        "rotation_metric": None,
        "demand_velocity": None,
        "turnover": None,
        "avg_on_hand": None,
        "rotation_band": None,
        "coverage_days": None,
        "recommended_quantity": None,
        "calculated_at": calculated_at.isoformat(),
    }

    # 2. Política
    policy: PlanningPolicy | None = planning_service.resolve_policy(
        db,
        company_id=company_id,
        warehouse_id=warehouse_id,
        on_date=hoy,
    )
    if policy is None:
        result_base["status"] = "PLAN_NOT_CONFIGURED"
        return result_base

    lookback_days = int(policy.lookback_days)
    horizon_days = int(policy.horizon_days)
    lead_time_days = int(policy.lead_time_days)
    safety_mode = str(policy.safety_mode)
    safety_value = Decimal(str(policy.safety_value)) if policy.safety_value is not None else Decimal("0")
    demand_source = str(policy.demand_source)
    rotation_metric = str(policy.rotation_metric)

    result_base["policy"] = {"id": policy.id, "code": policy.code, "version": policy.version}
    result_base["demand_source"] = demand_source
    result_base["lookback_days"] = lookback_days
    result_base["horizon_days"] = horizon_days
    result_base["lead_time_days"] = lead_time_days
    result_base["safety_mode"] = safety_mode
    result_base["safety_value"] = _q(safety_value)
    result_base["rotation_metric"] = rotation_metric

    # 3. Ventana
    start_day = hoy - timedelta(days=lookback_days - 1)
    window_start = inicio_del_dia_de_negocio(start_day)
    window_end = inicio_del_dia_de_negocio(hoy + timedelta(days=1))
    result_base["window_start"] = window_start.isoformat()
    result_base["window_end"] = window_end.isoformat()

    # 4. Historia
    first_at = db.scalars(
        select(func.min(inventory_models.InventoryMovement.occurred_at)).where(
            inventory_models.InventoryMovement.company_id == company_id,
            inventory_models.InventoryMovement.warehouse_id == warehouse_id,
            inventory_models.InventoryMovement.product_id == product_id,
            inventory_models.InventoryMovement.occurred_at < window_end,
        )
    ).first()
    if first_at is None:
        result_base["status"] = "INSUFFICIENT_HISTORY"
        return result_base

    first_day = ahora_de_negocio(first_at).date()
    effective_start = max(first_day, start_day)
    observed_history_days = min(lookback_days, (hoy - effective_start).days + 1)
    result_base["observed_history_days"] = observed_history_days
    result_base["history_partial"] = first_day > start_day

    # 5. Demanda
    movement_type_code_col = inventory_models.MovementType.code
    demand_type_codes: list[str] = []
    return_type_codes: list[str] = []
    if demand_source == "DISPATCHED_SALES":
        demand_type_codes = ["RECLASIFICACION"]
        return_type_codes = ["RECLASIFICACION"]
    elif demand_source == "INVENTORY_ISSUES":
        demand_type_codes = ["SALIDA_DESPACHO"]
        return_type_codes = []

    movements = db.execute(
        select(
            inventory_models.InventoryMovement,
            movement_type_code_col,
        )
        .join(
            inventory_models.MovementType,
            inventory_models.MovementType.id == inventory_models.InventoryMovement.movement_type_id,
        )
        .where(
            inventory_models.InventoryMovement.company_id == company_id,
            inventory_models.InventoryMovement.warehouse_id == warehouse_id,
            inventory_models.InventoryMovement.product_id == product_id,
            inventory_models.InventoryMovement.occurred_at >= window_start,
            inventory_models.InventoryMovement.occurred_at < window_end,
            inventory_models.InventoryMovement.status == "POSTED",
            inventory_models.InventoryMovement.reversed_by_id.is_(None),
        )
    ).all()

    gross_demand = Decimal("0")
    returned_quantity = Decimal("0")
    demand_events = 0
    demand_days: set[date] = set()
    first_demand_at: datetime | None = None
    last_demand_at: datetime | None = None

    for movement, type_code in movements:
        if type_code not in demand_type_codes and type_code not in return_type_codes:
            continue
        base_qty = movement.base_quantity if movement.base_quantity is not None else movement.quantity
        quantity = abs(Decimal(str(base_qty))) if base_qty is not None else Decimal("0")
        occurred = _utc(movement.occurred_at) if movement.occurred_at is not None else None

        is_demand = False
        is_return = False
        if demand_source == "DISPATCHED_SALES":
            if (
                type_code == "RECLASIFICACION"
                and movement.target_state == "DESPACHADO"
            ):
                is_demand = True
            elif (
                type_code == "RECLASIFICACION"
                and movement.source_state == "DESPACHADO"
                and movement.target_state == "DEVUELTO"
            ):
                is_return = True
        elif demand_source == "INVENTORY_ISSUES":
            if type_code == "SALIDA_DESPACHO":
                is_demand = True

        if not is_demand and not is_return:
            continue

        if is_demand:
            gross_demand += quantity
            demand_events += 1
            if occurred is not None:
                day = ahora_de_negocio(occurred).date()
                demand_days.add(day)
                if first_demand_at is None or occurred < first_demand_at:
                    first_demand_at = occurred
                if last_demand_at is None or occurred > last_demand_at:
                    last_demand_at = occurred
        elif is_return:
            returned_quantity += quantity

    net_demand = max(Decimal("0"), gross_demand - returned_quantity)

    result_base["gross_demand"] = _q(gross_demand)
    result_base["returned_quantity"] = _q(returned_quantity)
    result_base["net_demand"] = _q(net_demand)
    result_base["demand_events"] = demand_events
    result_base["demand_days"] = len(demand_days)
    result_base["first_demand_at"] = first_demand_at.isoformat() if first_demand_at else None
    result_base["last_demand_at"] = last_demand_at.isoformat() if last_demand_at else None

    # 6. Método AVG_CALENDAR_WINDOW_V1
    avg = net_demand / Decimal(str(lookback_days))
    projected = avg * Decimal(str(horizon_days))
    safety_stock: Decimal
    if safety_mode == "FIXED_QTY":
        safety_stock = safety_value
    elif safety_mode == "DAYS":
        safety_stock = avg * safety_value
    else:
        safety_stock = Decimal("0")
    reorder_point = avg * Decimal(str(lead_time_days)) + safety_stock
    coverage_days_value: Decimal | None
    if avg > 0:
        coverage_days_value = available_decimal / avg
    else:
        coverage_days_value = None
    recommended_value = max(
        Decimal("0"),
        projected + safety_stock - available_decimal,
    )

    result_base["avg_daily_demand"] = _q(avg)
    result_base["projected_demand"] = _q(projected)
    result_base["safety_stock"] = _q(safety_stock)
    result_base["reorder_point"] = _q(reorder_point)
    result_base["coverage_days"] = _q(coverage_days_value)
    result_base["recommended_quantity"] = _q(recommended_value)

    # 7. Rotación
    demand_velocity = avg
    result_base["demand_velocity"] = _q(demand_velocity)

    # Ledger de existencias: todos los movimientos POSTED del producto y almacén
    all_movements = db.execute(
        select(
            inventory_models.InventoryMovement,
            inventory_models.MovementType.code,
        )
        .join(
            inventory_models.MovementType,
            inventory_models.MovementType.id == inventory_models.InventoryMovement.movement_type_id,
        )
        .where(
            inventory_models.InventoryMovement.company_id == company_id,
            inventory_models.InventoryMovement.warehouse_id == warehouse_id,
            inventory_models.InventoryMovement.product_id == product_id,
            inventory_models.InventoryMovement.status == "POSTED",
        )
    ).all()

    deltas: list[tuple[datetime, Decimal]] = []
    for movement, _type_code in all_movements:
        occurred = _utc(movement.occurred_at) if movement.occurred_at is not None else None
        if occurred is None:
            continue
        base_qty = movement.base_quantity if movement.base_quantity is not None else movement.quantity
        magnitude = abs(Decimal(str(base_qty))) if base_qty is not None else Decimal("0")
        delta = Decimal("0")
        if movement.target_state == "DISPONIBLE":
            delta += magnitude
        if movement.source_state == "DISPONIBLE":
            delta -= magnitude
        if delta != 0:
            deltas.append((occurred, delta))

    saldo_inicial = Decimal("0")
    for occurred, delta in deltas:
        if occurred < window_start:
            saldo_inicial += delta

    daily_closes: list[Decimal] = []
    for day_offset in range(lookback_days):
        day = start_day + timedelta(days=day_offset)
        next_day_start = inicio_del_dia_de_negocio(day + timedelta(days=1))
        cierre = saldo_inicial
        for occurred, delta in deltas:
            if window_start <= occurred < next_day_start:
                cierre += delta
        daily_closes.append(cierre)

    avg_on_hand_value: Decimal | None
    if daily_closes:
        avg_on_hand_value = sum(daily_closes, Decimal("0")) / Decimal(str(len(daily_closes)))
    else:
        avg_on_hand_value = None
    result_base["avg_on_hand"] = _q(avg_on_hand_value)

    turnover_value: Decimal | None = None
    if avg_on_hand_value is not None and avg_on_hand_value > 0:
        turnover_value = net_demand / avg_on_hand_value
    result_base["turnover"] = _q(turnover_value)

    rotation_value: Decimal | None = demand_velocity
    if rotation_metric == "TURNOVER":
        rotation_value = turnover_value

    rotation_band: RotationBand | None = None
    if rotation_value is not None:
        rotation_band = planning_service.band_for(
            db,
            company_id=company_id,
            metric=rotation_metric,
            value=rotation_value,
        )
    result_base["rotation_band"] = (
        {"id": rotation_band.id, "code": rotation_band.code, "name": rotation_band.name}
        if rotation_band is not None
        else None
    )

    return result_base
