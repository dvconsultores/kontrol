"""Módulo de organización: Installation, Tenant, Company, Branch,
Establishment y la jerarquía física de almacén (Spec 008).

La jerarquía física es `Warehouse → Zone? → Aisle? → Rack? → Level? →
WarehouseLocation`. Solo el almacén y la ubicación son obligatorios: los cuatro
tramos intermedios son opcionales **por almacén** y se declaran en
`Warehouse.structure_levels` (R-008-1, ADR-D0-004).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, ForeignKeyConstraint, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.scope import Scope
from app.shared.mixins import CreatedByMixin, StatusMixin, TimestampMixin, UUIDMixin, VersionMixin


class Installation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "installations"
    __scope__ = Scope.GLOBAL

    installation_uuid: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    public_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    key_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)

    tenants: Mapped[list[Tenant]] = relationship(back_populates="installation")


class Tenant(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "tenants"
    __scope__ = Scope.INSTALLATION

    installation_id: Mapped[str] = mapped_column(ForeignKey("installations.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    plan: Mapped[str] = mapped_column(String(64), nullable=False, default="MONO_COMPANY")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

    installation: Mapped[Installation] = relationship(back_populates="tenants")
    companies: Mapped[list[Company]] = relationship(back_populates="tenant")


class Company(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, Base):
    __tablename__ = "companies"
    __scope__ = Scope.TENANT

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rif: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    legal_type: Mapped[str] = mapped_column(String(32), nullable=False, default="JURIDICA")
    activity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fiscal_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    functional_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="VED")
    #: Vigencia de la reserva de un pedido **mientras espera crédito** (Spec
    #: 030, R-D0-03-8). `NULL` = sin expiración, que es el defecto: una
    #: instalación recién creada no tiene reservas que caduquen por reloj.
    reservation_ttl_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: ¿Puede la misma persona preparar y confirmar? (`R-D0-12-5`, Spec 033).
    #: El defecto es `false` **a propósito**: «un control cuyo valor por defecto
    #: lo anula no es un control». Una empresa pequeña puede habilitarlo a
    #: conciencia, y la decisión queda auditada.
    confirmation_same_user_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false"))

    tenant: Mapped[Tenant] = relationship(back_populates="companies")
    branches: Mapped[list[Branch]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Branch(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, Base):
    __tablename__ = "branches"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager: Mapped[str | None] = mapped_column(String(200), nullable=True)

    company: Mapped[Company] = relationship(back_populates="branches")
    establishments: Mapped[list[Establishment]] = relationship(back_populates="branch", cascade="all, delete-orphan")


class Establishment(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, Base):
    __tablename__ = "establishments"
    __scope__ = Scope.COMPANY
    #: Deriva su empresa de la sucursal que lo contiene. La clave es obligatoria,
    #: así que la ruta nunca se corta.
    __scope_authority__ = "branch_id → branches"

    branch_id: Mapped[str] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    fiscal_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    issuance_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)

    branch: Mapped[Branch] = relationship(back_populates="establishments")


class ZoneType(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, Base):
    """Tipo **conceptual** de zona, distinto de su nombre (FR-008-012).

    KONTROL no entrega tipos predefinidos: el catálogo nace vacío y lo puebla
    cada empresa. No hay ningún valor de negocio en el esquema (P8).
    """

    __tablename__ = "zone_types"
    __scope__ = Scope.COMPANY
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_zone_types_company_code"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class LocationType(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, Base):
    """Tipo de ubicación. `is_storable` distingue las que admiten existencia
    disponible de las de tránsito, cuarentena o daño (CL-008-04)."""

    __tablename__ = "location_types"
    __scope__ = Scope.COMPANY
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_location_types_company_code"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_storable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Warehouse(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, VersionMixin, Base):
    __tablename__ = "warehouses"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_warehouses_company_code"),
        # Destino de la clave compuesta que ata la estructura interna a su
        # empresa. Es redundante con la clave primaria en cuanto a unicidad, y
        # necesaria para poder referenciar el par completo (ARCH-MC-001 N7).
        UniqueConstraint("company_id", "id", name="uq_warehouses_company_id"),
        Index("ix_warehouses_company_status", "company_id", "status"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    branch_id: Mapped[str | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    warehouse_type: Mapped[str] = mapped_column(String(32), nullable=False, default="PHYSICAL")
    policies: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)

    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_managed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    structure_levels: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    structure_regime: Mapped[str] = mapped_column(String(16), nullable=False, default="INITIAL", server_default="INITIAL")
    code_policy: Mapped[str] = mapped_column(String(16), nullable=False, default="GENERATED", server_default="GENERATED")
    code_pattern: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Sin `cascade="all, delete-orphan"` (R-008-8): borrar un almacén nunca
    # puede destruir ubicaciones con historial. El borrado lo gobierna el
    # servicio, que exige que no exista nada dependiente.
    locations: Mapped[list[WarehouseLocation]] = relationship(back_populates="warehouse")


class WarehouseZone(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, VersionMixin, Base):
    __tablename__ = "warehouse_zones"
    __scope__ = Scope.COMPANY
    #: La empresa y el almacén no pueden contradecirse: el par tiene que
    #: existir tal cual en `warehouses` (ARCH-MC-001 N7).
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "warehouse_id"], ["warehouses.company_id", "warehouses.id"],
            name="fk_warehouse_zones_company_warehouse",
        ),
        UniqueConstraint("warehouse_id", "code", name="uq_warehouse_zones_wh_code"),
        Index("ix_warehouse_zones_wh_sequence", "warehouse_id", "sequence"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    zone_type_id: Mapped[str | None] = mapped_column(ForeignKey("zone_types.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class WarehouseAisle(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, VersionMixin, Base):
    __tablename__ = "warehouse_aisles"
    __scope__ = Scope.COMPANY
    #: La empresa y el almacén no pueden contradecirse: el par tiene que
    #: existir tal cual en `warehouses` (ARCH-MC-001 N7).
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "warehouse_id"], ["warehouses.company_id", "warehouses.id"],
            name="fk_warehouse_aisles_company_warehouse",
        ),
        UniqueConstraint("warehouse_id", "code", name="uq_warehouse_aisles_wh_code"),
        Index("ix_warehouse_aisles_wh_sequence", "warehouse_id", "sequence"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # Opcional: un almacén con pasillos y sin zonas es válido (R-008-1).
    zone_id: Mapped[str | None] = mapped_column(ForeignKey("warehouse_zones.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class WarehouseRack(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, VersionMixin, Base):
    __tablename__ = "warehouse_racks"
    __scope__ = Scope.COMPANY
    #: La empresa y el almacén no pueden contradecirse: el par tiene que
    #: existir tal cual en `warehouses` (ARCH-MC-001 N7).
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "warehouse_id"], ["warehouses.company_id", "warehouses.id"],
            name="fk_warehouse_racks_company_warehouse",
        ),
        UniqueConstraint("warehouse_id", "code", name="uq_warehouse_racks_wh_code"),
        Index("ix_warehouse_racks_wh_sequence", "warehouse_id", "sequence"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    aisle_id: Mapped[str | None] = mapped_column(ForeignKey("warehouse_aisles.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class WarehouseLevel(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, VersionMixin, Base):
    __tablename__ = "warehouse_levels"
    __scope__ = Scope.COMPANY
    #: La empresa y el almacén no pueden contradecirse: el par tiene que
    #: existir tal cual en `warehouses` (ARCH-MC-001 N7).
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "warehouse_id"], ["warehouses.company_id", "warehouses.id"],
            name="fk_warehouse_levels_company_warehouse",
        ),
        UniqueConstraint("warehouse_id", "code", name="uq_warehouse_levels_wh_code"),
        Index("ix_warehouse_levels_wh_sequence", "warehouse_id", "sequence"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rack_id: Mapped[str | None] = mapped_column(ForeignKey("warehouse_racks.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # Orden vertical, distinto de la secuencia de recorrido.
    height_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class WarehouseLocation(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, VersionMixin, Base):
    """La hoja de la jerarquía. Es lo que las transacciones referencian.

    Guarda la **cadena completa** —no solo su padre inmediato— para poder
    ordenar y filtrar sin recursión y para sobrevivir a que un almacén use solo
    algunos tramos (CL-008-02). La etiqueta legible **no** es una columna: se
    deriva en lectura (CL-008-07).
    """

    __tablename__ = "warehouse_locations"
    __scope__ = Scope.COMPANY
    #: La empresa y el almacén no pueden contradecirse: el par tiene que
    #: existir tal cual en `warehouses` (ARCH-MC-001 N7).
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "warehouse_id"], ["warehouses.company_id", "warehouses.id"],
            name="fk_warehouse_locations_company_warehouse",
        ),
        UniqueConstraint("warehouse_id", "code", name="uq_warehouse_locations_wh_code"),
        Index("ix_warehouse_locations_wh_status", "warehouse_id", "status"),
        Index("ix_warehouse_locations_physical_order",
              "warehouse_id", "zone_id", "aisle_id", "rack_id", "level_id", "sequence"),
        Index("ix_warehouse_locations_company_code", "company_id", "code"),
        Index("ix_warehouse_locations_type", "location_type_id"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    zone_id: Mapped[str | None] = mapped_column(ForeignKey("warehouse_zones.id"), nullable=True)
    aisle_id: Mapped[str | None] = mapped_column(ForeignKey("warehouse_aisles.id"), nullable=True)
    rack_id: Mapped[str | None] = mapped_column(ForeignKey("warehouse_racks.id"), nullable=True)
    level_id: Mapped[str | None] = mapped_column(ForeignKey("warehouse_levels.id"), nullable=True)
    location_type_id: Mapped[str | None] = mapped_column(ForeignKey("location_types.id"), nullable=True)

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    capacity_units: Mapped[Any | None] = mapped_column(Numeric(18, 3), nullable=True)
    capacity_weight: Mapped[Any | None] = mapped_column(Numeric(18, 3), nullable=True)
    capacity_uom: Mapped[str | None] = mapped_column(String(16), nullable=True)
    restrictions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    barcode: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Texto libre original de `zone`/`aisle`/`rack` antes de la Spec 008.
    # Dato inerte: no se convierte en jerarquía ni sirve para reconstruir
    # referencias (R-008-4, CL-008-15).
    legacy_path: Mapped[str | None] = mapped_column(String(200), nullable=True)

    warehouse: Mapped[Warehouse] = relationship(back_populates="locations")
