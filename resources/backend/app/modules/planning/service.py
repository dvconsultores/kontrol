import re
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.organization.models import Warehouse
from app.modules.planning import models as planning_models
from app.shared.audit import record_audit

DEMAND_SOURCES = ("DISPATCHED_SALES", "INVENTORY_ISSUES")
SAFETY_MODES = ("NONE", "FIXED_QTY", "DAYS")
ROTATION_METRICS = ("DEMAND_VELOCITY", "TURNOVER")
METHOD = "AVG_CALENDAR_WINDOW_V1"

_POLICY_KEYS = (
    "code",
    "name",
    "warehouse_id",
    "demand_source",
    "lookback_days",
    "horizon_days",
    "lead_time_days",
    "safety_mode",
    "safety_value",
    "rotation_metric",
    "status",
    "version",
)

_BAND_KEYS = (
    "code",
    "name",
    "metric",
    "lower_bound",
    "upper_bound",
    "sort_order",
    "status",
    "version",
)


def _warehouse(db: Session, company_id: str, warehouse_id: str) -> Warehouse:
    warehouse = db.scalars(
        select(Warehouse).where(
            Warehouse.id == warehouse_id,
            Warehouse.company_id == company_id,
        )
    ).first()
    if warehouse is None:
        raise NotFoundError(code="WAREHOUSE_NOT_FOUND", message="Almacén no encontrado")
    return warehouse


def _validate_policy(data: dict[str, Any]) -> None:
    if data.get("demand_source") not in DEMAND_SOURCES:
        raise KontrolError(code="INVALID_DEMAND_SOURCE", message="Fuente de demanda inválida", status_code=422)
    if not isinstance(data.get("lookback_days"), int) or data["lookback_days"] <= 0:
        raise KontrolError(code="INVALID_LOOKBACK", message="Ventana retrospectiva inválida", status_code=422)
    if not isinstance(data.get("horizon_days"), int) or data["horizon_days"] <= 0:
        raise KontrolError(code="INVALID_HORIZON", message="Horizonte inválido", status_code=422)
    if not isinstance(data.get("lead_time_days"), int) or data["lead_time_days"] < 0:
        raise KontrolError(code="INVALID_LEAD_TIME", message="Lead time inválido", status_code=422)
    if data.get("safety_mode") not in SAFETY_MODES:
        raise KontrolError(code="INVALID_SAFETY_STOCK", message="Modo de stock de seguridad inválido", status_code=422)
    try:
        safety_value = Decimal(str(data.get("safety_value", 0)))
    except Exception as err:
        raise KontrolError(code="INVALID_SAFETY_STOCK", message="Stock de seguridad inválido", status_code=422) from err
    if safety_value < 0:
        raise KontrolError(code="INVALID_SAFETY_STOCK", message="Stock de seguridad inválido", status_code=422)
    if data["safety_mode"] == "NONE":
        data["safety_value"] = Decimal("0")
    else:
        data["safety_value"] = safety_value
    if data.get("rotation_metric") not in ROTATION_METRICS:
        raise KontrolError(code="INVALID_ROTATION_METRIC", message="Métrica de rotación inválida", status_code=422)
    if data.get("status") not in ("ACTIVE", "INACTIVE"):
        raise KontrolError(code="INVALID_STATUS", message="Estado inválido", status_code=422)
    valid_from = _as_date(data.get("valid_from"))
    valid_to = _as_date(data.get("valid_to"))
    if valid_from and valid_to and valid_to < valid_from:
        raise KontrolError(code="INVALID_VALIDITY", message="Rango de vigencia inválido", status_code=422)


def _as_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise KontrolError(
                code="INVALID_VALIDITY",
                message="Fecha de vigencia inválida",
                status_code=422,
            ) from None
    raise KontrolError(
        code="INVALID_VALIDITY",
        message="Fecha de vigencia inválida",
        status_code=422,
    )


def _as_int(value: object, code: str) -> int:
    if isinstance(value, bool):
        raise KontrolError(code=code, message="Valor entero inválido", status_code=422)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        if re.fullmatch(r"[+-]?\d+", value.strip()):
            return int(value.strip())
        raise KontrolError(code=code, message="Valor entero inválido", status_code=422) from None
    if isinstance(value, Decimal):
        if not value.is_finite() or value != value.to_integral_value():
            raise KontrolError(code=code, message="Valor entero inválido", status_code=422) from None
        return int(value)
    raise KontrolError(code=code, message="Valor entero inválido", status_code=422)


