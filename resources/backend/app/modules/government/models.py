"""Modelos del módulo de Gobierno (GOV-0 · línea de Gobierno, OQ-GAB-1 = A).

# GOV-0 · Configurar el ente

El ente de Gobierno es uno por contenedor de empresa (OD-GOV0-03). Cada cambio
queda registrado en una instantánea inmutable (`gov_entity_versions`).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DDL, JSON, BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, Numeric, String, Text, UniqueConstraint, event, text
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
TIPOS_ACTO_ADMINISTRATIVO = ("DECRETO", "RESOLUCION", "ORDEN", "PROVIDENCIA", "INSTRUCCION", "CIRCULAR", "OTRA_DECISION")
TITULARIDADES = ("TITULAR", "DELEGACION", "ENCARGADURIA", "SUPLENCIA")
CARACTERES_ACTO = ("GENERAL", "PARTICULAR", "INTERNO")
MEDIOS_EFICACIA = ("GACETA", "PERSONAL", "PRENSA")
ESTADOS_ACTO = ("BORRADOR", "EMITIDO", "EFICAZ", "REVOCADO", "NULO")
TIPOS_PERSONA = ("NATURAL", "JURIDICA")
ESTADOS_NOTIFICACION = ("PENDIENTE", "NOTIFICADA", "ANULADA")
MEDIOS_NOTIFICACION = ("PERSONAL", "PRENSA")
RESULTADOS_INTENTO = ("ENTREGADA", "FALLIDA", "PUBLICADA")
METODOS_MUESTREO = ("TODAS", "ESPECIFICA", "ALEATORIA")


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


class GovernmentAct(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Acto administrativo registrado del ente (GOV-DOC-003, OD-DOC02-01): el PDF es su evidencia; no es un expediente, una delegación ni una firma."""

    __tablename__ = "gov_acts"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("cargo_id", "tipo", "denominacion_clave", "numero_clave", name="uq_gov_acts_numero"),
        Index("ix_gov_acts_company_fecha", "company_id", "fecha"),
        Index("ix_gov_acts_company_status", "company_id", "status"),
        CheckConstraint(f"tipo IN ({en(TIPOS_ACTO_ADMINISTRATIVO)})", name="tipo"),
        CheckConstraint(f"titularidad IN ({en(TITULARIDADES)})", name="titularidad"),
        CheckConstraint(f"caracter IN ({en(CARACTERES_ACTO)})", name="caracter"),
        CheckConstraint(f"medio IS NULL OR medio IN ({en(MEDIOS_EFICACIA)})", name="medio"),
        CheckConstraint(f"status IN ({en(ESTADOS_ACTO)})", name="status"),
        CheckConstraint(f"competencia_accion IN ({en(ACCIONES_COMPETENCIA)})", name="competencia_accion"),
        CheckConstraint(f"competencia_materia IN ({en(MATERIAS_COMPETENCIA)})", name="competencia_materia"),
        CheckConstraint(
            "(tipo = 'OTRA_DECISION' AND denominacion_tipo <> '') OR (tipo <> 'OTRA_DECISION' AND denominacion_tipo = '')",
            name="denominacion",
        ),
        CheckConstraint(
            "(titularidad = 'DELEGACION' AND delegacion_numero IS NOT NULL AND delegacion_fecha IS NOT NULL) OR "
            "(titularidad <> 'DELEGACION' AND delegacion_numero IS NULL AND delegacion_fecha IS NULL)",
            name="delegacion",
        ),
        CheckConstraint("simple_tramite = false OR caracter = 'PARTICULAR'", name="simple_tramite"),
        CheckConstraint("delegacion_fecha IS NULL OR delegacion_fecha <= fecha", name="delegacion_fecha"),
        CheckConstraint("status = 'BORRADOR' OR (documento_acto_id IS NOT NULL AND emitido_en IS NOT NULL)", name="emitido_documentado"),
        CheckConstraint("status <> 'EFICAZ' OR fecha_eficacia IS NOT NULL", name="eficaz_fechado"),
        CheckConstraint("fecha_eficacia IS NULL OR fecha_eficacia >= fecha", name="eficacia_no_retroactiva"),
        CheckConstraint("(status = 'REVOCADO') = (revocado_por_id IS NOT NULL)", name="revocado_referenciado"),
        CheckConstraint("(status = 'NULO') = (anulado_por_id IS NOT NULL)", name="nulo_referenciado"),
        CheckConstraint("version >= 1", name="version"),
    )

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    denominacion_tipo: Mapped[str] = mapped_column(String(80), nullable=False, default="", server_default="")
    denominacion_clave: Mapped[str] = mapped_column(String(80), nullable=False, default="", server_default="")
    numero: Mapped[str] = mapped_column(String(60), nullable=False)
    numero_clave: Mapped[str] = mapped_column(String(60), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    lugar: Mapped[str] = mapped_column(String(120), nullable=False)
    cargo_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=False, index=True)
    competencia_accion: Mapped[str] = mapped_column(String(16), nullable=False)
    competencia_materia: Mapped[str] = mapped_column(String(16), nullable=False)
    fundamento_competencia: Mapped[str] = mapped_column(String(500), nullable=False)
    funcionario: Mapped[str] = mapped_column(String(200), nullable=False)
    titularidad: Mapped[str] = mapped_column(String(16), nullable=False)
    delegacion_numero: Mapped[str | None] = mapped_column(String(60), nullable=True)
    delegacion_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    caracter: Mapped[str] = mapped_column(String(16), nullable=False)
    simple_tramite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    destinatario: Mapped[str | None] = mapped_column(String(200), nullable=True)
    asunto: Mapped[str] = mapped_column(String(200), nullable=False)
    hechos: Mapped[str | None] = mapped_column(Text, nullable=True)
    fundamentos: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="BORRADOR", server_default="BORRADOR")
    documento_acto_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True)
    medio: Mapped[str | None] = mapped_column(String(16), nullable=True)
    referencia_publicacion: Mapped[str | None] = mapped_column(String(120), nullable=True)
    fecha_publicacion_notificacion: Mapped[date | None] = mapped_column(Date, nullable=True)
    documento_eficacia_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True)
    fecha_eficacia: Mapped[date | None] = mapped_column(Date, nullable=True)
    revocado_por_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=True)
    anulado_por_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=True)
    emitido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    emitido_por: Mapped[str | None] = mapped_column(String(36), nullable=True)


