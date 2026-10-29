"""spec001 roles tenant

Revision ID: 0062_spec001_roles_tenant
Revises: 0061_spec001_audit_immutability

OD-ISO-11: `roles.tenant_id` anulable con FK a `tenants` (NULO = roles protegidos
del sistema y roles heredados). Los roles NUEVOS llevan el tenant del actor;
listar, asignar y detectar duplicados se filtran por tenant. Esta migración NO
rellena ni toca datos existentes.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0062_spec001_roles_tenant"
down_revision = "0061_spec001_audit_immutability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("roles") as batch:
        batch.add_column(sa.Column("tenant_id", sa.String(length=36), nullable=True))
        batch.create_foreign_key("fk_roles_tenant_id_tenants", "tenants", ["tenant_id"], ["id"])
        batch.create_index("ix_roles_tenant_id", ["tenant_id"])


def downgrade() -> None:
    with op.batch_alter_table("roles") as batch:
        batch.drop_index("ix_roles_tenant_id")
        batch.drop_constraint("fk_roles_tenant_id_tenants", type_="foreignkey")
        batch.drop_column("tenant_id")
