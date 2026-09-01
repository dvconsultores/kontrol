"""Servicios del módulo de organización (001).

Incluye helpers de alcance compartidos por los módulos de negocio.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.organization.models import Branch, Company, Warehouse


def company_in_tenant(db: Session, tenant_id: str, company_id: str) -> bool:
    """¿Pertenece la empresa al tenant? (Company.tenant_id == tenant_id)."""
    company = db.get(Company, company_id)
    return bool(company and company.tenant_id == tenant_id)


def branch_in_tenant(db: Session, tenant_id: str, branch_id: str) -> bool:
    """¿Pertenece la sucursal a una empresa del tenant? (Branch → Company)."""
    branch = db.get(Branch, branch_id)
    if not branch:
        return False
    return company_in_tenant(db, tenant_id, branch.company_id)


def warehouse_in_tenant(db: Session, tenant_id: str, warehouse_id: str) -> bool:
    """¿Pertenece el almacén a una empresa del tenant? (Warehouse → Company)."""
    warehouse = db.get(Warehouse, warehouse_id)
    if not warehouse:
        return False
    return company_in_tenant(db, tenant_id, warehouse.company_id)


def warehouse_belongs_to(company_id: str, warehouse: Warehouse) -> bool:
    """¿Es este almacén de esta empresa?

    Sustituye a `warehouse_in_tenant_scope`, que reconciliaba el identificador
    del tenant con el de la empresa porque los módulos de negocio usaban el
    primero como alcance. Su docstring lo describía como diseño vigente y su
    segunda rama buscaba las empresas del tenant.

    Desde N2 los cuatro llamantes pasan la empresa real, así que aquella
    reconciliación era código muerto que funcionaba por accidente: si algún día
    un identificador de empresa hubiera coincidido con uno de tenant, habría
    aceptado el almacén equivocado. El nombre, además, invitaba a reintroducir
    la confusión que ARCH-MC-001 vino a corregir.

    Lo que hace falta comprobar es una sola cosa, y es esta.
    """
    return warehouse.company_id == company_id
