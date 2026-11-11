from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, require_write_allowed
from app.modules.identity_access.models import User
from app.modules.inventory import models as inventory_models
from app.modules.master_data.models import CatalogItem
from app.modules.planning import replenishment
from app.modules.planning import requisitions as planning_requisitions
from app.modules.planning import service as planning_service
from app.modules.planning.engine import compute_plan

router = APIRouter(prefix="/planning", tags=["planificacion"])


class PolicyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    auto_replenishment_enabled: bool = False
    code: str
    name: str
    warehouse_id: str | None = None
    demand_source: str
    lookback_days: int
    horizon_days: int
    lead_time_days: int
    safety_mode: str
    safety_value: Decimal
    rotation_metric: str
    status: str = "ACTIVE"
    valid_from: date | None = None
    valid_to: date | None = None


class PolicyPatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    auto_replenishment_enabled: bool | None = None
    expected_version: int
    code: str | None = None
    name: str | None = None
    warehouse_id: str | None = None
    demand_source: str | None = None
    lookback_days: int | None = None
    horizon_days: int | None = None
    lead_time_days: int | None = None
    safety_mode: str | None = None
    safety_value: Decimal | None = None
    rotation_metric: str | None = None
    status: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None


class BandBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    name: str
    metric: str
    lower_bound: Decimal
    upper_bound: Decimal | None = None
    sort_order: int = 0
    status: str = "ACTIVE"


class BandPatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int
    code: str | None = None
    name: str | None = None
    metric: str | None = None
    lower_bound: Decimal | None = None
    upper_bound: Decimal | None = None
    sort_order: int | None = None
    status: str | None = None


@router.get("/policies")
def list_policies(
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(get_current_user),
    _: None = Depends(require_permission("maestros", "view")),
) -> dict:
    policies = planning_service.list_policies(db, ctx.company_id)
    return {"items": [planning_service.policy_dict(db, p) for p in policies]}


@router.post("/policies")
def create_policy(
    body: PolicyBody,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(get_current_user),
    _: None = Depends(require_permission("maestros", "create")),
    __: None = Depends(require_write_allowed),
) -> dict:
    policy = planning_service.create_policy(
        db,
        company_id=ctx.company_id,
        data=body.model_dump(exclude_none=True),
        actor_id=str(user.id),
    )
    db.commit()
    return planning_service.policy_dict(db, policy)


@router.patch("/policies/{policy_id}")
def update_policy(
    policy_id: str,
    body: PolicyPatchBody,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(get_current_user),
    _: None = Depends(require_permission("maestros", "edit")),
    __: None = Depends(require_write_allowed),
) -> dict:
    policy = planning_service.update_policy(
        db,
        company_id=ctx.company_id,
        policy_id=policy_id,
        expected_version=body.expected_version,
        data=body.model_dump(exclude_none=True, exclude={"expected_version"}),
        actor_id=str(user.id),
    )
    db.commit()
    return planning_service.policy_dict(db, policy)


@router.get("/rotation-bands")
def list_bands(
    metric: str | None = Query(default=None),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(get_current_user),
    _: None = Depends(require_permission("maestros", "view")),
) -> dict:
    bands = planning_service.list_bands(db, ctx.company_id, metric=metric)
    return {"items": [planning_service.band_dict(b) for b in bands]}


@router.post("/rotation-bands")
def create_band(
    body: BandBody,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(get_current_user),
    _: None = Depends(require_permission("maestros", "create")),
    __: None = Depends(require_write_allowed),
) -> dict:
    band = planning_service.create_band(
        db,
        company_id=ctx.company_id,
        data=body.model_dump(exclude_none=True),
        actor_id=str(user.id),
    )
    db.commit()
    return planning_service.band_dict(band)


@router.patch("/rotation-bands/{band_id}")
def update_band(
    band_id: str,
    body: BandPatchBody,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(get_current_user),
    _: None = Depends(require_permission("maestros", "edit")),
    __: None = Depends(require_write_allowed),
) -> dict:
    band = planning_service.update_band(
        db,
        company_id=ctx.company_id,
        band_id=band_id,
        expected_version=body.expected_version,
        data=body.model_dump(exclude_none=True, exclude={"expected_version"}),
        actor_id=str(user.id),
    )
    db.commit()
    return planning_service.band_dict(band)


