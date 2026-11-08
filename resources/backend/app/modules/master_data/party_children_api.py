"""API de datos de terceros: direcciones, contactos y cuentas bancarias."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_permission, require_write_allowed
from app.modules.identity_access import authority
from app.modules.identity_access.models import User
from app.modules.master_data import party_children

router = APIRouter(prefix="/maestros", tags=["maestros"])


class AddressCreate(BaseModel):
    address_type: str = "PRINCIPAL"
    country: str = "VE"
    state: str | None = None
    city: str | None = None
    municipality: str | None = None
    postal_code: str | None = None
    address: str = Field(min_length=1, max_length=1000)
    is_fiscal: bool = False
    is_delivery: bool = False


def _validar_no_nulos(model: BaseModel, nombres: set[str]) -> None:
    for nombre in nombres:
        if nombre in model.model_fields_set and getattr(model, nombre) is None:
            raise ValueError(f"El campo {nombre} no puede ser null")


class AddressUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address_type: str | None = None
    country: str | None = None
    state: str | None = None
    city: str | None = None
    municipality: str | None = None
    postal_code: str | None = None
    address: str | None = Field(default=None, min_length=1, max_length=1000)
    is_fiscal: bool | None = None
    is_delivery: bool | None = None

    @model_validator(mode="after")
    def _validar(self) -> AddressUpdate:
        _validar_no_nulos(
            self,
            {"address_type", "country", "address", "is_fiscal", "is_delivery"},
        )
        return self


class ContactCreate(BaseModel):
    name: str | None = None
    role: str | None = None
    phone: str | None = None
    email: str | None = None
    preferred: bool = False


class ContactUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    role: str | None = None
    phone: str | None = None
    email: str | None = None
    preferred: bool | None = None

    @model_validator(mode="after")
    def _validar(self) -> ContactUpdate:
        _validar_no_nulos(self, {"preferred"})
        return self


class BankAccountCreate(BaseModel):
    bank: str
    account_type: str = "CORRIENTE"
    currency: str = "VED"
    account_number: str = Field(min_length=1, max_length=40)
    beneficiary: str | None = None


class BankAccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bank: str | None = None
    account_type: str | None = None
    currency: str | None = None
    account_number: str | None = Field(default=None, min_length=1, max_length=40)
    beneficiary: str | None = None

    @model_validator(mode="after")
    def _validar(self) -> BankAccountUpdate:
        _validar_no_nulos(self, {"bank", "account_type", "currency", "account_number"})
        return self


class BankAccountVerify(BaseModel):
    evidence: str = Field(min_length=1)


def _bank_full(db: Session, actor: User, ctx: CompanyContext) -> bool:
    return "maestros:edit" in authority.capabilities_in_company(db, actor, ctx.company_id)


@router.get("/terceros/{party_id}/addresses")
def list_addresses(
    party_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    return {"items": party_children.list_addresses(db, ctx.company_id, party_id)}


@router.post("/terceros/{party_id}/addresses", dependencies=[Depends(require_write_allowed)])
def create_address(
    party_id: str,
    body: AddressCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    address = party_children.create_address(
        db,
        company_id=ctx.company_id,
        party_id=party_id,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
        data=body.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(address)
    return party_children.address_dict(address)


@router.patch(
    "/terceros/{party_id}/addresses/{child_id}",
    dependencies=[Depends(require_write_allowed)],
)
def update_address(
    party_id: str,
    child_id: str,
    body: AddressUpdate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    address = party_children.update_address(
        db,
        company_id=ctx.company_id,
        party_id=party_id,
        child_id=child_id,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
        data=body.model_dump(exclude_unset=True),
        if_match=if_match,
    )
    db.commit()
    db.refresh(address)
    return party_children.address_dict(address)


@router.post(
    "/terceros/{party_id}/addresses/{child_id}/deactivate",
    dependencies=[Depends(require_write_allowed)],
)
def deactivate_address(
    party_id: str,
    child_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    address = party_children.deactivate_address(
        db,
        company_id=ctx.company_id,
        party_id=party_id,
        child_id=child_id,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
    )
    db.commit()
    db.refresh(address)
    return party_children.address_dict(address)


@router.get("/terceros/{party_id}/contacts")
def list_contacts(
    party_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    return {"items": party_children.list_contacts(db, ctx.company_id, party_id)}


@router.post("/terceros/{party_id}/contacts", dependencies=[Depends(require_write_allowed)])
def create_contact(
    party_id: str,
    body: ContactCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    contact = party_children.create_contact(
        db,
        company_id=ctx.company_id,
        party_id=party_id,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
        data=body.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(contact)
    return party_children.contact_dict(contact)


@router.patch(
    "/terceros/{party_id}/contacts/{child_id}",
    dependencies=[Depends(require_write_allowed)],
)
def update_contact(
    party_id: str,
    child_id: str,
    body: ContactUpdate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    contact = party_children.update_contact(
        db,
        company_id=ctx.company_id,
        party_id=party_id,
        child_id=child_id,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
        data=body.model_dump(exclude_unset=True),
        if_match=if_match,
    )
    db.commit()
    db.refresh(contact)
    return party_children.contact_dict(contact)


@router.post(
    "/terceros/{party_id}/contacts/{child_id}/deactivate",
    dependencies=[Depends(require_write_allowed)],
)
def deactivate_contact(
    party_id: str,
    child_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    contact = party_children.deactivate_contact(
        db,
        company_id=ctx.company_id,
        party_id=party_id,
        child_id=child_id,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
    )
    db.commit()
    db.refresh(contact)
    return party_children.contact_dict(contact)


@router.get("/terceros/{party_id}/bank-accounts")
def list_bank_accounts(
    party_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    return {
        "items": party_children.list_bank_accounts(
            db,
            ctx.company_id,
            party_id,
            _bank_full(db, actor, ctx),
        )
    }


@router.post("/terceros/{party_id}/bank-accounts", dependencies=[Depends(require_write_allowed)])
def create_bank_account(
    party_id: str,
    body: BankAccountCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    account = party_children.create_bank_account(
        db,
        company_id=ctx.company_id,
        party_id=party_id,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
        data=body.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(account)
    return party_children.bank_dict(account, _bank_full(db, actor, ctx))


@router.patch(
    "/terceros/{party_id}/bank-accounts/{child_id}",
    dependencies=[Depends(require_write_allowed)],
)
def update_bank_account(
    party_id: str,
    child_id: str,
    body: BankAccountUpdate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    account = party_children.update_bank_account(
        db,
        company_id=ctx.company_id,
        party_id=party_id,
        child_id=child_id,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
        data=body.model_dump(exclude_unset=True),
        if_match=if_match,
    )
    db.commit()
    db.refresh(account)
    return party_children.bank_dict(account, _bank_full(db, actor, ctx))


@router.post(
    "/terceros/{party_id}/bank-accounts/{child_id}/deactivate",
    dependencies=[Depends(require_write_allowed)],
)
def deactivate_bank_account(
    party_id: str,
    child_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    account = party_children.deactivate_bank_account(
        db,
        company_id=ctx.company_id,
        party_id=party_id,
        child_id=child_id,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
    )
    db.commit()
    db.refresh(account)
    return party_children.bank_dict(account, _bank_full(db, actor, ctx))


@router.post(
    "/terceros/{party_id}/bank-accounts/{child_id}/verify",
    dependencies=[Depends(require_write_allowed)],
)
def verify_bank_account(
    party_id: str,
    child_id: str,
    body: BankAccountVerify,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("compras", "approve")),
    ctx: CompanyContext = Depends(get_company_context),
):
    account = party_children.verify_bank_account(
        db,
        company_id=ctx.company_id,
        party_id=party_id,
        child_id=child_id,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
        evidence=body.evidence,
    )
    db.commit()
    db.refresh(account)
    return party_children.bank_dict(account, _bank_full(db, actor, ctx))