class GovernmentActVersion(UUIDMixin, TimestampMixin, Base):
    """Instantánea de cada cambio de un acto administrativo (solo inserción)."""

    __tablename__ = "gov_act_versions"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("act_id", "version", name="uq_gov_act_versions_act_id_version"),
        CheckConstraint(f"status IN ({en(ESTADOS_ACTO)})", name="status"),
        CheckConstraint("version >= 1", name="version"),
    )

    act_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class GovernmentNotification(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Notificación administrativa de un acto (GOV-DOC-005, DOC-04)."""

    __tablename__ = "gov_notifications"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        Index("ix_gov_notifications_company_status", "company_id", "status"),
        CheckConstraint(f"tipo_persona IN ({en(TIPOS_PERSONA)})", name="tipo_persona"),
        CheckConstraint(f"status IN ({en(ESTADOS_NOTIFICACION)})", name="status"),
        CheckConstraint(f"medio_notificacion IS NULL OR medio_notificacion IN ({en(MEDIOS_NOTIFICACION)})", name="medio"),
        CheckConstraint(
            "(status = 'NOTIFICADA') = (fecha_notificacion IS NOT NULL AND medio_notificacion IS NOT NULL)",
            name="notificada_fechada",
        ),
        CheckConstraint("(status = 'ANULADA') = (motivo_anulacion IS NOT NULL)", name="anulada_motivada"),
        CheckConstraint(
            "(apoderado_nombre IS NULL) = (apoderado_identificacion IS NULL)",
            name="apoderado_completo",
        ),
        Index(
            "uq_gov_notifications_act_destinatario",
            "act_id",
            "identificacion_clave",
            unique=True,
            postgresql_where=text("status <> 'ANULADA'"),
        ).ddl_if(dialect="postgresql"),
        CheckConstraint("version >= 1", name="version"),
    )

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    act_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=False, index=True)
    tipo_persona: Mapped[str] = mapped_column(String(8), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    identificacion: Mapped[str] = mapped_column(String(20), nullable=False)
    identificacion_clave: Mapped[str] = mapped_column(String(20), nullable=False)
    domicilio: Mapped[str] = mapped_column(String(500), nullable=False)
    apoderado_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    apoderado_identificacion: Mapped[str | None] = mapped_column(String(20), nullable=True)
    recursos: Mapped[str] = mapped_column(Text, nullable=False)
    documento_oficio_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDIENTE", server_default="PENDIENTE")
    fecha_notificacion: Mapped[date | None] = mapped_column(Date, nullable=True)
    medio_notificacion: Mapped[str | None] = mapped_column(String(8), nullable=True)
    motivo_anulacion: Mapped[str | None] = mapped_column(String(255), nullable=True)


class GovernmentNotificationAttempt(UUIDMixin, TimestampMixin, Base):
    """Intento de notificación administrativa (GOV-DOC-005, DOC-04)."""

    __tablename__ = "gov_notification_attempts"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("notification_id", "numero", name="uq_gov_notification_attempts_numero"),
        CheckConstraint(f"medio IN ({en(MEDIOS_NOTIFICACION)})", name="medio"),
        CheckConstraint(f"resultado IN ({en(RESULTADOS_INTENTO)})", name="resultado"),
        CheckConstraint("numero >= 1", name="numero"),
        CheckConstraint(
            "(medio = 'PERSONAL' AND resultado IN ('ENTREGADA', 'FALLIDA')) OR (medio = 'PRENSA' AND resultado = 'PUBLICADA')",
            name="medio_resultado",
        ),
        CheckConstraint(
            "(resultado = 'ENTREGADA') = (receptor_nombre IS NOT NULL AND receptor_identificacion IS NOT NULL)",
            name="entregada_receptor",
        ),
        CheckConstraint("(resultado = 'FALLIDA') = (motivo_fallo IS NOT NULL)", name="fallida_motivo"),
        CheckConstraint(
            "(resultado = 'PUBLICADA') = (diario IS NOT NULL AND referencia IS NOT NULL)",
            name="publicada_diario",
        ),
    )

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    notification_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_notifications.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    medio: Mapped[str] = mapped_column(String(8), nullable=False)
    resultado: Mapped[str] = mapped_column(String(10), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    receptor_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    receptor_identificacion: Mapped[str | None] = mapped_column(String(20), nullable=True)
    motivo_fallo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    diario: Mapped[str | None] = mapped_column(String(120), nullable=True)
    referencia: Mapped[str | None] = mapped_column(String(120), nullable=True)
    documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    registrado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)


class GovernmentNotificationVersion(UUIDMixin, TimestampMixin, Base):
    """Instantánea de cada cambio de una notificación administrativa (solo inserción)."""

    __tablename__ = "gov_notification_versions"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("notification_id", "version", name="uq_gov_notification_versions_notification_id_version"),
        CheckConstraint(f"status IN ({en(ESTADOS_NOTIFICACION)})", name="status"),
        CheckConstraint("version >= 1", name="version"),
    )

    notification_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_notifications.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


GOV_AUDIT_SAMPLES_IMMUTABLE_PG: tuple[str, ...] = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_audit_samples_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_AUDIT_SAMPLE_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$",
    "CREATE TRIGGER trg_gov_audit_samples_no_update BEFORE UPDATE ON gov_audit_samples FOR EACH ROW EXECUTE FUNCTION kontrol_gov_audit_samples_inmutable()",
    "CREATE TRIGGER trg_gov_audit_samples_no_delete BEFORE DELETE ON gov_audit_samples FOR EACH ROW EXECUTE FUNCTION kontrol_gov_audit_samples_inmutable()",
    "CREATE TRIGGER trg_gov_audit_samples_no_truncate BEFORE TRUNCATE ON gov_audit_samples FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_audit_samples_inmutable()",
)


GOV_AUDIT_SAMPLE_ITEMS_IMMUTABLE_PG: tuple[str, ...] = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_audit_sample_items_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_AUDIT_SAMPLE_ITEM_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$",
    "CREATE TRIGGER trg_gov_audit_sample_items_no_update BEFORE UPDATE ON gov_audit_sample_items FOR EACH ROW EXECUTE FUNCTION kontrol_gov_audit_sample_items_inmutable()",
    "CREATE TRIGGER trg_gov_audit_sample_items_no_delete BEFORE DELETE ON gov_audit_sample_items FOR EACH ROW EXECUTE FUNCTION kontrol_gov_audit_sample_items_inmutable()",
    "CREATE TRIGGER trg_gov_audit_sample_items_no_truncate BEFORE TRUNCATE ON gov_audit_sample_items FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_audit_sample_items_inmutable()",
)


class GovernmentAuditSample(UUIDMixin, TimestampMixin, Base):
    """Muestra de auditoría registrada por el auditor (CTL-04); inmutable."""

    __tablename__ = "gov_audit_samples"
    __scope__ = Scope.COMPANY

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    criterio: Mapped[str] = mapped_column(Text, nullable=False)
    justificacion: Mapped[str] = mapped_column(Text, nullable=False)
    metodo: Mapped[str] = mapped_column(String(12), nullable=False)
    semilla: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tamano: Mapped[int] = mapped_column(Integer, nullable=False)
    poblacion: Mapped[int] = mapped_column(Integer, nullable=False)
    filtros: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_audit_samples_company_id_codigo"),
        CheckConstraint(f"metodo IN ({en(METODOS_MUESTREO)})", name="metodo"),
        CheckConstraint("(metodo = 'ALEATORIA') = (semilla IS NOT NULL)", name="semilla_solo_aleatoria"),
        CheckConstraint("tamano >= 1 AND tamano <= poblacion", name="tamano"),
    )


class GovernmentAuditSampleItem(UUIDMixin, TimestampMixin, Base):
    """Partida de una muestra: referencia a un evento de auditoría inmutable."""

    __tablename__ = "gov_audit_sample_items"
    __scope__ = Scope.COMPANY

    sample_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_audit_samples.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    audit_event_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit_events.id"), nullable=False, index=True)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("sample_id", "audit_event_id", name="uq_gov_audit_sample_items_sample_id_audit_event_id"),
        UniqueConstraint("sample_id", "orden", name="uq_gov_audit_sample_items_sample_id_orden"),
        CheckConstraint("orden >= 1", name="orden"),
    )


for _sentencia in GOV_AUDIT_SAMPLES_IMMUTABLE_PG:
    event.listen(GovernmentAuditSample.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))
for _sentencia in GOV_AUDIT_SAMPLE_ITEMS_IMMUTABLE_PG:
    event.listen(GovernmentAuditSampleItem.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


RIESGOS_HALLAZGO = ("ALTO", "MEDIO", "BAJO")
ORIGENES_HALLAZGO = ("MUESTRA", "INDEPENDIENTE")
ESTADOS_HALLAZGO = ("ABIERTO", "PLAN_DE_ACCION", "EN_REMEDIACION", "EVIDENCIA_PRESENTADA", "CERRADO")
ESTADOS_ACCION_CORRECTIVA = ("PENDIENTE", "EN_CURSO", "COMPLETADA")
TIPOS_HISTORIA_HALLAZGO = ("CREADO", "RECOMENDACION", "ACCION", "PLAN", "EJECUCION", "AVANCE", "PRESENTADO", "VERIFICADO", "DEVUELTO")


GOV_FINDING_NOT_DELETABLE_PG: tuple[str, ...] = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_finding_no_borrable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_FINDING_NOT_DELETABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$",
    "CREATE TRIGGER trg_gov_findings_no_delete BEFORE DELETE ON gov_findings FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_no_borrable()",
    "CREATE TRIGGER trg_gov_findings_no_truncate BEFORE TRUNCATE ON gov_findings FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_finding_no_borrable()",
)


GOV_FINDING_RECORDS_IMMUTABLE_PG: tuple[str, ...] = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_finding_registros_inmutables() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_FINDING_RECORD_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$",
    "CREATE TRIGGER trg_gov_finding_events_no_update BEFORE UPDATE ON gov_finding_events FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()",
    "CREATE TRIGGER trg_gov_finding_events_no_delete BEFORE DELETE ON gov_finding_events FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()",
    "CREATE TRIGGER trg_gov_finding_events_no_truncate BEFORE TRUNCATE ON gov_finding_events FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()",
)


GOV_FINDING_RECOMMENDATIONS_IMMUTABLE_PG: tuple[str, ...] = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_finding_registros_inmutables() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_FINDING_RECORD_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$",
    "CREATE TRIGGER trg_gov_finding_recommendations_no_update BEFORE UPDATE ON gov_finding_recommendations FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()",
    "CREATE TRIGGER trg_gov_finding_recommendations_no_delete BEFORE DELETE ON gov_finding_recommendations FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()",
    "CREATE TRIGGER trg_gov_finding_recommendations_no_truncate BEFORE TRUNCATE ON gov_finding_recommendations FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()",
)


GOV_CORRECTIVE_ACTIONS_NOT_DELETABLE_PG: tuple[str, ...] = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_finding_no_borrable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_FINDING_NOT_DELETABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$",
    "CREATE TRIGGER trg_gov_corrective_actions_no_delete BEFORE DELETE ON gov_corrective_actions FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_no_borrable()",
    "CREATE TRIGGER trg_gov_corrective_actions_no_truncate BEFORE TRUNCATE ON gov_corrective_actions FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_finding_no_borrable()",
)


GOV_CORRECTIVE_ACTION_PROGRESS_IMMUTABLE_PG: tuple[str, ...] = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_finding_registros_inmutables() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_FINDING_RECORD_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$",
    "CREATE TRIGGER trg_gov_corrective_action_progress_no_update BEFORE UPDATE ON gov_corrective_action_progress FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()",
    "CREATE TRIGGER trg_gov_corrective_action_progress_no_delete BEFORE DELETE ON gov_corrective_action_progress FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()",
    "CREATE TRIGGER trg_gov_corrective_action_progress_no_truncate BEFORE TRUNCATE ON gov_corrective_action_progress FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()",
)


GOV_FINDING_HISTORY_IMMUTABLE_PG: tuple[str, ...] = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_finding_registros_inmutables() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_FINDING_RECORD_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$",
    "CREATE TRIGGER trg_gov_finding_history_no_update BEFORE UPDATE ON gov_finding_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()",
    "CREATE TRIGGER trg_gov_finding_history_no_delete BEFORE DELETE ON gov_finding_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()",
    "CREATE TRIGGER trg_gov_finding_history_no_truncate BEFORE TRUNCATE ON gov_finding_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()",
)


class GovernmentFinding(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Hallazgo de Control Interno (CTL-06) con su plan de acción correctiva."""

    __tablename__ = "gov_findings"
    __scope__ = Scope.COMPANY

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    condicion: Mapped[str] = mapped_column(Text, nullable=False)
    criterio: Mapped[str] = mapped_column(Text, nullable=False)
    causa: Mapped[str] = mapped_column(Text, nullable=False)
    efecto: Mapped[str] = mapped_column(Text, nullable=False)
    riesgo: Mapped[str] = mapped_column(String(5), nullable=False)
    origen: Mapped[str] = mapped_column(String(13), nullable=False)
    sample_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_audit_samples.id"), nullable=True, index=True)
    origen_descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estado: Mapped[str] = mapped_column(String(24), nullable=False, default="ABIERTO", server_default="ABIERTO")
    presentado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    presentado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verificado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    verificado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nota_verificacion: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_findings_company_id_codigo"),
        CheckConstraint(f"riesgo IN ({en(RIESGOS_HALLAZGO)})", name="riesgo"),
        CheckConstraint(f"origen IN ({en(ORIGENES_HALLAZGO)})", name="origen"),
        CheckConstraint(f"estado IN ({en(ESTADOS_HALLAZGO)})", name="estado"),
        CheckConstraint(
            "(origen = 'MUESTRA' AND sample_id IS NOT NULL AND origen_descripcion IS NULL) OR "
            "(origen = 'INDEPENDIENTE' AND sample_id IS NULL AND origen_descripcion IS NOT NULL)",
            name="origen_coherente",
        ),
    )


