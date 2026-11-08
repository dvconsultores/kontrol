"""API de extensiones de terceros: customer, supplier, carrier y driver."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Header
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_permission, require_write_allowed
from app.modules.identity_access.models import User
from app.modules.master_data import party_extensions
from app.modules.master_data.party_children_api import _validar_no_nulos

router = APIRouter(prefix="/maestros", tags=["maestros"])


class CustomerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    salesperson: str | None = None
    zone: str | None = None
    price_list: str | None = None
    payment_term: str | None = None
    credit_days: int | None = Field(default=None, ge=0)
    credit_limit: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    blocked: bool | None = None
    block_reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _validar(self) -> CustomerUpdate:
        _validar_no_nulos(self, {"credit_days", "blocked"})
        return self


class SupplierUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str | None = None
    buyer: str | None = None
    payment_term: str | None = None
    default_currency: str | None = Field(default=None, min_length=3, max_length=8)
    withholding_profile: str | None = None

    @model_validator(mode="after")
    def _validar(self) -> SupplierUpdate:
        _validar_no_nulos(self, {"default_currency"})
        return self


class CarrierUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    registration: str | None = None
    insurance: str | None = None
    permits: list[str] | None = None

    @model_validator(mode="after")
    def _validar(self) -> CarrierUpdate:
        _validar_no_nulos(self, {"permits"})
        return self


class DriverUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    license: str | None = None
    categories: list[str] | None = None
    expiry: AwareDatetime | None = None
    restrictions: str | None = None

    @model_validator(mode="after")
    def _validar(self) -> DriverUpdate:
        _validar_no_nulos(self, {"categories"})
        return self


class ApprovalBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=255)


@router.get(
    "/terceros/{party_id}/customer",
    dependencies=[Depends(require_permission("maestros", "view"))],
)
def get_customer(
    party_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
):
    ext = party_extensions.get_extension(db, ctx.company_id, party_id, "CLIENTE")
    db.commit()
    return party_extensions.extension_dict(ext)


@router.put(
    "/terceros/{party_id}/customer",
    dependencies=[Depends(require_write_allowed)],
)
def update_customer(
    party_id: str,
    body: CustomerUpdate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    ext = party_extensions.update_extension(
        db,
        company_id=ctx.company_id,
        party_id=party_id,
        role="CLIENTE",
        data=body.model_dump(exclude_unset=True),
        if_match=if_match,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
    )
    db.commit()
    db.refresh(ext)
    return party_extensions.extension_dict(ext)


@router.get(
    "/terceros/{party_id}/supplier",
    dependencies=[Depends(require_permission("maestros", "view"))],
)
def get_supplier(
    party_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
):
    ext = party_extensions.get_extension(db, ctx.company_id, party_id, "PROVEEDOR")
    db.commit()
    return party_extensions.extension_dict(ext)


@router.put(
    "/terceros/{party_id}/supplier",
    dependencies=[Depends(require_write_allowed)],
)
def update_supplier(
    party_id: str,
    body: SupplierUpdate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    ext = party_extensions.update_extension(
        db,
        company_id=ctx.company_id,
        party_id=party_id,
        role="PROVEEDOR",
        data=body.model_dump(exclude_unset=True),
        if_match=if_match,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
    )
    db.commit()
    db.refresh(ext)
    return party_extensions.extension_dict(ext)


@router.get(
    "/terceros/{party_id}/carrier",
    dependencies=[Depends(require_permission("maestros", "view"))],
)
def get_carrier(
    party_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
):
    ext = party_extensions.get_extension(db, ctx.company_id, party_id, "TRANSPORTISTA")
    db.commit()
    return party_extensions.extension_dict(ext)


@router.put(
    "/terceros/{party_id}/carrier",
    dependencies=[Depends(require_write_allowed)],
)
def update_carrier(
    party_id: str,
    body: CarrierUpdate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    ext = party_extensions.update_extension(
        db,
        company_id=ctx.company_id,
        party_id=party_id,
        role="TRANSPORTISTA",
        data=body.model_dump(exclude_unset=True),
        if_match=if_match,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
    )
    db.commit()
    db.refresh(ext)
    return party_extensions.extension_dict(ext)


@router.get(
    "/terceros/{party_id}/driver",
    dependencies=[Depends(require_permission("maestros", "view"))],
)
def get_driver(
    party_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
):
    ext = party_extensions.get_extension(db, ctx.company_id, party_id, "CONDUCTOR")
    db.commit()
    return party_extensions.extension_dict(ext)


@router.put(
    "/terceros/{party_id}/driver",
    dependencies=[Depends(require_write_allowed)],
)
def update_driver(
    party_id: str,
    body: DriverUpdate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    ext = party_extensions.update_extension(
        db,
        company_id=ctx.company_id,
        party_id=party_id,
        role="CONDUCTOR",
        data=body.model_dump(exclude_unset=True),
        if_match=if_match,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
    )
    db.commit()
    db.refresh(ext)
    return party_extensions.extension_dict(ext)


@router.post(
    "/terceros/{party_id}/roles/PROVEEDOR/approve",
    dependencies=[Depends(require_write_allowed)],
)
def approve_supplier(
    party_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("compras", "approve")),
    ctx: CompanyContext = Depends(get_company_context),
):
    ext = party_extensions.approve_supplier(
        db,
        company_id=ctx.company_id,
        party_id=party_id,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
    )
    db.commit()
    db.refresh(ext)
    return party_extensions.extension_dict(ext)


@router.post(
    "/terceros/{party_id}/roles/PROVEEDOR/reject",
    dependencies=[Depends(require_write_allowed)],
)
def reject_supplier(
    party_id: str,
    body: ApprovalBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("compras", "approve")),
    ctx: CompanyContext = Depends(get_company_context),
):
    ext = party_extensions.reject_supplier(
        db,
        company_id=ctx.company_id,
        party_id=party_id,
        reason=body.reason,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
    )
    db.commit()
    db.refresh(ext)
    return party_extensions.extension_dict(ext)


@router.post(
    "/terceros/{party_id}/roles/PROVEEDOR/resubmit",
    dependencies=[Depends(require_write_allowed)],
)
def resubmit_supplier(
    party_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    ext = party_extensions.resubmit_supplier(
        db,
        company_id=ctx.company_id,
        party_id=party_id,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
    )
    db.commit()
    db.refresh(ext)
    return party_extensions.extension_dict(ext)
