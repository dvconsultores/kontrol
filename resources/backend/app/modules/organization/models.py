"""Módulo de organización: Installation, Tenant, Company, Branch,
Establishment, Warehouse y Location (data-model.md §2.1)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.mixins import CreatedByMixin, StatusMixin, TimestampMixin, UUIDMixin


class Installation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "installations"

    installation_uuid: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    public_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    key_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)

    tenants: Mapped[list[Tenant]] = relationship(back_populates="installation")


class Tenant(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "tenants"

    installation_id: Mapped[str] = mapped_column(ForeignKey("installations.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    plan: Mapped[str] = mapped_column(String(64), nullable=False, default="MONO_COMPANY")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

    installation: Mapped[Installation] = relationship(back_populates="tenants")
    companies: Mapped[list[Company]] = relationship(back_populates="tenant")


class Company(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, Base):
    __tablename__ = "companies"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rif: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    legal_type: Mapped[str] = mapped_column(String(32), nullable=False, default="JURIDICA")
    activity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fiscal_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    functional_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="VED")

    tenant: Mapped[Tenant] = relationship(back_populates="companies")
    branches: Mapped[list[Branch]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Branch(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, Base):
    __tablename__ = "branches"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager: Mapped[str | None] = mapped_column(String(200), nullable=True)

    company: Mapped[Company] = relationship(back_populates="branches")
    establishments: Mapped[list[Establishment]] = relationship(back_populates="branch", cascade="all, delete-orphan")


class Establishment(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, Base):
    __tablename__ = "establishments"

    branch_id: Mapped[str] = mapped_column(ForeignKey("branches.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    fiscal_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    issuance_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)

    branch: Mapped[Branch] = relationship(back_populates="establishments")


class Warehouse(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, Base):
    __tablename__ = "warehouses"

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    branch_id: Mapped[str | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    warehouse_type: Mapped[str] = mapped_column(String(32), nullable=False, default="PHYSICAL")
    policies: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)

    locations: Mapped[list[Location]] = relationship(back_populates="warehouse", cascade="all, delete-orphan")


class Location(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, Base):
    __tablename__ = "locations"

    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    zone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    aisle: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rack: Mapped[str | None] = mapped_column(String(64), nullable=True)
    capacity: Mapped[float | None] = mapped_column(nullable=True)
    restrictions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)

    warehouse: Mapped[Warehouse] = relationship(back_populates="locations")
