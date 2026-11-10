from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_permission, require_write_allowed
from app.modules.identity_access.models import User
from app.modules.storage import service as storage_service

router = APIRouter(prefix="/storage", tags=["almacenamiento"])


class ConditionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    name: str
    description: str | None = None


class ConditionPatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int
    name: str | None = None
    description: str | None = None
    status: str | None = None


class SizeClassBody(ConditionBody):
    pass


class SizeClassPatchBody(ConditionPatchBody):
    pass


class ProfileBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int | None = None
    weight_value: Decimal | None = None
    weight_unit_id: str | None = None
    volume_value: Decimal | None = None
    volume_unit_id: str | None = None
    size_class_id: str | None = None
    condition_ids: list[str] = Field(default_factory=list)


class RuleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    name: str
    priority: int
    status: str = "ACTIVE"
    warehouse_id: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    taxonomy_id: str | None = None
    size_class_id: str | None = None
    condition_id: str | None = None
    rotation_band_id: str | None = None
    min_weight: Decimal | None = None
    max_weight: Decimal | None = None
    weight_unit_id: str | None = None
    min_volume: Decimal | None = None
    max_volume: Decimal | None = None
    volume_unit_id: str | None = None
    target_zone_id: str | None = None
    target_zone_type_id: str | None = None
    label_policy: str


class RulePatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int
    code: str | None = None
    name: str | None = None
    priority: int | None = None
    status: str | None = None
    warehouse_id: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    taxonomy_id: str | None = None
    size_class_id: str | None = None
    condition_id: str | None = None
    rotation_band_id: str | None = None
    min_weight: Decimal | None = None
    max_weight: Decimal | None = None
    weight_unit_id: str | None = None
    min_volume: Decimal | None = None
    max_volume: Decimal | None = None
    volume_unit_id: str | None = None
    target_zone_id: str | None = None
    target_zone_type_id: str | None = None
    label_policy: str | None = None


class PolicyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int | None = None
    mode: str
    on_no_rule: str


