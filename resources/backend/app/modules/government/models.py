"""Modelos del módulo de Gobierno (GOV-0 · línea de Gobierno, OQ-GAB-1 = A).

# GOV-0 · Configurar el ente

El ente de Gobierno es uno por contenedor de empresa (OD-GOV0-03). Cada cambio
queda registrado en una instantánea inmutable (`gov_entity_versions`).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, BigInteger, CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.scope import Scope
from app.shared.mixins import CreatedByMixin, TimestampMixin, UUIDMixin, VersionMixin

ESTADOS_ENTE = ("BORRADOR", "ACTIVO")
NIVELES_TERRITORIALES = ("NACIONAL", "ESTADAL", "MUNICIPAL")
FORMAS_ORGANIZATIVAS = (
    "ADMINISTRACION_CENTRAL",
    "INSTITUTO_PUBLICO",
    "SERVICIO_DESCONCENTRADO",
    "ENTE_DESCENTRALIZADO",
)
TIPOS_DE_ACTO = ("LEY", "DECRETO", "ORDENANZA", "RESOLUCION", "OTRO")


def en(valores: tuple[str, ...]) -> str:
    """Lista SQL de literales para una restricción de valores permitidos."""
    return ", ".join(f"'{v}'" for v in valores)


class GovernmentEntity(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """El ente de Gobierno: uno por contenedor de empresa (OD-GOV0-03)."""

    __tablename__ = "gov_entities"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", name="uq_gov_entities_company_id"),
        CheckConstraint(f"status IN ({en(ESTADOS_ENTE)})", name="status"),
        CheckConstraint(
            f"nivel_territorial IS NULL OR nivel_territorial IN ({en(NIVELES_TERRITORIALES)})",
            name="nivel_territorial",
        ),
        CheckConstraint(
            f"forma_organizativa IS NULL OR forma_organizativa IN ({en(FORMAS_ORGANIZATIVAS)})",
            name="forma_organizativa",
        ),
        CheckConstraint(f"acto_tipo IS NULL OR acto_tipo IN ({en(TIPOS_DE_ACTO)})", name="acto_tipo"),
        CheckConstraint("version >= 1", name="version"),
        CheckConstraint("status <> 'ACTIVO' OR activated_at IS NOT NULL", name="activo_fechado"),
    )

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    denominacion: Mapped[str] = mapped_column(String(200), nullable=False)
    siglas: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rif: Mapped[str | None] = mapped_column(String(12), nullable=True)
    nivel_territorial: Mapped[str | None] = mapped_column(String(16), nullable=True)
    forma_organizativa: Mapped[str | None] = mapped_column(String(32), nullable=True)
    organo_adscripcion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    entidad_federal: Mapped[str | None] = mapped_column(String(120), nullable=True)
    municipio: Mapped[str | None] = mapped_column(String(120), nullable=True)
    acto_tipo: Mapped[str | None] = mapped_column(String(16), nullable=True)
    acto_numero: Mapped[str | None] = mapped_column(String(60), nullable=True)
    acto_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    acto_publicacion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="BORRADOR", server_default="BORRADOR")
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class GovernmentEntityVersion(UUIDMixin, TimestampMixin, Base):
    """Instantánea inmutable de cada cambio del ente (solo inserción)."""

    __tablename__ = "gov_entity_versions"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("entity_id", "version", name="uq_gov_entity_versions_entity_id_version"),
        CheckConstraint(f"status IN ({en(ESTADOS_ENTE)})", name="status"),
        CheckConstraint("version >= 1", name="version"),
    )

    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_entities.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


ESTADOS_ESTRUCTURA = ("BORRADOR", "VIGENTE", "CERRADA")
TIPOS_DE_UNIDAD = (
    "ORGANO",
    "UNIDAD_ADMINISTRATIVA",
    "UNIDAD_EJECUTORA_LOCAL",
    "DEPENDENCIA",
    "SEDE",
    "CENTRO_GESTOR",
)
ESTADOS_UNIDAD = ("ACTIVA", "INACTIVA")


class GovernmentStructure(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Estructura organizativa del ente para un ejercicio (año calendario, OD-ORG02-01)."""

    __tablename__ = "gov_structures"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "exercise", name="uq_gov_structures_company_id_exercise"),
        CheckConstraint(f"status IN ({en(ESTADOS_ESTRUCTURA)})", name="status"),
        CheckConstraint("exercise BETWEEN 2000 AND 2100", name="exercise"),
        CheckConstraint("version >= 1", name="version"),
        CheckConstraint("status = 'BORRADOR' OR published_at IS NOT NULL", name="publicada_fechada"),
        CheckConstraint("status <> 'CERRADA' OR closed_at IS NOT NULL", name="cerrada_fechada"),
    )

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_entities.id"), nullable=False)
    exercise: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="BORRADOR", server_default="BORRADOR")
    copied_from_exercise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class GovernmentUnit(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Unidad de la estructura (GOV-ORG-002); sin superior depende directamente del ente."""

    __tablename__ = "gov_units"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("structure_id", "code", name="uq_gov_units_structure_id_code"),
        UniqueConstraint("structure_id", "id", name="uq_gov_units_structure_id_id"),
        ForeignKeyConstraint(
            ["structure_id", "parent_id"],
            ["gov_units.structure_id", "gov_units.id"],
            name="fk_gov_units_parent_misma_estructura",
        ),
        CheckConstraint(f"unit_type IN ({en(TIPOS_DE_UNIDAD)})", name="unit_type"),
        CheckConstraint(f"status IN ({en(ESTADOS_UNIDAD)})", name="status"),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="sin_autorreferencia"),
        CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="vigencia"),
        CheckConstraint(
            "(status = 'ACTIVA' AND valid_to IS NULL) OR (status = 'INACTIVA' AND valid_to IS NOT NULL)",
            name="inactiva_fechada",
        ),
        CheckConstraint("version >= 1", name="version"),
    )

    structure_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_structures.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit_type: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVA", server_default="ACTIVA")
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)


class GovernmentUnitVersion(UUIDMixin, TimestampMixin, Base):
    """Instantánea de cada cambio de una unidad (solo inserción)."""

    __tablename__ = "gov_unit_versions"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("unit_id", "version", name="uq_gov_unit_versions_unit_id_version"),
        CheckConstraint(f"status IN ({en(ESTADOS_UNIDAD)})", name="status"),
        CheckConstraint("version >= 1", name="version"),
    )

    unit_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_units.id"), nullable=False, index=True)
    structure_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_structures.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


ESTADOS_CARGO = ("BORRADOR", "VIGENTE", "INACTIVO")
ACCIONES_COMPETENCIA = ("SOLICITAR", "COMPROMETER", "CAUSAR", "ORDENAR_PAGO", "PAGAR", "REGISTRAR", "CUSTODIAR", "APROBAR", "AUDITAR", "FIRMAR")
MATERIAS_COMPETENCIA = ("PRESUPUESTO", "CONTRATACIONES", "TESORERIA", "CONTABILIDAD", "BIENES", "EXPEDIENTE")
TIPOS_DE_LIMITE = ("SIN_LIMITE", "MONTO")
MONEDAS_LIMITE = ("VES", "USD", "EUR")


class GovernmentPosition(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Cargo de la estructura de un ejercicio (GOV-ORG-003, OD-ORG03-01): porta competencias y límites; no es una persona ni un rol de software."""

    __tablename__ = "gov_positions"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("structure_id", "code", name="uq_gov_positions_structure_id_code"),

        ForeignKeyConstraint(
            ["structure_id", "unit_id"],
            ["gov_units.structure_id", "gov_units.id"],
            name="fk_gov_positions_unidad_misma_estructura",
        ),
        CheckConstraint(f"status IN ({en(ESTADOS_CARGO)})", name="status"),
        CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="vigencia"),
        CheckConstraint(
            "(status = 'INACTIVO' AND valid_to IS NOT NULL) OR (status <> 'INACTIVO' AND valid_to IS NULL)",
            name="inactivo_fechado",
        ),
        CheckConstraint("status = 'BORRADOR' OR activated_at IS NOT NULL", name="activado_fechado"),
        CheckConstraint("version >= 1", name="version"),
    )

    structure_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_structures.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    unit_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="BORRADOR", server_default="BORRADOR")
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class GovernmentPositionCompetency(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Competencia de un cargo: acción × materia con su límite de firma/aprobación (OD-ORG03-02/03). El monto es Decimal, nunca float."""

    __tablename__ = "gov_position_competencies"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("position_id", "action", "subject", name="uq_gov_position_competencies_position_id_action_subject"),

        CheckConstraint(f"action IN ({en(ACCIONES_COMPETENCIA)})", name="action"),
        CheckConstraint(f"subject IN ({en(MATERIAS_COMPETENCIA)})", name="subject"),
        CheckConstraint(f"limit_type IN ({en(TIPOS_DE_LIMITE)})", name="limit_type"),
        CheckConstraint(f"limit_currency IS NULL OR limit_currency IN ({en(MONEDAS_LIMITE)})", name="limit_currency"),
        CheckConstraint(
            "(limit_type = 'SIN_LIMITE' AND limit_amount IS NULL AND limit_currency IS NULL) OR (limit_type = 'MONTO' AND limit_amount IS NOT NULL AND limit_amount > 0 AND limit_currency IS NOT NULL)",
            name="limite_coherente",
        ),
    )

    position_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    subject: Mapped[str] = mapped_column(String(16), nullable=False)
    limit_type: Mapped[str] = mapped_column(String(16), nullable=False)
    limit_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    limit_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    basis: Mapped[str | None] = mapped_column(String(255), nullable=True)


class GovernmentPositionVersion(UUIDMixin, TimestampMixin, Base):
    """Instantánea de cada cambio de un cargo, con todas sus competencias (solo inserción)."""

    __tablename__ = "gov_position_versions"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("position_id", "version", name="uq_gov_position_versions_position_id_version"),
        CheckConstraint(f"status IN ({en(ESTADOS_CARGO)})", name="status"),
        CheckConstraint("version >= 1", name="version"),
    )

    position_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=False, index=True)
    structure_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_structures.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