@router.get("/plan")
def get_plan(
    warehouse_id: str,
    product_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(get_current_user),
    _: None = Depends(require_permission("compras", "view")),
) -> dict:
    warehouse = planning_service._warehouse(db, ctx.company_id, warehouse_id)
    result = compute_plan(
        db,
        company_id=ctx.company_id,
        warehouse_id=warehouse_id,
        product_id=product_id,
    )
    product = db.scalar(
        select(CatalogItem).where(
            CatalogItem.company_id == ctx.company_id,
            CatalogItem.id == product_id,
        )
    )
    result["product_code"] = product.code if product else None
    result["product_name"] = product.name if product else None
    result["warehouse_code"] = warehouse.code
    return result


@router.get("/plans")
def list_plans(
    warehouse_id: str,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(get_current_user),
    _: None = Depends(require_permission("compras", "view")),
) -> dict:
    warehouse = planning_service._warehouse(db, ctx.company_id, warehouse_id)

    base = select(CatalogItem).where(
        CatalogItem.company_id == ctx.company_id,
        CatalogItem.item_type == "PRODUCT",
        select(inventory_models.InventoryMovement.id)
        .where(
            inventory_models.InventoryMovement.warehouse_id == warehouse_id,
            inventory_models.InventoryMovement.product_id == CatalogItem.id,
            inventory_models.InventoryMovement.company_id == ctx.company_id,
        )
        .exists(),
    )
    if q:
        like = f"%{q}%"
        base = base.where(
            or_(
                CatalogItem.code.ilike(like),
                CatalogItem.name.ilike(like),
            )
        )

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.scalars(
        base.order_by(CatalogItem.code)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    result_items = []
    for product in items:
        plan = compute_plan(
            db,
            company_id=ctx.company_id,
            warehouse_id=warehouse_id,
            product_id=str(product.id),
        )
        plan["product_code"] = product.code
        plan["product_name"] = product.name
        plan["warehouse_code"] = warehouse.code
        result_items.append(plan)

    return {
        "items": result_items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


class PlannedLineBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str
    quantity: Decimal | None = None
    presentation_id: str | None = None
    notes: str | None = None
    use_recommendation: bool = False
    expected_policy_version: int | None = None
    replenishment_need_id: str | None = None


@router.get("/requisitions/{requisition_id}")
def get_requisition_detail(requisition_id: str, db: Session = Depends(get_db),
                           _: User = Depends(require_permission("compras", "view")),
                           ctx: CompanyContext = Depends(get_company_context)):
    return planning_requisitions.requisition_detail(db, company_id=ctx.company_id, requisition_id=requisition_id)


@router.post("/requisitions/{requisition_id}/lines", dependencies=[Depends(require_write_allowed)])
def create_requisition_line(requisition_id: str, body: PlannedLineBody, db: Session = Depends(get_db),
                            actor: User = Depends(require_permission("compras", "create")),
                            ctx: CompanyContext = Depends(get_company_context)):
    line, plan = planning_requisitions.add_planned_line(
        db,
        company_id=ctx.company_id,
        requisition_id=requisition_id,
        product_id=body.product_id,
        quantity=body.quantity,
        presentation_id=body.presentation_id,
        notes=body.notes,
        use_recommendation=body.use_recommendation,
        expected_policy_version=body.expected_policy_version,
        actor_id=str(actor.id),
        replenishment_need_id=body.replenishment_need_id,
    )
    db.commit()
    return {"line_id": line.id, "plan": planning_requisitions.line_plan_dict(plan)}


@router.get(
    "/replenishment-needs",
    response_model=dict,
    summary="Listar necesidades de reposición",
    description="Lista las necesidades de reposición de la empresa con filtros opcionales.",
)
def list_replenishment_needs(
    status: str | None = Query(None, pattern="^(ACTIVE|RESOLVED)$"),
    warehouse_id: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: User = Depends(require_permission("compras", "view")),
) -> dict:
    return replenishment.list_needs(
        db,
        company_id=ctx.company_id,
        status=status,
        warehouse_id=warehouse_id,
        q=q,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/replenishment-needs/{need_id}",
    response_model=dict,
    summary="Detalle de necesidad de reposición",
    description="Muestra el detalle completo de una necesidad de reposición.",
)
def get_replenishment_need(
    need_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _: User = Depends(require_permission("compras", "view")),
) -> dict:
    return replenishment.need_detail(db, company_id=ctx.company_id, need_id=need_id)
