"""Modelos de regulación y traslados (008, data-model.md).

Maestros regulatorios (organismos, tipos de permiso, registros, perfiles,
vehículos, conductores), permisos con ciclo de vida, guías SICA/SIGESAI/SACS
(registro y validación; Kontrol no fabrica permisos externos), evaluación
regulatoria por línea de despacho con bloqueo de salida, y contingencias solo
con regla oficial versionada.

Invariantes (Constitución P4/P5/P8, DOC-01 §5/§10, DOC-03 §12):
- Kontrol registra y valida documentos oficiales; no fabrica permisos externos.
- El despacho se bloquea si falta un documento, está vencido o no coincide.
- Cada documento conserva número, organismo, emisión, vigencia, archivo, hash,
  verificación, estado y auditoría.
- No hay eliminación física de permisos; corrección por documento vinculado.
- Contingencias solo mediante regla oficial versionada.
- 008 consume los despachos de 005; no duplica su lógica.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import CodeMixin, CreatedByMixin, NameMixin, TimestampMixin, UUIDMixin


# --------------------------------------------------------------------------- #
# Maestros regulatorios (DOC-01 §7 / DOC-02 §3 / DOC-03 §11)
# --------------------------------------------------------------------------- #
class RegulatoryAuthority(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, Base):
    __tablename__ = "regulatory_authorities"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    validation_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class PermitType(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, Base):
    __tablename__ = "permit_types"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    authority_id: Mapped[str] = mapped_column(ForeignKey("regulatory_authorities.id"), nullable=False, index=True)
    scope: Mapped[str | None] = mapped_column(String(120), nullable=True)
    validation_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class OfficialRegistration(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "official_registrations"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    authority_id: Mapped[str] = mapped_column(ForeignKey("regulatory_authorities.id"), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)  # COMPANY / PARTY / SITE / VEHICLE / PERSON
    ref_number: Mapped[str] = mapped_column(String(120), nullable=False)
    issued_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    file_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class RegulatoryProfile(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "regulatory_profiles"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rubric_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    product_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    operation: Mapped[str] = mapped_column(String(64), nullable=False, default="DESPACHO")
    origin: Mapped[str | None] = mapped_column(String(120), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(120), nullable=True)
    required_documents: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: [SICA, SIGESAI, SACS, ...]
    validity: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: from/to
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class TransportVehicle(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "transport_vehicles"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    plate: Mapped[str] = mapped_column(String(32), nullable=False)
    vehicle_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    capacity: Mapped[float | None] = mapped_column(Float, nullable=True)
    owner_party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), nullable=True)
    documents: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class TransportDriver(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "transport_drivers"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    license: Mapped[str | None] = mapped_column(String(64), nullable=True)
    documents: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


# --------------------------------------------------------------------------- #
# Permisos y guías (DOC-03 §11/§13 / DOC-01 §10)
# --------------------------------------------------------------------------- #
class PermitInstance(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "permit_instances"
    __table_args__ = (Index("ix_permit_instances_uom_id", "uom_id"),)

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    permit_type_id: Mapped[str] = mapped_column(ForeignKey("permit_types.id"), nullable=False, index=True)
    number: Mapped[str] = mapped_column(String(120), nullable=False)
    issued_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    origin: Mapped[str | None] = mapped_column(String(120), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(120), nullable=True)
    products: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    lots: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    vehicle_id: Mapped[str | None] = mapped_column(ForeignKey("transport_vehicles.id"), nullable=True)
    file_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    # DRAFT -> REGISTERED -> VERIFIED -> APPROVED_FOR_USE -> USED -> EXPIRED
    #                                   REJECTED / CANCELLED
    # Contrato de la Spec 011: cantidad autorizada con su unidad, sin
    # presentación comercial (CONTRACT_ONLY).
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
class OfficialDocument(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "official_documents"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # SICA / SIGESAI / SACS / GUIA_FISCAL / OTRO
    authority_id: Mapped[str | None] = mapped_column(ForeignKey("regulatory_authorities.id"), nullable=True)
    number: Mapped[str] = mapped_column(String(120), nullable=False)
    organism: Mapped[str | None] = mapped_column(String(120), nullable=True)
    issued_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    file_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="VALID")


# --------------------------------------------------------------------------- #
# Evaluación y bloqueo del despacho (DOC-03 §11 / DOC-01 §10)
# --------------------------------------------------------------------------- #
class RegulatoryEvaluation(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "regulatory_evaluations"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    shipment_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)  # Shipment 005
    shipment_line_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    profile_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    required: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: [SICA, ...]
    results: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    blockers: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: [{kind, reason}]
    override: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: {allowed_by, reason, at}
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CLEARED")  # CLEARED / BLOCKED / OVERRIDDEN


class RegulatoryApprovalRequest(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Solicitud de aprobación regulatoria (legado de 008).

    Renombrada en la Spec 045 (F1): el nombre `approval_requests` pasa al motor
    transversal. Esta entidad se conserva sin cambio de comportamiento hasta que
    la fase F6 migre sus datos al motor (FR-045-073). No añadir usos nuevos.
    """

    __tablename__ = "regulatory_approval_requests"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    object_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    requester_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approvers: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    risk: Mapped[str | None] = mapped_column(String(32), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)  # APPROVED / REJECTED
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")


# --------------------------------------------------------------------------- #
# Contingencias (DOC-01 §10)
# --------------------------------------------------------------------------- #
class RegulatoryContingency(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "regulatory_contingencies"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rule_ref: Mapped[str] = mapped_column(String(120), nullable=False)  # regla oficial versionada
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    allowed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
