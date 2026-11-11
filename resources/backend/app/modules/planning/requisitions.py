from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.master_data import uom as uom_engine
from app.modules.master_data.models import CatalogItem
from app.modules.organization.models import Warehouse
from app.modules.planning.engine import compute_plan
from app.modules.planning.models import ReplenishmentNeed, RequisitionLinePlan
from app.modules.purchasing.models import PurchaseRequisition, RequisitionLine
from app.shared.audit import record_audit


def _warehouse_belongs_to(db: Session, company_id: str, warehouse: Warehouse) -> bool:
    return warehouse.company_id == company_id


def add_planned_line(
    db: Session,
    *,
    company_id: str,
    requisition_id: str,
    product_id: str,
    quantity: Decimal | None,
    presentation_id: str | None,
    notes: str | None,
    use_recommendation: bool,
    expected_policy_version: int | None,
    actor_id: str,
    replenishment_need_id: str | None = None,
) -> tuple[RequisitionLine, RequisitionLinePlan]:
    req = db.get(PurchaseRequisition, requisition_id)
    if not req or req.company_id != company_id:
        raise NotFoundError(code="REQUISITION_NOT_FOUND", message="Requisición no encontrada")
    if req.status != "DRAFT":
        raise ConflictError(code="REQUISITION_NOT_EDITABLE", message="La requisición no es editable")
    if not req.warehouse_id:
        raise KontrolError(
            code="REQUISITION_WAREHOUSE_REQUIRED",
            message="La requisición requiere almacén",
            status_code=422,
        )

    if replenishment_need_id is not None:
        need = db.get(ReplenishmentNeed, replenishment_need_id)
        if need is None or need.company_id != company_id:
            raise NotFoundError(code="REPLENISHMENT_NEED_NOT_FOUND", message="Necesidad no encontrada")
        if need.warehouse_id != req.warehouse_id or need.product_id != product_id:
            raise KontrolError(
                code="REPLENISHMENT_NEED_MISMATCH",
                message="La necesidad no corresponde a este almacén y producto",
                status_code=422,
            )

    plan = compute_plan(db, company_id=company_id, warehouse_id=req.warehouse_id, product_id=product_id)

    current = plan["policy"]["version"] if plan["policy"] else None
    if expected_policy_version is not None and expected_policy_version != current:
        raise ConflictError(
            code="PLANNING_POLICY_STALE",
            message="La política de planificación cambió; vuelve a consultar la sugerencia",
        )

    if use_recommendation:
        if plan["status"] != "OK" or plan["recommended_quantity"] is None:
            raise KontrolError(
                code="RECOMMENDATION_NOT_AVAILABLE",
                message="No hay sugerencia disponible",
                status_code=422,
            )
        base = Decimal(plan["recommended_quantity"])
        if base <= 0:
            raise KontrolError(
                code="RECOMMENDATION_IS_ZERO",
                message="La sugerencia es cero",
                status_code=422,
            )
        if presentation_id is not None:
            raise KontrolError(
                code="INVALID_REQUEST",
                message="No se admite presentación al aceptar la sugerencia",
                status_code=422,
            )
    else:
        if quantity is None or quantity <= 0:
            raise KontrolError(
                code="INVALID_QUANTITY",
                message="Cantidad inválida",
                status_code=422,
            )
        conv = uom_engine.to_base(db, quantity, product_id, presentation_id)
        base = conv.base_quantity

    base_unit = uom_engine.base_unit_of(db, product_id)
    line = RequisitionLine(
        requisition_id=req.id,
        product_id=product_id,
        quantity=base,
        unit_id=base_unit.id if base_unit else None,
        notes=notes,
    )
    db.add(line)
    db.flush()

    def _dec(value):
        return Decimal(value) if value is not None else None

    def _dt(value):
        return datetime.fromisoformat(value) if value is not None else None

    policy = plan.get("policy")
    rotation_band = plan.get("rotation_band")
    recommended = _dec(plan.get("recommended_quantity"))

    line_plan = RequisitionLinePlan(
        company_id=company_id,
        requisition_id=req.id,
        requisition_line_id=line.id,
        warehouse_id=req.warehouse_id,
        product_id=product_id,
        status=plan["status"],
        method=plan["method"],
        policy_id=policy["id"] if policy else None,
        policy_version=policy["version"] if policy else None,
        policy_code=policy["code"] if policy else None,
        demand_source=plan.get("demand_source"),
        window_start=_dt(plan.get("window_start")),
        window_end=_dt(plan.get("window_end")),
        lookback_days=plan.get("lookback_days"),
        horizon_days=plan.get("horizon_days"),
        lead_time_days=plan.get("lead_time_days"),
        safety_mode=plan.get("safety_mode"),
        safety_value=_dec(plan.get("safety_value")),
        history_partial=bool(plan.get("history_partial")),
        observed_history_days=plan.get("observed_history_days"),
        demand_events=plan.get("demand_events"),
        demand_days=plan.get("demand_days"),
        first_demand_at=_dt(plan.get("first_demand_at")),
        last_demand_at=_dt(plan.get("last_demand_at")),
        net_demand=_dec(plan.get("net_demand")),
        avg_daily_demand=_dec(plan.get("avg_daily_demand")),
        projected_demand=_dec(plan.get("projected_demand")),
        safety_stock=_dec(plan.get("safety_stock")),
        reorder_point=_dec(plan.get("reorder_point")),
        on_hand=_dec(plan.get("on_hand")),
        reserved=_dec(plan.get("reserved")),
        available=_dec(plan.get("available")),
        open_supply=_dec(plan.get("open_supply")),
        demand_velocity=_dec(plan.get("demand_velocity")),
        turnover=_dec(plan.get("turnover")),
        avg_on_hand=_dec(plan.get("avg_on_hand")),
        coverage_days=_dec(plan.get("coverage_days")),
        recommended_quantity=recommended,
        open_supply_available=bool(plan.get("open_supply_available")),
        rotation_metric=plan.get("rotation_metric"),
        rotation_band_id=rotation_band["id"] if rotation_band else None,
        rotation_band_code=rotation_band["code"] if rotation_band else None,
        requested_base_quantity=base,
        difference=(base - recommended) if recommended is not None else None,
        accepted_recommendation=use_recommendation,
        calculated_at=_dt(plan["calculated_at"]),
        calculated_by=actor_id,
    replenishment_need_id=replenishment_need_id,
    )
    db.add(line_plan)
    db.flush()

    record_audit(
        db,
        action="REQUISITION_LINE_PLANNED",
        entity_type="RequisitionLine",
        entity_id=str(line.id),
        company_id=company_id,
        user_id=actor_id,
        after={
            "accepted": use_recommendation,
            "difference": str(line_plan.difference) if line_plan.difference is not None else None,
            "policy_version": line_plan.policy_version,
            "recommended_quantity": str(recommended) if recommended is not None else None,
            "requested_base_quantity": str(base),
            "replenishment_need_id": replenishment_need_id,
            "requisition_id": req.id,
            "status": plan["status"],
        },
    )

    return line, line_plan


