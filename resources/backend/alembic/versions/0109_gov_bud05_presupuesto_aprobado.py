"""BUD-05: presupuesto aprobado: estimación de ingresos, créditos presupuestarios y existencias del Tesoro (LOPPM 229, 238-240)."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0109_gov_bud05_aprobado"
down_revision = "0108_gov_bud03_04_plan_fuentes"
branch_labels = None
depends_on = None


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


TIPOS_HISTORIA_0108 = _en(
    'CREADO', 'NIVELES_CONFIGURADOS', 'CATEGORIA_CREADA', 'CATEGORIA_MODIFICADA',
    'CATEGORIA_ELIMINADA', 'CLASIFICADOR_REGISTRADO', 'PROCEDENCIA_MODIFICADA',
    'PARTIDA_CREADA', 'PARTIDA_ELIMINADA', 'PARTIDAS_IMPORTADAS', 'APROBADO',
    'RECONDUCIDO', 'CERRADO', 'PRECOMPROMISO_CAMBIADO',
    'PLAN_REGISTRADO', 'OBJETIVO_CREADO', 'OBJETIVO_MODIFICADO', 'OBJETIVO_ELIMINADO',
    'CATEGORIA_VINCULADA', 'META_CREADA', 'META_MODIFICADA', 'META_ELIMINADA', 'FUENTE_CREADA',
    'FUENTE_MODIFICADA', 'FUENTE_ELIMINADA', 'RESTRICCION_AGREGADA', 'RESTRICCION_ELIMINADA',
)
TIPOS_HISTORIA = _en(
    'CREADO', 'NIVELES_CONFIGURADOS', 'CATEGORIA_CREADA', 'CATEGORIA_MODIFICADA',
    'CATEGORIA_ELIMINADA', 'CLASIFICADOR_REGISTRADO', 'PROCEDENCIA_MODIFICADA',
    'PARTIDA_CREADA', 'PARTIDA_ELIMINADA', 'PARTIDAS_IMPORTADAS', 'APROBADO',
    'RECONDUCIDO', 'CERRADO', 'PRECOMPROMISO_CAMBIADO',
    'PLAN_REGISTRADO', 'OBJETIVO_CREADO', 'OBJETIVO_MODIFICADO', 'OBJETIVO_ELIMINADO',
    'CATEGORIA_VINCULADA', 'META_CREADA', 'META_MODIFICADA', 'META_ELIMINADA', 'FUENTE_CREADA',
    'FUENTE_MODIFICADA', 'FUENTE_ELIMINADA', 'RESTRICCION_AGREGADA', 'RESTRICCION_ELIMINADA',
    'INGRESO_REGISTRADO', 'INGRESO_MODIFICADO', 'INGRESO_ELIMINADO',
    'CREDITO_REGISTRADO', 'CREDITO_MODIFICADO', 'CREDITO_ELIMINADO',
    'EXISTENCIAS_REGISTRADAS', 'EXISTENCIAS_ELIMINADAS',
)


def upgrade() -> None:
    op.create_table(
        "gov_budget_income_estimates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("year_id", sa.String(36), sa.ForeignKey("gov_budget_years.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("item_id", sa.String(36), sa.ForeignKey("gov_budget_classifier_items.id"), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.UniqueConstraint("year_id", "item_id", name="uq_gov_budget_income_estimates_year_id_item_id"),
        sa.CheckConstraint("monto > 0", name="ck_gov_budget_income_estimates_monto"),
    )
    op.create_index("ix_gov_budget_income_estimates_year_id", "gov_budget_income_estimates", ["year_id"])
    op.create_index("ix_gov_budget_income_estimates_company_id", "gov_budget_income_estimates", ["company_id"])
    op.create_index("ix_gov_budget_income_estimates_item_id", "gov_budget_income_estimates", ["item_id"])

    op.create_table(
        "gov_budget_credits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("year_id", sa.String(36), sa.ForeignKey("gov_budget_years.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("gov_budget_categories.id"), nullable=False),
        sa.Column("item_id", sa.String(36), sa.ForeignKey("gov_budget_classifier_items.id"), nullable=False),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("gov_budget_funding_sources.id"), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.UniqueConstraint("year_id", "category_id", "item_id", "source_id", name="uq_gov_budget_credits_year_id_category_id_item_id_source_id"),
        sa.CheckConstraint("monto > 0", name="ck_gov_budget_credits_monto"),
    )
    op.create_index("ix_gov_budget_credits_year_id", "gov_budget_credits", ["year_id"])
    op.create_index("ix_gov_budget_credits_company_id", "gov_budget_credits", ["company_id"])
    op.create_index("ix_gov_budget_credits_category_id", "gov_budget_credits", ["category_id"])
    op.create_index("ix_gov_budget_credits_item_id", "gov_budget_credits", ["item_id"])
    op.create_index("ix_gov_budget_credits_source_id", "gov_budget_credits", ["source_id"])

    op.create_table(
        "gov_budget_treasury_holdings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("year_id", sa.String(36), sa.ForeignKey("gov_budget_years.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("fecha_corte", sa.Date(), nullable=False),
        sa.Column("documento_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("documento_sha256", sa.String(64), nullable=False),
        sa.CheckConstraint("monto > 0", name="ck_gov_budget_treasury_holdings_monto"),
    )
    op.create_index("ix_gov_budget_treasury_holdings_year_id", "gov_budget_treasury_holdings", ["year_id"], unique=True)
    op.create_index("ix_gov_budget_treasury_holdings_company_id", "gov_budget_treasury_holdings", ["company_id"])
    op.create_index("ix_gov_budget_treasury_holdings_documento_id", "gov_budget_treasury_holdings", ["documento_id"])

    op.drop_constraint("ck_gov_budget_year_history_tipo", "gov_budget_year_history", type_="check")
    op.create_check_constraint(
        "ck_gov_budget_year_history_tipo",
        "gov_budget_year_history",
        f"tipo IN ({TIPOS_HISTORIA})",
    )

    for tabla in (
        "gov_budget_income_estimates",
        "gov_budget_credits",
        "gov_budget_treasury_holdings",
    ):
        op.execute(f"""
            CREATE TRIGGER trg_{tabla}_frozen
            BEFORE INSERT OR UPDATE OR DELETE ON {tabla}
            FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio();
        """)


def downgrade() -> None:
    for tabla in (
        "gov_budget_income_estimates",
        "gov_budget_credits",
        "gov_budget_treasury_holdings",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tabla}_frozen ON {tabla}")

    op.drop_constraint("ck_gov_budget_year_history_tipo", "gov_budget_year_history", type_="check")
    op.create_check_constraint(
        "ck_gov_budget_year_history_tipo",
        "gov_budget_year_history",
        f"tipo IN ({TIPOS_HISTORIA_0108})",
    )

    op.drop_table("gov_budget_treasury_holdings")
    op.drop_table("gov_budget_credits")
    op.drop_table("gov_budget_income_estimates")
