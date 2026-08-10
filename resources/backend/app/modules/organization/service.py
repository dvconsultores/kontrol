"""Servicios del módulo de organización (001).

Incluye helpers de alcance compartidos por los módulos de negocio.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.organization.models import Company, Warehouse


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