class GovernmentFindingEvent(UUIDMixin, TimestampMixin, Base):
    """Evidencia de un hallazgo de Control Interno; inmutable."""

    __tablename__ = "gov_finding_events"
    __scope__ = Scope.COMPANY

    finding_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_findings.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    audit_event_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit_events.id"), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("finding_id", "audit_event_id", name="uq_gov_finding_events_finding_id_audit_event_id"),
    )


class GovernmentFindingRecommendation(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Recomendación asociada a un hallazgo; inmutable."""

    __tablename__ = "gov_finding_recommendations"
    __scope__ = Scope.COMPANY

    finding_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_findings.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("finding_id", "orden", name="uq_gov_finding_recommendations_finding_id_orden"),
        CheckConstraint("orden >= 1", name="orden"),
    )


class GovernmentCorrectiveAction(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Acción correctiva del plan de un hallazgo; avanza su porcentaje y estado, nunca se borra."""

    __tablename__ = "gov_corrective_actions"
    __scope__ = Scope.COMPANY

    finding_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_findings.id"), nullable=False, index=True)
    recommendation_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_finding_recommendations.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    position_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=False, index=True)
    cargo_codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    cargo_denominacion: Mapped[str] = mapped_column(String(200), nullable=False)
    unidad_id: Mapped[str] = mapped_column(String(36), nullable=False)
    unidad_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    ejercicio: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_objetivo: Mapped[date] = mapped_column(Date, nullable=False)
    porcentaje: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    estado: Mapped[str] = mapped_column(String(12), nullable=False, default="PENDIENTE", server_default="PENDIENTE")

    __table_args__ = (
        UniqueConstraint("finding_id", "orden", name="uq_gov_corrective_actions_finding_id_orden"),
        CheckConstraint("orden >= 1", name="orden"),
        CheckConstraint("porcentaje >= 0 AND porcentaje <= 100", name="porcentaje"),
        CheckConstraint(f"estado IN ({en(ESTADOS_ACCION_CORRECTIVA)})", name="estado"),
    )


