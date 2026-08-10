"""Servicios del módulo de organización (001).

Incluye helpers de alcance compartidos por los módulos de negocio.
"""

from __future__ import annotations

from sqlalchemy import select
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


def warehouse_in_tenant_scope(db: Session, tenant_id: str, warehouse: Warehouse) -> bool:
    """¿Pertenece el almacén a una empresa del tenant?

    Los módulos de negocio (ventas, compras, inventario) usan el `tenant_id`
    del usuario como alcance (`company_id`), mientras que la organización
    referencia los almacenes por `Company.id` (FK a companies).

    En el modelo MONO_COMPANY el tenant tiene una sola empresa, por lo que
    este helper reconcilia ambos identificadores sin debilitar el aislamiento
    entre tenants (solo acepta empresas del propio tenant).
    """
    if warehouse.company_id == tenant_id:
        return True
    companies = db.execute(
        select(Company.id).where(Company.tenant_id == tenant_id)
    ).scalars().all()
    return warehouse.company_id in companies
