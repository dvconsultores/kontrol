"""Spec 012 — maestros comerciales: las once tablas.

Revision ID: 0040_spec012_commercial_masters
Revises: 0039_n10_scope_reconciliation

Once tablas nuevas. Ninguna se siembra: ningún porcentaje, plazo, límite, zona
ni canal viene de fábrica (`P8`). Los catálogos nacen vacíos y es la empresa
quien los llena.

Ocho llevan `company_id` obligatoria con clave foránea a `companies`. Tres no la
llevan y la alcanzan por su padre; duplicarla daría dos respuestas a la misma
pregunta, y dos respuestas pueden discrepar.

Esta migración crea tablas, claves foráneas, unicidad y restricciones de
comprobación. La exclusión de solape entre versiones va aparte, en `0041`,
porque necesita una extensión y conviene poder verla fallar sola.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0040_spec012_commercial_masters"
down_revision = "0039_n10_scope_reconciliation"
branch_labels = None
depends_on = None

DINERO = sa.Numeric(18, 4)
PORCENTAJE = sa.Numeric(9, 4)
CANTIDAD = sa.Numeric(18, 6)


def _comunes() -> list[sa.Column]:
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
    ]


def upgrade() -> None:
    # -- 1. condiciones de pago -------------------------------------------- #
    op.create_table(
        "payment_terms", *_comunes(),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("days", sa.Integer(), nullable=True),
        sa.Column("installments", sa.JSON(), nullable=True),
        sa.Column("advance_percent", PORCENTAJE, nullable=True),
        sa.Column("due_offset_from", sa.String(32), nullable=False, server_default="ISSUE_DATE"),
        sa.Column("legacy_value", sa.String(255), nullable=True),
        sa.UniqueConstraint("company_id", "code", name="uq_payment_terms_company_code"),
        sa.CheckConstraint("kind IN ('CASH','DAYS','INSTALLMENTS','ADVANCE')",
                           name="ck_payment_terms_kind"),
        sa.CheckConstraint("due_offset_from IN ('ISSUE_DATE','DELIVERY_DATE','RECEPTION_DATE')",
                           name="ck_payment_terms_due_offset"),
    )
    op.create_index("ix_payment_terms_company", "payment_terms", ["company_id"])
    op.create_index("ix_payment_terms_company_id", "payment_terms", ["company_id"])

    # -- 2. zonas comerciales ---------------------------------------------- #
    op.create_table(
        "commercial_zones", *_comunes(),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("commercial_zones.id"), nullable=True),
        sa.Column("salesperson_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("route", sa.String(120), nullable=True),
        sa.Column("legacy_value", sa.String(255), nullable=True),
        sa.UniqueConstraint("company_id", "code", name="uq_commercial_zones_company_code"),
    )
    op.create_index("ix_commercial_zones_company", "commercial_zones", ["company_id"])
    op.create_index("ix_commercial_zones_company_id", "commercial_zones", ["company_id"])

    # -- 3. canales -------------------------------------------------------- #
    op.create_table(
        "sales_channels", *_comunes(),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("legacy_value", sa.String(255), nullable=True),
        sa.UniqueConstraint("company_id", "code", name="uq_sales_channels_company_code"),
    )
    op.create_index("ix_sales_channels_company", "sales_channels", ["company_id"])
    op.create_index("ix_sales_channels_company_id", "sales_channels", ["company_id"])

    # -- 4. listas de precios ---------------------------------------------- #
    op.create_table(
        "price_lists", *_comunes(),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("currency_id", sa.String(36), sa.ForeignKey("currencies.id"), nullable=False),
        sa.Column("segment", sa.String(120), nullable=True),
        sa.Column("channel_id", sa.String(36), sa.ForeignKey("sales_channels.id"), nullable=True),
        sa.Column("source", sa.String(255), nullable=True),
        sa.UniqueConstraint("company_id", "code", name="uq_price_lists_company_code"),
    )
    op.create_index("ix_price_lists_company", "price_lists", ["company_id"])
    op.create_index("ix_price_lists_company_id", "price_lists", ["company_id"])

    # -- 5. versiones ------------------------------------------------------- #
    op.create_table(
        "price_list_versions", *_comunes(),
        sa.Column("price_list_id", sa.String(36), sa.ForeignKey("price_lists.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column("approved_at", sa.String(64), nullable=True),
        sa.UniqueConstraint("price_list_id", "version_number",
                            name="uq_price_list_versions_list_number"),
        sa.CheckConstraint("status IN ('DRAFT','ACTIVE','SUPERSEDED','ARCHIVED')",
                           name="ck_price_list_versions_status"),
        sa.CheckConstraint("valid_to IS NULL OR valid_to > valid_from",
                           name="ck_price_list_versions_range"),
    )
    op.create_index("ix_price_list_versions_list_status", "price_list_versions",
                    ["price_list_id", "status"])
    op.create_index("ix_price_list_versions_price_list_id", "price_list_versions", ["price_list_id"])

    # -- 6. ítems ----------------------------------------------------------- #
    op.create_table(
        "price_list_items", *_comunes(),
        sa.Column("version_id", sa.String(36), sa.ForeignKey("price_list_versions.id"), nullable=False),
        sa.Column("item_id", sa.String(36), sa.ForeignKey("catalog_items.id"), nullable=True),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("taxonomy_nodes.id"), nullable=True),
        sa.Column("presentation_id", sa.String(36), sa.ForeignKey("presentations.id"), nullable=True),
        sa.Column("uom_id", sa.String(36), sa.ForeignKey("units_of_measure.id"), nullable=True),
        sa.Column("min_quantity", CANTIDAD, nullable=True),
        sa.Column("unit_price", DINERO, nullable=False),
        sa.CheckConstraint(
            "(item_id IS NOT NULL AND category_id IS NULL) OR "
            "(item_id IS NULL AND category_id IS NOT NULL)",
            name="ck_price_list_items_target"),
        sa.CheckConstraint("unit_price >= 0", name="ck_price_list_items_price"),
        sa.CheckConstraint("min_quantity IS NULL OR min_quantity > 0",
                           name="ck_price_list_items_min_qty"),
    )
    op.create_index("ix_price_list_items_version", "price_list_items", ["version_id"])
    op.create_index("ix_price_list_items_lookup", "price_list_items",
                    ["version_id", "item_id", "min_quantity"])

    # -- 7. precedencia ----------------------------------------------------- #
    op.create_table(
        "price_precedence", *_comunes(),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("source_kind", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("company_id", "order_index", name="uq_price_precedence_company_order"),
        sa.UniqueConstraint("company_id", "source_kind", name="uq_price_precedence_company_kind"),
        sa.CheckConstraint(
            "source_kind IN ('CUSTOMER_CONTRACT','CUSTOMER_LIST','SEGMENT_LIST',"
            "'BRANCH_LIST','COMPANY_LIST')",
            name="ck_price_precedence_kind"),
    )
    op.create_index("ix_price_precedence_company", "price_precedence", ["company_id"])
    op.create_index("ix_price_precedence_company_id", "price_precedence", ["company_id"])

    # -- 8. políticas de descuento ------------------------------------------ #
    op.create_table(
        "discount_policies", *_comunes(),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("applies_to", sa.String(16), nullable=False, server_default="ALL"),
        sa.Column("applies_ref", sa.String(120), nullable=True),
        sa.Column("max_percent", PORCENTAJE, nullable=True),
        sa.Column("requires_approval_above", PORCENTAJE, nullable=True),
        sa.Column("stackable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("incompatible_with", sa.JSON(), nullable=True),
        sa.UniqueConstraint("company_id", "code", "version",
                            name="uq_discount_policies_company_code_version"),
        sa.CheckConstraint("scope IN ('LINE','DOCUMENT')", name="ck_discount_policies_scope"),
        sa.CheckConstraint("applies_to IN ('ROLE','ITEM','CATEGORY','ALL')",
                           name="ck_discount_policies_applies"),
        sa.CheckConstraint("max_percent IS NULL OR (max_percent >= 0 AND max_percent <= 100)",
                           name="ck_discount_policies_max"),
    )
    op.create_index("ix_discount_policies_company", "discount_policies", ["company_id"])
    op.create_index("ix_discount_policies_company_id", "discount_policies", ["company_id"])

    # -- 9. políticas de crédito -------------------------------------------- #
    op.create_table(
        "credit_policies", *_comunes(),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("credit_limit", DINERO, nullable=True),
        sa.Column("exposure_calculation", sa.String(64), nullable=True),
        sa.Column("block_on_overdue", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("grace_days", sa.Integer(), nullable=True),
        sa.UniqueConstraint("company_id", "code", "version",
                            name="uq_credit_policies_company_code_version"),
        sa.CheckConstraint("credit_limit IS NULL OR credit_limit >= 0",
                           name="ck_credit_policies_limit"),
        sa.CheckConstraint("grace_days IS NULL OR grace_days >= 0",
                           name="ck_credit_policies_grace"),
    )
    op.create_index("ix_credit_policies_company", "credit_policies", ["company_id"])
    op.create_index("ix_credit_policies_company_id", "credit_policies", ["company_id"])

    # -- 10. condiciones del cliente ---------------------------------------- #
    op.create_table(
        "customer_commercial_terms", *_comunes(),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("price_list_id", sa.String(36), sa.ForeignKey("price_lists.id"), nullable=True),
        sa.Column("payment_term_id", sa.String(36), sa.ForeignKey("payment_terms.id"), nullable=True),
        sa.Column("commercial_zone_id", sa.String(36), sa.ForeignKey("commercial_zones.id"), nullable=True),
        sa.Column("sales_channel_id", sa.String(36), sa.ForeignKey("sales_channels.id"), nullable=True),
        sa.Column("credit_policy_id", sa.String(36), sa.ForeignKey("credit_policies.id"), nullable=True),
        sa.Column("salesperson_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("blocked_by", sa.String(36), nullable=True),
        sa.Column("blocked_at", sa.String(64), nullable=True),
        sa.Column("block_reason", sa.Text(), nullable=True),
        sa.UniqueConstraint("customer_id", name="uq_customer_commercial_terms_customer"),
    )

    # -- 11. comisiones, reservada ------------------------------------------ #
    op.create_table(
        "sales_commission_policies", *_comunes(),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("basis", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("company_id", "code", name="uq_sales_commission_policies_company_code"),
    )
    op.create_index("ix_sales_commission_policies_company", "sales_commission_policies", ["company_id"])
    op.create_index("ix_sales_commission_policies_company_id", "sales_commission_policies", ["company_id"])


def downgrade() -> None:
    for tabla in ("sales_commission_policies", "customer_commercial_terms", "credit_policies",
                  "discount_policies", "price_precedence", "price_list_items",
                  "price_list_versions", "price_lists", "sales_channels", "commercial_zones",
                  "payment_terms"):
        op.drop_table(tabla)