class GovernmentCorrectiveActionProgress(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Avance registrado en una acción correctiva; inmutable."""

    __tablename__ = "gov_corrective_action_progress"
    __scope__ = Scope.COMPANY

    action_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_corrective_actions.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    nota: Mapped[str] = mapped_column(Text, nullable=False)
    porcentaje: Mapped[int] = mapped_column(Integer, nullable=False)
    document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True, index=True)

    __table_args__ = (
        CheckConstraint("porcentaje >= 0 AND porcentaje <= 100", name="porcentaje"),
    )


class GovernmentFindingHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia de cambios de estado y eventos de un hallazgo; inmutable."""

    __tablename__ = "gov_finding_history"
    __scope__ = Scope.COMPANY

    finding_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_findings.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    estado_desde: Mapped[str | None] = mapped_column(String(24), nullable=True)
    estado_hasta: Mapped[str | None] = mapped_column(String(24), nullable=True)
    detalle: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        CheckConstraint(f"tipo IN ({en(TIPOS_HISTORIA_HALLAZGO)})", name="tipo"),
    )


for _sentencia in GOV_FINDING_NOT_DELETABLE_PG:
    event.listen(GovernmentFinding.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))
for _sentencia in GOV_FINDING_RECORDS_IMMUTABLE_PG:
    event.listen(GovernmentFindingEvent.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))
