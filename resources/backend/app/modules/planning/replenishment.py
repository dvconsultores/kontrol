from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import NotFoundError
from app.core.integrity import es_violacion_unica
from app.core.logging import get_logger
from app.modules.inventory.models import InventoryMovement
from app.modules.master_data.models import CatalogItem
from app.modules.notifications import service as notifications_service
from app.modules.organization.models import Company, Warehouse
from app.modules.planning import service as planning_service
from app.modules.planning.engine import compute_plan
from app.modules.planning.models import PlanningPolicy, ReplenishmentNeed, ReplenishmentScanCursor
from app.modules.purchasing.models import PurchaseRequisition
from app.modules.scheduler.service import Contexto, Resultado
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio

logger = get_logger(__name__)

TRIGGER_METHOD = "AVAILABLE_AT_OR_BELOW_REORDER_POINT_V1"
MAX_EVALUATIONS_PER_TICK = 500
ALERT_SOURCE_TYPE = "ReplenishmentNeed"
ALERT_ROUTE_KEY = "replenishment_need"
ALERT_CATEGORY = "replenishment.need_detected"
ALERT_MESSAGE_KEY = "replenishment.need_detected.alert"


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def condition_met(plan: dict) -> bool:
    if plan.get("status") != "OK":
        return False
    projected = _decimal(plan.get("projected_available"))
    reorder_point = _decimal(plan.get("reorder_point"))
    recommended_quantity = _decimal(plan.get("recommended_quantity"))
    if projected is None or reorder_point is None or recommended_quantity is None:
        return False
    return projected <= reorder_point and recommended_quantity > 0


@dataclass
class EvaluationResult:
    seen: int = 0
    processed: int = 0
    skipped: int = 0
    failed: int = 0


def _resolve(db: Session, need: ReplenishmentNeed, reason: str, now: datetime) -> None:
    need.status = "RESOLVED"
    need.resolved_at = now
    need.resolution_reason = reason
    db.flush()
    if need.alert_id:
        notifications_service.resolver_alerta_de_sistema(
            db,
            company_id=need.company_id,
            dedupe_key=f"replenishment-need:{need.id}",
            momento=now,
        )
    record_audit(
        db,
        action="REPLENISHMENT_NEED_RESOLVED",
        entity_type="ReplenishmentNeed",
        entity_id=str(need.id),
        company_id=need.company_id,
        user_id=None,
        source="SCHEDULER",
        after={
            "available": str(need.current_available) if need.current_available is not None else None,
            "reason": reason,
            "recommended_quantity": str(need.current_recommended_quantity) if need.current_recommended_quantity is not None else None,
            "reorder_point": str(need.current_reorder_point) if need.current_reorder_point is not None else None,
        },
    )


def _ensure_alert(db: Session, need: ReplenishmentNeed, company_id: str, correlation_id: str | None) -> None:
    producto = db.get(CatalogItem, need.product_id)
    almacen = db.get(Warehouse, need.warehouse_id)
    if producto is None or almacen is None:
        return
    alerta, _created = notifications_service.crear_alerta(
        db,
        notifications_service.Efecto(
            company_id=company_id,
            category=ALERT_CATEGORY,
            severity="WARNING",
            message_key=ALERT_MESSAGE_KEY,
            message_params={
                "product_code": producto.code,
                "product_name": producto.name,
                "warehouse_code": almacen.code,
            },
            source_type=ALERT_SOURCE_TYPE,
            source_id=str(need.id),
            route_key=ALERT_ROUTE_KEY,
            dedupe_key=f"replenishment-need:{need.id}",
            correlation_id=correlation_id,
        ),
    )
    if alerta is not None and need.alert_id is None:
        need.alert_id = str(alerta.id)