@router.get("/conditions")
def list_conditions(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    items = storage_service.list_conditions(db, ctx.company_id)
    return {"items": [{"id": str(c.id), "code": c.code, "name": c.name, "description": c.description, "status": c.status, "version": c.version} for c in items]}


@router.post("/conditions", dependencies=[Depends(require_write_allowed)])
def create_condition(
    body: ConditionBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    condition = storage_service.create_condition(
        db,
        company_id=ctx.company_id,
        code=body.code,
        name=body.name,
        description=body.description,
        actor_id=str(actor.id),
    )
    db.commit()
    return {"id": str(condition.id), "code": condition.code, "name": condition.name, "status": condition.status, "version": condition.version}


@router.patch("/conditions/{condition_id}", dependencies=[Depends(require_write_allowed)])
def update_condition(
    condition_id: str,
    body: ConditionPatchBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    condition = storage_service.update_condition(
        db,
        company_id=ctx.company_id,
        condition_id=condition_id,
        expected_version=body.expected_version,
        name=body.name,
        description=body.description,
        status=body.status,
        actor_id=str(actor.id),
    )
    db.commit()
    return {"id": str(condition.id), "code": condition.code, "name": condition.name, "status": condition.status, "version": condition.version}


@router.get("/size-classes")
def list_size_classes(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    items = storage_service.list_size_classes(db, ctx.company_id)
    return {"items": [{"id": str(c.id), "code": c.code, "name": c.name, "description": c.description, "status": c.status, "version": c.version} for c in items]}


@router.post("/size-classes", dependencies=[Depends(require_write_allowed)])
def create_size_class(
    body: SizeClassBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    size_class = storage_service.create_size_class(
        db,
        company_id=ctx.company_id,
        code=body.code,
        name=body.name,
        description=body.description,
        actor_id=str(actor.id),
    )
    db.commit()
    return {"id": str(size_class.id), "code": size_class.code, "name": size_class.name, "status": size_class.status, "version": size_class.version}


@router.patch("/size-classes/{size_class_id}", dependencies=[Depends(require_write_allowed)])
def update_size_class(
    size_class_id: str,
    body: SizeClassPatchBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    size_class = storage_service.update_size_class(
        db,
        company_id=ctx.company_id,
        size_class_id=size_class_id,
        expected_version=body.expected_version,
        name=body.name,
        description=body.description,
        status=body.status,
        actor_id=str(actor.id),
    )
    db.commit()
    return {"id": str(size_class.id), "code": size_class.code, "name": size_class.name, "status": size_class.status, "version": size_class.version}


@router.get("/profiles/{item_id}")
def get_profile(
    item_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    profile = storage_service.get_profile(db, ctx.company_id, item_id)
    if profile is None:
        return {
            "item_id": item_id,
            "version": None,
            "weight_value": None,
            "weight_unit": None,
            "volume_value": None,
            "volume_unit": None,
            "size_class": None,
            "conditions": [],
        }
    return profile


@router.put("/profiles/{item_id}", dependencies=[Depends(require_write_allowed)])
def save_profile(
    item_id: str,
    body: ProfileBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    profile = storage_service.save_profile(
        db,
        company_id=ctx.company_id,
        item_id=item_id,
        weight_value=body.weight_value,
        weight_unit_id=body.weight_unit_id,
        volume_value=body.volume_value,
        volume_unit_id=body.volume_unit_id,
        size_class_id=body.size_class_id,
        condition_ids=body.condition_ids,
        expected_version=body.expected_version,
        actor_id=str(actor.id),
    )
    db.commit()
    return storage_service.profile_dict(db, profile)


@router.get("/rules")
def list_rules(
    warehouse_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    rules = storage_service.list_rules(db, ctx.company_id, warehouse_id=warehouse_id)
    return {"items": [storage_service.rule_dict(db, rule) for rule in rules]}


@router.post("/rules", dependencies=[Depends(require_write_allowed)])
def create_rule(
    body: RuleBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    rule = storage_service.create_rule(
        db,
        company_id=ctx.company_id,
        data=body.model_dump(exclude_none=True),
        actor_id=str(actor.id),
    )
    db.commit()
    return storage_service.rule_dict(db, rule)


@router.patch("/rules/{rule_id}", dependencies=[Depends(require_write_allowed)])
def update_rule(
    rule_id: str,
    body: RulePatchBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    rule = storage_service.update_rule(
        db,
        company_id=ctx.company_id,
        rule_id=rule_id,
        expected_version=body.expected_version,
        data=body.model_dump(exclude_none=True, exclude={"expected_version"}),
        actor_id=str(actor.id),
    )
    db.commit()
    return storage_service.rule_dict(db, rule)


@router.get("/warehouse-policies/{warehouse_id}")
def get_policy(
    warehouse_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("organization", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    return storage_service.get_policy(db, ctx.company_id, warehouse_id)


@router.put("/warehouse-policies/{warehouse_id}", dependencies=[Depends(require_write_allowed)])
def save_policy(
    warehouse_id: str,
    body: PolicyBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("organization", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    policy = storage_service.save_policy(
        db,
        company_id=ctx.company_id,
        warehouse_id=warehouse_id,
        mode=body.mode,
        on_no_rule=body.on_no_rule,
        expected_version=body.expected_version,
        actor_id=str(actor.id),
    )
    db.commit()
    return {"warehouse_id": policy.warehouse_id, "mode": policy.mode, "on_no_rule": policy.on_no_rule, "version": policy.version}


@router.get("/evaluate")
def evaluate(
    warehouse_id: str = Query(...),
    item_id: str = Query(...),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventario", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    return storage_service.evaluate(db, company_id=ctx.company_id, warehouse_id=warehouse_id, item_id=item_id)