for _sentencia in GOV_FINDING_RECOMMENDATIONS_IMMUTABLE_PG:
    event.listen(GovernmentFindingRecommendation.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))
for _sentencia in GOV_CORRECTIVE_ACTIONS_NOT_DELETABLE_PG:
    event.listen(GovernmentCorrectiveAction.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))
for _sentencia in GOV_CORRECTIVE_ACTION_PROGRESS_IMMUTABLE_PG:
    event.listen(GovernmentCorrectiveActionProgress.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))
for _sentencia in GOV_FINDING_HISTORY_IMMUTABLE_PG:
    event.listen(GovernmentFindingHistory.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


RESULTADOS_VERIFICACION_PAQUETE = ("VALIDO", "INVALIDO", "INCOMPLETO", "VERSION_NO_SOPORTADA")


GOV_AUDIT_PACKAGES_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_audit_package_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_AUDIT_PACKAGE_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_audit_packages_no_update BEFORE UPDATE ON gov_audit_packages FOR EACH ROW EXECUTE FUNCTION kontrol_gov_audit_package_inmutable()",
    "CREATE TRIGGER trg_gov_audit_packages_no_delete BEFORE DELETE ON gov_audit_packages FOR EACH ROW EXECUTE FUNCTION kontrol_gov_audit_package_inmutable()",
    "CREATE TRIGGER trg_gov_audit_packages_no_truncate BEFORE TRUNCATE ON gov_audit_packages FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_audit_package_inmutable()",
)