def _policy_after(policy: planning_models.PlanningPolicy) -> dict[str, Any]:
    return {
        "code": policy.code,
        "name": policy.name,
        "warehouse_id": policy.warehouse_id,
        "demand_source": policy.demand_source,
        "lookback_days": policy.lookback_days,
        "horizon_days": policy.horizon_days,
        "lead_time_days": policy.lead_time_days,
        "safety_mode": policy.safety_mode,
        "safety_value": str(policy.safety_value),
        "rotation_metric": policy.rotation_metric,
        "status": policy.status,
        "version": policy.version,
    }


def _band_after(band: planning_models.RotationBand) -> dict[str, Any]:
    return {
        "code": band.code,
        "name": band.name,
        "metric": band.metric,
        "lower_bound": str(band.lower_bound),
        "upper_bound": str(band.upper_bound) if band.upper_bound is not None else None,
        "sort_order": band.sort_order,
        "status": band.status,
        "version": band.version,
    }


def create_policy(
    db: Session,
    *,
    company_id: str,
    data: dict[str, Any],
    actor_id: str,
) -> planning_models.PlanningPolicy:
    if data.get("warehouse_id"):
        _warehouse(db, company_id, str(data["warehouse_id"]))
    existing_code = db.scalars(
        select(planning_models.PlanningPolicy).where(
            planning_models.PlanningPolicy.company_id == company_id,
            planning_models.PlanningPolicy.code == data["code"],
        )
    ).first()
    if existing_code is not None:
        raise ConflictError(
            code="PLANNING_POLICY_CODE_TAKEN",
            message="El código de política ya está en uso",
        )
    _validate_policy(data)
    if data.get("status", "ACTIVE") == "ACTIVE":
        warehouse_id = data.get("warehouse_id")
        query = select(planning_models.PlanningPolicy).where(
            planning_models.PlanningPolicy.company_id == company_id,
            planning_models.PlanningPolicy.status == "ACTIVE",
            planning_models.PlanningPolicy.warehouse_id.is_(None) if warehouse_id is None else planning_models.PlanningPolicy.warehouse_id == warehouse_id,
        )
        existing_active = db.scalars(query).first()
        if existing_active is not None:
            raise ConflictError(
                code="PLANNING_POLICY_SCOPE_TAKEN",
                message="Ya existe una política ACTIVA para este alcance",
            )
    policy = planning_models.PlanningPolicy(
        company_id=company_id,
        warehouse_id=str(data["warehouse_id"]) if data.get("warehouse_id") is not None else None,
        code=str(data["code"]),
        name=str(data["name"]),
        demand_source=str(data["demand_source"]),
        lookback_days=_as_int(data["lookback_days"], "INVALID_LOOKBACK"),
        horizon_days=_as_int(data["horizon_days"], "INVALID_HORIZON"),
        lead_time_days=_as_int(data["lead_time_days"], "INVALID_LEAD_TIME"),
        safety_mode=str(data["safety_mode"]),
        safety_value=Decimal(str(data["safety_value"])),
        rotation_metric=str(data["rotation_metric"]),
        status=str(data.get("status", "ACTIVE")),
        valid_from=_as_date(data.get("valid_from")),
        valid_to=_as_date(data.get("valid_to")),
        created_by=actor_id,
    )
    db.add(policy)
    db.flush()
    record_audit(
        db,
        action="PLANNING_POLICY_CREATED",
        entity_type="PlanningPolicy",
        entity_id=str(policy.id),
        company_id=company_id,
        user_id=actor_id,
        after=_policy_after(policy),
    )
    return policy


