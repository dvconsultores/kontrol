"""Motor transversal de aprobaciones y segregación (Spec 045, F1).

Crea las 8 tablas del módulo `approvals` y renombra la tabla legada del módulo
regulatorio, que ocupaba el nombre `approval_requests`.

Migración de **esquema pura**: los permisos del recurso `aprobaciones` y el
traslado del histórico van en `0016_approvals_backfill`, siguiendo la separación
que el proyecto ya aplica (0013 es de datos). Así 0015 sigue siendo válida en
modo offline (`alembic upgrade --sql`).

Ninguna política, umbral, nivel ni aprobador se crea aquí: son datos de cada
empresa (Constitución P8, `ADR-D0-002` R-D0-02-1).

Revision ID: 0015_approvals
Revises: 0014_numeric_money_2
Create Date: 2026-08-29
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0015_approvals"
down_revision = "0014_numeric_money_2"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # El nombre `approval_requests` pasa al motor transversal: la tabla legada
    # del módulo regulatorio se renombra sin cambiar su comportamiento. Sus
    # datos se migran al motor en F6 (FR-045-073).
    #
    # PostgreSQL conserva los nombres de constraints e índices al renombrar una
    # tabla, así que hay que renombrarlos también o colisionan con los de la
    # tabla nueva (`pk_approval_requests`). SQLite recrea la tabla al renombrar
    # y no expone el problema: se detectó al validar sobre PostgreSQL real.
    op.rename_table("approval_requests", "regulatory_approval_requests")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER INDEX pk_approval_requests "
                   "RENAME TO pk_regulatory_approval_requests")
        op.execute("ALTER INDEX ix_approval_requests_company_id "
                   "RENAME TO ix_regulatory_approval_requests_company_id")

    op.create_table(
        "approval_policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("process_type", sa.String(64), nullable=False, index=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("requires_segregation", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allow_self_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("distinct_actors_across_levels", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("base_currency", sa.String(8), nullable=False, server_default="VED"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "process_type", "version",
                            name="uq_approval_policies_company_process_version"),
    )
    op.create_table(
        "approval_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("policy_id", sa.String(36), sa.ForeignKey("approval_policies.id"), nullable=False, index=True),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("condition_fields", sa.JSON(), nullable=False),
        sa.Column("is_exception", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("risk_class", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "approval_levels",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_id", sa.String(36), sa.ForeignKey("approval_rules.id"), nullable=False, index=True),
        sa.Column("level_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("resolver_type", sa.String(32), nullable=False),
        sa.Column("resolver_ref", sa.String(120), nullable=False),
        sa.Column("quorum_type", sa.String(16), nullable=False, server_default="ANY"),
        sa.Column("quorum_n", sa.Integer(), nullable=True),
        sa.Column("can_delegate", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sla_hours", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("process_type", sa.String(64), nullable=False, index=True),
        sa.Column("document_type", sa.String(64), nullable=False, index=True),
        sa.Column("document_id", sa.String(36), nullable=False, index=True),
        sa.Column("policy_id", sa.String(36), sa.ForeignKey("approval_policies.id"), nullable=True),
        sa.Column("policy_version", sa.String(32), nullable=False, server_default="1"),
        sa.Column("policy_snapshot", sa.JSON(), nullable=True),
        sa.Column("fingerprint", sa.String(64), nullable=False, index=True),
        sa.Column("fingerprint_fields", sa.JSON(), nullable=False),
        sa.Column("amount_base", sa.Numeric(18, 2), nullable=True),
        sa.Column("base_currency", sa.String(8), nullable=True),
        sa.Column("rate_snapshot", sa.Numeric(14, 6), nullable=True),
        sa.Column("requested_by", sa.String(36), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("current_level", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.Column("previous_request_id", sa.String(36), nullable=True),
        sa.Column("idempotency_key", sa.String(160), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # Impide dos solicitudes vivas para el mismo documento y la misma huella
    # (FR-045-053). Índice parcial: en PostgreSQL sólo cubre las no terminales.
    op.create_index(
        "uq_approval_requests_open_document",
        "approval_requests",
        ["company_id", "document_type", "document_id", "fingerprint"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING','IN_REVIEW')"),
        sqlite_where=sa.text("status IN ('PENDING','IN_REVIEW')"),
    )
    op.create_table(
        "approval_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("request_id", sa.String(36), sa.ForeignKey("approval_requests.id"), nullable=False, index=True),
        sa.Column("level_order", sa.Integer(), nullable=False),
        sa.Column("quorum_type", sa.String(16), nullable=False, server_default="ANY"),
        sa.Column("quorum_n", sa.Integer(), nullable=True),
        sa.Column("eligible_actors", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "approval_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("step_id", sa.String(36), sa.ForeignKey("approval_steps.id"), nullable=False, index=True),
        sa.Column("actor_id", sa.String(36), nullable=False, index=True),
        sa.Column("on_behalf_of_id", sa.String(36), nullable=True),
        sa.Column("delegation_id", sa.String(36), nullable=True),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # Un actor no decide dos veces sobre el mismo paso (INV-06).
        sa.UniqueConstraint("step_id", "actor_id", name="uq_approval_decisions_step_actor"),
    )
    op.create_table(
        "approval_delegations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("grantor_id", sa.String(36), nullable=False, index=True),
        sa.Column("grantee_id", sa.String(36), nullable=False, index=True),
        sa.Column("scope_process_type", sa.String(64), nullable=True),
        sa.Column("scope_branch_id", sa.String(36), nullable=True),
        sa.Column("scope_cost_center_id", sa.String(36), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("is_temporary_substitution", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "approval_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), nullable=False, index=True),
        sa.Column("request_id", sa.String(36), nullable=True, index=True),
        sa.Column("step_id", sa.String(36), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False, index=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

def downgrade() -> None:
    op.drop_table("approval_events")
    op.drop_table("approval_delegations")
    op.drop_table("approval_decisions")
    op.drop_table("approval_steps")
    op.drop_index("uq_approval_requests_open_document", table_name="approval_requests")
    op.drop_table("approval_requests")
    op.drop_table("approval_levels")
    op.drop_table("approval_rules")
    op.drop_table("approval_policies")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER INDEX pk_regulatory_approval_requests "
                   "RENAME TO pk_approval_requests")
        op.execute("ALTER INDEX ix_regulatory_approval_requests_company_id "
                   "RENAME TO ix_approval_requests_company_id")
    op.rename_table("regulatory_approval_requests", "approval_requests")
