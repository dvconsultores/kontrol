"""API de maestros (002-maestros): terceros, catálogo y perfiles."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_permission, require_write_allowed
from app.core.errors import NotFoundError
from app.modules.identity_access.models import User
from app.modules.master_data import service as master_service
from app.modules.master_data.models import (
    AttributeDefinition,
    CatalogItem,
    Party,
    Product,
    ProfileVersion,
    Service,
    TaxonomyNode,
    UnitConversion,
    UnitOfMeasure,
)
from app.shared.clock import InstanteDeEntrada

router = APIRouter(prefix="/maestros", tags=["maestros"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class PartyCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    person_type: str = "JURIDICA"
    legal_name: str | None = None
    trade_name: str | None = None
    tax_id: str | None = None
    economic_activity: str | None = None
    roles: list[str] = Field(default_factory=lambda: ["CLIENTE"])


class CustomerCreate(BaseModel):
    salesperson: str | None = None
    zone: str | None = None
    credit_days: int = 0
    credit_limit: float | None = None


class SupplierCreate(BaseModel):
    category: str | None = None
    buyer: str | None = None
    payment_term: str | None = None
    default_currency: str = "VED"
    withholding_profile: str | None = None


class PartyAddressCreate(BaseModel):
    address_type: str = "PRINCIPAL"
    state: str | None = None
    city: str | None = None
    municipality: str | None = None
    address: str = Field(min_length=1, max_length=1000)
    is_fiscal: bool = False
    is_delivery: bool = False


class PartyContactCreate(BaseModel):
    name: str | None = None
    role: str | None = None
    phone: str | None = None
    email: str | None = None
    preferred: bool = False


class PartyBankCreate(BaseModel):
    bank: str
    account_type: str = "CORRIENTE"
    currency: str = "VED"
    account_number: str = Field(min_length=1, max_length=40)


class ItemCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    item_type: str = "PRODUCT"
    short_description: str | None = None
    category_id: str | None = None
    base_unit_id: str | None = None
    tax_profile_id: str | None = None
    # Especialización producto
    inventory_profile_id: str | None = None
    traceability_profile_id: str | None = None
    regulatory_profile_id: str | None = None
    manufacturer: str | None = None
    origin_country: str | None = None
    # Especialización servicio
    billing_unit_id: str | None = None
    duration: str | None = None
    recurrence: bool = False
    contract_required: bool = False
    evidence_required: bool = False


class TaxonomyCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    level: str = "RUBRO"
    parent_id: str | None = None
    applies_to: list[str] = Field(default_factory=lambda: ["PRODUCT"])


class AttributeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    data_type: str = "TEXT"
    unit: str | None = None
    required: bool = False
    multiple: bool = False
    options: list[str] = Field(default_factory=list)
    searchable: bool = False


class UnitCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    dimension: str = "CANTIDAD"
    symbol: str = Field(min_length=1, max_length=16)
    decimals: int = 2


def _unidad_visible(db: Session, ctx: CompanyContext, unit_id: str) -> UnitOfMeasure:
    """Una unidad es visible si es de la plataforma o de la empresa activa."""
    unit = db.get(UnitOfMeasure, unit_id)
    if unit is None or (unit.company_id is not None and unit.company_id != ctx.company_id):
        raise NotFoundError(code="UOM_NOT_FOUND", message="Unidad no encontrada")
    return unit

def _visible_en_empresa(db: Session, ctx: CompanyContext, modelo: Any, obj_id: str, code: str, message: str) -> Any:
    """Un objeto es visible si es de la plataforma o de la empresa activa."""
    obj = db.get(modelo, obj_id)
    if obj is None or (obj.company_id is not None and obj.company_id != ctx.company_id):
        raise NotFoundError(code=code, message=message)
    return obj


class ConversionCreate(BaseModel):
    from_unit_id: str
    to_unit_id: str
    factor: float = Field(gt=0)
    rounding: int = 4


class ProfileCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    profile_type: str = "INVENTORY"
    effective_from: InstanteDeEntrada | None = None
    effective_to: InstanteDeEntrada | None = None
    stockable: bool = False
    lot: bool = False
    serial: bool = False
    expiry: bool = False
    trace_level: str = "NONE"
    tax_classification: str = "GRAVADO"
    islr_concept_ref: str | None = None
    requires_sica: bool = False
    requires_sigesai: bool = False
    requires_sacs: bool = False


# --------------------------------------------------------------------------- #
# Terceros
# --------------------------------------------------------------------------- #
def _party_dict(db: Session, party: Party) -> dict[str, Any]:
    return {
        "id": str(party.id),
        "code": party.code,
        "name": party.name,
        "person_type": party.person_type,
        "legal_name": party.legal_name,
        "trade_name": party.trade_name,
        "tax_id": party.tax_id,
        "roles": party.roles,
        "status": party.status,
        "allowed_actions": master_service.party_allowed_actions(party),
    }


@router.get("/terceros")
def list_parties(
    q: str = "",
    status: str | None = None,
    role: str | None = Query(None, pattern=r"^[A-Za-z_]{1,32}$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("maestros", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    query = select(Party).where(Party.company_id == ctx.company_id)
    if q:
        like = f"%{q}%"
        query = query.where((Party.name.ilike(like)) | (Party.tax_id.ilike(like)) | (Party.code.ilike(like)))
    if status:
        query = query.where(Party.status == status)
    if role:
        query = query.where(func.upper(cast(Party.roles, String)).like(f'%"{role.upper()}"%'))
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = db.execute(query.order_by(Party.created_at).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [_party_dict(db, p) for p in items], "total": total, "page": page, "page_size": page_size}


@router.post("/terceros", dependencies=[Depends(require_write_allowed)])
def create_party(
    body: PartyCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    tax_id = master_service.validate_tax_id(body.tax_id, body.person_type) if body.tax_id else None
    role = (body.roles or ["CLIENTE"])[0]
    master_service.ensure_no_duplicate(db, company_id=ctx.company_id, tax_id=tax_id or "", role=role)
    party = Party(
        company_id=ctx.company_id,
        code=body.code,
        name=body.name,
        person_type=body.person_type,
        legal_name=body.legal_name,
        trade_name=body.trade_name,
        tax_id=tax_id,
        economic_activity=body.economic_activity,
        roles=body.roles,
        status="ACTIVE",
        created_by=str(actor.id),
    )
    db.add(party)
    db.commit()
    db.refresh(party)
    return _party_dict(db, party)


@router.get("/terceros/{party_id}")
def get_party(party_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("maestros", "view")), ctx: CompanyContext = Depends(get_company_context)):
    party = db.get(Party, party_id)
    if not party or party.company_id != ctx.company_id:
        raise NotFoundError(code="PARTY_NOT_FOUND", message="Tercero no encontrado")
    return _party_dict(db, party)


@router.post("/terceros/{party_id}/deactivate", dependencies=[Depends(require_write_allowed)])
def deactivate_party(party_id: str, db: Session = Depends(get_db), actor: User = Depends(require_permission("maestros", "deactivate")), ctx: CompanyContext = Depends(get_company_context)):
    party = db.get(Party, party_id)
    # Esta ruta no comparaba la empresa: no es que usara el tenant, es que no
    # acotaba en absoluto, y por eso el barrido de N2 no la vio.
    if not party or party.company_id != ctx.company_id:
        raise NotFoundError(code="PARTY_NOT_FOUND", message="Tercero no encontrado")
    party.status = "INACTIVE"
    db.commit()
    return _party_dict(db, party)


@router.post("/terceros/{party_id}/roles/{role}", dependencies=[Depends(require_write_allowed)])
def add_party_role(
    party_id: str,
    role: str,
    body: PartyCreate | CustomerCreate | SupplierCreate = None,  # type: ignore[assignment]
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    """Agrega un rol a un tercero (cliente/proveedor/transportista/conductor)."""
    party = db.get(Party, party_id)
    if not party or party.company_id != ctx.company_id:
        raise NotFoundError(code="PARTY_NOT_FOUND", message="Tercero no encontrado")
    roles = set(party.roles or [])
    roles.add(role.upper())
    party.roles = sorted(roles)
    db.commit()
    db.refresh(party)
    return _party_dict(db, party)


# --------------------------------------------------------------------------- #
# Catálogo
# --------------------------------------------------------------------------- #
@router.get("/catalogos/items")
def list_items(
    q: str = "",
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("maestros", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    query = select(CatalogItem).where(CatalogItem.company_id == ctx.company_id)
    if q:
        like = f"%{q}%"
        query = query.where((CatalogItem.name.ilike(like)) | (CatalogItem.code.ilike(like)))
    if status:
        query = query.where(CatalogItem.status == status)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = db.execute(query.order_by(CatalogItem.created_at).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {
        "items": [
            {
                "id": str(i.id),
                "code": i.code,
                "name": i.name,
                "item_type": i.item_type,
                "status": i.status,
                "allowed_actions": master_service.item_allowed_actions(i.status),
            }
            for i in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/catalogos/items/search")
def search_items(
    q: str = "",
    item_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("maestros", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    """Búsqueda asíncrona backend para AsyncCombobox (FR-002-043)."""
    query = select(CatalogItem).where(CatalogItem.company_id == ctx.company_id, CatalogItem.status == "ACTIVE")
    if item_type:
        query = query.where(CatalogItem.item_type == item_type)
    if q:
        like = f"%{q}%"
        query = query.where((CatalogItem.name.ilike(like)) | (CatalogItem.code.ilike(like)))
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = db.execute(query.order_by(CatalogItem.name).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {
        "items": [{"id": str(i.id), "code": i.code, "name": i.name, "item_type": i.item_type} for i in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/catalogos/items", dependencies=[Depends(require_write_allowed)])
def create_item(
    body: ItemCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    if body.item_type not in ("PRODUCT", "SERVICE"):
        from app.core.errors import KontrolError

        raise KontrolError(code="INVALID_ITEM_TYPE", message="El tipo de ítem debe ser PRODUCT o SERVICE", status_code=422)
    # Validar relaciones antes de persistir (contrato de aislamiento)
    if body.category_id:
        _visible_en_empresa(db, ctx, TaxonomyNode, body.category_id, "CATEGORY_NOT_FOUND", "Categoría no encontrada")
    if body.base_unit_id:
        _unidad_visible(db, ctx, body.base_unit_id)
    if body.tax_profile_id:
        _visible_en_empresa(db, ctx, ProfileVersion, body.tax_profile_id, "PROFILE_NOT_FOUND", "Perfil no encontrado")
    if body.item_type == "PRODUCT" and body.inventory_profile_id:
        _visible_en_empresa(db, ctx, ProfileVersion, body.inventory_profile_id, "PROFILE_NOT_FOUND", "Perfil no encontrado")
    if body.item_type == "SERVICE" and body.billing_unit_id:
        _unidad_visible(db, ctx, body.billing_unit_id)
    item = CatalogItem(
        company_id=ctx.company_id,
        code=body.code,
        name=body.name,
        item_type=body.item_type,
        short_description=body.short_description,
        category_id=body.category_id,
        base_unit_id=body.base_unit_id,
        tax_profile_id=body.tax_profile_id,
        status="ACTIVE",
        created_by=str(actor.id),
    )
    db.add(item)
    db.flush()
    if body.item_type == "PRODUCT":
        db.add(Product(item_id=str(item.id), inventory_profile_id=body.inventory_profile_id))
    else:
        db.add(
            Service(
                item_id=str(item.id),
                billing_unit_id=body.billing_unit_id,
                duration=body.duration,
                recurrence=body.recurrence,
                contract_required=body.contract_required,
                evidence_required=body.evidence_required,
            )
        )
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "code": item.code, "name": item.name, "item_type": item.item_type}


@router.get("/catalogos/items/{item_id}")
def get_item(item_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("maestros", "view")), ctx: CompanyContext = Depends(get_company_context)):
    item = db.get(CatalogItem, item_id)
    if not item or item.company_id != ctx.company_id:
        raise NotFoundError(code="ITEM_NOT_FOUND", message="Ítem no encontrado")
    return {
        "id": str(item.id),
        "code": item.code,
        "name": item.name,
        "item_type": item.item_type,
        "short_description": item.short_description,
        "status": item.status,
        "allowed_actions": master_service.item_allowed_actions(item.status),
    }


@router.get("/catalogos/taxonomia")
def list_taxonomy(parent_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("maestros", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(TaxonomyNode).where((TaxonomyNode.company_id == ctx.company_id) | (TaxonomyNode.company_id.is_(None)))
    if parent_id:
        query = query.where(TaxonomyNode.parent_id == parent_id)
    return [{"id": str(n.id), "code": n.code, "name": n.name, "level": n.level, "status": n.status} for n in db.execute(query.order_by(TaxonomyNode.level, TaxonomyNode.name)).scalars().all()]


@router.get("/catalogos/taxonomia/search")
def search_taxonomy(
    q: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("maestros", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    """Búsqueda asíncrona de nodos de taxonomía para AsyncCombobox (FR-002-043, PDD-API-12)."""
    query = select(TaxonomyNode).where(
        ((TaxonomyNode.company_id == ctx.company_id) | (TaxonomyNode.company_id.is_(None)))
        & (TaxonomyNode.status == "ACTIVE")
    )
    if q:
        query = query.where(
            TaxonomyNode.name.ilike(f"%{q}%") | TaxonomyNode.code.ilike(f"%{q}%")
        )
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    items = db.execute(
        query.order_by(TaxonomyNode.name, TaxonomyNode.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    return {
        "items": [{"id": str(n.id), "code": n.code, "name": n.name, "level": n.level} for n in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/catalogos/taxonomia", dependencies=[Depends(require_write_allowed)])
def create_taxonomy(body: TaxonomyCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("maestros", "create")), ctx: CompanyContext = Depends(get_company_context)):
    if body.parent_id:
        _visible_en_empresa(db, ctx, TaxonomyNode, body.parent_id, "TAXONOMY_NODE_NOT_FOUND", "Nodo de taxonomía no encontrado")
    node = TaxonomyNode(
        company_id=ctx.company_id,
        code=body.code,
        name=body.name,
        level=body.level,
        parent_id=body.parent_id,
        applies_to=body.applies_to,
        status="ACTIVE",
        created_by=str(actor.id),
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return {"id": str(node.id), "code": node.code, "name": node.name, "level": node.level}


@router.get("/catalogos/atributos")
def list_attributes(db: Session = Depends(get_db), user: User = Depends(require_permission("maestros", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(AttributeDefinition).where((AttributeDefinition.company_id == ctx.company_id) | (AttributeDefinition.company_id.is_(None)))
    return [{"id": str(a.id), "code": a.code, "name": a.name, "data_type": a.data_type, "searchable": a.searchable} for a in db.execute(query.order_by(AttributeDefinition.name)).scalars().all()]


@router.post("/catalogos/atributos", dependencies=[Depends(require_write_allowed)])
def create_attribute(body: AttributeCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("maestros", "create")), ctx: CompanyContext = Depends(get_company_context)):
    attr = AttributeDefinition(
        company_id=ctx.company_id,
        code=body.code,
        name=body.name,
        data_type=body.data_type,
        unit=body.unit,
        required=body.required,
        multiple=body.multiple,
        options=body.options,
        searchable=body.searchable,
        status="ACTIVE",
        created_by=str(actor.id),
    )
    db.add(attr)
    db.commit()
    db.refresh(attr)
    return {"id": str(attr.id), "code": attr.code, "name": attr.name}


@router.get("/catalogos/unidades")
def list_units(db: Session = Depends(get_db), user: User = Depends(require_permission("maestros", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(UnitOfMeasure).where((UnitOfMeasure.company_id == ctx.company_id) | (UnitOfMeasure.company_id.is_(None)))
    return [{"id": str(u.id), "code": u.code, "name": u.name, "symbol": u.symbol, "dimension": u.dimension} for u in db.execute(query.order_by(UnitOfMeasure.name)).scalars().all()]


@router.post("/catalogos/unidades", dependencies=[Depends(require_write_allowed)])
def create_unit(body: UnitCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("maestros", "create")), ctx: CompanyContext = Depends(get_company_context)):
    unit = UnitOfMeasure(
        company_id=ctx.company_id,
        code=body.code,
        name=body.name,
        dimension=body.dimension,
        symbol=body.symbol,
        decimals=body.decimals,
        status="ACTIVE",
        created_by=str(actor.id),
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return {"id": str(unit.id), "code": unit.code, "name": unit.name, "symbol": unit.symbol}


@router.post("/catalogos/unidades/{unit_id}/conversiones", dependencies=[Depends(require_write_allowed)])
def create_conversion(unit_id: str, body: ConversionCreate, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("maestros", "create")),
                      ctx: CompanyContext = Depends(get_company_context)):
    """Conversión entre dos unidades **visibles para la empresa activa**.

    La ruta creaba la conversión sin mirar nada: ni que las unidades existieran,
    ni de quién eran. Una unidad con `company_id` nulo es de la plataforma y la
    ven todas las empresas; una con empresa solo la ve la suya. Sin esa
    comprobación, la empresa B podía relacionar dos unidades privadas de A.

    La ruta equivalente de la Spec 011, `/unidades/{id}/conversiones-fisicas`,
    ya lo hacía y además exige la misma dimensión. Esta conserva su contrato y
    adopta la comprobación de pertenencia.
    """
    _unidad_visible(db, ctx, unit_id)
    _unidad_visible(db, ctx, body.to_unit_id)
    conversion = UnitConversion(from_unit_id=unit_id, to_unit_id=body.to_unit_id, factor=body.factor, rounding=body.rounding)
    db.add(conversion)
    db.commit()
    db.refresh(conversion)
    return {"id": str(conversion.id), "from_unit_id": unit_id, "to_unit_id": body.to_unit_id, "factor": body.factor}


# --------------------------------------------------------------------------- #
# Perfiles
# --------------------------------------------------------------------------- #
@router.get("/perfiles")
def list_profiles(profile_type: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("maestros", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(ProfileVersion).where((ProfileVersion.company_id == ctx.company_id) | (ProfileVersion.company_id.is_(None)))
    if profile_type:
        query = query.where(ProfileVersion.profile_type == profile_type)
    return [
        {
            "id": str(p.id),
            "code": p.code,
            "name": p.name,
            "profile_type": p.profile_type,
            "version": p.version,
            "status": p.status,
            "approval_status": p.approval_status,
        }
        for p in db.execute(query.order_by(ProfileVersion.profile_type, ProfileVersion.name)).scalars().all()
    ]


@router.post("/perfiles", dependencies=[Depends(require_write_allowed)])
def create_profile(body: ProfileCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("maestros", "create")), ctx: CompanyContext = Depends(get_company_context)):
    master_service.assert_no_overlap(
        db,
        profile_type=body.profile_type,
        code=body.code,
        effective_from=body.effective_from,
        effective_to=body.effective_to,
    )
    profile = ProfileVersion(
        company_id=ctx.company_id,
        code=body.code,
        name=body.name,
        profile_type=body.profile_type,
        effective_from=body.effective_from,
        effective_to=body.effective_to,
        stockable=body.stockable,
        lot=body.lot,
        serial=body.serial,
        expiry=body.expiry,
        trace_level=body.trace_level,
        tax_classification=body.tax_classification,
        islr_concept_ref=body.islr_concept_ref,
        requires_sica=body.requires_sica,
        requires_sigesai=body.requires_sigesai,
        requires_sacs=body.requires_sacs,
        status="ACTIVE",
        approval_status="DRAFT",
        created_by=str(actor.id),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return {
        "id": str(profile.id),
        "code": profile.code,
        "name": profile.name,
        "profile_type": profile.profile_type,
        "approval_status": profile.approval_status,
    }
