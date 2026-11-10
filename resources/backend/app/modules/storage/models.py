from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.scope import Scope
from app.shared.mixins import TimestampMixin, UUIDMixin, VersionMixin


class StorageCondition(UUIDMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "storage_conditions"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_storage_conditions_company_code"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status"),
    )

    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")


class StorageSizeClass(UUIDMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "storage_size_classes"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_storage_size_classes_company_code"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status"),
    )

    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")


class ProductStorageProfile(UUIDMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "product_storage_profiles"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("item_id", name="uq_product_storage_profiles_item"),
        CheckConstraint("(weight_value IS NULL) = (weight_unit_id IS NULL)", name="weight_pair"),
        CheckConstraint("(volume_value IS NULL) = (volume_unit_id IS NULL)", name="volume_pair"),
        CheckConstraint("weight_value IS NULL OR weight_value > 0", name="weight_positive"),
        CheckConstraint("volume_value IS NULL OR volume_value > 0", name="volume_positive"),
    )

    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    weight_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    weight_unit_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    volume_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    volume_unit_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    size_class_id: Mapped[str | None] = mapped_column(ForeignKey("storage_size_classes.id"), nullable=True)


class ProductStorageCondition(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "product_storage_conditions"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("profile_id", "condition_id", name="uq_product_storage_conditions_pair"),
    )

    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("product_storage_profiles.id"), nullable=False, index=True)
    condition_id: Mapped[str] = mapped_column(ForeignKey("storage_conditions.id"), nullable=False)


class StorageRule(UUIDMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "storage_rules"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_storage_rules_company_code"),
        CheckConstraint("priority >= 1", name="priority_positive"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status"),
        CheckConstraint("label_policy IN ('REQUIRED', 'OPTIONAL', 'NOT_REQUIRED')", name="label_policy"),
        CheckConstraint("(target_zone_id IS NULL) <> (target_zone_type_id IS NULL)", name="single_target"),
        CheckConstraint("target_zone_id IS NULL OR warehouse_id IS NOT NULL", name="zone_needs_warehouse"),
        CheckConstraint("(min_weight IS NULL AND max_weight IS NULL) OR weight_unit_id IS NOT NULL", name="weight_unit"),
        CheckConstraint("(min_volume IS NULL AND max_volume IS NULL) OR volume_unit_id IS NOT NULL", name="volume_unit"),
        CheckConstraint(
            "taxonomy_id IS NOT NULL OR size_class_id IS NOT NULL OR condition_id IS NOT NULL OR "
            "min_weight IS NOT NULL OR max_weight IS NOT NULL OR min_volume IS NOT NULL OR max_volume IS NOT NULL "
            "OR rotation_band_id IS NOT NULL",
            name="has_criterion",
        ),
        CheckConstraint("valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from", name="validity_range"),
    )

    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    warehouse_id: Mapped[str | None] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    taxonomy_id: Mapped[str | None] = mapped_column(ForeignKey("taxonomy_nodes.id"), nullable=True)
    size_class_id: Mapped[str | None] = mapped_column(ForeignKey("storage_size_classes.id"), nullable=True)
    condition_id: Mapped[str | None] = mapped_column(ForeignKey("storage_conditions.id"), nullable=True)
    rotation_band_id: Mapped[str | None] = mapped_column(ForeignKey("rotation_bands.id"), nullable=True)
    min_weight: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    max_weight: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    weight_unit_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    min_volume: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    max_volume: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    volume_unit_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    target_zone_id: Mapped[str | None] = mapped_column(ForeignKey("warehouse_zones.id"), nullable=True)
    target_zone_type_id: Mapped[str | None] = mapped_column(ForeignKey("zone_types.id"), nullable=True)
    label_policy: Mapped[str] = mapped_column(String(16), nullable=False)


class WarehouseStoragePolicy(UUIDMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "warehouse_storage_policies"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("warehouse_id", name="uq_warehouse_storage_policies_warehouse"),
        CheckConstraint("mode IN ('DISABLED', 'ENFORCED')", name="mode"),
        CheckConstraint("on_no_rule IN ('BLOCK', 'ALLOW_ANY')", name="on_no_rule"),
    )

    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    on_no_rule: Mapped[str] = mapped_column(String(16), nullable=False)


class StorageClassification(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "storage_classifications"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        CheckConstraint("result IN ('CLASSIFIED', 'NO_RULE', 'AMBIGUOUS')", name="result"),
        CheckConstraint("status IN ('CURRENT', 'SUPERSEDED')", name="status"),
        CheckConstraint("result <> 'CLASSIFIED' OR rule_id IS NOT NULL", name="classified_has_rule"),
        Index("ix_storage_classifications_lookup", "company_id", "warehouse_id", "item_id", "receipt_id"),
    )

    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    item_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    import_file_id: Mapped[str | None] = mapped_column(ForeignKey("import_files.id"), nullable=True)
    receipt_id: Mapped[str | None] = mapped_column(ForeignKey("goods_receipts.id"), nullable=True)
    document_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("storage_rules.id"), nullable=True)
    rule_version: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    rule_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rule_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    label_policy: Mapped[str | None] = mapped_column(String(16), nullable=True)
    target_zone_id: Mapped[str | None] = mapped_column(ForeignKey("warehouse_zones.id"), nullable=True)
    target_zone_type_id: Mapped[str | None] = mapped_column(ForeignKey("zone_types.id"), nullable=True)
    target_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_taxonomy_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    input_weight: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_volume: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_size_class: Mapped[str | None] = mapped_column(String(200), nullable=True)
    input_rotation_band: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_conditions: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    reasons: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    missing_criteria: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    candidate_rules: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    classified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    classified_by: Mapped[str] = mapped_column(String(36), nullable=False)


class StorageLabel(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "storage_labels"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "reference", name="uq_storage_labels_company_reference"),
        UniqueConstraint("company_id", "sequence", name="uq_storage_labels_company_sequence"),
    )

    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    classification_id: Mapped[str] = mapped_column(ForeignKey("storage_classifications.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    reference: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_name: Mapped[str] = mapped_column(String(120), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_by: Mapped[str] = mapped_column(String(36), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_code: Mapped[str] = mapped_column(String(64), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    receipt_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    zone_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
