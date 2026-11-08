"""Servicio para extensiones de terceros: customer, supplier, carrier y driver."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError
from app.modules.master_data import party_service
from app.modules.master_data.models import (
    Carrier,
    Customer,
    Driver,
    Party,
    PartyBankAccount,
    Supplier,
)

ROLE_TO_MODEL: dict[str, Any] = {
    "CLIENTE": Customer,
    "PROVEEDOR": Supplier,
    "TRANSPORTISTA": Carrier,
    "CONDUCTOR": Driver,
}

AUDIT_KEYS = {
    "CUSTOMER_UPDATED": [
        "blocked",
        "credit_days",
        "credit_limit",
        "payment_term",
        "price_list",
        "salesperson",
        "zone",
    ],
    "SUPPLIER_UPDATED": [
        "buyer",
        "category",
        "default_currency",
        "payment_term",
        "withholding_profile",
    ],
    "CARRIER_UPDATED": ["insurance", "permits", "registration"],
    "DRIVER_UPDATED": ["categories", "expiry", "license"],
}


def _decimal_to_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _datetime_to_iso(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def extension_dict(ext: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": str(ext.id),
        "party_id": ext.party_id,
        "version": int(ext.version),
    }
    for col in ext.__table__.columns:
        if col.name in ("id", "party_id", "version"):
            continue
        value = getattr(ext, col.name)
        if col.name == "credit_limit":
            value = _decimal_to_str(value)
        elif col.name == "expiry":
            value = _datetime_to_iso(value)
        data[col.name] = value
    return data


def _audit_snapshot(ext: Any, keys: list[str]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for key in keys:
        value = getattr(ext, key)
        if key == "credit_limit":
            value = _decimal_to_str(value)
        elif key == "expiry":
            value = _datetime_to_iso(value)
        snapshot[key] = value
    return snapshot


def _load(
    db: Session,
    company_id: str,
    party_id: str,
    role: str,
    *,
    for_update: bool,
    require_active: bool,
) -> tuple[Party, Any]:
    party = party_service.get_party(db, company_id, party_id, for_update=for_update)
    normalized_roles = {r.upper() for r in party.roles or []}
    if role not in normalized_roles:
        raise ConflictError(code="PARTY_ROLE_REQUIRED", message="El tercero no tiene ese rol")
    if require_active and party.status != "ACTIVE":
        raise ConflictError(code="PARTY_INACTIVE", message="El tercero está inactivo")

    model = ROLE_TO_MODEL[role]
    ext = db.scalars(select(model).where(model.party_id == party_id)).one_or_none()
    if ext is None:
        party_service.ensure_extension(db, party, role)
        db.flush()
        ext = db.scalars(select(model).where(model.party_id == party_id)).one()
    return party, ext


def get_extension(
    db: Session,
    company_id: str,
    party_id: str,
    role: str,
) -> Any:
    _, ext = _load(
        db,
        company_id,
        party_id,
        role,
        for_update=False,
        require_active=False,
    )
    db.commit()
    return ext


def _transition(
    db: Session,
    party: Party,
    supplier: Supplier,
    new_status: str,
    actor_id: str,
    tenant_id: str,
    reason: str | None = None,
) -> Supplier:
    previous_status = supplier.approval_status
    supplier.approval_status = new_status
    party_service.bump(supplier)
    party_service.audit_party(
        db,
        party=party,
        action="SUPPLIER_APPROVAL_CHANGED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        before={"approval_status": previous_status},
        after={"approval_status": new_status},
        reason=reason,
    )
    return supplier


def update_extension(
    db: Session,
    company_id: str,
    party_id: str,
    role: str,
    data: dict[str, Any],
    if_match: str | None,
    actor_id: str,
    tenant_id: str,
) -> Any:
    party, ext = _load(
        db,
        company_id,
        party_id,
        role,
        for_update=True,
        require_active=True,
    )
    party_service.check_version(ext, if_match)

    audit_event = {
        "CLIENTE": "CUSTOMER_UPDATED",
        "PROVEEDOR": "SUPPLIER_UPDATED",
        "TRANSPORTISTA": "CARRIER_UPDATED",
        "CONDUCTOR": "DRIVER_UPDATED",
    }[role]
    audit_keys = AUDIT_KEYS[audit_event]
    audit_before = _audit_snapshot(ext, audit_keys)

    for key, value in data.items():
        setattr(ext, key, value)

    reason = None
    if role == "CLIENTE":
        if ext.blocked and not ext.block_reason:
            raise KontrolError(
                code="CUSTOMER_BLOCK_REASON_REQUIRED",
                message="Indica el motivo del bloqueo",
                status_code=422,
            )
        if not ext.blocked:
            ext.block_reason = None
        reason = ext.block_reason

    audit_after = _audit_snapshot(ext, audit_keys)
    party_service.bump(ext)
    party_service.audit_party(
        db,
        party=party,
        action=audit_event,
        actor_id=actor_id,
        tenant_id=tenant_id,
        before=audit_before,
        after=audit_after,
        reason=reason,
    )
    return ext


def approve_supplier(
    db: Session,
    company_id: str,
    party_id: str,
    actor_id: str,
    tenant_id: str,
) -> Supplier:
    party, supplier = _load(
        db,
        company_id,
        party_id,
        "PROVEEDOR",
        for_update=True,
        require_active=True,
    )

    if supplier.approval_status != "PENDING_APPROVAL":
        raise ConflictError(
            code="SUPPLIER_INVALID_TRANSITION",
            message="La transición de aprobación no es válida",
        )

    missing: list[str] = []
    if not party.tax_id:
        missing.append("tax_id")
    active_verified = db.scalar(
        select(PartyBankAccount).where(
            PartyBankAccount.party_id == party_id,
            PartyBankAccount.validity == "ACTIVE",
            PartyBankAccount.verified.is_(True),
        )
    )
    if active_verified is None:
        missing.append("verified_bank_account")

    if missing:
        raise ConflictError(
            code="SUPPLIER_APPROVAL_PRECONDITION",
            message="Faltan requisitos para aprobar",
            details={"missing": sorted(missing)},
        )

    return _transition(
        db,
        party,
        supplier,
        "APPROVED",
        actor_id,
        tenant_id,
    )


def reject_supplier(
    db: Session,
    company_id: str,
    party_id: str,
    reason: str,
    actor_id: str,
    tenant_id: str,
) -> Supplier:
    party, supplier = _load(
        db,
        company_id,
        party_id,
        "PROVEEDOR",
        for_update=True,
        require_active=False,
    )

    if supplier.approval_status not in ("PENDING_APPROVAL", "APPROVED"):
        raise ConflictError(
            code="SUPPLIER_INVALID_TRANSITION",
            message="La transición de aprobación no es válida",
        )

    return _transition(
        db,
        party,
        supplier,
        "REJECTED",
        actor_id,
        tenant_id,
        reason=reason,
    )


def resubmit_supplier(
    db: Session,
    company_id: str,
    party_id: str,
    actor_id: str,
    tenant_id: str,
) -> Supplier:
    party, supplier = _load(
        db,
        company_id,
        party_id,
        "PROVEEDOR",
        for_update=True,
        require_active=True,
    )

    if supplier.approval_status != "REJECTED":
        raise ConflictError(
            code="SUPPLIER_INVALID_TRANSITION",
            message="La transición de aprobación no es válida",
        )

    return _transition(
        db,
        party,
        supplier,
        "PENDING_APPROVAL",
        actor_id,
        tenant_id,
    )