def _evaluate_one(
    db: Session,
    *,
    company_id: str,
    warehouse_id: str,
    product_id: str,
    now: datetime,
    correlation_id: str | None,
) -> str:
    active = db.scalars(
        select(ReplenishmentNeed)
        .where(
            ReplenishmentNeed.company_id == company_id,
            ReplenishmentNeed.warehouse_id == warehouse_id,
            ReplenishmentNeed.product_id == product_id,
            ReplenishmentNeed.status == "ACTIVE",
        )
        .with_for_update()
    ).first()

    producto = db.get(CatalogItem, product_id)
    if producto is None or producto.company_id != company_id or producto.status != "ACTIVE":
        if active is not None:
            _resolve(db, active, "PRODUCT_INACTIVE", now)
            db.commit()
            return "RESOLVED"
        return "NONE"

    almacen = db.get(Warehouse, warehouse_id)
    if almacen is None or almacen.company_id != company_id or almacen.status != "ACTIVE":
        if active is not None:
            _resolve(db, active, "WAREHOUSE_INACTIVE", now)
            db.commit()
            return "RESOLVED"
        return "NONE"

    policy = planning_service.resolve_policy(
        db,
        company_id=company_id,
        warehouse_id=warehouse_id,
        on_date=hoy_de_negocio(now),
    )
    if policy is None or not policy.auto_replenishment_enabled:
        if active is not None:
            _resolve(db, active, "POLICY_DISABLED", now)
            db.commit()
            return "RESOLVED"
        return "NONE"

    plan = compute_plan(db, company_id=company_id, warehouse_id=warehouse_id, product_id=product_id, now=now)

    if condition_met(plan):
        if active is None:
            need = ReplenishmentNeed(
                company_id=company_id,
                warehouse_id=warehouse_id,
                product_id=product_id,
                status="ACTIVE",
                trigger_method=TRIGGER_METHOD,
                triggered_at=now,
                last_evaluated_at=now,
                trigger_policy_id=plan["policy"]["id"],
                trigger_policy_version=plan["policy"]["version"],
                trigger_policy_code=plan["policy"]["code"],
                trigger_available=_decimal(plan["available"]),
                trigger_on_hand=_decimal(plan["on_hand"]),
                trigger_reserved=_decimal(plan["reserved"]),
                trigger_reorder_point=_decimal(plan["reorder_point"]),
                trigger_projected_demand=_decimal(plan["projected_demand"]),
                trigger_avg_daily_demand=_decimal(plan["avg_daily_demand"]),
                trigger_safety_stock=_decimal(plan["safety_stock"]),
                trigger_recommended_quantity=_decimal(plan["recommended_quantity"]),
                trigger_open_supply=_decimal(plan.get("open_supply")),
                trigger_projected_available=_decimal(plan.get("projected_available")),
                trigger_rotation_band_code=plan["rotation_band"]["code"] if plan.get("rotation_band") else None,
                trigger_calculated_at=datetime.fromisoformat(plan["calculated_at"]),
                trigger_snapshot=plan,
                current_policy_version=plan["policy"]["version"],
                current_available=_decimal(plan["available"]),
                current_reorder_point=_decimal(plan["reorder_point"]),
                current_projected_demand=_decimal(plan["projected_demand"]),
                current_recommended_quantity=_decimal(plan["recommended_quantity"]),
                current_open_supply=_decimal(plan.get("open_supply")),
                current_projected_available=_decimal(plan.get("projected_available")),
                current_rotation_band_code=plan["rotation_band"]["code"] if plan.get("rotation_band") else None,
            )
            try:
                with db.begin_nested():
                    db.add(need)
                    db.flush()
            except IntegrityError as exc:
                if es_violacion_unica(exc, "uq_replenishment_needs_active"):
                    return "KEPT"
                raise
            _ensure_alert(db, need, company_id, correlation_id)
            record_audit(
                db,
                action="REPLENISHMENT_NEED_DETECTED",
                entity_type="ReplenishmentNeed",
                entity_id=str(need.id),
                company_id=company_id,
                user_id=None,
                source="SCHEDULER",
                after={
                    "available": str(need.trigger_available),
                    "policy_version": str(need.trigger_policy_version),
                    "product_id": product_id,
                    "recommended_quantity": str(need.trigger_recommended_quantity),
                    "reorder_point": str(need.trigger_reorder_point),
                    "warehouse_id": warehouse_id,
                },
            )
            db.commit()
            return "OPENED"

        active.last_evaluated_at = now
        active.current_policy_version = plan["policy"]["version"]
        active.current_available = _decimal(plan["available"])
        active.current_reorder_point = _decimal(plan["reorder_point"])
        active.current_projected_demand = _decimal(plan["projected_demand"])
        active.current_recommended_quantity = _decimal(plan["recommended_quantity"])
        active.current_open_supply = _decimal(plan.get("open_supply"))
        active.current_projected_available = _decimal(plan.get("projected_available"))
        active.current_rotation_band_code = plan["rotation_band"]["code"] if plan.get("rotation_band") else None
        _ensure_alert(db, active, company_id, correlation_id)
        db.commit()
        return "KEPT"

    if active is not None:
        active.last_evaluated_at = now
        active.current_policy_version = plan["policy"]["version"] if plan.get("policy") else None
        active.current_available = _decimal(plan.get("available"))
        active.current_reorder_point = _decimal(plan.get("reorder_point"))
        active.current_projected_demand = _decimal(plan.get("projected_demand"))
        active.current_recommended_quantity = _decimal(plan.get("recommended_quantity"))
        active.current_open_supply = _decimal(plan.get("open_supply"))
        active.current_projected_available = _decimal(plan.get("projected_available"))
        active.current_rotation_band_code = plan["rotation_band"]["code"] if plan.get("rotation_band") else None
        reason = "CONDITION_CLEARED" if plan.get("status") == "OK" else "PLAN_UNAVAILABLE"
        _resolve(db, active, reason, now)
        db.commit()
        return "RESOLVED"
    return "NONE"


