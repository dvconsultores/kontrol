"""API de unidades, presentaciones y conversiones (Spec 011).

Prefijo `/api/v1/maestros`, la convención vigente del módulo. Todo endpoint
exige sesión, permiso y filtra por empresa: el aislamiento vive aquí, no en el
frontend (P6).

No existe endpoint que **edite** una versión de factor. Es deliberado: corregir
un factor **es** crear una versión nueva (FR-011-036).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_permission, require_write_allowed
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.identity_access.models import User
from app.modules.master_data import uom
from app.modules.master_data.models import (
    CatalogItem,
    Presentation,
    ProductPresentationVersion,
    UnitConversion,
    UnitOfMeasure,
)
from app.shared.audit import record_audit

router = APIRouter(prefix="/maestros", tags=["maestros-uom"])


# --------------------------------------------------------------------------
# Utilidades de alcance y control
# --------------------------------------------------------------------------

def _visible_units(ctx: CompanyContext):
    """Unidades de la empresa **más** el catálogo global de plataforma.

    `OQ-MC-01` quedó cerrada: la unidad de negocio —BULTO, SACO, ROLLO— es de la
    empresa; la unidad de sistema, con `company_id` nulo, es de la plataforma.
    """
    return or_(UnitOfMeasure.company_id == ctx.company_id, UnitOfMeasure.company_id.is_(None))


def _get_unit(db: Session, ctx: CompanyContext, unit_id: str) -> UnitOfMeasure:
    unit = db.get(UnitOfMeasure, unit_id)
    if unit is None or (unit.company_id is not None and unit.company_id != ctx.company_id):
        raise NotFoundError(code="UOM_NOT_FOUND", message="Unidad no encontrada")
    return unit


def _assert_editable(unit: UnitOfMeasure) -> None:
    """Una unidad global es de solo lectura para la empresa (FR-011-003)."""
    if unit.company_id is None:
        raise KontrolError(
            code="UOM_GLOBAL_READ_ONLY",
            message="Las unidades del catálogo global no se editan desde una empresa",
            status_code=403,
            details={"reason": "Unidad de plataforma", "allowed_actions": ["view"]})


def _get_product(db: Session, ctx: CompanyContext, product_id: str) -> CatalogItem:
    item = db.get(CatalogItem, product_id)
    if item is None or item.company_id != ctx.company_id:
        raise NotFoundError(code="ITEM_NOT_FOUND", message="Producto no encontrado")
    return item


def _get_presentation(db: Session, ctx: CompanyContext, presentation_id: str) -> Presentation:
    presentation = db.get(Presentation, presentation_id)
    if presentation is None:
        raise NotFoundError(code="PRESENTATION_NOT_FOUND", message="Presentación no encontrada")
    _get_product(db, ctx, presentation.product_id)
    return presentation


def _check_version(entity: Any, if_match: str | None) -> None:
    if if_match is None:
        return
    expected = if_match.strip('"')
    if not expected.isdigit() or int(expected) != int(entity.version):
        raise ConflictError(code="VERSION_CONFLICT",
                            message="El registro fue modificado por otra operación")


def _audit(db: Session, user: User, action: str, entity_type: str, entity_id: str,
           before: dict | None = None, after: dict | None = None) -> None:
    record_audit(db, action=action, entity_type=entity_type, entity_id=entity_id,
                 tenant_id=user.tenant_id, user_id=str(user.id), before=before, after=after)


# Permisos EN la empresa de la petición (Spec 003, capacidad × empresa).
def _permissions(db: Session, user: User, company_id: str) -> set[str]:
    from app.modules.identity_access import authority

    return authority.capabilities_in_company(db, user, company_id)


def _filter_actions(actions: list[str], permissions: set[str]) -> list[str]:
    required = {"edit": "maestros:edit", "activate": "maestros:edit",
                "deactivate": "maestros:deactivate", "delete": "maestros:delete",
                "create_version": "maestros:create", "close": "maestros:edit"}
    return [a for a in actions if required.get(a, "maestros:view") in permissions]


# --------------------------------------------------------------------------
# Unidades de medida
# --------------------------------------------------------------------------

class UnitIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    symbol: str = Field(min_length=1, max_length=16)
    dimension: str = "CANTIDAD"
    decimals: int = Field(default=0, ge=0, le=6)
    rounding_mode: str = "HALF_UP"

    @field_validator("dimension")
    @classmethod
    def _dimension(cls, value: str) -> str:
        if value not in uom.__dict__.get("_DIMS", ()) and value not in (
                "CANTIDAD", "MASA", "PESO", "VOLUMEN", "LONGITUD", "AREA", "TIEMPO"):
            raise ValueError("dimensión no reconocida")
        return value

    @field_validator("rounding_mode")
    @classmethod
    def _rounding(cls, value: str) -> str:
        if value not in uom.ROUNDING:
            raise ValueError("modo de redondeo no reconocido")
        return value


class UnitPatch(BaseModel):
    name: str | None = None
    symbol: str | None = None
    decimals: int | None = Field(default=None, ge=0, le=6)
    rounding_mode: str | None = None


def _unit_dict(db: Session, unit: UnitOfMeasure, permissions: set[str]) -> dict[str, Any]:
    in_use = _unit_in_use(db, unit.id)
    actions = ["edit", "deactivate" if unit.status == "ACTIVE" else "activate"]
    if not in_use:
        actions.append("delete")
    if unit.company_id is None:
        actions = []          # el catálogo global es de solo lectura aquí
    return {
        "id": str(unit.id), "code": unit.code, "name": unit.name, "symbol": unit.symbol,
        "dimension": unit.dimension, "decimals": unit.decimals,
        "rounding_mode": unit.rounding_mode, "status": unit.status,
        "scope": "GLOBAL" if unit.company_id is None else "COMPANY",
        "company_id": unit.company_id, "version": int(unit.version),
        "can_delete": (not in_use) and unit.company_id is not None,
        "allowed_actions": _filter_actions(actions, permissions),
    }


def _unit_in_use(db: Session, unit_id: str) -> bool:
    from app.core.database import Base

    for table in Base.metadata.tables.values():
        if "uom_id" not in table.c:
            continue
        found = db.execute(select(table.c.id).where(table.c.uom_id == unit_id).limit(1)).first()
        if found is not None:
            return True
    for model, column in ((CatalogItem, CatalogItem.base_unit_id),
                          (ProductPresentationVersion, ProductPresentationVersion.factor_uom_id)):
        if db.execute(select(model.id).where(column == unit_id).limit(1)).first():
            return True
    if db.execute(select(UnitConversion.id).where(
            or_(UnitConversion.from_unit_id == unit_id,
                UnitConversion.to_unit_id == unit_id)).limit(1)).first():
        return True
    return False


@router.get("/unidades")
def list_units(q: str | None = None, dimension: str | None = None, status: str | None = None,
               scope: str | None = None, limit: int = 100, offset: int = 0,
               db: Session = Depends(get_db),
               user: User = Depends(require_permission("maestros", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(UnitOfMeasure).where(_visible_units(ctx))
    if dimension:
        query = query.where(UnitOfMeasure.dimension == dimension)
    if status:
        query = query.where(UnitOfMeasure.status == status)
    if scope == "GLOBAL":
        query = query.where(UnitOfMeasure.company_id.is_(None))
    elif scope == "COMPANY":
        query = query.where(UnitOfMeasure.company_id == ctx.company_id)
    if q:
        pattern = f"%{q}%"
        query = query.where(UnitOfMeasure.code.ilike(pattern) | UnitOfMeasure.name.ilike(pattern))
    total = int(db.execute(select(func.count()).select_from(query.subquery())).scalar_one())
    rows = db.execute(query.order_by(UnitOfMeasure.code).limit(limit).offset(offset)).scalars().all()
    permissions = _permissions(db, user, ctx.company_id)
    return {"total": total, "limit": limit, "offset": offset,
            "items": [_unit_dict(db, u, permissions) for u in rows]}


@router.post("/unidades", dependencies=[Depends(require_write_allowed)])
def create_unit(body: UnitIn, db: Session = Depends(get_db),
                actor: User = Depends(require_permission("maestros", "create")), ctx: CompanyContext = Depends(get_company_context)):
    unit = UnitOfMeasure(company_id=ctx.company_id, status="ACTIVE",
                         created_by=str(actor.id), **body.model_dump())
    db.add(unit)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(code="UOM_CODE_DUPLICATE",
                            message="Ya existe una unidad con ese código") from exc
    db.refresh(unit)
    _audit(db, actor, "CREATE", "unit_of_measure", str(unit.id), after={"code": unit.code})
    db.commit()
    return _unit_dict(db, unit, _permissions(db, actor, ctx.company_id))


@router.get("/unidades/{unit_id}")
def get_unit(unit_id: str, db: Session = Depends(get_db),
             user: User = Depends(require_permission("maestros", "view")), ctx: CompanyContext = Depends(get_company_context)):
    return _unit_dict(db, _get_unit(db, ctx, unit_id), _permissions(db, user, ctx.company_id))


@router.patch("/unidades/{unit_id}", dependencies=[Depends(require_write_allowed)])
def patch_unit(unit_id: str, body: UnitPatch,
               if_match: str | None = Header(default=None, alias="If-Match"),
               db: Session = Depends(get_db),
               actor: User = Depends(require_permission("maestros", "edit")), ctx: CompanyContext = Depends(get_company_context)):
    unit = _get_unit(db, ctx, unit_id)
    _assert_editable(unit)
    _check_version(unit, if_match)
    before = {"name": unit.name, "decimals": unit.decimals}
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(unit, field, value)
    unit.version = int(unit.version) + 1
    _audit(db, actor, "UPDATE", "unit_of_measure", str(unit.id), before=before,
           after={"name": unit.name, "decimals": unit.decimals})
    db.commit()
    db.refresh(unit)
    return _unit_dict(db, unit, _permissions(db, actor, ctx.company_id))


def _set_unit_status(db: Session, ctx: CompanyContext, actor: User, unit_id: str, status: str) -> dict[str, Any]:
    unit = _get_unit(db, ctx, unit_id)
    _assert_editable(unit)
    unit.status = status
    unit.version = int(unit.version) + 1
    _audit(db, actor, status, "unit_of_measure", str(unit.id), after={"status": status})
    db.commit()
    return {"id": str(unit.id), "status": unit.status}


@router.post("/unidades/{unit_id}/activate", dependencies=[Depends(require_write_allowed)])
def activate_unit(unit_id: str, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("maestros", "edit")), ctx: CompanyContext = Depends(get_company_context)):
    return _set_unit_status(db, ctx, actor, unit_id, "ACTIVE")


@router.post("/unidades/{unit_id}/deactivate", dependencies=[Depends(require_write_allowed)])
def deactivate_unit(unit_id: str, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("maestros", "deactivate")), ctx: CompanyContext = Depends(get_company_context)):
    return _set_unit_status(db, ctx, actor, unit_id, "INACTIVE")


@router.delete("/unidades/{unit_id}", dependencies=[Depends(require_write_allowed)])
def delete_unit(unit_id: str, db: Session = Depends(get_db),
                actor: User = Depends(require_permission("maestros", "delete")), ctx: CompanyContext = Depends(get_company_context)):
    unit = _get_unit(db, ctx, unit_id)
    _assert_editable(unit)
    if _unit_in_use(db, unit_id):
        _audit(db, actor, "DELETE_BLOCKED", "unit_of_measure", str(unit.id))
        db.commit()
        raise KontrolError(
            code="UOM_IN_USE", message="La unidad está en uso y no puede borrarse",
            status_code=409,
            details={"reason": "Existen líneas, productos o conversiones que la referencian",
                     "allowed_actions": ["deactivate"]})
    _audit(db, actor, "DELETE", "unit_of_measure", str(unit.id), before={"code": unit.code})
    db.delete(unit)
    db.commit()
    return {"deleted": True}


# --------------------------------------------------------------------------
# Conversión física entre unidades
# --------------------------------------------------------------------------

class PhysicalConversionIn(BaseModel):
    to_unit_id: str
    factor: Decimal = Field(gt=0)
    rounding: int = 4


@router.get("/unidades/{unit_id}/conversiones")
def list_conversions(unit_id: str, db: Session = Depends(get_db),
                     user: User = Depends(require_permission("maestros", "view")), ctx: CompanyContext = Depends(get_company_context)):
    _get_unit(db, ctx, unit_id)
    rows = db.execute(select(UnitConversion).where(
        or_(UnitConversion.from_unit_id == unit_id, UnitConversion.to_unit_id == unit_id)
    )).scalars().all()
    return [{"id": str(c.id), "from_unit_id": c.from_unit_id, "to_unit_id": c.to_unit_id,
             "factor": str(c.factor), "validity": c.validity} for c in rows]


@router.post("/unidades/{unit_id}/conversiones-fisicas",
             dependencies=[Depends(require_write_allowed)])
def create_physical_conversion(unit_id: str, body: PhysicalConversionIn,
                               db: Session = Depends(get_db),
                               actor: User = Depends(require_permission("maestros", "create")), ctx: CompanyContext = Depends(get_company_context)):
    """Conversión **física**: solo dentro de la misma dimensión.

    `KG ↔ L` se rechaza: no se inventan conversiones físicamente inválidas. Una
    relación por densidad sería otra capacidad, fuera de 011 (§42).
    """
    _get_unit(db, ctx, unit_id)
    _get_unit(db, ctx, body.to_unit_id)
    uom.assert_same_dimension(db, unit_id, body.to_unit_id)
    conversion = UnitConversion(from_unit_id=unit_id, to_unit_id=body.to_unit_id,
                                factor=body.factor, rounding=body.rounding, validity="ACTIVE")
    db.add(conversion)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(code="UOM_CONVERSION_DUPLICATE",
                            message="Ya existe esa conversión") from exc
    db.refresh(conversion)
    _audit(db, actor, "CREATE", "unit_conversion", str(conversion.id),
           after={"factor": str(conversion.factor)})
    db.commit()
    return {"id": str(conversion.id), "from_unit_id": unit_id,
            "to_unit_id": body.to_unit_id, "factor": str(conversion.factor)}


# --------------------------------------------------------------------------
# Presentaciones del producto
# --------------------------------------------------------------------------

class PresentationIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=200)
    unit_id: str | None = None
    barcode: str | None = None
    buyable: bool = True
    sellable: bool = True
    storable: bool = True
    dispatchable: bool = True
    #: Equivalencia inicial. Opcional: una presentación puede crearse y
    #: versionarse después.
    factor_to_base: Decimal | None = Field(default=None, gt=0)
    factor_uom_id: str | None = None
    exact_in_base: bool = True
    valid_from: datetime | None = None


class PresentationPatch(BaseModel):
    name: str | None = None
    barcode: str | None = None
    buyable: bool | None = None
    sellable: bool | None = None
    storable: bool | None = None
    dispatchable: bool | None = None


class VersionIn(BaseModel):
    factor_to_base: Decimal = Field(gt=0)
    factor_uom_id: str | None = None
    exact_in_base: bool = True
    valid_from: datetime | None = None


def _presentation_in_use(db: Session, presentation_id: str) -> bool:
    from app.core.database import Base

    for table in Base.metadata.tables.values():
        if "presentation_id" not in table.c or table.name == "product_presentation_versions":
            continue
        if db.execute(select(table.c.id).where(
                table.c.presentation_id == presentation_id).limit(1)).first():
            return True
    return False


def _open_version(db: Session, presentation_id: str) -> ProductPresentationVersion | None:
    return db.execute(
        select(ProductPresentationVersion).where(
            ProductPresentationVersion.presentation_id == presentation_id,
            ProductPresentationVersion.valid_to.is_(None))
    ).scalars().first()


def _presentation_dict(db: Session, presentation: Presentation,
                       permissions: set[str]) -> dict[str, Any]:
    current = _open_version(db, presentation.id)
    in_use = _presentation_in_use(db, presentation.id)
    base_unit = uom.base_unit_of(db, presentation.product_id)
    actions = ["edit", "deactivate" if presentation.status == "ACTIVE" else "activate",
               "create_version"]
    if not in_use and current is None:
        actions.append("delete")
    return {
        "id": str(presentation.id), "product_id": presentation.product_id,
        "company_id": presentation.company_id, "code": presentation.code,
        "name": presentation.name, "status": presentation.status,
        "buyable": presentation.buyable, "sellable": presentation.sellable,
        "storable": presentation.storable, "dispatchable": presentation.dispatchable,
        "barcode": presentation.barcode, "version": int(presentation.version),
        "legacy_content": float(presentation.content) if presentation.content is not None else None,
        "base_unit": ({"id": str(base_unit.id), "code": base_unit.code,
                       "symbol": base_unit.symbol} if base_unit else None),
        "current_factor": str(current.factor_to_base) if current else None,
        "current_version_id": str(current.id) if current else None,
        "in_use": in_use,
        "can_delete": (not in_use) and current is None,
        "allowed_actions": _filter_actions(actions, permissions),
    }


@router.get("/productos/{product_id}/presentaciones")
def list_presentations(product_id: str, status: str | None = None,
                       db: Session = Depends(get_db),
                       user: User = Depends(require_permission("maestros", "view")), ctx: CompanyContext = Depends(get_company_context)):
    _get_product(db, ctx, product_id)
    query = select(Presentation).where(Presentation.product_id == product_id)
    if status:
        query = query.where(Presentation.status == status)
    permissions = _permissions(db, user, ctx.company_id)
    return [_presentation_dict(db, p, permissions)
            for p in db.execute(query.order_by(Presentation.code)).scalars().all()]


@router.post("/productos/{product_id}/presentaciones",
             dependencies=[Depends(require_write_allowed)])
def create_presentation(product_id: str, body: PresentationIn, db: Session = Depends(get_db),
                        actor: User = Depends(require_permission("maestros", "create")), ctx: CompanyContext = Depends(get_company_context)):
    item = _get_product(db, ctx, product_id)
    if item.item_type == "PRODUCT" and item.base_unit_id is None:
        raise KontrolError(code="BASE_UNIT_REQUIRED",
                           message="El producto no declara unidad base", status_code=422)
    data = body.model_dump(exclude={"factor_to_base", "factor_uom_id",
                                    "exact_in_base", "valid_from"})
    presentation = Presentation(product_id=product_id, company_id=item.company_id,
                                status="ACTIVE", created_by=str(actor.id), **data)
    db.add(presentation)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(code="PRESENTATION_CODE_DUPLICATE",
                            message="Ya existe una presentación con ese código") from exc

    if body.factor_to_base is not None:
        db.add(ProductPresentationVersion(
            presentation_id=presentation.id, product_id=product_id,
            company_id=item.company_id, factor_to_base=body.factor_to_base,
            factor_uom_id=body.factor_uom_id or item.base_unit_id,
            exact_in_base=body.exact_in_base,
            valid_from=body.valid_from or datetime.now(UTC),
            status="ACTIVE", created_by=str(actor.id)))
    db.commit()
    db.refresh(presentation)
    _audit(db, actor, "CREATE", "presentation", str(presentation.id),
           after={"code": presentation.code})
    db.commit()
    return _presentation_dict(db, presentation, _permissions(db, actor, ctx.company_id))


@router.get("/presentaciones/{presentation_id}")
def get_presentation(presentation_id: str, db: Session = Depends(get_db),
                     user: User = Depends(require_permission("maestros", "view")), ctx: CompanyContext = Depends(get_company_context)):
    return _presentation_dict(db, _get_presentation(db, ctx, presentation_id),
                              _permissions(db, user, ctx.company_id))


@router.patch("/presentaciones/{presentation_id}", dependencies=[Depends(require_write_allowed)])
def patch_presentation(presentation_id: str, body: PresentationPatch,
                       if_match: str | None = Header(default=None, alias="If-Match"),
                       db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("maestros", "edit")), ctx: CompanyContext = Depends(get_company_context)):
    """Solo **metadata**. El factor no se edita aquí: se versiona."""
    presentation = _get_presentation(db, ctx, presentation_id)
    _check_version(presentation, if_match)
    before = {"name": presentation.name}
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(presentation, field, value)
    presentation.version = int(presentation.version) + 1
    _audit(db, actor, "UPDATE", "presentation", str(presentation.id), before=before,
           after={"name": presentation.name})
    db.commit()
    db.refresh(presentation)
    return _presentation_dict(db, presentation, _permissions(db, actor, ctx.company_id))


def _set_presentation_status(db: Session, ctx: CompanyContext, actor: User,
                             presentation_id: str, status: str) -> dict[str, Any]:
    presentation = _get_presentation(db, ctx, presentation_id)
    presentation.status = status
    presentation.version = int(presentation.version) + 1
    _audit(db, actor, status, "presentation", str(presentation.id), after={"status": status})
    db.commit()
    return {"id": str(presentation.id), "status": presentation.status}


@router.post("/presentaciones/{presentation_id}/activate",
             dependencies=[Depends(require_write_allowed)])
def activate_presentation(presentation_id: str, db: Session = Depends(get_db),
                          actor: User = Depends(require_permission("maestros", "edit")), ctx: CompanyContext = Depends(get_company_context)):
    return _set_presentation_status(db, ctx, actor, presentation_id, "ACTIVE")


@router.post("/presentaciones/{presentation_id}/deactivate",
             dependencies=[Depends(require_write_allowed)])
def deactivate_presentation(presentation_id: str, db: Session = Depends(get_db),
                            actor: User = Depends(require_permission("maestros", "deactivate")), ctx: CompanyContext = Depends(get_company_context)):
    return _set_presentation_status(db, ctx, actor, presentation_id, "INACTIVE")


@router.delete("/presentaciones/{presentation_id}", dependencies=[Depends(require_write_allowed)])
def delete_presentation(presentation_id: str, db: Session = Depends(get_db),
                        actor: User = Depends(require_permission("maestros", "delete")), ctx: CompanyContext = Depends(get_company_context)):
    presentation = _get_presentation(db, ctx, presentation_id)
    if _presentation_in_use(db, presentation_id):
        _audit(db, actor, "DELETE_BLOCKED", "presentation", str(presentation.id))
        db.commit()
        raise KontrolError(
            code="PRESENTATION_IN_USE",
            message="La presentación fue utilizada y no puede borrarse", status_code=409,
            details={"reason": "Existen líneas de documento que la referencian",
                     "allowed_actions": ["deactivate"]})
    for version in db.execute(select(ProductPresentationVersion).where(
            ProductPresentationVersion.presentation_id == presentation_id)).scalars().all():
        db.delete(version)
    _audit(db, actor, "DELETE", "presentation", str(presentation.id),
           before={"code": presentation.code})
    db.delete(presentation)
    db.commit()
    return {"deleted": True}


# --------------------------------------------------------------------------
# Versiones del factor — se crean, no se editan (FR-011-036)
# --------------------------------------------------------------------------

@router.get("/presentaciones/{presentation_id}/versiones")
def list_versions(presentation_id: str, db: Session = Depends(get_db),
                  user: User = Depends(require_permission("maestros", "view")), ctx: CompanyContext = Depends(get_company_context)):
    _get_presentation(db, ctx, presentation_id)
    rows = db.execute(
        select(ProductPresentationVersion)
        .where(ProductPresentationVersion.presentation_id == presentation_id)
        .order_by(ProductPresentationVersion.valid_from.desc())
    ).scalars().all()
    permissions = _permissions(db, user, ctx.company_id)
    result = []
    for version in rows:
        in_use = db.execute(select(ProductPresentationVersion.id).where(
            ProductPresentationVersion.id == version.id).limit(1)).first() is not None
        result.append({
            "id": str(version.id), "presentation_id": version.presentation_id,
            "factor_to_base": str(version.factor_to_base),
            "factor_uom_id": version.factor_uom_id,
            "exact_in_base": version.exact_in_base,
            "valid_from": version.valid_from.isoformat() if version.valid_from else None,
            "valid_to": version.valid_to.isoformat() if version.valid_to else None,
            "status": version.status,
            "is_open": version.valid_to is None,
            "in_use": in_use,
            # Una versión cerrada no se edita ni se borra: solo se consulta.
            "allowed_actions": _filter_actions(
                ["close"] if version.valid_to is None else [], permissions),
        })
    return result


@router.post("/presentaciones/{presentation_id}/versiones",
             dependencies=[Depends(require_write_allowed)])
def create_version(presentation_id: str, body: VersionIn, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("maestros", "create")), ctx: CompanyContext = Depends(get_company_context)):
    """Cambiar un factor **crea una versión** y cierra la anterior.

    No existe `PATCH` de versión: sobrescribir un factor reescribiría el
    significado de todo el histórico que lo usó (R-D0-09-4).
    """
    presentation = _get_presentation(db, ctx, presentation_id)
    item = _get_product(db, ctx, presentation.product_id)
    start = body.valid_from or datetime.now(UTC)

    current = _open_version(db, presentation_id)
    if current is not None:
        current_start = current.valid_from
        if current_start.tzinfo is None:
            current_start = current_start.replace(tzinfo=UTC)
        if start <= current_start:
            raise ConflictError(
                code="PRESENTATION_VERSION_OVERLAP",
                message="La nueva vigencia debe empezar después de la actual")
        current.valid_to = start
        db.flush()

    uom.assert_no_version_overlap(db, presentation_id, start, None)
    version = ProductPresentationVersion(
        presentation_id=presentation_id, product_id=presentation.product_id,
        company_id=item.company_id, factor_to_base=body.factor_to_base,
        factor_uom_id=body.factor_uom_id or item.base_unit_id,
        exact_in_base=body.exact_in_base, valid_from=start,
        status="ACTIVE", created_by=str(actor.id))
    db.add(version)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            code="PRESENTATION_VERSION_OVERLAP",
            message="Ya existe una equivalencia vigente para esa presentación") from exc
    db.refresh(version)
    _audit(db, actor, "CREATE_VERSION", "product_presentation_version", str(version.id),
           after={"factor": str(version.factor_to_base),
                  "valid_from": start.isoformat()})
    db.commit()
    return {"id": str(version.id), "factor_to_base": str(version.factor_to_base),
            "valid_from": start.isoformat(), "valid_to": None}


# --------------------------------------------------------------------------
# Previsualización de conversión — informativa, no vinculante
# --------------------------------------------------------------------------

class PreviewIn(BaseModel):
    product_id: str
    presentation_id: str | None = None
    quantity: Decimal
    date: datetime | None = None


@router.post("/conversion/preview")
def preview_conversion(body: PreviewIn, db: Session = Depends(get_db),
                       user: User = Depends(require_permission("maestros", "view")), ctx: CompanyContext = Depends(get_company_context)):
    """Vista previa. El frontend la muestra; **no vincula**: al guardar, el
    backend recalcula (FR-011-044, AC-011-18)."""
    _get_product(db, ctx, body.product_id)
    if body.presentation_id:
        _get_presentation(db, ctx, body.presentation_id)
    conversion = uom.to_base(db, body.quantity, body.product_id,
                             body.presentation_id, body.date)
    base_unit = uom.base_unit_of(db, body.product_id)
    presentation = (db.get(Presentation, body.presentation_id)
                    if body.presentation_id else None)
    symbol = base_unit.symbol if base_unit else ""
    label = presentation.name if presentation else (base_unit.code if base_unit else "")
    return {
        "quantity": str(body.quantity),
        "presentation": ({"id": str(presentation.id), "code": presentation.code,
                          "label": presentation.name} if presentation else None),
        "factor_applied": str(conversion.factor),
        "version_id": conversion.version_id,
        "base_quantity": str(conversion.base_quantity),
        "base_uom": ({"id": str(base_unit.id), "code": base_unit.code,
                      "symbol": base_unit.symbol} if base_unit else None),
        "exact": conversion.exact,
        "explanation": f"{body.quantity} {label} = {conversion.base_quantity} {symbol}".strip(),
    }


# --------------------------------------------------------------------------
# Unidad base del producto
# --------------------------------------------------------------------------

class BaseUnitIn(BaseModel):
    base_unit_id: str


@router.patch("/productos/{product_id}/unidad-base",
              dependencies=[Depends(require_write_allowed)])
def set_base_unit(product_id: str, body: BaseUnitIn, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("maestros", "edit")), ctx: CompanyContext = Depends(get_company_context)):
    """Cambiar la unidad base. Bloqueado si el producto tiene historial
    (R-011-3): el bloqueo se produce **aquí**, no en la interfaz."""
    item = _get_product(db, ctx, product_id)
    _get_unit(db, ctx, body.base_unit_id)
    try:
        uom.assert_base_unit_changeable(db, product_id)
    except KontrolError:
        _audit(db, actor, "BASE_UNIT_CHANGE_BLOCKED", "catalog_item", str(item.id))
        db.commit()
        raise
    before = {"base_unit_id": item.base_unit_id}
    item.base_unit_id = body.base_unit_id
    _audit(db, actor, "BASE_UNIT_CHANGED", "catalog_item", str(item.id), before=before,
           after={"base_unit_id": item.base_unit_id})
    db.commit()
    return {"id": str(item.id), "base_unit_id": item.base_unit_id,
            "base_unit_locked": item.base_unit_locked}