def update_policy(
    db: Session,
    *,
    company_id: str,
    policy_id: str,
    expected_version: int,
    data: dict[str, Any],
    actor_id: str,
) -> planning_models.PlanningPolicy:
    policy = db.scalars(
        select(planning_models.PlanningPolicy)
        .where(
            planning_models.PlanningPolicy.id == policy_id,
            planning_models.PlanningPolicy.company_id == company_id,
        )
        .with_for_update()
    ).first()
    if policy is None:
        raise NotFoundError(code="PLANNING_POLICY_NOT_FOUND", message="Política de planificación no encontrada")
    if policy.version != expected_version:
        raise ConflictError(code="VERSION_CONFLICT", message="La versión no coincide. Recargue e intente de nuevo.")
    merged = {
        "code": policy.code,
        "name": policy.name,
        "warehouse_id": policy.warehouse_id,
        "demand_source": policy.demand_source,
        "lookback_days": policy.lookback_days,
        "horizon_days": policy.horizon_days,
        "lead_time_days": policy.lead_time_days,
        "safety_mode": policy.safety_mode,
        "safety_value": policy.safety_value,
        "rotation_metric": policy.rotation_metric,
        "status": policy.status,
        "valid_from": policy.valid_from,
        "valid_to": policy.valid_to,
    }
    for key, value in data.items():
        if value is not None:
            merged[key] = value
    if merged.get("warehouse_id"):
        _warehouse(db, company_id, str(merged["warehouse_id"]))
    existing_code = db.scalars(
        select(planning_models.PlanningPolicy).where(
            planning_models.PlanningPolicy.company_id == company_id,
            planning_models.PlanningPolicy.code == merged["code"],
            planning_models.PlanningPolicy.id != policy_id,
        )
    ).first()
    if existing_code is not None:
        raise ConflictError(
            code="PLANNING_POLICY_CODE_TAKEN",
            message="El código de política ya está en uso",
        )
    _validate_policy(merged)
    if merged.get("status", "ACTIVE") == "ACTIVE":
        warehouse_id = merged.get("warehouse_id")
        query = select(planning_models.PlanningPolicy).where(
            planning_models.PlanningPolicy.company_id == company_id,
            planning_models.PlanningPolicy.status == "ACTIVE",
            planning_models.PlanningPolicy.id != policy_id,
            planning_models.PlanningPolicy.warehouse_id.is_(None) if warehouse_id is None else planning_models.PlanningPolicy.warehouse_id == warehouse_id,
        )
        existing_active = db.scalars(query).first()
        if existing_active is not None:
            raise ConflictError(
                code="PLANNING_POLICY_SCOPE_TAKEN",
                message="Ya existe una política ACTIVA para este alcance",
            )
    before = _policy_after(policy)
    policy.code = str(merged["code"])
    policy.name = str(merged["name"])
    policy.warehouse_id = str(merged["warehouse_id"]) if merged.get("warehouse_id") is not None else None
    policy.demand_source = str(merged["demand_source"])
    policy.lookback_days = _as_int(merged["lookback_days"], "INVALID_LOOKBACK")
    policy.horizon_days = _as_int(merged["horizon_days"], "INVALID_HORIZON")
    policy.lead_time_days = _as_int(merged["lead_time_days"], "INVALID_LEAD_TIME")
    policy.safety_mode = str(merged["safety_mode"])
    policy.safety_value = Decimal(str(merged["safety_value"]))
    policy.rotation_metric = str(merged["rotation_metric"])
    policy.status = str(merged["status"])
    policy.valid_from = _as_date(merged.get("valid_from"))
    policy.valid_to = _as_date(merged.get("valid_to"))
    policy.version += 1
    after = _policy_after(policy)
    record_audit(
        db,
        action="PLANNING_POLICY_UPDATED",
        entity_type="PlanningPolicy",
        entity_id=str(policy.id),
        company_id=company_id,
        user_id=actor_id,
        before=before,
        after=after,
    )
    return policy


def list_policies(db: Session, company_id: str) -> list[planning_models.PlanningPolicy]:
    return list(
        db.scalars(
            select(planning_models.PlanningPolicy)
            .where(planning_models.PlanningPolicy.company_id == company_id)
            .order_by(
                planning_models.PlanningPolicy.warehouse_id.is_(None).desc(),
                planning_models.PlanningPolicy.warehouse_id,
                planning_models.PlanningPolicy.code,
            )
        ).all()
    )


def policy_dict(db: Session, policy: planning_models.PlanningPolicy) -> dict[str, Any]:
    data = {
        "id": str(policy.id),
        "company_id": policy.company_id,
        "warehouse_id": policy.warehouse_id,
        "warehouse_code": None,
        "code": policy.code,
        "name": policy.name,
        "demand_source": policy.demand_source,
        "lookback_days": policy.lookback_days,
        "horizon_days": policy.horizon_days,
        "lead_time_days": policy.lead_time_days,
        "safety_mode": policy.safety_mode,
        "safety_value": str(policy.safety_value),
        "rotation_metric": policy.rotation_metric,
        "status": policy.status,
        "valid_from": policy.valid_from.isoformat() if policy.valid_from else None,
        "valid_to": policy.valid_to.isoformat() if policy.valid_to else None,
        "version": policy.version,
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
        "created_by": policy.created_by,
    }
    if policy.warehouse_id:
        warehouse = db.get(Warehouse, policy.warehouse_id)
        if warehouse is not None:
            data["warehouse_code"] = warehouse.code
    return data