def _active_needs_for_company(db: Session, company_id: str) -> list[ReplenishmentNeed]:
    return list(
        db.scalars(
            select(ReplenishmentNeed)
            .where(
                ReplenishmentNeed.company_id == company_id,
                ReplenishmentNeed.status == "ACTIVE",
            )
            .order_by(ReplenishmentNeed.warehouse_id, ReplenishmentNeed.product_id)
        ).all()
    )


def _candidate_keys(db: Session, company_id: str, warehouse_id: str) -> list[str]:
    rows = db.execute(
        select(InventoryMovement.product_id)
        .join(CatalogItem, and_(CatalogItem.id == InventoryMovement.product_id, CatalogItem.company_id == company_id))
        .where(
            InventoryMovement.company_id == company_id,
            InventoryMovement.warehouse_id == warehouse_id,
            CatalogItem.item_type == "PRODUCT",
            CatalogItem.status == "ACTIVE",
        )
        .distinct()
        .order_by(InventoryMovement.product_id)
    ).scalars().all()
    keys = [f"{warehouse_id}:{product_id}" for product_id in rows]
    keys.sort()
    return keys


def _get_cursor(db: Session, company_id: str) -> ReplenishmentScanCursor | None:
    return db.scalars(select(ReplenishmentScanCursor).where(ReplenishmentScanCursor.company_id == company_id)).first()


