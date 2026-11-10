"""Storage classification

Revision ID: 0092_storage_classification
Revises: 0091_location_validations
Create Date: 2024-01-01 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "0092_storage_classification"
down_revision = "0091_location_validations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "storage_conditions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "code", name="uq_storage_conditions_company_code"),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status"),
    )
    op.create_index("ix_storage_conditions_company_id", "storage_conditions", ["company_id"])

    op.create_table(
        "storage_size_classes",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "code", name="uq_storage_size_classes_company_code"),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status"),
    )
    op.create_index("ix_storage_size_classes_company_id", "storage_size_classes", ["company_id"])

    op.create_table(
        "product_storage_profiles",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("item_id", sa.String(36), nullable=False),
        sa.Column("weight_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("weight_unit_id", sa.String(36), nullable=True),
        sa.Column("volume_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("volume_unit_id", sa.String(36), nullable=True),
        sa.Column("size_class_id", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["catalog_items.id"]),
        sa.ForeignKeyConstraint(["size_class_id"], ["storage_size_classes.id"]),
        sa.ForeignKeyConstraint(["volume_unit_id"], ["units_of_measure.id"]),
        sa.ForeignKeyConstraint(["weight_unit_id"], ["units_of_measure.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("item_id", name="uq_product_storage_profiles_item"),
        sa.CheckConstraint("(weight_value IS NULL) = (weight_unit_id IS NULL)", name="weight_pair"),
        sa.CheckConstraint("(volume_value IS NULL) = (volume_unit_id IS NULL)", name="volume_pair"),
        sa.CheckConstraint("weight_value IS NULL OR weight_value > 0", name="weight_positive"),
        sa.CheckConstraint("volume_value IS NULL OR volume_value > 0", name="volume_positive"),
    )
    op.create_index("ix_product_storage_profiles_company_id", "product_storage_profiles", ["company_id"])

    op.create_table(
        "product_storage_conditions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("condition_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["condition_id"], ["storage_conditions.id"]),
        sa.ForeignKeyConstraint(["profile_id"], ["product_storage_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "condition_id", name="uq_product_storage_conditions_pair"),
    )
    op.create_index("ix_product_storage_conditions_company_id", "product_storage_conditions", ["company_id"])
    op.create_index("ix_product_storage_conditions_profile_id", "product_storage_conditions", ["profile_id"])

    op.create_table(
        "storage_rules",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("warehouse_id", sa.String(36), nullable=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("taxonomy_id", sa.String(36), nullable=True),
        sa.Column("size_class_id", sa.String(36), nullable=True),
        sa.Column("condition_id", sa.String(36), nullable=True),
        sa.Column("min_weight", sa.Numeric(18, 6), nullable=True),
        sa.Column("max_weight", sa.Numeric(18, 6), nullable=True),
        sa.Column("weight_unit_id", sa.String(36), nullable=True),
        sa.Column("min_volume", sa.Numeric(18, 6), nullable=True),
        sa.Column("max_volume", sa.Numeric(18, 6), nullable=True),
        sa.Column("volume_unit_id", sa.String(36), nullable=True),
        sa.Column("target_zone_id", sa.String(36), nullable=True),
        sa.Column("target_zone_type_id", sa.String(36), nullable=True),
        sa.Column("label_policy", sa.String(16), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["condition_id"], ["storage_conditions.id"]),
        sa.ForeignKeyConstraint(["size_class_id"], ["storage_size_classes.id"]),
        sa.ForeignKeyConstraint(["target_zone_id"], ["warehouse_zones.id"]),
        sa.ForeignKeyConstraint(["target_zone_type_id"], ["zone_types.id"]),
        sa.ForeignKeyConstraint(["taxonomy_id"], ["taxonomy_nodes.id"]),
        sa.ForeignKeyConstraint(["volume_unit_id"], ["units_of_measure.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.ForeignKeyConstraint(["weight_unit_id"], ["units_of_measure.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "code", name="uq_storage_rules_company_code"),
        sa.CheckConstraint("(min_volume IS NULL AND max_volume IS NULL) OR volume_unit_id IS NOT NULL", name="volume_unit"),
        sa.CheckConstraint("(min_weight IS NULL AND max_weight IS NULL) OR weight_unit_id IS NOT NULL", name="weight_unit"),
        sa.CheckConstraint("(target_zone_id IS NULL) <> (target_zone_type_id IS NULL)", name="single_target"),
        sa.CheckConstraint(
            "taxonomy_id IS NOT NULL OR size_class_id IS NOT NULL OR condition_id IS NOT NULL OR "
            "min_weight IS NOT NULL OR max_weight IS NOT NULL OR min_volume IS NOT NULL OR max_volume IS NOT NULL",
            name="has_criterion",
        ),
        sa.CheckConstraint("label_policy IN ('REQUIRED', 'OPTIONAL', 'NOT_REQUIRED')", name="label_policy"),
        sa.CheckConstraint("priority >= 1", name="priority_positive"),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status"),
        sa.CheckConstraint("target_zone_id IS NULL OR warehouse_id IS NOT NULL", name="zone_needs_warehouse"),
        sa.CheckConstraint("valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from", name="validity_range"),
    )
    op.create_index("ix_storage_rules_company_id", "storage_rules", ["company_id"])

    op.create_table(
        "warehouse_storage_policies",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("warehouse_id", sa.String(36), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("on_no_rule", sa.String(16), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("warehouse_id", name="uq_warehouse_storage_policies_warehouse"),
        sa.CheckConstraint("mode IN ('DISABLED', 'ENFORCED')", name="mode"),
        sa.CheckConstraint("on_no_rule IN ('BLOCK', 'ALLOW_ANY')", name="on_no_rule"),
    )
    op.create_index("ix_warehouse_storage_policies_company_id", "warehouse_storage_policies", ["company_id"])

    op.create_table(
        "storage_classifications",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("warehouse_id", sa.String(36), nullable=False),
        sa.Column("item_id", sa.String(36), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("import_file_id", sa.String(36), nullable=True),
        sa.Column("receipt_id", sa.String(36), nullable=True),
        sa.Column("document_ref", sa.String(200), nullable=True),
        sa.Column("result", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("rule_id", sa.String(36), nullable=True),
        sa.Column("rule_version", sa.BigInteger(), nullable=True),
        sa.Column("rule_code", sa.String(64), nullable=True),
        sa.Column("rule_name", sa.String(200), nullable=True),
        sa.Column("label_policy", sa.String(16), nullable=True),
        sa.Column("target_zone_id", sa.String(36), nullable=True),
        sa.Column("target_zone_type_id", sa.String(36), nullable=True),
        sa.Column("target_label", sa.String(255), nullable=True),
        sa.Column("input_taxonomy_name", sa.String(200), nullable=True),
        sa.Column("input_weight", sa.String(64), nullable=True),
        sa.Column("input_volume", sa.String(64), nullable=True),
        sa.Column("input_size_class", sa.String(200), nullable=True),
        sa.Column("input_conditions", sa.JSON(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("missing_criteria", sa.JSON(), nullable=False),
        sa.Column("candidate_rules", sa.JSON(), nullable=False),
        sa.Column("classified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("classified_by", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["import_file_id"], ["import_files.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["catalog_items.id"]),
        sa.ForeignKeyConstraint(["receipt_id"], ["goods_receipts.id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["storage_rules.id"]),
        sa.ForeignKeyConstraint(["target_zone_id"], ["warehouse_zones.id"]),
        sa.ForeignKeyConstraint(["target_zone_type_id"], ["zone_types.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("result <> 'CLASSIFIED' OR rule_id IS NOT NULL", name="classified_has_rule"),
        sa.CheckConstraint("result IN ('CLASSIFIED', 'NO_RULE', 'AMBIGUOUS')", name="result"),
        sa.CheckConstraint("status IN ('CURRENT', 'SUPERSEDED')", name="status"),
    )
    op.create_index("ix_storage_classifications_company_id", "storage_classifications", ["company_id"])
    op.create_index(
        "ix_storage_classifications_lookup",
        "storage_classifications",
        ["company_id", "warehouse_id", "item_id", "receipt_id"],
    )

    op.create_table(
        "storage_labels",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("classification_id", sa.String(36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(32), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("file_name", sa.String(120), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_by", sa.String(36), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("product_code", sa.String(64), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.String(64), nullable=True),
        sa.Column("receipt_code", sa.String(64), nullable=True),
        sa.Column("file_code", sa.String(64), nullable=True),
        sa.Column("zone_label", sa.String(255), nullable=True),
        sa.Column("location_code", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["classification_id"], ["storage_classifications.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "reference", name="uq_storage_labels_company_reference"),
        sa.UniqueConstraint("company_id", "sequence", name="uq_storage_labels_company_sequence"),
    )
    op.create_index("ix_storage_labels_company_id", "storage_labels", ["company_id"])
    op.create_index("ix_storage_labels_classification_id", "storage_labels", ["classification_id"])


def downgrade() -> None:
    op.drop_index("ix_storage_labels_classification_id", table_name="storage_labels")
    op.drop_index("ix_storage_labels_company_id", table_name="storage_labels")
    op.drop_table("storage_labels")

    op.drop_index("ix_storage_classifications_lookup", table_name="storage_classifications")
    op.drop_index("ix_storage_classifications_company_id", table_name="storage_classifications")
    op.drop_table("storage_classifications")

    op.drop_index("ix_warehouse_storage_policies_company_id", table_name="warehouse_storage_policies")
    op.drop_table("warehouse_storage_policies")

    op.drop_index("ix_storage_rules_company_id", table_name="storage_rules")
    op.drop_table("storage_rules")

    op.drop_index("ix_product_storage_conditions_profile_id", table_name="product_storage_conditions")
    op.drop_index("ix_product_storage_conditions_company_id", table_name="product_storage_conditions")
    op.drop_table("product_storage_conditions")

    op.drop_index("ix_product_storage_profiles_company_id", table_name="product_storage_profiles")
    op.drop_table("product_storage_profiles")

    op.drop_index("ix_storage_size_classes_company_id", table_name="storage_size_classes")
    op.drop_table("storage_size_classes")

    op.drop_index("ix_storage_conditions_company_id", table_name="storage_conditions")
    op.drop_table("storage_conditions")
