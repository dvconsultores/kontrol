"""Spec 038 — la tasa deja de inventarse y el crédito a favor puede devolverse.

Dos decisiones expresas del owner abren este ciclo. La primera: el reembolso de
un crédito a favor se soporta, explícito y aprobado. La segunda: la política
cambiaria es parametrizable y la conversión, explícita.

La arquitectura funcional §9 dejaba el hueco a propósito —«las diferencias
cambiarias se calculan al aplicar o valorar **según política**»— y no había
política ninguna. Lo que había era peor que nada: `_rate_snapshot` devolvía
**1,0** cuando no encontraba la moneda o no había tasa cargada, así que un pago
en divisa se registraba al cambio uno y nadie se enteraba.

Todo nace anulable o con tabla nueva. No hay un solo `UPDATE`: las operaciones
anteriores no tienen procedencia de tasa y no se les inventa una.

Revision ID: 0055_spec038_treasury
Revises: 0054_spec036_returns
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0055_spec038_treasury"
down_revision = "0054_spec036_returns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------- política cambiaria
    # Versionada y con vigencia: «la política debe poder cambiar en el futuro sin
    # reescribir operaciones históricas». Por eso la operación guarda **qué
    # versión** la gobernó, y no se consulta la política de hoy para explicar un
    # movimiento de ayer.
    op.create_table(
        "treasury_fx_policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("policy_code", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("functional_currency", sa.String(8), nullable=False),
        #: `TRANSACTION` o `SETTLEMENT`. No se escribe cuál rige: se configura.
        sa.Column("effective_date_basis", sa.String(32), nullable=False,
                  server_default="SETTLEMENT"),
        sa.Column("rate_source", sa.String(120), nullable=True),
        sa.Column("rate_type", sa.String(64), nullable=True),
        sa.Column("allow_cross_currency", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("allow_manual_rate", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("manual_rate_requires_approval", sa.Boolean(), nullable=False,
                  server_default=sa.text("true")),
        sa.Column("allow_refund", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("refund_requires_approval", sa.Boolean(), nullable=False,
                  server_default=sa.text("true")),
        #: Qué norma o decisión la respalda. Vacío mientras no la haya: el
        #: mecanismo es parametrizable y la validación legal sigue en `D0-07`.
        sa.Column("authority_reference", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("effective_date_basis IN ('TRANSACTION', 'SETTLEMENT')",
                           name="ck_treasury_fx_policies_basis"),
        sa.CheckConstraint("status IN ('DRAFT', 'ACTIVE', 'SUPERSEDED')",
                           name="ck_treasury_fx_policies_status"),
    )
    op.create_index("ix_treasury_fx_policies_company_id", "treasury_fx_policies", ["company_id"])
    # Una sola versión activa por código y empresa: dos políticas vigentes a la
    # vez harían que la misma operación tuviera dos respuestas.
    op.create_index("uq_treasury_fx_policies_active", "treasury_fx_policies",
                    ["company_id", "policy_code"], unique=True,
                    postgresql_where=sa.text("status = 'ACTIVE'"))

    # --------------------------------------------------- instantánea de tasa
    # La procedencia entera de una conversión, congelada. Una tasa futura no
    # cambia una operación pasada porque la operación no vuelve a preguntar.
    op.create_table(
        "treasury_rate_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("source_currency", sa.String(8), nullable=False),
        sa.Column("target_currency", sa.String(8), nullable=False),
        sa.Column("rate", sa.Numeric(18, 8), nullable=False),
        sa.Column("rate_source", sa.String(120), nullable=True),
        sa.Column("rate_type", sa.String(64), nullable=True),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("exchange_rate_id", sa.String(36),
                  sa.ForeignKey("exchange_rates.id"), nullable=True),
        sa.Column("policy_id", sa.String(36),
                  sa.ForeignKey("treasury_fx_policies.id"), nullable=True),
        sa.Column("policy_version", sa.Integer(), nullable=True),
        #: `REGISTERED` si viene del maestro, `MANUAL` si la escribió una
        #: persona. Nunca hay una tercera: no existe tasa por defecto.
        sa.Column("origin", sa.String(16), nullable=False, server_default="REGISTERED"),
        sa.Column("manual_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("rate > 0", name="ck_treasury_rate_snapshots_positive"),
        sa.CheckConstraint("origin IN ('REGISTERED', 'MANUAL')",
                           name="ck_treasury_rate_snapshots_origin"),
    )
    op.create_index("ix_treasury_rate_snapshots_company_id", "treasury_rate_snapshots",
                    ["company_id"])

    # ------------------------------------------------------- conversión de moneda
    # Un hecho propio, no un número escondido dentro de otro movimiento.
    op.create_table(
        "treasury_fx_conversions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("source_account_id", sa.String(36),
                  sa.ForeignKey("financial_accounts.id"), nullable=False),
        sa.Column("target_account_id", sa.String(36),
                  sa.ForeignKey("financial_accounts.id"), nullable=False),
        sa.Column("source_currency", sa.String(8), nullable=False),
        sa.Column("target_currency", sa.String(8), nullable=False),
        sa.Column("source_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("target_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("rate_snapshot_id", sa.String(36),
                  sa.ForeignKey("treasury_rate_snapshots.id"), nullable=False),
        sa.Column("source_movement_id", sa.String(36), nullable=True),
        sa.Column("target_movement_id", sa.String(36), nullable=True),
        #: La diferencia cambiaria es su propio hecho y no reescribe ningún
        #: documento fiscal: «no alteran el IVA original por sí solas».
        sa.Column("exchange_difference", sa.Numeric(18, 2), nullable=True),
        sa.Column("difference_currency", sa.String(8), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="SETTLED"),
        sa.Column("reversal_of", sa.String(36), nullable=True),
        sa.Column("idempotency_key", sa.String(120), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("source_amount > 0 AND target_amount > 0",
                           name="ck_treasury_fx_conversions_positive"),
    )
    op.create_index("ix_treasury_fx_conversions_company_id", "treasury_fx_conversions",
                    ["company_id"])
    op.create_index("uq_treasury_fx_conversions_idem", "treasury_fx_conversions",
                    ["company_id", "idempotency_key"], unique=True,
                    postgresql_where=sa.text("idempotency_key IS NOT NULL"))

    # ------------------------------------------------------------- reembolso
    # El crédito lo habilita la 037 y el dinero lo mueve la 038. Aquí vive la
    # solicitud, su reserva y su ejecución; el saldo económico sigue allí.
    op.create_table(
        "treasury_refunds",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("credit_note_id", sa.String(36),
                  sa.ForeignKey("sales_credit_notes.id"), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("account_id", sa.String(36),
                  sa.ForeignKey("financial_accounts.id"), nullable=True),
        sa.Column("payment_method_id", sa.String(36),
                  sa.ForeignKey("payment_methods.id"), nullable=True),
        sa.Column("beneficiary_reference", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="REQUESTED"),
        sa.Column("status_reason", sa.Text(), nullable=True),
        sa.Column("movement_id", sa.String(36), nullable=True),
        sa.Column("reversal_of", sa.String(36), nullable=True),
        sa.Column("idempotency_key", sa.String(120), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by", sa.String(36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settled_by", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("amount > 0", name="ck_treasury_refunds_positive"),
        sa.CheckConstraint(
            "status IN ('REQUESTED', 'APPROVED', 'REJECTED', 'SETTLED', 'CANCELLED', 'REVERSED')",
            name="ck_treasury_refunds_status"),
    )
    op.create_index("ix_treasury_refunds_company_id", "treasury_refunds", ["company_id"])
    op.create_index("ix_treasury_refunds_credit_note_id", "treasury_refunds", ["credit_note_id"])
    op.create_index("uq_treasury_refunds_idem", "treasury_refunds",
                    ["company_id", "idempotency_key"], unique=True,
                    postgresql_where=sa.text("idempotency_key IS NOT NULL"))

    # ------------------------------------- el crédito reservado, en su dueña
    # El importe reservado para un reembolso no puede aplicarse a una CxC. Vive
    # en la nota porque el crédito es suyo: duplicar el saldo económico dentro
    # de tesorería sería tener dos verdades.
    op.add_column("sales_credit_notes",
                  sa.Column("refund_reserved", sa.Numeric(18, 2), nullable=False,
                            server_default=sa.text("0")))
    op.add_column("sales_credit_notes",
                  sa.Column("refunded", sa.Numeric(18, 2), nullable=False,
                            server_default=sa.text("0")))

    # --------------------------------- la instantánea que el movimiento usó
    op.add_column("bank_transactions",
                  sa.Column("rate_snapshot_id", sa.String(36), nullable=True))
    op.create_foreign_key("fk_bank_transactions_rate_snapshot", "bank_transactions",
                          "treasury_rate_snapshots", ["rate_snapshot_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_bank_transactions_rate_snapshot", "bank_transactions",
                       type_="foreignkey")
    op.drop_column("bank_transactions", "rate_snapshot_id")
    op.drop_column("sales_credit_notes", "refunded")
    op.drop_column("sales_credit_notes", "refund_reserved")
    op.drop_index("uq_treasury_refunds_idem", table_name="treasury_refunds")
    op.drop_index("ix_treasury_refunds_credit_note_id", table_name="treasury_refunds")
    op.drop_index("ix_treasury_refunds_company_id", table_name="treasury_refunds")
    op.drop_table("treasury_refunds")
    op.drop_index("uq_treasury_fx_conversions_idem", table_name="treasury_fx_conversions")
    op.drop_index("ix_treasury_fx_conversions_company_id", table_name="treasury_fx_conversions")
    op.drop_table("treasury_fx_conversions")
    op.drop_index("ix_treasury_rate_snapshots_company_id", table_name="treasury_rate_snapshots")
    op.drop_table("treasury_rate_snapshots")
    op.drop_index("uq_treasury_fx_policies_active", table_name="treasury_fx_policies")
    op.drop_index("ix_treasury_fx_policies_company_id", table_name="treasury_fx_policies")
    op.drop_table("treasury_fx_policies")