GOV_AUDIT_PACKAGE_VERIFICATIONS_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_audit_package_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_AUDIT_PACKAGE_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_audit_package_verifications_no_update BEFORE UPDATE ON gov_audit_package_verifications FOR EACH ROW EXECUTE FUNCTION kontrol_gov_audit_package_inmutable()",
    "CREATE TRIGGER trg_gov_audit_package_verifications_no_delete BEFORE DELETE ON gov_audit_package_verifications FOR EACH ROW EXECUTE FUNCTION kontrol_gov_audit_package_inmutable()",
    "CREATE TRIGGER trg_gov_audit_package_verifications_no_truncate BEFORE TRUNCATE ON gov_audit_package_verifications FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_audit_package_inmutable()",
)


class GovernmentAuditPackage(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Paquete de auditoría exportable generado desde una muestra (DOC-08, GOV-DOC-010); inmutable."""

    __tablename__ = "gov_audit_packages"
    __scope__ = Scope.COMPANY

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    sample_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_audit_samples.id"), nullable=False, index=True)
    numero_generacion: Mapped[int] = mapped_column(Integer, nullable=False)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    proposito: Mapped[str] = mapped_column(Text, nullable=False)
    version_manifiesto: Mapped[int] = mapped_column(Integer, nullable=False)
    huella_manifiesto: Mapped[str] = mapped_column(String(64), nullable=False)
    huella_paquete: Mapped[str] = mapped_column(String(64), nullable=False)
    bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    clave_almacenamiento: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(String(80), nullable=False)
    eventos: Mapped[int] = mapped_column(Integer, nullable=False)
    documentos_incluidos: Mapped[int] = mapped_column(Integer, nullable=False)
    documentos_excluidos: Mapped[int] = mapped_column(Integer, nullable=False)
    hallazgos: Mapped[int] = mapped_column(Integer, nullable=False)
    archivos: Mapped[int] = mapped_column(Integer, nullable=False)
    manifiesto: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_audit_packages_company_id_codigo"),
        UniqueConstraint("sample_id", "numero_generacion", name="uq_gov_audit_packages_sample_id_numero_generacion"),
        UniqueConstraint("company_id", "idempotency_key", name="uq_gov_audit_packages_company_id_idempotency_key"),
        UniqueConstraint("clave_almacenamiento", name="uq_gov_audit_packages_clave_almacenamiento"),
        CheckConstraint("length(huella_manifiesto) = 64 AND length(huella_paquete) = 64", name="huellas"),
        CheckConstraint("bytes > 0", name="bytes"),
        CheckConstraint("eventos >= 0 AND documentos_incluidos >= 0 AND documentos_excluidos >= 0 AND hallazgos >= 0 AND archivos >= 0", name="contadores"),
        CheckConstraint("numero_generacion >= 1", name="numero_generacion"),
        CheckConstraint("version_manifiesto = 1", name="version_manifiesto"),
    )


class GovernmentAuditPackageVerification(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Verificación de integridad de una copia de un paquete de auditoría (DOC-08); inmutable."""

    __tablename__ = "gov_audit_package_verifications"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    package_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_audit_packages.id"), nullable=False, index=True)
    resultado: Mapped[str] = mapped_column(String(20), nullable=False)
    motivos: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    huella_archivo: Mapped[str] = mapped_column(String(64), nullable=False)
    bytes_archivo: Mapped[int] = mapped_column(BigInteger, nullable=False)
    identico: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (
        CheckConstraint(f"resultado IN ({en(RESULTADOS_VERIFICACION_PAQUETE)})", name="resultado"),
        CheckConstraint("length(huella_archivo) = 64", name="huella_archivo"),
        CheckConstraint("bytes_archivo >= 0", name="bytes_archivo"),
    )


for _sentencia in GOV_AUDIT_PACKAGES_IMMUTABLE_PG:
    event.listen(GovernmentAuditPackage.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_AUDIT_PACKAGE_VERIFICATIONS_IMMUTABLE_PG:
    event.listen(GovernmentAuditPackageVerification.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))
