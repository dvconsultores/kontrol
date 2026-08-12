"""Modelos de maestros (002-maestros, data-model.md).

Terceros (Party + extensiones), taxonomía y atributos gobernados, catálogo
(items/producto/servicio, unidades, presentaciones), perfiles versionados.
Los datos críticos (inventario, impuestos, lotes, seriales, regulación) NUNCA
se almacenan en EAV/JSON libre (Constitución P8, DOC-01 §8).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import (
    CodeMixin,
    CreatedByMixin,
    NameMixin,
    StatusMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
)


# --------------------------------------------------------------------------- #
# Terceros (Party + extensiones)
# --------------------------------------------------------------------------- #
class Party(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, StatusMixin, Base):
    __tablename__ = "parties"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    person_type: Mapped[str] = mapped_column(String(32), nullable=False, default="JURIDICA")
    nationality: Mapped[str | None] = mapped_column(String(64), nullable=True)
    residence: Mapped[str | None] = mapped_column(String(64), nullable=True)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(20), nullable=True)  # RIF (texto)
    economic_activity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    roles: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)  # cliente/proveedor/...


class PartyAddress(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "party_addresses"

    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    address_type: Mapped[str] = mapped_column(String(32), nullable=False, default="PRINCIPAL")
    country: Mapped[str] = mapped_column(String(64), nullable=False, default="VE")
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    municipality: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    is_fiscal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_delivery: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validity: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class PartyContact(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "party_contacts"

    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)  # texto
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    preferred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validity: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class PartyBankAccount(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "party_bank_accounts"

    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    bank: Mapped[str] = mapped_column(String(120), nullable=False)
    account_type: Mapped[str] = mapped_column(String(32), nullable=False, default="CORRIENTE")
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    account_number: Mapped[str] = mapped_column(String(40), nullable=False)  # texto
    beneficiary: Mapped[str | None] = mapped_column(String(200), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)


class Customer(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "customers"

    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, unique=True, index=True)
    salesperson: Mapped[str | None] = mapped_column(String(200), nullable=True)
    zone: Mapped[str | None] = mapped_column(String(120), nullable=True)
    price_list: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payment_term: Mapped[str | None] = mapped_column(String(120), nullable=True)
    credit_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    credit_limit: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    block_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Supplier(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "suppliers"

    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    buyer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    payment_term: Mapped[str | None] = mapped_column(String(120), nullable=True)
    default_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_APPROVAL")
    withholding_profile: Mapped[str | None] = mapped_column(String(120), nullable=True)


class Carrier(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "carriers"

    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, unique=True, index=True)
    registration: Mapped[str | None] = mapped_column(String(120), nullable=True)
    insurance: Mapped[str | None] = mapped_column(String(120), nullable=True)
    permits: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class Driver(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "drivers"

    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, unique=True, index=True)
    license: Mapped[str | None] = mapped_column(String(64), nullable=True)
    categories: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restrictions: Mapped[str | None] = mapped_column(Text, nullable=True)


# --------------------------------------------------------------------------- #
# Taxonomía y atributos gobernados
# --------------------------------------------------------------------------- #
class TaxonomyNode(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, StatusMixin, Base):
    __tablename__ = "taxonomy_nodes"

    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)  # None = global
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("taxonomy_nodes.id"), nullable=True)
    level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # SECTOR/RUBRO/CATEGORIA/...
    applies_to: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)  # PRODUCT/SERVICE


class AttributeDefinition(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, StatusMixin, Base):
    __tablename__ = "attribute_definitions"

    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    data_type: Mapped[str] = mapped_column(String(32), nullable=False, default="TEXT")  # TEXT/NUMBER/DATE/OPTION/BOOLEAN
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    multiple: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    options: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    validation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    searchable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    permissions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class AttributeApplicability(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "attribute_applicabilities"

    attribute_id: Mapped[str] = mapped_column(ForeignKey("attribute_definitions.id"), nullable=False, index=True)
    taxonomy_id: Mapped[str | None] = mapped_column(ForeignKey("taxonomy_nodes.id"), nullable=True)
    template_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    condition: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    section: Mapped[str | None] = mapped_column(String(120), nullable=True)


class AttributeValue(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "attribute_values"

    item_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    attribute_id: Mapped[str] = mapped_column(ForeignKey("attribute_definitions.id"), nullable=False, index=True)
    typed_value: Mapped[Any] = mapped_column(JSON, nullable=False)
    validity: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


# --------------------------------------------------------------------------- #
# Catálogo: unidades, plantillas, items, presentaciones
# --------------------------------------------------------------------------- #
class UnitOfMeasure(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, StatusMixin, Base):
    __tablename__ = "units_of_measure"

    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    dimension: Mapped[str] = mapped_column(String(32), nullable=False, default="CANTIDAD")
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    decimals: Mapped[int] = mapped_column(Integer, nullable=False, default=2)


class UnitConversion(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "unit_conversions"

    from_unit_id: Mapped[str] = mapped_column(ForeignKey("units_of_measure.id"), nullable=False, index=True)
    to_unit_id: Mapped[str] = mapped_column(ForeignKey("units_of_measure.id"), nullable=False, index=True)
    factor: Mapped[float] = mapped_column(Float, nullable=False)
    rounding: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    validity: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class ProductTemplate(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, VersionMixin, StatusMixin, Base):
    __tablename__ = "product_templates"

    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    behaviors: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ServiceTemplate(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, VersionMixin, StatusMixin, Base):
    __tablename__ = "service_templates"

    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    billing_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="HOUR")
    recurrence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scheduling: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contract_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    materials: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acceptance: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CatalogItem(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, StatusMixin, Base):
    __tablename__ = "catalog_items"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # PRODUCT/SERVICE
    short_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    long_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("taxonomy_nodes.id"), nullable=True)
    base_unit_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    tax_profile_id: Mapped[str | None] = mapped_column(ForeignKey("profile_versions.id"), nullable=True)


class Product(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "products"

    item_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, unique=True, index=True)
    template_id: Mapped[str | None] = mapped_column(ForeignKey("product_templates.id"), nullable=True)
    inventory_profile_id: Mapped[str | None] = mapped_column(ForeignKey("profile_versions.id"), nullable=True)
    traceability_profile_id: Mapped[str | None] = mapped_column(ForeignKey("profile_versions.id"), nullable=True)
    regulatory_profile_id: Mapped[str | None] = mapped_column(ForeignKey("profile_versions.id"), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    origin_country: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Service(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "services"

    item_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, unique=True, index=True)
    template_id: Mapped[str | None] = mapped_column(ForeignKey("service_templates.id"), nullable=True)
    billing_unit_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recurrence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    delivery_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contract_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Presentation(UUIDMixin, TimestampMixin, NameMixin, Base):
    __tablename__ = "presentations"

    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    unit_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    content: Mapped[float | None] = mapped_column(Float, nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    buyable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sellable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    storable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Barcode(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "barcodes"

    item_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    symbology: Mapped[str] = mapped_column(String(32), nullable=False, default="EAN13")
    value: Mapped[str] = mapped_column(String(64), nullable=False)  # texto
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validity: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class ProductVariant(UUIDMixin, TimestampMixin, CodeMixin, StatusMixin, Base):
    __tablename__ = "product_variants"

    parent_product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    combination: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True)


# --------------------------------------------------------------------------- #
# Perfiles versionados (inventario/trazabilidad/fiscal/regulatorio)
# --------------------------------------------------------------------------- #
class ProfileVersion(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, VersionMixin, StatusMixin, Base):
    __tablename__ = "profile_versions"

    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    profile_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # INVENTORY/TRACEABILITY/FISCAL/REGULATORY
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")

    # Inventario
    stockable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    serial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expiry: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    variants: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    weight: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    kit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    decimals: Mapped[int] = mapped_column(Integer, nullable=False, default=2)

    # Trazabilidad
    trace_level: Mapped[str] = mapped_column(String(32), nullable=False, default="NONE")  # NONE/LOT/SERIAL/IMEI
    fefo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    warranty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cold_chain: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Fiscal
    tax_classification: Mapped[str] = mapped_column(String(32), nullable=False, default="GRAVADO")  # GRAVADO/EXENTO/EXONERADO/NO_SUJETO
    islr_concept_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)  # referencia a regla, no % fijo

    # Regulatorio
    requires_seniat_dispatch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_sica: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_sigesai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_sacs: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_animal_health: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_plant_health: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_lot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_origin_unit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_destination_auth: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_vehicle: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_driver: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_other_permit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
