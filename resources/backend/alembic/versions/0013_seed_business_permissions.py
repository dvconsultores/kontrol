"""Permisos de negocio al rol ADMIN (T-07 / permisos completos).

La auditoría 012 detectó que el seed original solo otorgaba 7 recursos al rol
ADMIN; los módulos de negocio usan maestros/compras/ventas/inventario/tesoreria/
fiscal/regulatorio/reportes, por lo que el admin recibía 403 en operaciones de
negocio. Esta migración otorga los permisos faltantes de forma idempotente a las
instalaciones existentes.

Revision ID: 0013_seed_business_permissions
Revises: 0012_numeric_money
Create Date: 2026-08-10
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0013_seed_business_permissions"
down_revision = "0012_numeric_money"
branch_labels = None
depends_on = None

RESOURCES_ACTIONS = {
    "dashboard": ["view"],
    "organization": ["view", "create", "edit", "deactivate", "activate"],
    "users": ["view", "create", "edit", "deactivate", "activate"],
    "roles": ["view", "create", "edit"],
    "audit": ["view"],
    "license": ["view", "create", "edit", "approve"],
    "homologacion": ["view", "create", "edit", "approve"],
    "maestros": ["view", "create", "edit", "deactivate"],
    "compras": ["view", "create", "approve", "quality", "apply"],
    "ventas": ["view", "create", "approve", "quality", "apply"],
    "inventario": ["view", "create", "approve", "transition", "reserve"],
    "tesoreria": ["view", "create", "approve"],
    "fiscal": ["view", "create", "approve"],
    "regulatorio": ["view", "create", "approve"],
    "reportes": ["view", "export"],
}


def upgrade() -> None:
    bind = op.get_bind()
    admin = bind.execute(
        sa.text("SELECT id FROM roles WHERE code = 'ADMIN' AND company_id IS NULL LIMIT 1")
    ).fetchone()
    if not admin:
        # Instalación sin rol ADMIN todavía: el seed de setup lo crea completo.
        return
    admin_id = admin[0]
    for resource, actions in RESOURCES_ACTIONS.items():
        for action in actions:
            row = bind.execute(
                sa.text("SELECT id FROM permissions WHERE resource = :r AND action = :a"),
                {"r": resource, "a": action},
            ).fetchone()
            if row:
                perm_id = row[0]
            else:
                perm_id = str(uuid.uuid4())
                bind.execute(
                    sa.text(
                        "INSERT INTO permissions (id, resource, action, scope_type) "
                        "VALUES (:id, :r, :a, 'COMPANY')"
                    ),
                    {"id": perm_id, "r": resource, "a": action},
                )
            rp = bind.execute(
                sa.text("SELECT 1 FROM role_permissions WHERE role_id = :rid AND permission_id = :pid"),
                {"rid": admin_id, "pid": perm_id},
            ).fetchone()
            if not rp:
                bind.execute(
                    sa.text(
                        "INSERT INTO role_permissions (id, role_id, permission_id) VALUES (:id, :rid, :pid)"
                    ),
                    {"id": str(uuid.uuid4()), "rid": admin_id, "pid": perm_id},
                )


def downgrade() -> None:
    # No se revocan permisos en rollback (evita quitar acceso por error).
    pass
