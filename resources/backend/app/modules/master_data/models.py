"""Modelos de maestros (002-maestros, data-model.md).

Terceros (Party + extensiones), taxonomía y atributos gobernados, catálogo
(items/producto/servicio, unidades, presentaciones), perfiles versionados.
Los datos críticos (inventario, impuestos, lotes, seriales, regulación) NUNCA
se almacenan en EAV/JSON libre (Constitución P8, DOC-01 §8).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.scope import Scope
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
    __scope__ = Scope.COMPANY

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
    __scope__ = Scope.COMPANY
    __scope_authority__ = "party_id → parties"

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
    __scope__ = Scope.COMPANY
    __scope_authority__ = "party_id → parties"

    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)  # texto
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    preferred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validity: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class PartyBankAccount(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "party_bank_accounts"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "party_id → parties"

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
    __scope__ = Scope.COMPANY
    __scope_authority__ = "party_id → parties"

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
    __scope__ = Scope.COMPANY
    __scope_authority__ = "party_id → parties"

    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    buyer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    payment_term: Mapped[str | None] = mapped_column(String(120), nullable=True)
    default_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_APPROVAL")
    withholding_profile: Mapped[str | None] = mapped_column(String(120), nullable=True)


class Carrier(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "carriers"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "party_id → parties"

    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, unique=True, index=True)
    registration: Mapped[str | None] = mapped_column(String(120), nullable=True)
    insurance: Mapped[str | None] = mapped_column(String(120), nullable=True)
    permits: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class Driver(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "drivers"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "party_id → parties"

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
    __scope__ = Scope.COMPANY

    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)  # None = global
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("taxonomy_nodes.id"), nullable=True)
    level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # SECTOR/RUBRO/CATEGORIA/...
    applies_to: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)  # PRODUCT/SERVICE


class AttributeDefinition(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, StatusMixin, Base):
    __tablename__ = "attribute_definitions"
    __scope__ = Scope.COMPANY

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
    __scope__ = Scope.COMPANY
    __scope_authority__ = "attribute_id → attribute_definitions"

    attribute_id: Mapped[str] = mapped_column(ForeignKey("attribute_definitions.id"), nullable=False, index=True)
    taxonomy_id: Mapped[str | None] = mapped_column(ForeignKey("taxonomy_nodes.id"), nullable=True)
    template_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    condition: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    section: Mapped[str | None] = mapped_column(String(120), nullable=True)


class AttributeValue(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "attribute_values"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "item_id → catalog_items"

    item_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    attribute_id: Mapped[str] = mapped_column(ForeignKey("attribute_definitions.id"), nullable=False, index=True)
    typed_value: Mapped[Any] = mapped_column(JSON, nullable=False)
    validity: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


# --------------------------------------------------------------------------- #
# Catálogo: unidades, plantillas, items, presentaciones
# --------------------------------------------------------------------------- #
#: Vocabulario cerrado de dimensiones físicas. Las dimensiones no las inventa un
#: cliente; las unidades sí (CL-011-20).
#: `MASA` y `PESO` coexisten porque ambas ya existen en datos y pruebas
#: anteriores a esta Spec. Rechazar una invalidaría filas existentes (P5).
UOM_DIMENSIONS: tuple[str, ...] = (
    "CANTIDAD", "MASA", "PESO", "VOLUMEN", "LONGITUD", "AREA", "TIEMPO",
)

#: Modos de redondeo admitidos. La unidad declara el suyo; no se deduce del código
#: de la unidad (P8).
UOM_ROUNDING_MODES: tuple[str, ...] = ("HALF_UP", "HALF_EVEN", "DOWN", "UP")


class UnitOfMeasure(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin,
                    StatusMixin, VersionMixin, Base):
    """Unidad de medida.

    `company_id` nulo = unidad **global de plataforma**, de solo lectura para las
    empresas. El catálogo global nace vacío: KONTROL no entrega `UND`, `KG` ni
    ninguna otra (FR-011-004, P8).
    """

    __tablename__ = "units_of_measure"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_units_of_measure_company_code"),
        CheckConstraint("decimals >= 0 AND decimals <= 6", name="ck_units_of_measure_decimals"),
        CheckConstraint(
            "dimension IN ('CANTIDAD','MASA','PESO','VOLUMEN','LONGITUD','AREA','TIEMPO')",
            name="ck_units_of_measure_dimension"),
    )

    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    dimension: Mapped[str] = mapped_column(String(32), nullable=False, default="CANTIDAD")
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    decimals: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    rounding_mode: Mapped[str] = mapped_column(String(16), nullable=False,
                                               default="HALF_UP", server_default="HALF_UP")


class UnitConversion(UUIDMixin, TimestampMixin, Base):
    """Conversión **física** entre unidades de la misma dimensión.

    Sin versionado: un kilo siempre serán mil gramos. La conversión **comercial**
    de una presentación a la unidad base es otra cosa y vive en
    `ProductPresentationVersion` (R-011-2).
    """

    __tablename__ = "unit_conversions"
    __scope__ = Scope.GLOBAL
    __table_args__ = (
        UniqueConstraint("from_unit_id", "to_unit_id", name="uq_unit_conversions_pair"),
        CheckConstraint("factor > 0", name="ck_unit_conversions_factor_positive"),
    )

    from_unit_id: Mapped[str] = mapped_column(ForeignKey("units_of_measure.id"), nullable=False, index=True)
    to_unit_id: Mapped[str] = mapped_column(ForeignKey("units_of_measure.id"), nullable=False, index=True)
    factor: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    rounding: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    validity: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class ProductTemplate(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, VersionMixin, StatusMixin, Base):
    __tablename__ = "product_templates"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    behaviors: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ServiceTemplate(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, VersionMixin, StatusMixin, Base):
    __tablename__ = "service_templates"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    billing_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="HOUR")
    recurrence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scheduling: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contract_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    materials: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acceptance: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CatalogItem(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, StatusMixin, Base):
    __tablename__ = "catalog_items"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # PRODUCT/SERVICE
    short_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    long_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("taxonomy_nodes.id"), nullable=True)
    base_unit_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    #: Pasa a `true` con el primer movimiento y **no vuelve atrás**. Cambiar la
    #: unidad base de un producto con historial reinterpretaría retroactivamente
    #: todas sus cantidades (R-011-3). Es el análogo de `structure_regime` en la
    #: Spec 008.
    base_unit_locked: Mapped[bool] = mapped_column(Boolean, nullable=False,
                                                   default=False, server_default="false")
    tax_profile_id: Mapped[str | None] = mapped_column(ForeignKey("profile_versions.id"), nullable=True)


class Product(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "item_id → catalog_items"

    item_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, unique=True, index=True)
    template_id: Mapped[str | None] = mapped_column(ForeignKey("product_templates.id"), nullable=True)
    inventory_profile_id: Mapped[str | None] = mapped_column(ForeignKey("profile_versions.id"), nullable=True)
    traceability_profile_id: Mapped[str | None] = mapped_column(ForeignKey("profile_versions.id"), nullable=True)
    regulatory_profile_id: Mapped[str | None] = mapped_column(ForeignKey("profile_versions.id"), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    origin_country: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Service(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "services"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "item_id → catalog_items"

    item_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, unique=True, index=True)
    template_id: Mapped[str | None] = mapped_column(ForeignKey("service_templates.id"), nullable=True)
    billing_unit_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recurrence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    delivery_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contract_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Presentation(UUIDMixin, TimestampMixin, CreatedByMixin, NameMixin,
                  StatusMixin, VersionMixin, Base):
    """Presentación de **un producto concreto**.

    No es un SKU (R-011-1): un producto con caja, bolsa y pallet sigue siendo un
    producto. El **factor** no vive aquí sino en `ProductPresentationVersion`,
    porque la caja de un producto son 100 unidades y la de otro 24 (§43).
    """

    __tablename__ = "presentations"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("product_id", "code", name="uq_presentations_product_code"),
        Index("ix_presentations_product_status", "product_id", "status"),
    )

    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    #: Dato legado anterior a la Spec 011. **No se usa para calcular**: si alguna
    #: instalación tuviera filas, este número es la única evidencia de la
    #: intención original y por eso se conserva (CL-011-11).
    content: Mapped[float | None] = mapped_column(Float, nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    buyable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sellable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    storable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    #: Distingue la presentación comercial de la unidad de despacho (§20).
    dispatchable: Mapped[bool] = mapped_column(Boolean, nullable=False,
                                               default=True, server_default="true")


class ProductPresentationVersion(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, Base):
    """El factor y su vigencia. Corazón del versionado.

    Cambiar un factor **crea una versión**; jamás sobrescribe la anterior
    (FR-011-036). Es lo único que permite que una caja pase de 100 a 120 sin que
    la compra del año pasado cambie de significado.
    """

    __tablename__ = "product_presentation_versions"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        CheckConstraint("factor_to_base > 0", name="ck_ppv_factor_positive"),
        CheckConstraint("valid_to IS NULL OR valid_to > valid_from", name="ck_ppv_range"),
        UniqueConstraint("presentation_id", "valid_from", name="uq_ppv_presentation_from"),
        # Una sola versión **abierta** por presentación: impide el solapamiento
        # que haría la conversión no determinista (FR-011-035). El solapamiento
        # entre rangos cerrados se valida en servicio, dentro de la transacción.
        Index("uq_ppv_open_version", "presentation_id", unique=True,
              postgresql_where=text("valid_to IS NULL"),
              sqlite_where=text("valid_to IS NULL")),
        Index("ix_ppv_resolution", "presentation_id", "valid_from", "valid_to"),
        Index("ix_ppv_bulk", "product_id", "company_id"),
    )

    presentation_id: Mapped[str] = mapped_column(ForeignKey("presentations.id"), nullable=False)
    #: Redundante y deliberado: permite la resolución masiva por documento sin
    #: join adicional (NFR-011-01).
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    factor_to_base: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    factor_uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    #: `false` cuando la conversión produce fracciones en la unidad base. Debe
    #: declararse: el sistema no redondea en silencio (R-D0-09-5).
    exact_in_base: Mapped[bool] = mapped_column(Boolean, nullable=False,
                                                default=True, server_default="true")
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Barcode(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "barcodes"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "item_id → catalog_items"

    item_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    symbology: Mapped[str] = mapped_column(String(32), nullable=False, default="EAN13")
    value: Mapped[str] = mapped_column(String(64), nullable=False)  # texto
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validity: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class ProductVariant(UUIDMixin, TimestampMixin, CodeMixin, StatusMixin, Base):
    __tablename__ = "product_variants"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "parent_product_id → catalog_items"

    parent_product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    combination: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True)


# --------------------------------------------------------------------------- #
# Perfiles versionados (inventario/trazabilidad/fiscal/regulatorio)
# --------------------------------------------------------------------------- #
class ProfileVersion(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, VersionMixin, StatusMixin, Base):
    __tablename__ = "profile_versions"
    __scope__ = Scope.COMPANY

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