def evaluate_replenishment_needs(
    session_factory: sessionmaker,
    *,
    now: datetime,
    correlation_id: str | None = None,
    limit: int = MAX_EVALUATIONS_PER_TICK,
) -> EvaluationResult:
    result = EvaluationResult()
    processed: set[tuple[str, str]] = set()

    with session_factory() as db:
        companies = list(
            db.scalars(
                select(Company.id)
                .join(PlanningPolicy, and_(PlanningPolicy.company_id == Company.id, PlanningPolicy.status == "ACTIVE"))
                .where(PlanningPolicy.auto_replenishment_enabled.is_(True))
                .distinct()
                .order_by(Company.id)
            ).all()
        )
        active_rows = db.execute(
            select(
                ReplenishmentNeed.company_id,
                ReplenishmentNeed.warehouse_id,
                ReplenishmentNeed.product_id,
            )
            .where(ReplenishmentNeed.status == "ACTIVE")
            .order_by(ReplenishmentNeed.company_id, ReplenishmentNeed.warehouse_id, ReplenishmentNeed.product_id)
        ).all()

    active_tuples = [(row[0], row[1], row[2]) for row in active_rows]

    for company_id, warehouse_id, product_id in active_tuples:
        if result.processed >= limit:
            result.skipped += 1
            continue
        result.seen += 1
        with session_factory() as db:
            try:
                _evaluate_one(
                    db,
                    company_id=company_id,
                    warehouse_id=warehouse_id,
                    product_id=product_id,
                    now=now,
                    correlation_id=correlation_id,
                )
                result.processed += 1
                processed.add((company_id, f"{warehouse_id}:{product_id}"))
            except Exception:
                db.rollback()
                result.failed += 1
                logger.exception("Error evaluando necesidad activa %s %s %s", company_id, warehouse_id, product_id)

    for company_id in companies:
        if result.processed >= limit:
            result.skipped += 1
            continue
        with session_factory() as db:
            warehouses = list(
                db.scalars(
                    select(Warehouse.id)
                    .where(Warehouse.company_id == company_id, Warehouse.status == "ACTIVE")
                    .order_by(Warehouse.id)
                ).all()
            )
        for warehouse_id in warehouses:
            if result.processed >= limit:
                result.skipped += 1
                continue
            with session_factory() as db:
                try:
                    policy = planning_service.resolve_policy(
                        db,
                        company_id=company_id,
                        warehouse_id=warehouse_id,
                        on_date=hoy_de_negocio(now),
                    )
                except Exception:
                    db.rollback()
                    result.failed += 1
                    logger.exception("Error resolviendo política %s %s", company_id, warehouse_id)
                    continue
            if policy is None or not policy.auto_replenishment_enabled:
                continue

            with session_factory() as db:
                keys = _candidate_keys(db, company_id, warehouse_id)
                cursor = _get_cursor(db, company_id)

            if not keys:
                with session_factory() as db:
                    cursor = _get_cursor(db, company_id)
                    if cursor is not None and cursor.last_key is not None:
                        cursor.last_key = None
                        db.commit()
                continue

            ordered = list(sorted(set(keys)))
            if cursor is not None and cursor.last_key is not None:
                start_idx = None
                for idx, key in enumerate(ordered):
                    if key > cursor.last_key:
                        start_idx = idx
                        break
                if start_idx is None:
                    start_idx = 0
                rotated = ordered[start_idx:] + ordered[:start_idx]
            else:
                rotated = ordered

            last_processed_key: str | None = None
            completed_full = True
            for key in rotated:
                if result.processed >= limit:
                    completed_full = False
                    result.skipped += 1
                    continue
                if (company_id, key) in processed:
                    last_processed_key = key
                    continue
                wh_id, prod_id = key.split(":", 1)
                result.seen += 1
                with session_factory() as db:
                    try:
                        _evaluate_one(
                            db,
                            company_id=company_id,
                            warehouse_id=wh_id,
                            product_id=prod_id,
                            now=now,
                            correlation_id=correlation_id,
                        )
                        result.processed += 1
                        processed.add((company_id, f"{wh_id}:{prod_id}"))
                        last_processed_key = key
                    except Exception:
                        db.rollback()
                        result.failed += 1
                        logger.exception("Error evaluando candidato %s %s %s", company_id, wh_id, prod_id)

            with session_factory() as db:
                cursor = _get_cursor(db, company_id)
                if cursor is None:
                    cursor = ReplenishmentScanCursor(company_id=company_id, last_key=None)
                    db.add(cursor)
                if completed_full:
                    cursor.last_key = None
                elif last_processed_key is not None:
                    cursor.last_key = last_processed_key
                db.commit()

    return result


def _recibido_sin_confirmar_derivado(
    projected: Decimal | None,
    available: Decimal | None,
    open_supply: Decimal | None,
) -> Decimal | None:
    if projected is None or available is None or open_supply is None:
        return None
    return projected - available - open_supply


def _need_trigger_dict(need: ReplenishmentNeed) -> dict[str, Any]:
    def _d(value: Decimal | None) -> str | None:
        if value is None:
            return None
        return format(value.quantize(Decimal("0.000001")), "f")

    received_unconfirmed = _recibido_sin_confirmar_derivado(
        need.trigger_projected_available,
        need.trigger_available,
        need.trigger_open_supply,
    )

    return {
        "policy_id": need.trigger_policy_id,
        "policy_code": need.trigger_policy_code,
        "policy_version": need.trigger_policy_version,
        "available": _d(need.trigger_available),
        "on_hand": _d(need.trigger_on_hand),
        "reserved": _d(need.trigger_reserved),
        "reorder_point": _d(need.trigger_reorder_point),
        "projected_demand": _d(need.trigger_projected_demand),
        "avg_daily_demand": _d(need.trigger_avg_daily_demand),
        "safety_stock": _d(need.trigger_safety_stock),
        "recommended_quantity": _d(need.trigger_recommended_quantity),
        "open_supply": _d(need.trigger_open_supply),
        "received_unconfirmed": _d(received_unconfirmed),
        "projected_available": _d(need.trigger_projected_available),
        "rotation_band_code": need.trigger_rotation_band_code,
        "calculated_at": need.trigger_calculated_at.isoformat() if need.trigger_calculated_at else None,
    }


