"""Servicio para direcciones, contactos y cuentas bancarias de terceros."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.master_data import party_service
from app.modules.master_data.models import (
    Party,
    PartyAddress,
    PartyBankAccount,
    PartyContact,
    Supplier,
)


def address_dict(address: PartyAddress) -> dict[str, Any]:
    return {
        "id": str(address.id),
        "party_id": address.party_id,
        "address_type": address.address_type,
        "country": address.country,
        "state": address.state,
        "city": address.city,
        "municipality": address.municipality,
        "postal_code": address.postal_code,
        "address": address.address,
        "is_fiscal": address.is_fiscal,
        "is_delivery": address.is_delivery,
        "validity": address.validity,
        "version": address.version,
    }


def contact_dict(contact: PartyContact) -> dict[str, Any]:
    return {
        "id": str(contact.id),
        "party_id": contact.party_id,
        "name": contact.name,
        "role": contact.role,
        "phone": contact.phone,
        "email": contact.email,
        "preferred": contact.preferred,
        "validity": contact.validity,
        "version": contact.version,
    }


def bank_dict(account: PartyBankAccount, full: bool) -> dict[str, Any]:
    account_number = account.account_number if full else f"****{account.account_number[-4:]}"
    return {
        "id": str(account.id),
        "party_id": account.party_id,
        "bank": account.bank,
        "account_type": account.account_type,
        "currency": account.currency,
        "account_number": account_number,
        "account_last4": account.account_number[-4:],
        "beneficiary": account.beneficiary,
        "verified": account.verified,
        "evidence": account.evidence,
        "validity": account.validity,
        "version": account.version,
    }


def _audit_address(address: PartyAddress) -> dict[str, Any]:
    return {
        "address_id": str(address.id),
        "address_type": address.address_type,
        "city": address.city,
        "is_delivery": address.is_delivery,
        "is_fiscal": address.is_fiscal,
        "state": address.state,
        "validity": address.validity,
    }


def _audit_contact(contact: PartyContact) -> dict[str, Any]:
    return {
        "contact_id": str(contact.id),
        "preferred": contact.preferred,
        "role": contact.role,
        "validity": contact.validity,
    }


def _audit_bank(account: PartyBankAccount) -> dict[str, Any]:
    return {
        "account_id": str(account.id),
        "account_last4": account.account_number[-4:],
        "account_type": account.account_type,
        "bank": account.bank,
        "currency": account.currency,
        "validity": account.validity,
        "verified": account.verified,
    }


def _clear_fiscal_flags(db: Session, party_id: str, keep_id: str) -> None:
    addresses = db.scalars(
        select(PartyAddress).where(
            PartyAddress.party_id == party_id,
            PartyAddress.validity == "ACTIVE",
            PartyAddress.is_fiscal.is_(True),
            PartyAddress.id != keep_id,
        )
    ).all()
    for address in addresses:
        address.is_fiscal = False
        party_service.bump(address)


def _clear_preferred_contacts(db: Session, party_id: str, keep_id: str) -> None:
    contacts = db.scalars(
        select(PartyContact).where(
            PartyContact.party_id == party_id,
            PartyContact.validity == "ACTIVE",
            PartyContact.preferred.is_(True),
            PartyContact.id != keep_id,
        )
    ).all()
    for contact in contacts:
        contact.preferred = False
        party_service.bump(contact)


def _get_party_for_mutation(db: Session, company_id: str, party_id: str) -> Party:
    party = party_service.get_party(db, company_id, party_id, for_update=True)
    if party.status != "ACTIVE":
        raise ConflictError(code="PARTY_INACTIVE", message="El tercero está inactivo")
    return party


def _get_address(db: Session, party_id: str, child_id: str) -> PartyAddress:
    address = db.scalar(
        select(PartyAddress).where(
            PartyAddress.id == child_id,
            PartyAddress.party_id == party_id,
        )
    )
    if address is None:
        raise NotFoundError(code="PARTY_CHILD_NOT_FOUND", message="Registro no encontrado")
    return address


def _get_contact(db: Session, party_id: str, child_id: str) -> PartyContact:
    contact = db.scalar(
        select(PartyContact).where(
            PartyContact.id == child_id,
            PartyContact.party_id == party_id,
        )
    )
    if contact is None:
        raise NotFoundError(code="PARTY_CHILD_NOT_FOUND", message="Registro no encontrado")
    return contact


def _get_bank_account(db: Session, party_id: str, child_id: str) -> PartyBankAccount:
    account = db.scalar(
        select(PartyBankAccount).where(
            PartyBankAccount.id == child_id,
            PartyBankAccount.party_id == party_id,
        )
    )
    if account is None:
        raise NotFoundError(code="PARTY_CHILD_NOT_FOUND", message="Registro no encontrado")
    return account


def _supplier_pending_approval(db: Session, party: Party, actor_id: str, tenant_id: str) -> None:
    supplier = db.scalar(select(Supplier).where(Supplier.party_id == party.id))
    if supplier is not None and supplier.approval_status == "APPROVED":
        party_service.bump(supplier)
        supplier.approval_status = "PENDING_APPROVAL"
        party_service.audit_party(
            db,
            party=party,
            action="SUPPLIER_APPROVAL_CHANGED",
            actor_id=actor_id,
            tenant_id=tenant_id,
            before={"approval_status": "APPROVED"},
            after={"approval_status": "PENDING_APPROVAL"},
        )


def list_addresses(db: Session, company_id: str, party_id: str) -> list[dict[str, Any]]:
    party_service.get_party(db, company_id, party_id)
    addresses = db.scalars(
        select(PartyAddress)
        .where(PartyAddress.party_id == party_id)
        .order_by(PartyAddress.created_at)
    ).all()
    return [address_dict(address) for address in addresses]


def create_address(
    db: Session,
    *,
    company_id: str,
    party_id: str,
    actor_id: str,
    tenant_id: str,
    data: dict[str, Any],
) -> PartyAddress:
    party = _get_party_for_mutation(db, company_id, party_id)
    address = PartyAddress(party_id=party_id, **data)
    db.add(address)
    db.flush()
    if address.is_fiscal:
        _clear_fiscal_flags(db, party_id, keep_id=str(address.id))
    party_service.audit_party(
        db,
        party=party,
        action="PARTY_ADDRESS_CREATED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        after=_audit_address(address),
    )
    return address


def update_address(
    db: Session,
    *,
    company_id: str,
    party_id: str,
    child_id: str,
    actor_id: str,
    tenant_id: str,
    data: dict[str, Any],
    if_match: str | None,
) -> PartyAddress:
    party = _get_party_for_mutation(db, company_id, party_id)
    address = _get_address(db, party_id, child_id)
    if address.validity != "ACTIVE":
        raise ConflictError(code="PARTY_CHILD_INACTIVE", message="El registro está inactivo")
    party_service.check_version(address, if_match)
    for key, value in data.items():
        setattr(address, key, value)
    if address.is_fiscal:
        _clear_fiscal_flags(db, party_id, keep_id=str(address.id))
    party_service.bump(address)
    party_service.audit_party(
        db,
        party=party,
        action="PARTY_ADDRESS_UPDATED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        after=_audit_address(address),
    )
    return address


def deactivate_address(
    db: Session,
    *,
    company_id: str,
    party_id: str,
    child_id: str,
    actor_id: str,
    tenant_id: str,
) -> PartyAddress:
    party = _get_party_for_mutation(db, company_id, party_id)
    address = _get_address(db, party_id, child_id)
    if address.validity != "ACTIVE":
        raise ConflictError(code="PARTY_CHILD_INACTIVE", message="El registro está inactivo")
    address.validity = "INACTIVE"
    party_service.bump(address)
    party_service.audit_party(
        db,
        party=party,
        action="PARTY_ADDRESS_DEACTIVATED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        after=_audit_address(address),
    )
    return address


def list_contacts(db: Session, company_id: str, party_id: str) -> list[dict[str, Any]]:
    party_service.get_party(db, company_id, party_id)
    contacts = db.scalars(
        select(PartyContact)
        .where(PartyContact.party_id == party_id)
        .order_by(PartyContact.created_at)
    ).all()
    return [contact_dict(contact) for contact in contacts]


def create_contact(
    db: Session,
    *,
    company_id: str,
    party_id: str,
    actor_id: str,
    tenant_id: str,
    data: dict[str, Any],
) -> PartyContact:
    party = _get_party_for_mutation(db, company_id, party_id)
    if not any(data.get(field) for field in ("name", "phone", "email")):
        raise KontrolError(
            code="PARTY_CONTACT_EMPTY",
            message="Indica al menos nombre, teléfono o correo",
            status_code=422,
        )
    contact = PartyContact(party_id=party_id, **data)
    db.add(contact)
    db.flush()
    if contact.preferred:
        _clear_preferred_contacts(db, party_id, keep_id=str(contact.id))
    party_service.audit_party(
        db,
        party=party,
        action="PARTY_CONTACT_CREATED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        after=_audit_contact(contact),
    )
    return contact


def update_contact(
    db: Session,
    *,
    company_id: str,
    party_id: str,
    child_id: str,
    actor_id: str,
    tenant_id: str,
    data: dict[str, Any],
    if_match: str | None,
) -> PartyContact:
    party = _get_party_for_mutation(db, company_id, party_id)
    contact = _get_contact(db, party_id, child_id)
    if contact.validity != "ACTIVE":
        raise ConflictError(code="PARTY_CHILD_INACTIVE", message="El registro está inactivo")
    party_service.check_version(contact, if_match)
    for key, value in data.items():
        setattr(contact, key, value)
    if not any(getattr(contact, field) for field in ("name", "phone", "email")):
        raise KontrolError(
            code="PARTY_CONTACT_EMPTY",
            message="Indica al menos nombre, teléfono o correo",
            status_code=422,
        )
    if contact.preferred:
        _clear_preferred_contacts(db, party_id, keep_id=str(contact.id))
    party_service.bump(contact)
    party_service.audit_party(
        db,
        party=party,
        action="PARTY_CONTACT_UPDATED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        after=_audit_contact(contact),
    )
    return contact


def deactivate_contact(
    db: Session,
    *,
    company_id: str,
    party_id: str,
    child_id: str,
    actor_id: str,
    tenant_id: str,
) -> PartyContact:
    party = _get_party_for_mutation(db, company_id, party_id)
    contact = _get_contact(db, party_id, child_id)
    if contact.validity != "ACTIVE":
        raise ConflictError(code="PARTY_CHILD_INACTIVE", message="El registro está inactivo")
    contact.validity = "INACTIVE"
    party_service.bump(contact)
    party_service.audit_party(
        db,
        party=party,
        action="PARTY_CONTACT_DEACTIVATED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        after=_audit_contact(contact),
    )
    return contact


def list_bank_accounts(
    db: Session,
    company_id: str,
    party_id: str,
    full: bool,
) -> list[dict[str, Any]]:
    party_service.get_party(db, company_id, party_id)
    accounts = db.scalars(
        select(PartyBankAccount)
        .where(PartyBankAccount.party_id == party_id)
        .order_by(PartyBankAccount.created_at)
    ).all()
    return [bank_dict(account, full) for account in accounts]


def create_bank_account(
    db: Session,
    *,
    company_id: str,
    party_id: str,
    actor_id: str,
    tenant_id: str,
    data: dict[str, Any],
) -> PartyBankAccount:
    party = _get_party_for_mutation(db, company_id, party_id)
    account = PartyBankAccount(party_id=party_id, verified=False, evidence=None, **data)
    db.add(account)
    db.flush()
    _supplier_pending_approval(db, party, actor_id, tenant_id)
    party_service.audit_party(
        db,
        party=party,
        action="PARTY_BANK_ACCOUNT_CREATED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        after=_audit_bank(account),
    )
    return account


def update_bank_account(
    db: Session,
    *,
    company_id: str,
    party_id: str,
    child_id: str,
    actor_id: str,
    tenant_id: str,
    data: dict[str, Any],
    if_match: str | None,
) -> PartyBankAccount:
    party = _get_party_for_mutation(db, company_id, party_id)
    account = _get_bank_account(db, party_id, child_id)
    if account.validity != "ACTIVE":
        raise ConflictError(code="PARTY_CHILD_INACTIVE", message="El registro está inactivo")
    party_service.check_version(account, if_match)
    for key, value in data.items():
        setattr(account, key, value)
    account.verified = False
    account.evidence = None
    party_service.bump(account)
    _supplier_pending_approval(db, party, actor_id, tenant_id)
    party_service.audit_party(
        db,
        party=party,
        action="PARTY_BANK_ACCOUNT_UPDATED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        after=_audit_bank(account),
    )
    return account


def deactivate_bank_account(
    db: Session,
    *,
    company_id: str,
    party_id: str,
    child_id: str,
    actor_id: str,
    tenant_id: str,
) -> PartyBankAccount:
    party = _get_party_for_mutation(db, company_id, party_id)
    account = _get_bank_account(db, party_id, child_id)
    if account.validity != "ACTIVE":
        raise ConflictError(code="PARTY_CHILD_INACTIVE", message="El registro está inactivo")
    account.validity = "INACTIVE"
    account.verified = False
    party_service.bump(account)
    _supplier_pending_approval(db, party, actor_id, tenant_id)
    party_service.audit_party(
        db,
        party=party,
        action="PARTY_BANK_ACCOUNT_DEACTIVATED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        after=_audit_bank(account),
    )
    return account


def verify_bank_account(
    db: Session,
    *,
    company_id: str,
    party_id: str,
    child_id: str,
    actor_id: str,
    tenant_id: str,
    evidence: str,
) -> PartyBankAccount:
    party = _get_party_for_mutation(db, company_id, party_id)
    account = _get_bank_account(db, party_id, child_id)
    if account.validity != "ACTIVE":
        raise ConflictError(code="PARTY_CHILD_INACTIVE", message="El registro está inactivo")
    account.verified = True
    account.evidence = evidence
    party_service.bump(account)
    party_service.audit_party(
        db,
        party=party,
        action="PARTY_BANK_ACCOUNT_VERIFIED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        after=_audit_bank(account),
    )
    return account
