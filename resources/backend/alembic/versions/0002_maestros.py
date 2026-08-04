"""Maestros: terceros, catálogo y perfiles (002-maestros).

Revision ID: 0002_maestros
Revises: 0001_fundacion
Create Date: 2026-08-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_maestros"
down_revision = "0001_fundacion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------- Terceros ----------------
    op.create_table(
        "parties",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("person_type", sa.String(length=32), nullable=False, server_default="JURIDICA"),
        sa.Column("nationality", sa.String(length=64), nullable=True),
        sa.Column("residence", sa.String(length=64), nullable=True),
        sa.Column("legal_name", sa.String(length=255), nullable=True),
        sa.Column("trade_name", sa.String(length=255), nullable=True),
        sa.Column("tax_id", sa.String(length=20), nullable=True),
        sa.Column("economic_activity", sa.String(length=255), nullable=True),
        sa.Column("roles", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parties_company_id", "parties", ["company_id"])
    op.create_index("ix_parties_tax_id", "parties", ["tax_id"])

    op.create_table(
        "party_addresses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("address_type", sa.String(length=32), nullable=False, server_default="PRINCIPAL"),
        sa.Column("country", sa.String(length=64), nullable=False, server_default="VE"),
        sa.Column("state", sa.String(length=120), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("municipality", sa.String(length=120), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("is_fiscal", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_delivery", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("validity", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_party_addresses_party_id", "party_addresses", ["party_id"])

    op.create_table(
        "party_contacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("role", sa.String(length=64), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("preferred", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("validity", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_party_contacts_party_id", "party_contacts", ["party_id"])

    op.create_table(
        "party_bank_accounts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("bank", sa.String(length=120), nullable=False),
        sa.Column("account_type", sa.String(length=32), nullable=False, server_default="CORRIENTE"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("account_number", sa.String(length=40), nullable=False),
        sa.Column("beneficiary", sa.String(length=200), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_party_bank_accounts_party_id", "party_bank_accounts", ["party_id"])

    op.create_table(
        "customers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False, unique=True),
        sa.Column("salesperson", sa.String(length=200), nullable=True),
        sa.Column("zone", sa.String(length=120), nullable=True),
        sa.Column("price_list", sa.String(length=120), nullable=True),
        sa.Column("payment_term", sa.String(length=120), nullable=True),
        sa.Column("credit_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("credit_limit", sa.Float(), nullable=True),
        sa.Column("blocked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("block_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customers_party_id", "customers", ["party_id"], unique=True)

    op.create_table(
        "suppliers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False, unique=True),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("buyer", sa.String(length=200), nullable=True),
        sa.Column("payment_term", sa.String(length=120), nullable=True),
        sa.Column("default_currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("approval_status", sa.String(length=32), nullable=False, server_default="PENDING_APPROVAL"),
        sa.Column("withholding_profile", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_suppliers_party_id", "suppliers", ["party_id"], unique=True)

    op.create_table(
        "carriers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False, unique=True),
        sa.Column("registration", sa.String(length=120), nullable=True),
        sa.Column("insurance", sa.String(length=120), nullable=True),
        sa.Column("permits", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_carriers_party_id", "carriers", ["party_id"], unique=True)

    op.create_table(
        "drivers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False, unique=True),
        sa.Column("license", sa.String(length=64), nullable=True),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("restrictions", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drivers_party_id", "drivers", ["party_id"], unique=True)

    # ---------------- Taxonomía y atributos ----------------
    op.create_table(
        "taxonomy_nodes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("parent_id", sa.String(length=36), sa.ForeignKey("taxonomy_nodes.id"), nullable=True),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("applies_to", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_taxonomy_nodes_company_id", "taxonomy_nodes", ["company_id"])
    op.create_index("ix_taxonomy_nodes_level", "taxonomy_nodes", ["level"])

    op.create_table(
        "attribute_definitions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("data_type", sa.String(length=32), nullable=False, server_default="TEXT"),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("multiple", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("validation", sa.String(length=255), nullable=True),
        sa.Column("searchable", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attribute_definitions_company_id", "attribute_definitions", ["company_id"])

    op.create_table(
        "attribute_applicabilities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("attribute_id", sa.String(length=36), sa.ForeignKey("attribute_definitions.id"), nullable=False),
        sa.Column("taxonomy_id", sa.String(length=36), sa.ForeignKey("taxonomy_nodes.id"), nullable=True),
        sa.Column("template_id", sa.String(length=36), nullable=True),
        sa.Column("condition", sa.String(length=255), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("section", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attribute_applicabilities_attribute_id", "attribute_applicabilities", ["attribute_id"])
    op.create_index("ix_attribute_applicabilities_taxonomy_id", "attribute_applicabilities", ["taxonomy_id"])

    # ---------------- Unidades, plantillas y catálogo ----------------
    op.create_table(
        "units_of_measure",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("dimension", sa.String(length=32), nullable=False, server_default="CANTIDAD"),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("decimals", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_units_of_measure_company_id", "units_of_measure", ["company_id"])

    op.create_table(
        "unit_conversions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("from_unit_id", sa.String(length=36), sa.ForeignKey("units_of_measure.id"), nullable=False),
        sa.Column("to_unit_id", sa.String(length=36), sa.ForeignKey("units_of_measure.id"), nullable=False),
        sa.Column("factor", sa.Float(), nullable=False),
        sa.Column("rounding", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("validity", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_unit_conversions_from_unit_id", "unit_conversions", ["from_unit_id"])
    op.create_index("ix_unit_conversions_to_unit_id", "unit_conversions", ["to_unit_id"])

    op.create_table(
        "product_templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("behaviors", sa.JSON(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_templates_company_id", "product_templates", ["company_id"])

    op.create_table(
        "service_templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("billing_mode", sa.String(length=32), nullable=False, server_default="HOUR"),
        sa.Column("recurrence", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("scheduling", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("contract_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("materials", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("acceptance", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_service_templates_company_id", "service_templates", ["company_id"])

    op.create_table(
        "profile_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("profile_type", sa.String(length=32), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("stockable", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("lot", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("serial", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("expiry", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("variants", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("weight", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("kit", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("decimals", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("trace_level", sa.String(length=32), nullable=False, server_default="NONE"),
        sa.Column("fefo", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("warranty", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("cold_chain", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("tax_classification", sa.String(length=32), nullable=False, server_default="GRAVADO"),
        sa.Column("islr_concept_ref", sa.String(length=120), nullable=True),
        sa.Column("requires_seniat_dispatch", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_sica", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_sigesai", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_sacs", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_animal_health", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_plant_health", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_lot", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_origin_unit", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_destination_auth", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_vehicle", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_driver", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_other_permit", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_profile_versions_company_id", "profile_versions", ["company_id"])
    op.create_index("ix_profile_versions_profile_type", "profile_versions", ["profile_type"])

    op.create_table(
        "catalog_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("item_type", sa.String(length=16), nullable=False),
        sa.Column("short_description", sa.String(length=255), nullable=True),
        sa.Column("long_description", sa.Text(), nullable=True),
        sa.Column("category_id", sa.String(length=36), sa.ForeignKey("taxonomy_nodes.id"), nullable=True),
        sa.Column("base_unit_id", sa.String(length=36), sa.ForeignKey("units_of_measure.id"), nullable=True),
        sa.Column("tax_profile_id", sa.String(length=36), sa.ForeignKey("profile_versions.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_catalog_items_company_id", "catalog_items", ["company_id"])
    op.create_index("ix_catalog_items_item_type", "catalog_items", ["item_type"])

    op.create_table(
        "products",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("item_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False, unique=True),
        sa.Column("template_id", sa.String(length=36), sa.ForeignKey("product_templates.id"), nullable=True),
        sa.Column("inventory_profile_id", sa.String(length=36), sa.ForeignKey("profile_versions.id"), nullable=True),
        sa.Column("traceability_profile_id", sa.String(length=36), sa.ForeignKey("profile_versions.id"), nullable=True),
        sa.Column("regulatory_profile_id", sa.String(length=36), sa.ForeignKey("profile_versions.id"), nullable=True),
        sa.Column("manufacturer", sa.String(length=200), nullable=True),
        sa.Column("origin_country", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_item_id", "products", ["item_id"], unique=True)

    op.create_table(
        "services",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("item_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False, unique=True),
        sa.Column("template_id", sa.String(length=36), sa.ForeignKey("service_templates.id"), nullable=True),
        sa.Column("billing_unit_id", sa.String(length=36), sa.ForeignKey("units_of_measure.id"), nullable=True),
        sa.Column("duration", sa.String(length=64), nullable=True),
        sa.Column("recurrence", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("delivery_mode", sa.String(length=64), nullable=True),
        sa.Column("contract_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("evidence_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_services_item_id", "services", ["item_id"], unique=True)

    op.create_table(
        "presentations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("unit_id", sa.String(length=36), sa.ForeignKey("units_of_measure.id"), nullable=True),
        sa.Column("content", sa.Float(), nullable=True),
        sa.Column("barcode", sa.String(length=64), nullable=True),
        sa.Column("buyable", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sellable", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("storable", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_presentations_product_id", "presentations", ["product_id"])

    op.create_table(
        "barcodes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("item_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("presentation_id", sa.String(length=36), sa.ForeignKey("presentations.id"), nullable=True),
        sa.Column("symbology", sa.String(length=32), nullable=False, server_default="EAN13"),
        sa.Column("value", sa.String(length=64), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("validity", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_barcodes_item_id", "barcodes", ["item_id"])

    op.create_table(
        "product_variants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("parent_product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("combination", sa.JSON(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("barcode", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_variants_parent_product_id", "product_variants", ["parent_product_id"])

    op.create_table(
        "attribute_values",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("item_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("attribute_id", sa.String(length=36), sa.ForeignKey("attribute_definitions.id"), nullable=False),
        sa.Column("typed_value", sa.JSON(), nullable=False),
        sa.Column("validity", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attribute_values_item_id", "attribute_values", ["item_id"])
    op.create_index("ix_attribute_values_attribute_id", "attribute_values", ["attribute_id"])


def downgrade() -> None:
    for table in [
        "attribute_values",
        "product_variants",
        "barcodes",
        "presentations",
        "services",
        "products",
        "catalog_items",
        "profile_versions",
        "service_templates",
        "product_templates",
        "unit_conversions",
        "units_of_measure",
        "attribute_applicabilities",
        "attribute_definitions",
        "taxonomy_nodes",
        "drivers",
        "carriers",
        "suppliers",
        "customers",
        "party_bank_accounts",
        "party_contacts",
        "party_addresses",
        "parties",
    ]:
        op.drop_table(table)