def _need_current_dict(need: ReplenishmentNeed) -> dict[str, Any]:
    def _d(value: Decimal | None) -> str | None:
        if value is None:
            return None
        return format(value.quantize(Decimal("0.000001")), "f")

    received_unconfirmed = _recibido_sin_confirmar_derivado(
        need.current_projected_available,
        need.current_available,
        need.current_open_supply,
    )

    return {
        "policy_version": need.current_policy_version,
        "available": _d(need.current_available),
        "reorder_point": _d(need.current_reorder_point),
        "projected_demand": _d(need.current_projected_demand),
        "recommended_quantity": _d(need.current_recommended_quantity),
        "open_supply": _d(need.current_open_supply),
        "received_unconfirmed": _d(received_unconfirmed),
        "projected_available": _d(need.current_projected_available),
        "rotation_band_code": need.current_rotation_band_code,
    }


def need_dict(db: Session, need: ReplenishmentNeed) -> dict[str, Any]:
    producto = db.get(CatalogItem, need.product_id)
    almacen = db.get(Warehouse, need.warehouse_id)
    return {
        "id": str(need.id),
        "status": need.status,
        "trigger_method": need.trigger_method,
        "triggered_at": need.triggered_at.isoformat() if need.triggered_at else None,
        "resolved_at": need.resolved_at.isoformat() if need.resolved_at else None,
        "resolution_reason": need.resolution_reason,
        "last_evaluated_at": need.last_evaluated_at.isoformat() if need.last_evaluated_at else None,
        "product": {
            "id": producto.id if producto else None,
            "code": producto.code if producto else None,
            "name": producto.name if producto else None,
        },
        "warehouse": {
            "id": almacen.id if almacen else None,
            "code": almacen.code if almacen else None,
            "name": almacen.name if almacen else None,
        },
        "trigger": _need_trigger_dict(need),
        "current": _need_current_dict(need),
        "alert_id": need.alert_id,
    }


def need_detail(db: Session, *, company_id: str, need_id: str) -> dict[str, Any]:
    from app.modules.planning.models import RequisitionLinePlan

    need = db.get(ReplenishmentNeed, need_id)
    if need is None or need.company_id != company_id:
        raise NotFoundError(code="REPLENISHMENT_NEED_NOT_FOUND", message="Necesidad no encontrada")
    result = need_dict(db, need)
    result["trigger_snapshot"] = need.trigger_snapshot
    lines = db.execute(
        select(RequisitionLinePlan, PurchaseRequisition)
        .join(
            PurchaseRequisition,
            PurchaseRequisition.id == RequisitionLinePlan.requisition_id,
        )
        .where(RequisitionLinePlan.replenishment_need_id == need_id)
        .order_by(PurchaseRequisition.code)
    ).all()
    result["requisitions"] = [
        {
            "requisition_id": str(plan.requisition_id),
            "requisition_code": req.code,
            "requisition_status": req.status,
            "line_id": str(plan.requisition_line_id),
            "requested_base_quantity": str(plan.requested_base_quantity) if plan.requested_base_quantity is not None else None,
            "calculated_at": plan.calculated_at.isoformat() if plan.calculated_at else None,
        }
        for plan, req in lines
    ]
    return result


def list_needs(
    db: Session,
    *,
    company_id: str,
    status: str | None,
    warehouse_id: str | None,
    q: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    conditions = [ReplenishmentNeed.company_id == company_id]
    if status:
        conditions.append(ReplenishmentNeed.status == status)
    if warehouse_id:
        conditions.append(ReplenishmentNeed.warehouse_id == warehouse_id)
    query = select(ReplenishmentNeed).where(*conditions)
    if q:
        like = f"%{q}%"
        query = query.join(CatalogItem, CatalogItem.id == ReplenishmentNeed.product_id).where(
            CatalogItem.code.ilike(like) | CatalogItem.name.ilike(like)
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        db.scalars(
            query.order_by(ReplenishmentNeed.triggered_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return {
        "items": [need_dict(db, need) for need in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def detectar_necesidades(contexto: Contexto) -> Resultado:
    evaluation = evaluate_replenishment_needs(
        contexto.session_factory,
        now=contexto.now,
        correlation_id=contexto.correlation_id,
    )
    return Resultado(
        seen=evaluation.seen,
        processed=evaluation.processed,
        skipped=evaluation.skipped,
        failed=evaluation.failed,
    )