def resolve_policy(
    db: Session,
    *,
    company_id: str,
    warehouse_id: str | None,
    on_date: date,
) -> planning_models.PlanningPolicy | None:
    def base_query():
        return select(planning_models.PlanningPolicy).where(
            planning_models.PlanningPolicy.company_id == company_id,
            planning_models.PlanningPolicy.status == "ACTIVE",
        )
    if warehouse_id is not None:
        policy = db.scalars(
            base_query().where(
                planning_models.PlanningPolicy.warehouse_id == warehouse_id,
                (planning_models.PlanningPolicy.valid_from.is_(None)) | (planning_models.PlanningPolicy.valid_from <= on_date),
                (planning_models.PlanningPolicy.valid_to.is_(None)) | (planning_models.PlanningPolicy.valid_to >= on_date),
            ).order_by(planning_models.PlanningPolicy.valid_from.is_(None).desc(), planning_models.PlanningPolicy.valid_from)
        ).first()
        if policy is not None:
            return policy
    policy = db.scalars(
        base_query().where(
            planning_models.PlanningPolicy.warehouse_id.is_(None),
            (planning_models.PlanningPolicy.valid_from.is_(None)) | (planning_models.PlanningPolicy.valid_from <= on_date),
            (planning_models.PlanningPolicy.valid_to.is_(None)) | (planning_models.PlanningPolicy.valid_to >= on_date),
        ).order_by(planning_models.PlanningPolicy.valid_from.is_(None).desc(), planning_models.PlanningPolicy.valid_from)
    ).first()
    return policy


def _validate_band(data: dict[str, Any]) -> None:
    if data.get("metric") not in ROTATION_METRICS:
        raise KontrolError(code="INVALID_ROTATION_METRIC", message="Métrica de rotación inválida", status_code=422)
    try:
        lower = Decimal(str(data["lower_bound"]))
    except Exception as err:
        raise KontrolError(code="INVALID_BAND_RANGE", message="Rango de banda inválido", status_code=422) from err
    if lower < 0:
        raise KontrolError(code="INVALID_BAND_RANGE", message="Rango de banda inválido", status_code=422)
    if data.get("upper_bound") is not None:
        try:
            upper = Decimal(str(data["upper_bound"]))
        except Exception as err:
            raise KontrolError(code="INVALID_BAND_RANGE", message="Rango de banda inválido", status_code=422) from err
        if upper <= lower:
            raise KontrolError(code="INVALID_BAND_RANGE", message="Rango de banda inválido", status_code=422)
    if data.get("status") not in ("ACTIVE", "INACTIVE"):
        raise KontrolError(code="INVALID_STATUS", message="Estado inválido", status_code=422)


def _check_band_overlap(
    db: Session,
    *,
    company_id: str,
    metric: str,
    lower: Decimal,
    upper: Decimal | None,
    exclude_id: str | None = None,
) -> None:
    query = select(planning_models.RotationBand).where(
        planning_models.RotationBand.company_id == company_id,
        planning_models.RotationBand.metric == metric,
        planning_models.RotationBand.status == "ACTIVE",
    )
    if exclude_id is not None:
        query = query.where(planning_models.RotationBand.id != exclude_id)
    bands = db.scalars(query).all()
    for band in bands:
        band_lower = band.lower_bound
        band_upper = band.upper_bound
        overlap_lower = band_lower < upper if upper is not None else True
        overlap_upper = band_upper is None or band_upper > lower
        if overlap_lower and overlap_upper:
            raise ConflictError(
                code="ROTATION_BAND_OVERLAP",
                message="El rango se solapa con otra banda ACTIVA",
            )


def create_band(
    db: Session,
    *,
    company_id: str,
    data: dict[str, Any],
    actor_id: str,
) -> planning_models.RotationBand:
    existing = db.scalars(
        select(planning_models.RotationBand).where(
            planning_models.RotationBand.company_id == company_id,
            planning_models.RotationBand.code == data["code"],
        )
    ).first()
    if existing is not None:
        raise ConflictError(
            code="ROTATION_BAND_CODE_TAKEN",
            message="El código de banda ya está en uso",
        )
    _validate_band(data)
    if data.get("status", "ACTIVE") == "ACTIVE":
        _check_band_overlap(
            db,
            company_id=company_id,
            metric=str(data["metric"]),
            lower=Decimal(str(data["lower_bound"])),
            upper=Decimal(str(data["upper_bound"])) if data.get("upper_bound") is not None else None,
        )
    band = planning_models.RotationBand(
        company_id=company_id,
        code=str(data["code"]),
        name=str(data["name"]),
        metric=str(data["metric"]),
        lower_bound=Decimal(str(data["lower_bound"])),
        upper_bound=Decimal(str(data["upper_bound"])) if data.get("upper_bound") is not None else None,
        sort_order=int(data.get("sort_order", 0)),
        status=str(data.get("status", "ACTIVE")),
        created_by=actor_id,
    )
    db.add(band)
    db.flush()
    record_audit(
        db,
        action="ROTATION_BAND_CREATED",
        entity_type="RotationBand",
        entity_id=str(band.id),
        company_id=company_id,
        user_id=actor_id,
        after=_band_after(band),
    )
    return band


