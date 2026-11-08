"""Servicio de Terceros: núcleo de Party con versión optimista y extensiones."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.master_data import service as master_service
from app.modules.master_data.models import Carrier, Customer, Driver, Party, Supplier
from app.modules.organization.models import Company
from app.shared.audit import record_audit

PARTY_ROLES: tuple[str, ...] = (
    "BENEFICIARIO",
    "CLIENTE",
    "CONDUCTOR",
    "PROVEEDOR",
    "TRANSPORTISTA",
    "VENDEDOR",
)


def normalize_role(role: str) -> str:
    """Normaliza un rol a su forma canónica."""
    normalized = role.strip().upper()
    if normalized not in PARTY_ROLES:
        raise KontrolError(
            code="PARTY_ROLE_INVALID",
            message=f"Rol no reconocido: {role}",
            status_code=422,
        )
    return normalized


def normalize_roles(roles: list[str]) -> list[str]:
    """Normaliza, desduplica y ordena roles."""
    normalized = sorted({normalize_role(role) for role in roles})
    if not normalized:
        raise KontrolError(
            code="PARTY_ROLE_REQUIRED_ONE",
            message="Debe indicar al menos un rol.",
            status_code=422,
        )
    return normalized


def check_version(entity: Any, if_match: str | None) -> None:
    """Valida la cabecera If-Match contra la versión actual del registro."""
    if if_match is None:
        raise KontrolError(
            code="VERSION_REQUIRED",
            message="Falta la versión del registro (cabecera If-Match).",
            status_code=428,
        )
    cleaned = if_match.strip().strip('"')
    if not cleaned.isdigit() or int(cleaned) != int(entity.version):
        raise ConflictError(
            code="VERSION_CONFLICT",
            message="El registro fue modificado por otra operación",
        )


def bump(entity: Any) -> None:
    """Incrementa la versión del registro."""
    entity.version = int(entity.version) + 1


def get_party(db: Session, company_id: str, party_id: str, *, for_update: bool = False) -> Party:
    """Obtiene un tercero por id y empresa, opcionalmente con bloqueo."""
    query = select(Party).where(Party.id == party_id, Party.company_id == company_id)
    if for_update:
        query = query.with_for_update()
    party = db.execute(query).scalar_one_or_none()
    if party is None:
        raise NotFoundError(code="PARTY_NOT_FOUND", message="Tercero no encontrado")
    return party


def check_tax_id_available(
    db: Session,
    *,
    company_id: str,
    tax_id: str | None,
    roles: list[str],
    exclude_party_id: str | None = None,
) -> None:
    """Valida que el RIF no esté en uso por otro tercero con rol compartido."""
    if tax_id is None:
        return

    parties = (
        db.execute(
            select(Party).where(Party.company_id == company_id, Party.tax_id == tax_id)
        )
        .scalars()
        .all()
    )
    if exclude_party_id is not None:
        parties = [party for party in parties if party.id != exclude_party_id]
    if not parties:
        return

    upper_roles = {role.upper() for role in roles}
    shares_role = False
    first_details: dict[str, Any] | None = None
    for party in parties:
        details = {
            "party_id": str(party.id),
            "code": party.code,
            "name": party.name,
            "roles": party.roles,
        }
        if first_details is None:
            first_details = details
        existing_roles = {role.upper() for role in (party.roles or [])}
        if existing_roles.intersection(upper_roles):
            shares_role = True
            first_details = details
            break

    if shares_role:
        raise ConflictError(
            code="PARTY_DUPLICATE_TAX_ID",
            message="Ya existe un tercero con este RIF y este rol en la empresa.",
            details=first_details,
        )
    raise ConflictError(
        code="PARTY_TAX_ID_EXISTS",
        message="Ya existe un tercero con este RIF: añada el rol a ese tercero.",
        details=first_details,
    )


def ensure_extension(db: Session, party: Party, role: str) -> None:
    """Crea la extensión correspondiente al rol si no existe."""
    model: type[Customer | Supplier | Carrier | Driver]
    if role == "CLIENTE":
        model = Customer
    elif role == "PROVEEDOR":
        model = Supplier
    elif role == "TRANSPORTISTA":
        model = Carrier
    elif role == "CONDUCTOR":
        model = Driver
    else:
        return

    exists = (
        db.execute(select(model).where(model.party_id == str(party.id))).scalars().first()
    )
    if exists is None:
        db.add(model(party_id=str(party.id)))


PERSON_TYPES: tuple[str, ...] = ("EXTRANJERA", "GUBERNAMENTAL", "JURIDICA", "NATURAL", "PUBLICA")


def normalize_person_type(value: str) -> str:
    if value not in PERSON_TYPES:
        raise KontrolError(
            code="PARTY_PERSON_TYPE_INVALID",
            message="Tipo de persona no reconocido.",
            status_code=422,
        )
    return value


def _audit_snapshot(party: Party) -> dict[str, Any]:
    return {
        "code": party.code,
        "economic_activity": party.economic_activity,
        "legal_name": party.legal_name,
        "name": party.name,
        "nationality": party.nationality,
        "person_type": party.person_type,
        "residence": party.residence,
        "roles": party.roles,
        "status": party.status,
        "tax_id": party.tax_id,
        "trade_name": party.trade_name,
        "version": party.version,
    }


def create_party(
    db: Session,
    *,
    company_id: str,
    actor_id: str,
    tenant_id: str,
    data: dict[str, Any],
) -> Party:
    """Crea un tercero completo con roles normalizados y extensiones."""
    db.execute(select(Company).where(Company.id == company_id).with_for_update())

    roles = normalize_roles(data.get("roles") or [])
    person_type = normalize_person_type(data.get("person_type") or "JURIDICA")
    tax_id = data.get("tax_id")
    if tax_id:
        tax_id = master_service.validate_tax_id(tax_id, person_type)
    else:
        tax_id = None
    check_tax_id_available(db, company_id=company_id, tax_id=tax_id, roles=roles)

    party = Party(
        company_id=company_id,
        code=data["code"],
        name=data["name"],
        person_type=person_type,
        nationality=data.get("nationality"),
        residence=data.get("residence"),
        legal_name=data.get("legal_name"),
        trade_name=data.get("trade_name"),
        tax_id=tax_id,
        economic_activity=data.get("economic_activity"),
        roles=roles,
        status="ACTIVE",
        created_by=actor_id,
    )
    db.add(party)
    db.flush()

    for role in roles:
        ensure_extension(db, party, role)

    audit_party(
        db,
        party=party,
        action="PARTY_CREATED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        after=_audit_snapshot(party),
    )
    return party


def update_party(
    db: Session,
    *,
    party: Party,
    actor_id: str,
    tenant_id: str,
    changes: dict[str, Any],
) -> Party:
    """Aplica cambios parciales a un tercero con revalidación y auditoría."""
    if party.status != "ACTIVE":
        raise ConflictError(
            code="PARTY_INACTIVE",
            message="El tercero no está activo.",
        )

    allowed = {
        "name",
        "person_type",
        "nationality",
        "residence",
        "legal_name",
        "trade_name",
        "tax_id",
        "economic_activity",
    }

    resulting: dict[str, Any] = {
        field: getattr(party, field)
        for field in allowed
    }
    for field, value in changes.items():
        if field not in allowed:
            continue
        if field == "tax_id":
            resulting[field] = value if value else None
        elif field == "name":
            if not isinstance(value, str) or not value.strip():
                raise KontrolError(
                    code="PARTY_NAME_REQUIRED",
                    message="El nombre es obligatorio.",
                    status_code=422,
                )
            resulting[field] = value
        elif field == "person_type":
            if value is None:
                raise KontrolError(
                    code="PARTY_PERSON_TYPE_INVALID",
                    message="Tipo de persona no reconocido.",
                    status_code=422,
                )
            resulting[field] = normalize_person_type(value)
        else:
            resulting[field] = value

    person_type = resulting["person_type"] or "JURIDICA"
    tax_id = resulting["tax_id"]
    if "tax_id" in changes or "person_type" in changes:
        if tax_id:
            tax_id = master_service.validate_tax_id(tax_id, person_type)
        resulting["tax_id"] = tax_id
        check_tax_id_available(
            db,
            company_id=party.company_id,
            tax_id=tax_id,
            roles=party.roles,
            exclude_party_id=str(party.id),
        )

    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    for field in allowed:
        current = getattr(party, field)
        new_value = resulting[field]
        if new_value != current:
            before[field] = current
            after[field] = new_value
            setattr(party, field, new_value)

    if not before:
        return party

    bump(party)
    audit_party(
        db,
        party=party,
        action="PARTY_UPDATED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        before=before,
        after=after,
    )
    return party


def _active_documents(
    db: Session,
    party: Party,
    *,
    role: str | None = None,
) -> list[dict[str, Any]]:
    """Devuelve los documentos activos que bloquean acciones sobre un tercero."""
    from app.modules.purchasing.models import (
        Advance,
        OpenItem,
        Payment,
        PaymentSchedule,
        PurchaseOrder,
        SupplierInvoice,
        SupplierQuote,
        Withholding,
    )
    from app.modules.regulatory.models import TransportDriver, TransportVehicle
    from app.modules.sales.models import SalesInvoice, SalesOrder, SalesQuote, SalesReturn
    from app.modules.treasury.models import TreasuryRefund

    _matrix = [
        ({"CLIENTE"}, "ventas", "SalesQuote", SalesQuote, SalesQuote.customer_id, ("DRAFT", "SENT", "ACCEPTED"), None),
        ({"CLIENTE"}, "ventas", "SalesOrder", SalesOrder, SalesOrder.customer_id, ("DRAFT", "SUBMITTED", "RELEASED", "PREPARING", "PREPARED", "CONFIRMED", "READY_FOR_BILLING", "INVOICED", "SHIPPED"), None),
        ({"CLIENTE"}, "ventas", "SalesInvoice", SalesInvoice, SalesInvoice.customer_id, ("DRAFT", "VALIDATED", "APPROVED", "EMITTED", "DELIVERED", "PARTIALLY_PAID"), None),
        ({"CLIENTE"}, "ventas", "SalesReturn", SalesReturn, SalesReturn.customer_id, ("DRAFT", "REQUESTED", "RECEIVED", "INSPECTED", "APPROVED"), None),
        ({"PROVEEDOR"}, "compras", "SupplierQuote", SupplierQuote, SupplierQuote.supplier_id, ("ACTIVE",), None),
        ({"PROVEEDOR"}, "compras", "PurchaseOrder", PurchaseOrder, PurchaseOrder.supplier_id, ("DRAFT", "SUBMITTED", "APPROVED", "PARTIALLY_RECEIVED", "RECEIVED"), None),
        ({"PROVEEDOR"}, "compras", "SupplierInvoice", SupplierInvoice, SupplierInvoice.supplier_id, ("DRAFT", "VALIDATED", "MATCHED", "EXCEPTION", "APPROVED", "POSTED", "PARTIALLY_PAID"), None),
        ({"PROVEEDOR"}, "compras", "PaymentSchedule", PaymentSchedule, PaymentSchedule.party_id, ("PENDING",), None),
        ({"CLIENTE"}, "cuentas", "OpenItem", OpenItem, OpenItem.party_id, ("OPEN",), "IN"),
        ({"PROVEEDOR"}, "cuentas", "OpenItem", OpenItem, OpenItem.party_id, ("OPEN",), "OUT"),
        ({"CLIENTE"}, "cuentas", "Payment", Payment, Payment.party_id, ("DRAFT", "SUBMITTED", "APPROVED"), "IN"),
        ({"PROVEEDOR"}, "cuentas", "Payment", Payment, Payment.party_id, ("DRAFT", "SUBMITTED", "APPROVED"), "OUT"),
        ({"CLIENTE"}, "cuentas", "Advance", Advance, Advance.party_id, ("ACTIVE",), "IN"),
        ({"PROVEEDOR"}, "cuentas", "Advance", Advance, Advance.party_id, ("ACTIVE",), "OUT"),
        (None, "compras", "Withholding", Withholding, Withholding.party_id, ("CALCULADA", "PRACTICADA", "EMITIDA", "DECLARADA", "PAGADA"), None),
        (None, "regulatorio", "TransportVehicle", TransportVehicle, TransportVehicle.owner_party_id, ("ACTIVE",), None),
        ({"CLIENTE"}, "tesoreria", "TreasuryRefund", TreasuryRefund, TreasuryRefund.customer_id, ("REQUESTED", "APPROVED"), None),
        ({"CONDUCTOR"}, "regulatorio", "TransportDriver", TransportDriver, TransportDriver.party_id, ("ACTIVE",), None),
    ]

    aggregated: dict[tuple[str, str], dict[str, Any]] = {}
    party_id = party.id
    for roles, module, document, model, column, active_statuses, direction in _matrix:
        if role is not None and roles is not None and role not in roles:
            continue

        tabla: Any = model
        query = select(func.count()).select_from(tabla).where(
            column == party_id,
            tabla.status.in_(active_statuses),
        )
        if direction is not None and hasattr(tabla, "direction"):
            query = query.where(tabla.direction == direction)
        count = db.execute(query).scalar() or 0
        if count <= 0:
            continue

        key = (module, document)
        if key not in aggregated:
            aggregated[key] = {"module": module, "document": document, "count": 0}
        aggregated[key]["count"] += count

    return list(aggregated.values())


def has_relations(db: Session, party: Party) -> bool:
    """Comprueba si un tercero tiene filas relacionadas que impidan su borrado."""
    from app.core.database import Base
    from app.modules.commercial.models import CustomerCommercialTerms
    from app.modules.inventory.models import InventoryLot

    excluded_tables = {
        "party_addresses",
        "party_contacts",
        "party_bank_accounts",
        "customers",
        "suppliers",
        "carriers",
        "drivers",
    }

    party_id = party.id
    for table in Base.metadata.sorted_tables:
        if table.name in excluded_tables:
            continue
        for fk in table.foreign_keys:
            if fk.target_fullname != "parties.id":
                continue
            column = fk.parent
            count = db.execute(
                select(func.count()).select_from(table).where(column == party_id)
            ).scalar() or 0
            if count > 0:
                return True

    customer = db.execute(select(Customer).where(Customer.party_id == party_id)).scalar_one_or_none()
    if customer is not None:
        count = db.execute(
            select(func.count())
            .select_from(CustomerCommercialTerms)
            .where(CustomerCommercialTerms.customer_id == customer.id)
        ).scalar() or 0
        if count > 0:
            return True

    count = db.execute(
        select(func.count())
        .select_from(InventoryLot)
        .where(InventoryLot.supplier_id == party_id)
    ).scalar() or 0
    return count > 0


def add_role(
    db: Session,
    *,
    party: Party,
    role: str,
    actor_id: str,
    tenant_id: str,
) -> Party:
    normalized = normalize_role(role)
    if party.status != "ACTIVE":
        raise ConflictError(code="PARTY_INACTIVE", message="El tercero debe estar activo para modificar roles.")
    roles = party.roles or []
    if normalized in roles:
        return party
    new_roles = sorted(roles + [normalized])
    party.roles = new_roles
    ensure_extension(db, party=party, role=normalized)
    bump(party)
    audit_party(
        db,
        party=party,
        action="PARTY_ROLE_ADDED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        after={"role": normalized, "roles": new_roles},
    )
    return party


def remove_role(
    db: Session,
    *,
    party: Party,
    role: str,
    actor_id: str,
    tenant_id: str,
) -> Party:
    normalized = normalize_role(role)
    roles = party.roles or []
    if normalized not in roles:
        raise ConflictError(code="PARTY_ROLE_NOT_ASSIGNED", message="El rol no está asignado al tercero.")
    if len(roles) == 1:
        raise ConflictError(
            code="PARTY_LAST_ROLE",
            message="El tercero debe conservar al menos un rol.",
        )
    documents = _active_documents(db, party, role=normalized)
    if documents:
        raise ConflictError(
            code="PARTY_ROLE_IN_USE",
            message="El rol tiene documentos activos.",
            details={"documents": documents},
        )
    new_roles = sorted(r for r in roles if r != normalized)
    party.roles = new_roles
    bump(party)
    audit_party(
        db,
        party=party,
        action="PARTY_ROLE_REMOVED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        after={"role": normalized, "roles": new_roles},
    )
    return party


def activate_party(
    db: Session,
    *,
    party: Party,
    actor_id: str,
    tenant_id: str,
) -> Party:
    if party.status == "ACTIVE":
        raise ConflictError(
            code="PARTY_INVALID_TRANSITION",
            message="El tercero ya está activo.",
        )
    before = {"code": party.code, "status": party.status, "version": party.version}
    party.status = "ACTIVE"
    bump(party)
    audit_party(
        db,
        party=party,
        action="PARTY_ACTIVATED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        before=before,
        after={"code": party.code, "status": party.status, "version": party.version},
    )
    return party


def deactivate_party(
    db: Session,
    *,
    party: Party,
    actor_id: str,
    tenant_id: str,
) -> Party:
    if party.status == "INACTIVE":
        raise ConflictError(
            code="PARTY_INVALID_TRANSITION",
            message="El tercero ya está inactivo.",
        )
    documents = _active_documents(db, party)
    if documents:
        raise ConflictError(
            code="PARTY_HAS_ACTIVE_DOCUMENTS",
            message="El tercero tiene documentos activos.",
            details={"documents": documents},
        )
    before = {"code": party.code, "status": party.status, "version": party.version}
    party.status = "INACTIVE"
    bump(party)
    audit_party(
        db,
        party=party,
        action="PARTY_DEACTIVATED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        before=before,
        after={"code": party.code, "status": party.status, "version": party.version},
    )
    return party


def delete_party(
    db: Session,
    *,
    party: Party,
    actor_id: str,
    tenant_id: str,
) -> None:
    if has_relations(db, party):
        raise ConflictError(
            code="PARTY_HAS_RELATIONS",
            message="El tercero tiene relaciones y no puede eliminarse.",
        )
    before = {"code": party.code, "status": party.status, "version": party.version}
    audit_party(
        db,
        party=party,
        action="PARTY_DELETED",
        actor_id=actor_id,
        tenant_id=tenant_id,
        before=before,
    )

    from app.modules.master_data.models import PartyAddress, PartyBankAccount, PartyContact

    party_id = party.id
    db.execute(delete(PartyAddress).where(PartyAddress.party_id == party_id))
    db.execute(delete(PartyContact).where(PartyContact.party_id == party_id))
    db.execute(delete(PartyBankAccount).where(PartyBankAccount.party_id == party_id))
    db.execute(delete(Customer).where(Customer.party_id == party_id))
    db.execute(delete(Supplier).where(Supplier.party_id == party_id))
    db.execute(delete(Carrier).where(Carrier.party_id == party_id))
    db.execute(delete(Driver).where(Driver.party_id == party_id))
    db.delete(party)


def party_detail(db: Session, party: Party) -> dict[str, Any]:
    """Serializa un tercero para el detalle, con acciones y bloqueos reales."""
    blocking_documents = _active_documents(db, party)
    actions = master_service.party_allowed_actions(party)
    actions["deactivate"] = party.status == "ACTIVE" and not blocking_documents
    actions["delete"] = not has_relations(db, party)

    supplier = None
    if "PROVEEDOR" in (party.roles or []):
        supplier = db.execute(
            select(Supplier).where(Supplier.party_id == party.id)
        ).scalar_one_or_none()

    if supplier is None:
        actions.update({"approve": False, "reject": False, "resubmit": False})
        supplier_approval_status = None
    else:
        approval_status = supplier.approval_status
        supplier_approval_status = approval_status
        actions["approve"] = approval_status == "PENDING_APPROVAL"
        actions["reject"] = approval_status in {"PENDING_APPROVAL", "APPROVED"}
        actions["resubmit"] = approval_status == "REJECTED"

    result = party_dict(party)
    result["blocking_documents"] = blocking_documents
    result["allowed_actions"] = actions
    result["supplier_approval_status"] = supplier_approval_status
    return result


def audit_party(
    db: Session,
    *,
    party: Party,
    action: str,
    actor_id: str,
    tenant_id: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
) -> None:
    """Registra una acción de auditoría para un tercero."""
    record_audit(
        db,
        action=action,
        entity_type="Party",
        entity_id=str(party.id),
        tenant_id=tenant_id,
        company_id=party.company_id,
        user_id=actor_id,
        before=before,
        after=after,
        reason=reason,
    )


def party_dict(party: Party) -> dict[str, Any]:
    """Serializa un tercero para la API."""
    return {
        "id": str(party.id),
        "code": party.code,
        "name": party.name,
        "person_type": party.person_type,
        "nationality": party.nationality,
        "residence": party.residence,
        "legal_name": party.legal_name,
        "trade_name": party.trade_name,
        "tax_id": party.tax_id,
        "economic_activity": party.economic_activity,
        "roles": party.roles,
        "status": party.status,
        "version": party.version,
        "allowed_actions": master_service.party_allowed_actions(party),
    }