def line_plan_dict(plan: RequisitionLinePlan) -> dict:
    def dec(value):
        if value is None:
            return None
        return str(Decimal(value).quantize(Decimal("0.000001")))

    def dt(value):
        return value.isoformat() if value is not None else None

    return {
        "id": plan.id,
        "status": plan.status,
        "method": plan.method,
        "policy_id": plan.policy_id,
        "policy_version": plan.policy_version,
        "policy_code": plan.policy_code,
        "demand_source": plan.demand_source,
        "window_start": dt(plan.window_start),
        "window_end": dt(plan.window_end),
        "lookback_days": plan.lookback_days,
        "horizon_days": plan.horizon_days,
        "lead_time_days": plan.lead_time_days,
        "safety_mode": plan.safety_mode,
        "safety_value": dec(plan.safety_value),
        "history_partial": plan.history_partial,
        "observed_history_days": plan.observed_history_days,
        "demand_events": plan.demand_events,
        "demand_days": plan.demand_days,
        "first_demand_at": dt(plan.first_demand_at),
        "last_demand_at": dt(plan.last_demand_at),
        "net_demand": dec(plan.net_demand),
        "avg_daily_demand": dec(plan.avg_daily_demand),
        "projected_demand": dec(plan.projected_demand),
        "safety_stock": dec(plan.safety_stock),
        "reorder_point": dec(plan.reorder_point),
        "on_hand": dec(plan.on_hand),
        "reserved": dec(plan.reserved),
        "available": dec(plan.available),
        "open_supply": dec(plan.open_supply),
        "demand_velocity": dec(plan.demand_velocity),
        "turnover": dec(plan.turnover),
        "avg_on_hand": dec(plan.avg_on_hand),
        "coverage_days": dec(plan.coverage_days),
        "recommended_quantity": dec(plan.recommended_quantity),
        "open_supply_available": plan.open_supply_available,
        "rotation_metric": plan.rotation_metric,
        "rotation_band_id": plan.rotation_band_id,
        "rotation_band_code": plan.rotation_band_code,
        "requested_base_quantity": dec(plan.requested_base_quantity),
        "difference": dec(plan.difference),
        "accepted_recommendation": plan.accepted_recommendation,
        "calculated_at": plan.calculated_at.isoformat(),
        "calculated_by": plan.calculated_by,
        "replenishment_need_id": plan.replenishment_need_id,
    }


def requisition_detail(db: Session, *, company_id: str, requisition_id: str) -> dict:
    req = db.get(PurchaseRequisition, requisition_id)
    if not req or req.company_id != company_id:
        raise NotFoundError(code="REQUISITION_NOT_FOUND", message="Requisición no encontrada")

    warehouse_code = None
    if req.warehouse_id:
        warehouse = db.get(Warehouse, req.warehouse_id)
        if warehouse:
            warehouse_code = warehouse.code

    lines: list[dict[str, object]] = []
    requisition_lines = db.scalars(
        select(RequisitionLine).where(RequisitionLine.requisition_id == req.id).order_by(RequisitionLine.created_at)
    ).all()
    for line in requisition_lines:
        product = db.get(CatalogItem, line.product_id)
        plan = db.scalar(
            select(RequisitionLinePlan).where(RequisitionLinePlan.requisition_line_id == line.id)
        )
        lines.append(
            {
                "id": line.id,
                "product_id": line.product_id,
                "product_code": product.code if product else None,
                "product_name": product.name if product else None,
                "quantity": str(Decimal(line.quantity).quantize(Decimal("0.000001"))),
                "unit_id": line.unit_id,
                "notes": line.notes,
                "plan": line_plan_dict(plan) if plan else None,
            }
        )

    return {
        "id": req.id,
        "code": req.code,
        "status": req.status,
        "warehouse_id": req.warehouse_id,
        "warehouse_code": warehouse_code,
        "need_date": req.need_date.isoformat() if req.need_date else None,
        "lines": lines,
    }