def update_band(
    db: Session,
    *,
    company_id: str,
    band_id: str,
    expected_version: int,
    data: dict[str, Any],
    actor_id: str,
) -> planning_models.RotationBand:
    band = db.scalars(
        select(planning_models.RotationBand)
        .where(
            planning_models.RotationBand.id == band_id,
            planning_models.RotationBand.company_id == company_id,
        )
        .with_for_update()
    ).first()
    if band is None:
        raise NotFoundError(code="ROTATION_BAND_NOT_FOUND", message="Banda de rotación no encontrada")
    if band.version != expected_version:
        raise ConflictError(code="VERSION_CONFLICT", message="La versión no coincide. Recargue e intente de nuevo.")
    merged = {
        "code": band.code,
        "name": band.name,
        "metric": band.metric,
        "lower_bound": band.lower_bound,
        "upper_bound": band.upper_bound,
        "sort_order": band.sort_order,
        "status": band.status,
    }
    for key, value in data.items():
        if value is not None:
            merged[key] = value
    existing = db.scalars(
        select(planning_models.RotationBand).where(
            planning_models.RotationBand.company_id == company_id,
            planning_models.RotationBand.code == merged["code"],
            planning_models.RotationBand.id != band_id,
        )
    ).first()
    if existing is not None:
        raise ConflictError(
            code="ROTATION_BAND_CODE_TAKEN",
            message="El código de banda ya está en uso",
        )
    _validate_band(merged)
    if merged.get("status", "ACTIVE") == "ACTIVE":
        _check_band_overlap(
            db,
            company_id=company_id,
            metric=str(merged["metric"]),
            lower=Decimal(str(merged["lower_bound"])),
            upper=Decimal(str(merged["upper_bound"])) if merged.get("upper_bound") is not None else None,
            exclude_id=band_id,
        )
    before = _band_after(band)
    band.code = str(merged["code"])
    band.name = str(merged["name"])
    band.metric = str(merged["metric"])
    band.lower_bound = Decimal(str(merged["lower_bound"]))
    band.upper_bound = Decimal(str(merged["upper_bound"])) if merged.get("upper_bound") is not None else None
    band.sort_order = _as_int(merged["sort_order"], "INVALID_BAND_RANGE")
    band.status = str(merged["status"])
    band.version += 1
    after = _band_after(band)
    record_audit(
        db,
        action="ROTATION_BAND_UPDATED",
        entity_type="RotationBand",
        entity_id=str(band.id),
        company_id=company_id,
        user_id=actor_id,
        before=before,
        after=after,
    )
    return band


def list_bands(db: Session, company_id: str, metric: str | None = None) -> list[planning_models.RotationBand]:
    query = select(planning_models.RotationBand).where(
        planning_models.RotationBand.company_id == company_id
    )
    if metric is not None:
        query = query.where(planning_models.RotationBand.metric == metric)
    return list(
        db.scalars(
            query.order_by(
                planning_models.RotationBand.metric,
                planning_models.RotationBand.sort_order,
                planning_models.RotationBand.lower_bound,
            )
        ).all()
    )


def band_dict(band: planning_models.RotationBand) -> dict[str, Any]:
    return {
        "id": str(band.id),
        "company_id": band.company_id,
        "code": band.code,
        "name": band.name,
        "metric": band.metric,
        "lower_bound": str(band.lower_bound),
        "upper_bound": str(band.upper_bound) if band.upper_bound is not None else None,
        "sort_order": band.sort_order,
        "status": band.status,
        "version": band.version,
        "created_at": band.created_at.isoformat() if band.created_at else None,
        "updated_at": band.updated_at.isoformat() if band.updated_at else None,
        "created_by": band.created_by,
    }


def band_for(
    db: Session,
    *,
    company_id: str,
    metric: str,
    value: Decimal | None,
) -> planning_models.RotationBand | None:
    if value is None:
        return None
    bands = list_bands(db, company_id, metric=metric)
    for band in bands:
        if band.status != "ACTIVE":
            continue
        if Decimal(str(band.lower_bound)) <= value and (
            band.upper_bound is None or value < Decimal(str(band.upper_bound))
        ):
            return band
    return None
