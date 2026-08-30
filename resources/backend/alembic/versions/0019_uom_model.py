"""Modelo de unidades y presentaciones versionadas (Spec 011, F1-F2).

Extiende `units_of_measure`, corrige `unit_conversions`, amplía `presentations`
y crea `product_presentation_versions`, donde vive el factor con su vigencia.

Migración de **esquema pura**: válida en modo offline (`alembic upgrade --sql`).
La conversión de tipos va en `0020`, las columnas de línea en `0021` y el
backfill en `0022`, que es el único que lee datos.

Ninguna unidad ni presentación se crea aquí: el catálogo nace **vacío** y lo
puebla cada empresa (FR-011-004, P8).

Revision ID: 0019_uom_model
Revises: 0018_location_fk_and_legacy
Create Date: 2026-08-30
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0019_uom_model"
down_revision = "0018_location_fk_and_legacy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name

    # --- units_of_measure ---
    op.add_column("units_of_measure",
                  sa.Column("rounding_mode", sa.String(16), nullable=False, server_default="HALF_UP"))
    op.add_column("units_of_measure",
                  sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"))
    op.create_unique_constraint("uq_units_of_measure_company_code", "units_of_measure",
                                ["company_id", "code"])
    op.create_check_constraint("ck_units_of_measure_decimals", "units_of_measure",
                               "decimals >= 0 AND decimals <= 6")
    op.create_check_constraint(
        "ck_units_of_measure_dimension", "units_of_measure",
        "dimension IN ('CANTIDAD','MASA','PESO','VOLUMEN','LONGITUD','AREA','TIEMPO')")

    # --- unit_conversions: el factor deja de ser Float ---
    if dialect == "postgresql":
        op.execute("ALTER TABLE unit_conversions ALTER COLUMN factor "
                   "TYPE NUMERIC(18,6) USING factor::numeric(18,6)")
    else:
        op.alter_column("unit_conversions", "factor",
                        type_=sa.Numeric(18, 6), existing_type=sa.Float())
    op.create_unique_constraint("uq_unit_conversions_pair", "unit_conversions",
                                ["from_unit_id", "to_unit_id"])
    op.create_check_constraint("ck_unit_conversions_factor_positive", "unit_conversions",
                               "factor > 0")

    # --- presentations ---
    for column in (
        sa.Column("company_id", sa.String(36), nullable=True),
        # `code` nace nulo y se rellena desde el nombre antes de imponer la
        # unicidad: no se inventa un valor, se deriva del dato existente.
        sa.Column("code", sa.String(32), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("dispatchable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
    ):
        op.add_column("presentations", column)

    op.execute("UPDATE presentations SET code = UPPER(SUBSTR(name, 1, 32)) WHERE code IS NULL")
    op.execute("UPDATE presentations SET company_id = ("
               "  SELECT c.company_id FROM catalog_items c WHERE c.id = presentations.product_id)"
               " WHERE company_id IS NULL")
    op.alter_column("presentations", "code", existing_type=sa.String(32), nullable=False)
    op.create_unique_constraint("uq_presentations_product_code", "presentations",
                                ["product_id", "code"])
    op.create_index("ix_presentations_company_id", "presentations", ["company_id"])
    op.create_index("ix_presentations_product_status", "presentations", ["product_id", "status"])

    # --- catalog_items ---
    op.add_column("catalog_items",
                  sa.Column("base_unit_locked", sa.Boolean(), nullable=False, server_default=sa.false()))

    # --- product_presentation_versions ---
    op.create_table(
        "product_presentation_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("presentation_id", sa.String(36), sa.ForeignKey("presentations.id"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=True),
        sa.Column("factor_to_base", sa.Numeric(18, 6), nullable=False),
        sa.Column("factor_uom_id", sa.String(36), sa.ForeignKey("units_of_measure.id"), nullable=True),
        sa.Column("exact_in_base", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("factor_to_base > 0", name="ck_ppv_factor_positive"),
        sa.CheckConstraint("valid_to IS NULL OR valid_to > valid_from", name="ck_ppv_range"),
        sa.UniqueConstraint("presentation_id", "valid_from", name="uq_ppv_presentation_from"),
    )
    # Una sola versión **abierta** por presentación. Es lo que impide dos
    # factores vigentes a la vez sin exigir `btree_gist` (research §8).
    op.create_index("uq_ppv_open_version", "product_presentation_versions",
                    ["presentation_id"], unique=True,
                    postgresql_where=sa.text("valid_to IS NULL"),
                    sqlite_where=sa.text("valid_to IS NULL"))
    op.create_index("ix_ppv_resolution", "product_presentation_versions",
                    ["presentation_id", "valid_from", "valid_to"])
    op.create_index("ix_ppv_bulk", "product_presentation_versions", ["product_id", "company_id"])


def downgrade() -> None:
    op.drop_table("product_presentation_versions")
    op.drop_column("catalog_items", "base_unit_locked")
    op.drop_index("ix_presentations_product_status", table_name="presentations")
    op.drop_index("ix_presentations_company_id", table_name="presentations")
    op.drop_constraint("uq_presentations_product_code", "presentations", type_="unique")
    for column in ("version", "created_by", "dispatchable", "status", "code", "company_id"):
        op.drop_column("presentations", column)
    op.drop_constraint("ck_unit_conversions_factor_positive", "unit_conversions", type_="check")
    op.drop_constraint("uq_unit_conversions_pair", "unit_conversions", type_="unique")
    op.alter_column("unit_conversions", "factor", type_=sa.Float(), existing_type=sa.Numeric(18, 6))
    op.drop_constraint("ck_units_of_measure_dimension", "units_of_measure", type_="check")
    op.drop_constraint("ck_units_of_measure_decimals", "units_of_measure", type_="check")
    op.drop_constraint("uq_units_of_measure_company_code", "units_of_measure", type_="unique")
    op.drop_column("units_of_measure", "version")
    op.drop_column("units_of_measure", "rounding_mode")
