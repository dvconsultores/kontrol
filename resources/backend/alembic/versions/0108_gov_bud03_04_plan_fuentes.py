"""BUD-03/BUD-04: plan operativo, objetivos, metas, fuentes de financiamiento y restricciones (D-GOV-02)."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0108_gov_bud03_04_plan_fuentes"
down_revision = "0107_gov_bud01_ejercicio"
branch_labels = None
depends_on = None


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


TIPOS_HISTORIA_0107 = _en(
    'CREADO', 'NIVELES_CONFIGURADOS', 'CATEGORIA_CREADA', 'CATEGORIA_MODIFICADA',
    'CATEGORIA_ELIMINADA', 'CLASIFICADOR_REGISTRADO', 'PROCEDENCIA_MODIFICADA',
    'PARTIDA_CREADA', 'PARTIDA_ELIMINADA', 'PARTIDAS_IMPORTADAS', 'APROBADO',
    'RECONDUCIDO', 'CERRADO', 'PRECOMPROMISO_CAMBIADO',
)
TIPOS_HISTORIA = _en(
    'CREADO', 'NIVELES_CONFIGURADOS', 'CATEGORIA_CREADA', 'CATEGORIA_MODIFICADA',
    'CATEGORIA_ELIMINADA', 'CLASIFICADOR_REGISTRADO', 'PROCEDENCIA_MODIFICADA',
    'PARTIDA_CREADA', 'PARTIDA_ELIMINADA', 'PARTIDAS_IMPORTADAS', 'APROBADO',
    'RECONDUCIDO', 'CERRADO', 'PRECOMPROMISO_CAMBIADO',
    'PLAN_REGISTRADO', 'OBJETIVO_CREADO', 'OBJETIVO_MODIFICADO', 'OBJETIVO_ELIMINADO',
    'CATEGORIA_VINCULADA', 'META_CREADA', 'META_MODIFICADA', 'META_ELIMINADA', 'FUENTE_CREADA',
    'FUENTE_MODIFICADA', 'FUENTE_ELIMINADA', 'RESTRICCION_AGREGADA', 'RESTRICCION_ELIMINADA',
)


def upgrade() -> None:
    op.create_table(
        "gov_budget_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("year_id", sa.String(36), sa.ForeignKey("gov_budget_years.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("denominacion", sa.String(300), nullable=False),
        sa.Column("documento_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("documento_sha256", sa.String(64), nullable=True),
    )
    op.create_index("ix_gov_budget_plans_year_id", "gov_budget_plans", ["year_id"], unique=True)
    op.create_index("ix_gov_budget_plans_company_id", "gov_budget_plans", ["company_id"])
    op.create_index("ix_gov_budget_plans_documento_id", "gov_budget_plans", ["documento_id"])

    op.create_table(
        "gov_budget_objectives",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("year_id", sa.String(36), sa.ForeignKey("gov_budget_years.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("descripcion", sa.String(500), nullable=False),
        sa.UniqueConstraint("year_id", "codigo", name="uq_gov_budget_objectives_year_id_codigo"),
    )
    op.create_index("ix_gov_budget_objectives_year_id", "gov_budget_objectives", ["year_id"])
    op.create_index("ix_gov_budget_objectives_company_id", "gov_budget_objectives", ["company_id"])

    op.create_table(
        "gov_budget_goals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("year_id", sa.String(36), sa.ForeignKey("gov_budget_years.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("gov_budget_categories.id"), nullable=False),
        sa.Column("descripcion", sa.String(500), nullable=False),
        sa.Column("unidad_medida", sa.String(60), nullable=False),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=False),
        sa.Column("indicador", sa.String(200), nullable=False),
        sa.Column("formula", sa.String(500), nullable=True),
        sa.CheckConstraint("cantidad > 0", name="ck_gov_budget_goals_cantidad"),
    )
    op.create_index("ix_gov_budget_goals_year_id", "gov_budget_goals", ["year_id"])
    op.create_index("ix_gov_budget_goals_company_id", "gov_budget_goals", ["company_id"])
    op.create_index("ix_gov_budget_goals_category_id", "gov_budget_goals", ["category_id"])

    op.create_table(
        "gov_budget_funding_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("year_id", sa.String(36), sa.ForeignKey("gov_budget_years.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("denominacion", sa.String(300), nullable=False),
        sa.Column("procedencia", sa.String(1000), nullable=False),
        sa.Column("documento_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("documento_sha256", sa.String(64), nullable=True),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.UniqueConstraint("year_id", "codigo", name="uq_gov_budget_funding_sources_year_id_codigo"),
        sa.CheckConstraint(
            "vigente_hasta IS NULL OR vigente_hasta >= vigente_desde",
            name="ck_gov_budget_funding_sources_vigencia",
        ),
    )
    op.create_index("ix_gov_budget_funding_sources_year_id", "gov_budget_funding_sources", ["year_id"])
    op.create_index("ix_gov_budget_funding_sources_company_id", "gov_budget_funding_sources", ["company_id"])
    op.create_index("ix_gov_budget_funding_sources_documento_id", "gov_budget_funding_sources", ["documento_id"])

    op.create_table(
        "gov_budget_funding_restrictions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("year_id", sa.String(36), sa.ForeignKey("gov_budget_years.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("gov_budget_funding_sources.id"), nullable=False),
        sa.Column("descripcion", sa.String(500), nullable=False),
        sa.Column("fundamento", sa.String(500), nullable=False),
        sa.Column("partidas", sa.JSON(), nullable=False),
    )
    op.create_index("ix_gov_budget_funding_restrictions_year_id", "gov_budget_funding_restrictions", ["year_id"])
    op.create_index("ix_gov_budget_funding_restrictions_company_id", "gov_budget_funding_restrictions", ["company_id"])
    op.create_index("ix_gov_budget_funding_restrictions_source_id", "gov_budget_funding_restrictions", ["source_id"])

    op.add_column("gov_budget_categories", sa.Column("unit_id", sa.String(36), nullable=True))
    op.add_column("gov_budget_categories", sa.Column("objective_id", sa.String(36), nullable=True))
    op.create_index("ix_gov_budget_categories_unit_id", "gov_budget_categories", ["unit_id"])
    op.create_index("ix_gov_budget_categories_objective_id", "gov_budget_categories", ["objective_id"])
    op.create_foreign_key(
        "fk_gov_budget_categories_unit_id_gov_units",
        "gov_budget_categories",
        "gov_units",
        ["unit_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_gov_budget_categories_objective_id_gov_budget_objectives",
        "gov_budget_categories",
        "gov_budget_objectives",
        ["objective_id"],
        ["id"],
    )

    op.drop_constraint("ck_gov_budget_year_history_tipo", "gov_budget_year_history", type_="check")
    op.create_check_constraint(
        "ck_gov_budget_year_history_tipo",
        "gov_budget_year_history",
        f"tipo IN ({TIPOS_HISTORIA})",
    )

    for tabla in (
        "gov_budget_plans",
        "gov_budget_objectives",
        "gov_budget_goals",
        "gov_budget_funding_sources",
        "gov_budget_funding_restrictions",
    ):
        op.execute(f"""
            CREATE TRIGGER trg_{tabla}_frozen
            BEFORE INSERT OR UPDATE OR DELETE ON {tabla}
            FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio();
        """)


def downgrade() -> None:
    for tabla in (
        "gov_budget_plans",
        "gov_budget_objectives",
        "gov_budget_goals",
        "gov_budget_funding_sources",
        "gov_budget_funding_restrictions",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tabla}_frozen ON {tabla}")

    op.drop_constraint("ck_gov_budget_year_history_tipo", "gov_budget_year_history", type_="check")
    op.create_check_constraint(
        "ck_gov_budget_year_history_tipo",
        "gov_budget_year_history",
        f"tipo IN ({TIPOS_HISTORIA_0107})",
    )

    op.drop_constraint("fk_gov_budget_categories_objective_id_gov_budget_objectives", "gov_budget_categories", type_="foreignkey")
    op.drop_constraint("fk_gov_budget_categories_unit_id_gov_units", "gov_budget_categories", type_="foreignkey")
    op.drop_index("ix_gov_budget_categories_objective_id", table_name="gov_budget_categories")
    op.drop_index("ix_gov_budget_categories_unit_id", table_name="gov_budget_categories")
    op.drop_column("gov_budget_categories", "objective_id")
    op.drop_column("gov_budget_categories", "unit_id")

    op.drop_table("gov_budget_funding_restrictions")
    op.drop_table("gov_budget_funding_sources")
    op.drop_table("gov_budget_goals")
    op.drop_table("gov_budget_objectives")
    op.drop_table("gov_budget_plans")
