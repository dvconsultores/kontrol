"""Modelos del módulo de Gobierno (GOV-0 · línea de Gobierno, OQ-GAB-1 = A).

# GOV-0 · Configurar el ente

El ente de Gobierno es uno por contenedor de empresa (OD-GOV0-03). Cada cambio
queda registrado en una instantánea inmutable (`gov_entity_versions`).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DDL, JSON, BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, event, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.scope import Scope
from app.modules.government.garantias_reglas import ACCIONES_GARANTIA, ESTADOS_EMISOR, ESTADOS_GARANTIA, ETAPAS_GARANTIA, FORMAS_GARANTIA, ORIGENES_GARANTIA, PRECONDICIONES_LIBERACION, TIPOS_EMISOR, TIPOS_GARANTIA
from app.shared.mixins import CreatedByMixin, TimestampMixin, UUIDMixin, VersionMixin, utcnow

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


ESTADOS_REGLA_SOD = ("BORRADOR", "VIGENTE", "CERRADA")
ALCANCES_REGLA_SOD = ("MISMO_OBJETO",)
MODOS_REGLA_SOD = ("BLOQUEAR",)
PROCESOS_SOD = ("DOC-02", "CTL-06", "TRE-01", "TRE-02", "CTL-10", "ORG-04", "ORG-06", "PROC-02", "PROC-03", "BUD-09", "TRE-03")
TIPOS_HISTORIA_SOD = ("CREADA", "EDITADA", "ACTIVADA", "CERRADA")


GOV_SOD_RULES_NOT_DELETABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_sod_no_borrable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_SOD_RULE_NOT_DELETABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_sod_rules_no_delete BEFORE DELETE ON gov_sod_rules FOR EACH ROW EXECUTE FUNCTION kontrol_gov_sod_no_borrable()",
    "CREATE TRIGGER trg_gov_sod_rules_no_truncate BEFORE TRUNCATE ON gov_sod_rules FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_sod_no_borrable()",
)

GOV_SOD_RULE_HISTORY_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_sod_historia_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_SOD_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_sod_rule_history_no_update BEFORE UPDATE ON gov_sod_rule_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_sod_historia_inmutable()",
    "CREATE TRIGGER trg_gov_sod_rule_history_no_delete BEFORE DELETE ON gov_sod_rule_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_sod_historia_inmutable()",
    "CREATE TRIGGER trg_gov_sod_rule_history_no_truncate BEFORE TRUNCATE ON gov_sod_rule_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_sod_historia_inmutable()",
)


class GovernmentSoDRule(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Regla de segregación de funciones de Control Interno (CTL-01, GOV-CTL-001)."""

    __tablename__ = "gov_sod_rules"
    __scope__ = Scope.COMPANY

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    proceso: Mapped[str] = mapped_column(String(10), nullable=False)
    accion_a: Mapped[str] = mapped_column(String(32), nullable=False)
    accion_b: Mapped[str] = mapped_column(String(32), nullable=False)
    bidireccional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    alcance: Mapped[str] = mapped_column(String(16), nullable=False, default="MISMO_OBJETO", server_default="MISMO_OBJETO")
    modo: Mapped[str] = mapped_column(String(10), nullable=False, default="BLOQUEAR", server_default="BLOQUEAR")
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="BORRADOR", server_default="BORRADOR")
    activada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    activada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cerrada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_cierre: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_sod_rules_company_id_codigo"),
        CheckConstraint(f"estado IN ({en(ESTADOS_REGLA_SOD)})", name="estado"),
        CheckConstraint(f"alcance IN ({en(ALCANCES_REGLA_SOD)})", name="alcance"),
        CheckConstraint(f"modo IN ({en(MODOS_REGLA_SOD)})", name="modo"),
        CheckConstraint(f"proceso IN ({en(PROCESOS_SOD)})", name="proceso"),
        CheckConstraint("accion_a <> accion_b", name="acciones_distintas"),
        CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
    )


class GovernmentSoDRuleHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia inmutable de una regla de segregación de funciones (CTL-01)."""

    __tablename__ = "gov_sod_rule_history"
    __scope__ = Scope.COMPANY

    rule_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_sod_rules.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    detalle: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        CheckConstraint(f"tipo IN ({en(TIPOS_HISTORIA_SOD)})", name="tipo"),
    )


for _sentencia in GOV_SOD_RULES_NOT_DELETABLE_PG:
    event.listen(GovernmentSoDRule.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_SOD_RULE_HISTORY_IMMUTABLE_PG:
    event.listen(GovernmentSoDRuleHistory.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


# PROC-11 · GOV-PROC-017: funciones incompatibles del procedimiento de contratación.
FUNCIONES_PROCEDIMIENTO = ("SOLICITANTE", "RECEPTOR", "EVALUADOR", "ADJUDICADOR")
TIPOS_HISTORIA_REGLA_FUNCION = ("CREADA", "ACTIVADA", "CERRADA")


GOV_SOD_ROLE_RULES_NOT_DELETABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_sod_funcion_no_borrable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_SOD_ROLE_RULE_NOT_DELETABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_sod_role_rules_no_delete BEFORE DELETE ON gov_sod_role_rules FOR EACH ROW EXECUTE FUNCTION kontrol_gov_sod_funcion_no_borrable()",
    "CREATE TRIGGER trg_gov_sod_role_rules_no_truncate BEFORE TRUNCATE ON gov_sod_role_rules FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_sod_funcion_no_borrable()",
)

GOV_SOD_ROLE_RULE_HISTORY_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_sod_funcion_historia_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_SOD_ROLE_RULE_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_sod_role_rule_history_no_update BEFORE UPDATE ON gov_sod_role_rule_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_sod_funcion_historia_inmutable()",
    "CREATE TRIGGER trg_gov_sod_role_rule_history_no_delete BEFORE DELETE ON gov_sod_role_rule_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_sod_funcion_historia_inmutable()",
    "CREATE TRIGGER trg_gov_sod_role_rule_history_no_truncate BEFORE TRUNCATE ON gov_sod_role_rule_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_sod_funcion_historia_inmutable()",
)


class GovernmentSoDRoleRule(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Par de funciones del procedimiento que no puede ejercer la misma persona (PROC-11, GOV-PROC-017)."""

    __tablename__ = "gov_sod_role_rules"
    __scope__ = Scope.COMPANY

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    proceso: Mapped[str] = mapped_column(String(10), nullable=False)
    rol_a: Mapped[str] = mapped_column(String(16), nullable=False)
    rol_b: Mapped[str] = mapped_column(String(16), nullable=False)
    fundamento: Mapped[str] = mapped_column(String(1000), nullable=False)
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="BORRADOR", server_default="BORRADOR")
    activada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    activada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cerrada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_cierre: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_sod_role_rules_company_id_codigo"),
        CheckConstraint(f"estado IN ({en(ESTADOS_REGLA_SOD)})", name="estado"),
        CheckConstraint("proceso = 'PROC-03'", name="proceso"),
        CheckConstraint(f"rol_a IN ({en(FUNCIONES_PROCEDIMIENTO)})", name="rol_a"),
        CheckConstraint(f"rol_b IN ({en(FUNCIONES_PROCEDIMIENTO)})", name="rol_b"),
        CheckConstraint("rol_a <> rol_b", name="funciones_distintas"),
        CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        CheckConstraint(
            "estado <> 'VIGENTE' OR (activada_por IS NOT NULL AND activada_en IS NOT NULL)",
            name="vigente_con_activacion",
        ),
        CheckConstraint(
            "estado <> 'CERRADA' OR (cerrada_por IS NOT NULL AND cerrada_en IS NOT NULL AND motivo_cierre IS NOT NULL)",
            name="cerrada_con_motivo",
        ),
        Index(
            "uq_gov_sod_role_rules_par_vigente",
            "company_id",
            "rol_a",
            "rol_b",
            unique=True,
            postgresql_where=text("estado = 'VIGENTE'"),
            sqlite_where=text("estado = 'VIGENTE'"),
        ),
    )


class GovernmentSoDRoleRuleHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia inmutable de una regla de funciones incompatibles (PROC-11)."""

    __tablename__ = "gov_sod_role_rule_history"
    __scope__ = Scope.COMPANY

    rule_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_sod_role_rules.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    detalle: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        CheckConstraint(f"tipo IN ({en(TIPOS_HISTORIA_REGLA_FUNCION)})", name="tipo"),
    )


for _sentencia in GOV_SOD_ROLE_RULES_NOT_DELETABLE_PG:
    event.listen(GovernmentSoDRoleRule.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_SOD_ROLE_RULE_HISTORY_IMMUTABLE_PG:
    event.listen(GovernmentSoDRoleRuleHistory.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


# BUD-01/BUD-02 · ejercicio presupuestario, programa, clasificador y su historia (GOV-BUD-01/02).
ESTADOS_EJERCICIO_PRESUPUESTARIO = ("BORRADOR", "APROBADO", "RECONDUCIDO", "CERRADO")
TIPOS_FUNDAMENTO_PRESUPUESTARIO = ("ORDENANZA", "RECONDUCCION")
TIPOS_PARTIDA_CLASIFICADOR = ("RECURSO", "EGRESO")
TIPOS_HISTORIA_EJERCICIO = (
    "CREADO", "NIVELES_CONFIGURADOS", "CATEGORIA_CREADA", "CATEGORIA_MODIFICADA", "CATEGORIA_ELIMINADA",
    "CLASIFICADOR_REGISTRADO", "PROCEDENCIA_MODIFICADA", "PARTIDA_CREADA", "PARTIDA_ELIMINADA",
    "PARTIDAS_IMPORTADAS", "APROBADO", "RECONDUCIDO", "CERRADO", "PRECOMPROMISO_CAMBIADO",
    "PLAN_REGISTRADO", "OBJETIVO_CREADO", "OBJETIVO_MODIFICADO", "OBJETIVO_ELIMINADO",
    "CATEGORIA_VINCULADA", "META_CREADA", "META_MODIFICADA", "META_ELIMINADA", "FUENTE_CREADA",
    "FUENTE_MODIFICADA", "FUENTE_ELIMINADA", "RESTRICCION_AGREGADA", "RESTRICCION_ELIMINADA",
    "INGRESO_REGISTRADO", "INGRESO_MODIFICADO", "INGRESO_ELIMINADO",
    "CREDITO_REGISTRADO", "CREDITO_MODIFICADO", "CREDITO_ELIMINADO", "EXISTENCIAS_REGISTRADAS", "EXISTENCIAS_ELIMINADAS",
    "CERTIFICACION_EMITIDA", "CERTIFICACION_ANULADA",
    "COMPROMISO_REGISTRADO", "COMPROMISO_ANULADO",
)


GOV_BUDGET_YEARS_NOT_DELETABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_no_borrable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_YEAR_NOT_DELETABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_years_no_delete BEFORE DELETE ON gov_budget_years FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_no_borrable()",
    "CREATE TRIGGER trg_gov_budget_years_no_truncate BEFORE TRUNCATE ON gov_budget_years FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_no_borrable()",
)

GOV_BUDGET_FOUNDATIONS_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_fundamento_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_FOUNDATION_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_year_foundations_no_update BEFORE UPDATE ON gov_budget_year_foundations FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_fundamento_inmutable()",
    "CREATE TRIGGER trg_gov_budget_year_foundations_no_delete BEFORE DELETE ON gov_budget_year_foundations FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_fundamento_inmutable()",
    "CREATE TRIGGER trg_gov_budget_year_foundations_no_truncate BEFORE TRUNCATE ON gov_budget_year_foundations FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_fundamento_inmutable()",
)

GOV_BUDGET_HISTORY_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_historia_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_year_history_no_update BEFORE UPDATE ON gov_budget_year_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
    "CREATE TRIGGER trg_gov_budget_year_history_no_delete BEFORE DELETE ON gov_budget_year_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
    "CREATE TRIGGER trg_gov_budget_year_history_no_truncate BEFORE TRUNCATE ON gov_budget_year_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
)

GOV_BUDGET_LEVELS_FROZEN_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio() RETURNS TRIGGER AS $$ DECLARE v varchar; BEGIN IF TG_OP = 'DELETE' THEN v := OLD.year_id; ELSE v := NEW.year_id; END IF; IF (SELECT estado FROM gov_budget_years WHERE id = v) <> 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_YEAR_FROZEN', DETAIL = TG_TABLE_NAME; END IF; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_program_levels_frozen BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_program_levels FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio()",
)

GOV_BUDGET_CATEGORIES_FROZEN_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio() RETURNS TRIGGER AS $$ DECLARE v varchar; BEGIN IF TG_OP = 'DELETE' THEN v := OLD.year_id; ELSE v := NEW.year_id; END IF; IF (SELECT estado FROM gov_budget_years WHERE id = v) <> 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_YEAR_FROZEN', DETAIL = TG_TABLE_NAME; END IF; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_categories_frozen BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_categories FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio()",
)

GOV_BUDGET_CLASSIFIERS_FROZEN_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio() RETURNS TRIGGER AS $$ DECLARE v varchar; BEGIN IF TG_OP = 'DELETE' THEN v := OLD.year_id; ELSE v := NEW.year_id; END IF; IF (SELECT estado FROM gov_budget_years WHERE id = v) <> 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_YEAR_FROZEN', DETAIL = TG_TABLE_NAME; END IF; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_classifiers_frozen BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_classifiers FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio()",
)

GOV_BUDGET_ITEMS_FROZEN_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_congelado_por_clasificador() RETURNS TRIGGER AS $$ DECLARE v_clasificador varchar; BEGIN IF TG_OP = 'DELETE' THEN v_clasificador := OLD.classifier_id; ELSE v_clasificador := NEW.classifier_id; END IF; IF (SELECT y.estado FROM gov_budget_years y JOIN gov_budget_classifiers gc ON gc.year_id = y.id WHERE gc.id = v_clasificador) <> 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_YEAR_FROZEN', DETAIL = TG_TABLE_NAME; END IF; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_classifier_items_frozen BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_classifier_items FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_clasificador()",
)


class GovernmentBudgetYear(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Ejercicio presupuestario de un ente (BUD-01, GOV-BUD-01)."""

    __tablename__ = "gov_budget_years"
    __scope__ = Scope.COMPANY

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    anio: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    moneda_funcional: Mapped[str] = mapped_column(String(3), nullable=False)
    estado: Mapped[str] = mapped_column(String(12), nullable=False, default="BORRADOR", server_default="BORRADOR")
    precompromiso_activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    precompromiso_desde: Mapped[date | None] = mapped_column(Date, nullable=True)
    fijado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    fijado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cerrado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_cierre: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "anio", name="uq_gov_budget_years_company_id_anio"),
        CheckConstraint("anio BETWEEN 2000 AND 2100", name="anio"),
        CheckConstraint(f"estado IN ({en(ESTADOS_EJERCICIO_PRESUPUESTARIO)})", name="estado"),
        CheckConstraint("length(moneda_funcional) = 3", name="moneda"),
        CheckConstraint("estado = 'BORRADOR' OR (fijado_por IS NOT NULL AND fijado_en IS NOT NULL)", name="fijado"),
        CheckConstraint("estado <> 'CERRADO' OR (cerrado_por IS NOT NULL AND cerrado_en IS NOT NULL)", name="cerrado"),
    )


class GovernmentBudgetYearFoundation(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Fundamento jurídico inmodificable de un ejercicio presupuestario (BUD-01)."""

    __tablename__ = "gov_budget_year_foundations"
    __scope__ = Scope.COMPANY

    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    referencia: Mapped[str] = mapped_column(String(300), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    documento_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    huella: Mapped[str] = mapped_column(String(64), nullable=False)
    fotografia: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        CheckConstraint(f"tipo IN ({en(TIPOS_FUNDAMENTO_PRESUPUESTARIO)})", name="tipo"),
    )


class GovernmentBudgetProgramLevel(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Nivel programático configurado para un ejercicio presupuestario (BUD-01)."""

    __tablename__ = "gov_budget_program_levels"
    __scope__ = Scope.COMPANY

    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    orden: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)

    __table_args__ = (
        UniqueConstraint("year_id", "orden", name="uq_gov_budget_program_levels_year_id_orden"),
        UniqueConstraint("year_id", "nombre", name="uq_gov_budget_program_levels_year_id_nombre"),
        CheckConstraint("orden BETWEEN 1 AND 8", name="orden"),
    )


class GovernmentBudgetCategory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Categoría programática de un ejercicio presupuestario (BUD-01)."""

    __tablename__ = "gov_budget_categories"
    __scope__ = Scope.COMPANY

    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    level_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_program_levels.id"), nullable=False, index=True)
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_budget_categories.id"), nullable=True, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    codigo_completo: Mapped[str] = mapped_column(String(200), nullable=False)
    denominacion: Mapped[str] = mapped_column(String(300), nullable=False)
    unit_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_units.id"), nullable=True, index=True)
    objective_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_budget_objectives.id"), nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("year_id", "codigo_completo", name="uq_gov_budget_categories_year_id_codigo_completo"),
    )


class GovernmentBudgetClassifier(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Clasificador presupuestario versionado de un ejercicio (BUD-02, GOV-BUD-02)."""

    __tablename__ = "gov_budget_classifiers"
    __scope__ = Scope.COMPANY

    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False, unique=True, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    edicion: Mapped[str] = mapped_column(String(200), nullable=False)
    fecha_edicion: Mapped[date | None] = mapped_column(Date, nullable=True)
    procedencia: Mapped[str] = mapped_column(String(1000), nullable=False)
    documento_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    documento_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)


class GovernmentBudgetClassifierItem(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Partida presupuestaria del clasificador versionado (BUD-02)."""

    __tablename__ = "gov_budget_classifier_items"
    __scope__ = Scope.COMPANY

    classifier_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_classifiers.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(8), nullable=False)
    codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    denominacion: Mapped[str] = mapped_column(String(300), nullable=False)
    nivel: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_budget_classifier_items.id"), nullable=True, index=True)
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("classifier_id", "tipo", "codigo", name="uq_gov_budget_classifier_items_classifier_id_tipo_codigo"),
        CheckConstraint(f"tipo IN ({en(TIPOS_PARTIDA_CLASIFICADOR)})", name="tipo"),
        CheckConstraint("nivel BETWEEN 1 AND 12", name="nivel"),
        CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
    )


class GovernmentBudgetYearHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia inmutable de un ejercicio presupuestario (BUD-01)."""

    __tablename__ = "gov_budget_year_history"
    __scope__ = Scope.COMPANY

    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    detalle: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        CheckConstraint(f"tipo IN ({en(TIPOS_HISTORIA_EJERCICIO)})", name="tipo"),
    )


for _sentencia in GOV_BUDGET_YEARS_NOT_DELETABLE_PG:
    event.listen(GovernmentBudgetYear.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_BUDGET_FOUNDATIONS_IMMUTABLE_PG:
    event.listen(GovernmentBudgetYearFoundation.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_BUDGET_HISTORY_IMMUTABLE_PG:
    event.listen(GovernmentBudgetYearHistory.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_BUDGET_LEVELS_FROZEN_PG:
    event.listen(GovernmentBudgetProgramLevel.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_BUDGET_CATEGORIES_FROZEN_PG:
    event.listen(GovernmentBudgetCategory.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_BUDGET_CLASSIFIERS_FROZEN_PG:
    event.listen(GovernmentBudgetClassifier.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_BUDGET_ITEMS_FROZEN_PG:
    event.listen(GovernmentBudgetClassifierItem.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


class GovernmentBudgetPlan(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Plan operativo registrado para un ejercicio presupuestario (BUD-03)."""

    __tablename__ = "gov_budget_plans"
    __scope__ = Scope.COMPANY

    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False, index=True, unique=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    denominacion: Mapped[str] = mapped_column(String(300), nullable=False)
    documento_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    documento_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)


class GovernmentBudgetObjective(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Objetivo definido dentro del plan operativo de un ejercicio (BUD-03)."""

    __tablename__ = "gov_budget_objectives"
    __scope__ = Scope.COMPANY

    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(500), nullable=False)

    __table_args__ = (
        UniqueConstraint("year_id", "codigo", name="uq_gov_budget_objectives_year_id_codigo"),
    )


class GovernmentBudgetGoal(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Meta física asociada a una categoría programática (BUD-03)."""

    __tablename__ = "gov_budget_goals"
    __scope__ = Scope.COMPANY

    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_categories.id"), nullable=False, index=True)
    descripcion: Mapped[str] = mapped_column(String(500), nullable=False)
    unidad_medida: Mapped[str] = mapped_column(String(60), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    indicador: Mapped[str] = mapped_column(String(200), nullable=False)
    formula: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        CheckConstraint("cantidad > 0", name="cantidad"),
    )


class GovernmentBudgetFundingSource(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Fuente de financiamiento registrada para un ejercicio (BUD-04)."""

    __tablename__ = "gov_budget_funding_sources"
    __scope__ = Scope.COMPANY

    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    denominacion: Mapped[str] = mapped_column(String(300), nullable=False)
    procedencia: Mapped[str] = mapped_column(String(1000), nullable=False)
    documento_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    documento_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("year_id", "codigo", name="uq_gov_budget_funding_sources_year_id_codigo"),
        CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
    )


class GovernmentBudgetFundingRestriction(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Restricción de uso asociada a una fuente de financiamiento (BUD-04)."""

    __tablename__ = "gov_budget_funding_restrictions"
    __scope__ = Scope.COMPANY

    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_funding_sources.id"), nullable=False, index=True)
    descripcion: Mapped[str] = mapped_column(String(500), nullable=False)
    fundamento: Mapped[str] = mapped_column(String(500), nullable=False)
    partidas: Mapped[list[str]] = mapped_column(JSON, nullable=False)


GOV_BUDGET_PLANS_FROZEN_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio() RETURNS TRIGGER AS $$ DECLARE v varchar; BEGIN IF TG_OP = 'DELETE' THEN v := OLD.year_id; ELSE v := NEW.year_id; END IF; IF (SELECT estado FROM gov_budget_years WHERE id = v) <> 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_YEAR_FROZEN', DETAIL = TG_TABLE_NAME; END IF; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_plans_frozen BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_plans FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio()",
)

GOV_BUDGET_OBJECTIVES_FROZEN_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio() RETURNS TRIGGER AS $$ DECLARE v varchar; BEGIN IF TG_OP = 'DELETE' THEN v := OLD.year_id; ELSE v := NEW.year_id; END IF; IF (SELECT estado FROM gov_budget_years WHERE id = v) <> 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_YEAR_FROZEN', DETAIL = TG_TABLE_NAME; END IF; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_objectives_frozen BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_objectives FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio()",
)

GOV_BUDGET_GOALS_FROZEN_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio() RETURNS TRIGGER AS $$ DECLARE v varchar; BEGIN IF TG_OP = 'DELETE' THEN v := OLD.year_id; ELSE v := NEW.year_id; END IF; IF (SELECT estado FROM gov_budget_years WHERE id = v) <> 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_YEAR_FROZEN', DETAIL = TG_TABLE_NAME; END IF; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_goals_frozen BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_goals FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio()",
)

GOV_BUDGET_FUNDING_SOURCES_FROZEN_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio() RETURNS TRIGGER AS $$ DECLARE v varchar; BEGIN IF TG_OP = 'DELETE' THEN v := OLD.year_id; ELSE v := NEW.year_id; END IF; IF (SELECT estado FROM gov_budget_years WHERE id = v) <> 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_YEAR_FROZEN', DETAIL = TG_TABLE_NAME; END IF; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_funding_sources_frozen BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_funding_sources FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio()",
)

GOV_BUDGET_FUNDING_RESTRICTIONS_FROZEN_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio() RETURNS TRIGGER AS $$ DECLARE v varchar; BEGIN IF TG_OP = 'DELETE' THEN v := OLD.year_id; ELSE v := NEW.year_id; END IF; IF (SELECT estado FROM gov_budget_years WHERE id = v) <> 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_YEAR_FROZEN', DETAIL = TG_TABLE_NAME; END IF; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_funding_restrictions_frozen BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_funding_restrictions FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio()",
)


for _sentencia in GOV_BUDGET_PLANS_FROZEN_PG:
    event.listen(GovernmentBudgetPlan.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_BUDGET_OBJECTIVES_FROZEN_PG:
    event.listen(GovernmentBudgetObjective.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_BUDGET_GOALS_FROZEN_PG:
    event.listen(GovernmentBudgetGoal.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_BUDGET_FUNDING_SOURCES_FROZEN_PG:
    event.listen(GovernmentBudgetFundingSource.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_BUDGET_FUNDING_RESTRICTIONS_FROZEN_PG:
    event.listen(GovernmentBudgetFundingRestriction.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


class GovernmentBudgetIncomeEstimate(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Estimación de ingresos del presupuesto aprobado (BUD-05)."""

    __tablename__ = "gov_budget_income_estimates"
    __scope__ = Scope.COMPANY

    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_classifier_items.id"), nullable=False, index=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    __table_args__ = (
        UniqueConstraint("year_id", "item_id", name="uq_gov_budget_income_estimates_year_id_item_id"),
        CheckConstraint("monto > 0", name="monto"),
    )


class GovernmentBudgetCredit(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Crédito presupuestario del presupuesto aprobado (BUD-05)."""

    __tablename__ = "gov_budget_credits"
    __scope__ = Scope.COMPANY

    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_categories.id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_classifier_items.id"), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_funding_sources.id"), nullable=False, index=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    __table_args__ = (
        UniqueConstraint("year_id", "category_id", "item_id", "source_id", name="uq_gov_budget_credits_year_id_category_id_item_id_source_id"),
        CheckConstraint("monto > 0", name="monto"),
    )


class GovernmentBudgetTreasuryHoldings(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Existencias del Tesoro no comprometidas del presupuesto aprobado (BUD-05)."""

    __tablename__ = "gov_budget_treasury_holdings"
    __scope__ = Scope.COMPANY

    year_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gov_budget_years.id"),
        nullable=False,
        index=True,
        unique=True,
    )
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    fecha_corte: Mapped[date] = mapped_column(Date, nullable=False)
    documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    documento_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    __table_args__ = (CheckConstraint("monto > 0", name="monto"),)


GOV_BUDGET_INCOME_ESTIMATES_FROZEN_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio() RETURNS TRIGGER AS $$ DECLARE v varchar; BEGIN IF TG_OP = 'DELETE' THEN v := OLD.year_id; ELSE v := NEW.year_id; END IF; IF (SELECT estado FROM gov_budget_years WHERE id = v) <> 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_YEAR_FROZEN', DETAIL = TG_TABLE_NAME; END IF; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_income_estimates_frozen BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_income_estimates FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio()",
)

GOV_BUDGET_CREDITS_FROZEN_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio() RETURNS TRIGGER AS $$ DECLARE v varchar; BEGIN IF TG_OP = 'DELETE' THEN v := OLD.year_id; ELSE v := NEW.year_id; END IF; IF (SELECT estado FROM gov_budget_years WHERE id = v) <> 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_YEAR_FROZEN', DETAIL = TG_TABLE_NAME; END IF; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_credits_frozen BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_credits FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio()",
)

GOV_BUDGET_TREASURY_HOLDINGS_FROZEN_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio() RETURNS TRIGGER AS $$ DECLARE v varchar; BEGIN IF TG_OP = 'DELETE' THEN v := OLD.year_id; ELSE v := NEW.year_id; END IF; IF (SELECT estado FROM gov_budget_years WHERE id = v) <> 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_YEAR_FROZEN', DETAIL = TG_TABLE_NAME; END IF; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_treasury_holdings_frozen BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_treasury_holdings FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_congelado_por_ejercicio()",
)

for _sentencia in GOV_BUDGET_INCOME_ESTIMATES_FROZEN_PG:
    event.listen(GovernmentBudgetIncomeEstimate.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_BUDGET_CREDITS_FROZEN_PG:
    event.listen(GovernmentBudgetCredit.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_BUDGET_TREASURY_HOLDINGS_FROZEN_PG:
    event.listen(GovernmentBudgetTreasuryHoldings.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


ESTADOS_CERTIFICACION = ("VIGENTE", "ANULADA")


class GovernmentBudgetCertificate(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Certificación de disponibilidad presupuestaria (BUD-06)."""

    __tablename__ = "gov_budget_certificates"
    __scope__ = Scope.COMPANY

    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    credit_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_credits.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="VIGENTE", server_default="VIGENTE")
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    saldo_antes: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    saldo_despues: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    concepto: Mapped[str] = mapped_column(String(500), nullable=False)
    expediente_referencia: Mapped[str] = mapped_column(String(120), nullable=False)
    procurement_file_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=True, index=True)
    firmante_cargo_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=False, index=True)
    firmante_cargo_codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    firmante_cargo_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    firmante_unidad: Mapped[str] = mapped_column(String(250), nullable=False)
    firmante_funcionario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    firmante_funcionario_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    emitida_por: Mapped[str] = mapped_column(String(36), nullable=False)
    emitida_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    huella: Mapped[str] = mapped_column(String(64), nullable=False)
    documento_storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    documento_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    documento_tamano: Mapped[int] = mapped_column(Integer, nullable=False)
    documento_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    anulada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    anulada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_anulacion: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("year_id", "numero", name="uq_gov_budget_certificates_year_id_numero"),
        UniqueConstraint("company_id", "codigo", name="uq_gov_budget_certificates_company_id_codigo"),
        CheckConstraint("estado IN ('VIGENTE', 'ANULADA')", name="estado"),
        CheckConstraint("monto > 0", name="monto"),
        CheckConstraint("saldo_antes >= monto AND saldo_despues = saldo_antes - monto", name="saldos"),
        CheckConstraint("(estado = 'VIGENTE' AND anulada_por IS NULL AND anulada_en IS NULL AND motivo_anulacion IS NULL) OR (estado = 'ANULADA' AND anulada_por IS NOT NULL AND anulada_en IS NOT NULL AND motivo_anulacion IS NOT NULL)", name="anulacion"),
    )


GOV_BUDGET_CERTIFICATES_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_certificado_inmutable() RETURNS TRIGGER AS $$ BEGIN IF TG_OP = 'DELETE' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CERTIFICATE_IMMUTABLE', DETAIL = TG_OP; END IF; IF OLD.estado <> 'VIGENTE' OR NEW.estado <> 'ANULADA' OR NEW.year_id IS DISTINCT FROM OLD.year_id OR NEW.company_id IS DISTINCT FROM OLD.company_id OR NEW.credit_id IS DISTINCT FROM OLD.credit_id OR NEW.numero IS DISTINCT FROM OLD.numero OR NEW.codigo IS DISTINCT FROM OLD.codigo OR NEW.monto IS DISTINCT FROM OLD.monto OR NEW.saldo_antes IS DISTINCT FROM OLD.saldo_antes OR NEW.saldo_despues IS DISTINCT FROM OLD.saldo_despues OR NEW.moneda IS DISTINCT FROM OLD.moneda OR NEW.fecha IS DISTINCT FROM OLD.fecha OR NEW.concepto IS DISTINCT FROM OLD.concepto OR NEW.expediente_referencia IS DISTINCT FROM OLD.expediente_referencia OR NEW.procurement_file_id IS DISTINCT FROM OLD.procurement_file_id OR NEW.firmante_cargo_id IS DISTINCT FROM OLD.firmante_cargo_id OR NEW.emitida_por IS DISTINCT FROM OLD.emitida_por OR NEW.emitida_en IS DISTINCT FROM OLD.emitida_en OR NEW.huella IS DISTINCT FROM OLD.huella OR NEW.documento_sha256 IS DISTINCT FROM OLD.documento_sha256 OR NEW.documento_storage_key IS DISTINCT FROM OLD.documento_storage_key THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CERTIFICATE_IMMUTABLE', DETAIL = TG_OP; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_certificates_inmutable BEFORE UPDATE OR DELETE ON gov_budget_certificates FOR EACH ROW EXECUTE FUNCTION kontrol_gov_certificado_inmutable()",
    "CREATE TRIGGER trg_gov_budget_certificates_no_truncate BEFORE TRUNCATE ON gov_budget_certificates FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
)

for _sentencia in GOV_BUDGET_CERTIFICATES_IMMUTABLE_PG:
    event.listen(GovernmentBudgetCertificate.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


ESTADOS_COMPROMISO = ("VIGENTE", "ANULADO")


class GovernmentBudgetCommitment(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Compromiso presupuestario (BUD-08, GOV-BUD-012)."""

    __tablename__ = "gov_budget_commitments"
    __scope__ = Scope.COMPANY

    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="VIGENTE", server_default="VIGENTE")
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    concepto: Mapped[str] = mapped_column(String(500), nullable=False)
    expediente_referencia: Mapped[str] = mapped_column(String(120), nullable=False)
    procurement_file_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=True, index=True)
    autoridad_cargo_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=False, index=True)
    autoridad_cargo_codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    autoridad_cargo_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    autoridad_unidad: Mapped[str] = mapped_column(String(250), nullable=False)
    autoridad_funcionario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    autoridad_funcionario_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    limite_tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    limite_monto: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    limite_moneda: Mapped[str | None] = mapped_column(String(3), nullable=True)
    soporte_documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    soporte_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    emitido_por: Mapped[str] = mapped_column(String(36), nullable=False)
    emitido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    huella: Mapped[str] = mapped_column(String(64), nullable=False)
    documento_storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    documento_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    documento_tamano: Mapped[int] = mapped_column(Integer, nullable=False)
    documento_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    anulado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    anulado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_anulacion: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("year_id", "numero", name="uq_gov_budget_commitments_year_id_numero"),
        UniqueConstraint("company_id", "codigo", name="uq_gov_budget_commitments_company_id_codigo"),
        CheckConstraint("estado IN ('VIGENTE', 'ANULADO')", name="estado"),
        CheckConstraint(
            "(limite_tipo = 'SIN_LIMITE' AND limite_monto IS NULL AND limite_moneda IS NULL) OR "
            "(limite_tipo = 'MONTO' AND limite_monto > 0 AND limite_moneda IS NOT NULL)",
            name="limite",
        ),
        CheckConstraint(
            "(estado = 'VIGENTE' AND anulado_por IS NULL AND anulado_en IS NULL AND motivo_anulacion IS NULL) OR "
            "(estado = 'ANULADO' AND anulado_por IS NOT NULL AND anulado_en IS NOT NULL AND motivo_anulacion IS NOT NULL)",
            name="anulacion",
        ),
    )


class GovernmentBudgetCommitmentLine(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Imputación de un compromiso a una certificación (BUD-08)."""

    __tablename__ = "gov_budget_commitment_lines"
    __scope__ = Scope.COMPANY

    commitment_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_commitments.id"), nullable=False, index=True)
    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    certificate_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_certificates.id"), nullable=False, index=True)
    credit_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_credits.id"), nullable=False, index=True)
    linea: Mapped[int] = mapped_column(Integer, nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint("commitment_id", "certificate_id", name="uq_gov_budget_commitment_lines_commitment_id_certificate_id"),
        UniqueConstraint("commitment_id", "linea", name="uq_gov_budget_commitment_lines_commitment_id_linea"),
        CheckConstraint("monto > 0", name="monto"),
        CheckConstraint("linea BETWEEN 1 AND 20", name="linea"),
    )


GOV_BUDGET_COMMITMENTS_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_compromiso_inmutable() RETURNS TRIGGER AS $$ BEGIN IF TG_OP = 'DELETE' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_COMMITMENT_IMMUTABLE', DETAIL = TG_OP; END IF; IF OLD.estado <> 'VIGENTE' OR NEW.estado <> 'ANULADO' OR NEW.year_id IS DISTINCT FROM OLD.year_id OR NEW.company_id IS DISTINCT FROM OLD.company_id OR NEW.numero IS DISTINCT FROM OLD.numero OR NEW.codigo IS DISTINCT FROM OLD.codigo OR NEW.moneda IS DISTINCT FROM OLD.moneda OR NEW.fecha IS DISTINCT FROM OLD.fecha OR NEW.concepto IS DISTINCT FROM OLD.concepto OR NEW.expediente_referencia IS DISTINCT FROM OLD.expediente_referencia OR NEW.procurement_file_id IS DISTINCT FROM OLD.procurement_file_id OR NEW.autoridad_cargo_id IS DISTINCT FROM OLD.autoridad_cargo_id OR NEW.limite_tipo IS DISTINCT FROM OLD.limite_tipo OR NEW.limite_monto IS DISTINCT FROM OLD.limite_monto OR NEW.limite_moneda IS DISTINCT FROM OLD.limite_moneda OR NEW.soporte_documento_id IS DISTINCT FROM OLD.soporte_documento_id OR NEW.soporte_sha256 IS DISTINCT FROM OLD.soporte_sha256 OR NEW.emitido_por IS DISTINCT FROM OLD.emitido_por OR NEW.emitido_en IS DISTINCT FROM OLD.emitido_en OR NEW.huella IS DISTINCT FROM OLD.huella OR NEW.documento_sha256 IS DISTINCT FROM OLD.documento_sha256 OR NEW.documento_storage_key IS DISTINCT FROM OLD.documento_storage_key THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_COMMITMENT_IMMUTABLE', DETAIL = TG_OP; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_commitments_inmutable BEFORE UPDATE OR DELETE ON gov_budget_commitments FOR EACH ROW EXECUTE FUNCTION kontrol_gov_compromiso_inmutable()",
    "CREATE TRIGGER trg_gov_budget_commitments_no_truncate BEFORE TRUNCATE ON gov_budget_commitments FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
)

ESTADOS_TASA = ("BORRADOR", "APROBADA", "SUSTITUIDA", "ANULADA")
MONEDAS_TASA = ("USD", "EUR")


class GovernmentOfficialExchangeRate(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Tasa oficial BCV de Gobierno (TRE-09, GOV-TRE-011; N39)."""

    __tablename__ = "gov_official_exchange_rates"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    moneda_cotizacion: Mapped[str] = mapped_column(String(3), nullable=False, default="VES", server_default="VES")
    fecha_efectiva: Mapped[date] = mapped_column(Date, nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    fuente: Mapped[str] = mapped_column(String(10), nullable=False, default="BCV", server_default="BCV")
    fuente_referencia: Mapped[str] = mapped_column(String(300), nullable=False)
    publicada_en: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(String(12), nullable=False, default="BORRADOR", server_default="BORRADOR")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sustituye_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_official_exchange_rates.id"), nullable=True, index=True)
    motivo_correccion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    capturada_por: Mapped[str] = mapped_column(String(36), nullable=False)
    capturada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    aprobada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    aprobada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidencia_documento_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    evidencia_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sustituida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    anulada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    anulada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_anulacion: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        CheckConstraint(f"moneda IN ({en(MONEDAS_TASA)})", name="moneda"),
        CheckConstraint("moneda_cotizacion = 'VES'", name="cotizacion"),
        CheckConstraint("fuente = 'BCV'", name="fuente"),
        CheckConstraint("valor > 0", name="valor"),
        CheckConstraint(f"estado IN ({en(ESTADOS_TASA)})", name="estado"),
        CheckConstraint("version >= 1", name="version"),
        CheckConstraint("publicada_en IS NULL OR publicada_en <= fecha_efectiva", name="publicacion"),
        CheckConstraint("(sustituye_id IS NULL) = (motivo_correccion IS NULL)", name="correccion"),
        CheckConstraint(
            "(estado = 'BORRADOR' AND aprobada_por IS NULL AND aprobada_en IS NULL AND evidencia_documento_id IS NULL AND evidencia_sha256 IS NULL) OR "
            "(estado IN ('APROBADA', 'SUSTITUIDA') AND aprobada_por IS NOT NULL AND aprobada_en IS NOT NULL AND evidencia_documento_id IS NOT NULL AND evidencia_sha256 IS NOT NULL) OR "
            "estado = 'ANULADA'",
            name="aprobacion",
        ),
        CheckConstraint("(estado = 'SUSTITUIDA') = (sustituida_en IS NOT NULL)", name="sustitucion"),
        CheckConstraint(
            "(estado = 'ANULADA' AND anulada_por IS NOT NULL AND anulada_en IS NOT NULL AND motivo_anulacion IS NOT NULL) OR "
            "(estado <> 'ANULADA' AND anulada_por IS NULL AND anulada_en IS NULL AND motivo_anulacion IS NULL)",
            name="anulacion",
        ),
        Index("ix_gov_official_exchange_rates_clave", "company_id", "moneda", "fecha_efectiva"),
        Index("uq_gov_official_exchange_rates_aprobada", "company_id", "moneda", "fecha_efectiva", unique=True,
              postgresql_where=text("estado = 'APROBADA'"), sqlite_where=text("estado = 'APROBADA'")),
        Index("uq_gov_official_exchange_rates_borrador", "company_id", "moneda", "fecha_efectiva", unique=True,
              postgresql_where=text("estado = 'BORRADOR'"), sqlite_where=text("estado = 'BORRADOR'")),
    )


GOV_OFFICIAL_RATES_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_tasa_oficial_inmutable() RETURNS TRIGGER AS $$ BEGIN IF TG_OP = 'DELETE' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_OFFICIAL_RATE_IMMUTABLE', DETAIL = TG_OP; END IF; IF NEW.company_id IS DISTINCT FROM OLD.company_id OR NEW.moneda IS DISTINCT FROM OLD.moneda OR NEW.moneda_cotizacion IS DISTINCT FROM OLD.moneda_cotizacion OR NEW.fecha_efectiva IS DISTINCT FROM OLD.fecha_efectiva OR NEW.valor IS DISTINCT FROM OLD.valor OR NEW.fuente IS DISTINCT FROM OLD.fuente OR NEW.fuente_referencia IS DISTINCT FROM OLD.fuente_referencia OR NEW.publicada_en IS DISTINCT FROM OLD.publicada_en OR NEW.version IS DISTINCT FROM OLD.version OR NEW.sustituye_id IS DISTINCT FROM OLD.sustituye_id OR NEW.motivo_correccion IS DISTINCT FROM OLD.motivo_correccion OR NEW.capturada_por IS DISTINCT FROM OLD.capturada_por OR NEW.capturada_en IS DISTINCT FROM OLD.capturada_en OR NOT ((OLD.estado = 'BORRADOR' AND NEW.estado IN ('APROBADA', 'ANULADA')) OR (OLD.estado = 'APROBADA' AND NEW.estado IN ('SUSTITUIDA', 'ANULADA'))) OR (OLD.estado <> 'BORRADOR' AND (NEW.aprobada_por IS DISTINCT FROM OLD.aprobada_por OR NEW.aprobada_en IS DISTINCT FROM OLD.aprobada_en OR NEW.evidencia_documento_id IS DISTINCT FROM OLD.evidencia_documento_id OR NEW.evidencia_sha256 IS DISTINCT FROM OLD.evidencia_sha256)) THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_OFFICIAL_RATE_IMMUTABLE', DETAIL = TG_OP; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_official_exchange_rates_inmutable BEFORE UPDATE OR DELETE ON gov_official_exchange_rates FOR EACH ROW EXECUTE FUNCTION kontrol_gov_tasa_oficial_inmutable()",
    "CREATE TRIGGER trg_gov_official_exchange_rates_no_truncate BEFORE TRUNCATE ON gov_official_exchange_rates FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
)

for _sentencia in GOV_OFFICIAL_RATES_IMMUTABLE_PG:
    event.listen(GovernmentOfficialExchangeRate.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


GOV_BUDGET_COMMITMENT_LINES_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_compromiso_linea_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_COMMITMENT_LINE_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_budget_commitment_lines_inmutable BEFORE UPDATE OR DELETE ON gov_budget_commitment_lines FOR EACH ROW EXECUTE FUNCTION kontrol_gov_compromiso_linea_inmutable()",
    "CREATE TRIGGER trg_gov_budget_commitment_lines_no_truncate BEFORE TRUNCATE ON gov_budget_commitment_lines FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
)

for _sentencia in GOV_BUDGET_COMMITMENTS_IMMUTABLE_PG:
    event.listen(GovernmentBudgetCommitment.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_BUDGET_COMMITMENT_LINES_IMMUTABLE_PG:
    event.listen(GovernmentBudgetCommitmentLine.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


ESTADOS_BANCO = ("ACTIVO", "INACTIVO")
ESTADOS_CUENTA_BANCARIA = ("BORRADOR", "VIGENTE", "INACTIVA", "CERRADA")
TIPOS_CUENTA_BANCARIA = ("CORRIENTE", "AHORRO")
TIPOS_HISTORIA_CUENTA = ("CREADA", "EDITADA", "ACTO_VINCULADO", "ACTIVADA", "INACTIVADA", "REACTIVADA", "CERRADA", "AUTORIZADO_ALTA", "AUTORIZADO_FIN")


GOV_BANK_ACCOUNTS_NOT_DELETABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_cuenta_no_borrable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BANK_ACCOUNT_NOT_DELETABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_bank_accounts_no_delete BEFORE DELETE ON gov_bank_accounts FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cuenta_no_borrable()",
    "CREATE TRIGGER trg_gov_bank_accounts_no_truncate BEFORE TRUNCATE ON gov_bank_accounts FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_cuenta_no_borrable()",
)

GOV_BANK_ACCOUNT_AUTHORIZATIONS_NOT_DELETABLE_PG = (
    "CREATE TRIGGER trg_gov_bank_account_authorizations_no_delete BEFORE DELETE ON gov_bank_account_authorizations FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cuenta_no_borrable()",
    "CREATE TRIGGER trg_gov_bank_account_authorizations_no_truncate BEFORE TRUNCATE ON gov_bank_account_authorizations FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_cuenta_no_borrable()",
)

GOV_BANK_ACCOUNT_HISTORY_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_cuenta_historia_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BANK_ACCOUNT_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_bank_account_history_no_update BEFORE UPDATE ON gov_bank_account_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cuenta_historia_inmutable()",
    "CREATE TRIGGER trg_gov_bank_account_history_no_delete BEFORE DELETE ON gov_bank_account_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cuenta_historia_inmutable()",
    "CREATE TRIGGER trg_gov_bank_account_history_no_truncate BEFORE TRUNCATE ON gov_bank_account_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_cuenta_historia_inmutable()",
)


class GovernmentBank(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Banco del catálogo de Tesorería de Gobierno (TRE-01, OD-TRE01-04): no precarga códigos oficiales."""

    __tablename__ = "gov_banks"
    __scope__ = Scope.COMPANY

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(4), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="ACTIVO", server_default="ACTIVO")

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_banks_company_id_codigo"),
        CheckConstraint(f"estado IN ({en(ESTADOS_BANCO)})", name="estado"),
        CheckConstraint("version >= 1", name="version"),
    )


class GovernmentBankAccount(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Cuenta bancaria pública del ente (TRE-01, GOV-TRE-001): nunca se borra; el número completo no sale por la API de consulta."""

    __tablename__ = "gov_bank_accounts"
    __scope__ = Scope.COMPANY

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    denominacion: Mapped[str] = mapped_column(String(200), nullable=False)
    bank_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_banks.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="BORRADOR", server_default="BORRADOR")
    acto_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=True, index=True)
    activada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    activada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cerrada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_cierre: Mapped[date | None] = mapped_column(Date, nullable=True)
    motivo_cierre: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_bank_accounts_company_id_codigo"),
        UniqueConstraint("company_id", "bank_id", "numero", name="uq_gov_bank_accounts_numero"),
        Index("ix_gov_bank_accounts_company_estado", "company_id", "estado"),
        CheckConstraint(f"estado IN ({en(ESTADOS_CUENTA_BANCARIA)})", name="estado"),
        CheckConstraint(f"tipo IN ({en(TIPOS_CUENTA_BANCARIA)})", name="tipo"),
        CheckConstraint(f"moneda IN ({en(MONEDAS_LIMITE)})", name="moneda"),
        CheckConstraint("length(numero) = 20", name="numero_largo"),
        CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        CheckConstraint("estado = 'BORRADOR' OR (acto_id IS NOT NULL AND activada_en IS NOT NULL)", name="activada_con_acto"),
        CheckConstraint("(estado = 'CERRADA') = (cerrada_en IS NOT NULL AND fecha_cierre IS NOT NULL AND motivo_cierre IS NOT NULL)", name="cierre_completo"),
        CheckConstraint("version >= 1", name="version"),
    )


class GovernmentBankAccountAuthorization(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Autorización de un cargo sobre una cuenta (TRE-01, OD-TRE01-01): no es una persona; nunca se sobrescribe."""

    __tablename__ = "gov_bank_account_authorizations"
    __scope__ = Scope.COMPANY

    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_bank_accounts.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    position_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=False, index=True)
    cargo_codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    cargo_denominacion: Mapped[str] = mapped_column(String(200), nullable=False)
    cargo_unidad: Mapped[str] = mapped_column(String(200), nullable=False)
    acto_alta_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=False, index=True)
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    acto_fin_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=True)
    motivo_fin: Mapped[str | None] = mapped_column(String(500), nullable=True)
    terminada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    terminada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "uq_gov_bank_account_authorizations_en_vigor",
            "account_id",
            "position_id",
            unique=True,
            postgresql_where=text("vigente_hasta IS NULL"),
            sqlite_where=text("vigente_hasta IS NULL"),
        ),
        CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        CheckConstraint("(vigente_hasta IS NULL) = (motivo_fin IS NULL AND terminada_en IS NULL)", name="fin_completo"),
        CheckConstraint("acto_fin_id IS NULL OR vigente_hasta IS NOT NULL", name="acto_fin_terminada"),
    )


class GovernmentBankAccountHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia inmutable de una cuenta bancaria (TRE-01): nunca guarda el número completo."""

    __tablename__ = "gov_bank_account_history"
    __scope__ = Scope.COMPANY

    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_bank_accounts.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    detalle: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        CheckConstraint(f"tipo IN ({en(TIPOS_HISTORIA_CUENTA)})", name="tipo"),
    )


for _sentencia in GOV_BANK_ACCOUNTS_NOT_DELETABLE_PG:
    event.listen(GovernmentBankAccount.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_BANK_ACCOUNT_AUTHORIZATIONS_NOT_DELETABLE_PG:
    event.listen(GovernmentBankAccountAuthorization.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_BANK_ACCOUNT_HISTORY_IMMUTABLE_PG:
    event.listen(GovernmentBankAccountHistory.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


ESTADOS_RUBRO_CAJA = ("ACTIVO", "INACTIVO")
TIPOS_RUBRO_CAJA = ("INGRESO", "DESEMBOLSO")

ESTADOS_PROGRAMA_CAJA = ("BORRADOR", "VIGENTE", "CERRADO", "DESCARTADO")
ESTADOS_VERSION_PROGRAMA_CAJA = ("BORRADOR", "VIGENTE", "SUPERADA", "DESCARTADA", "CERRADA")
TIPOS_HISTORIA_PROGRAMA_CAJA = (
    "CREADO",
    "DECLARACION",
    "LINEA",
    "ACTIVADO",
    "REPROGRAMADO",
    "DESCARTADO",
    "CERRADO",
)

GOV_CASH_PROGRAMS_NOT_DELETABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_cash_program_no_borrable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CASH_PROGRAM_NOT_DELETABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_cash_programs_no_delete BEFORE DELETE ON gov_cash_programs FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cash_program_no_borrable()",
    "CREATE TRIGGER trg_gov_cash_programs_no_truncate BEFORE TRUNCATE ON gov_cash_programs FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_cash_program_no_borrable()",
)

GOV_CASH_PROGRAM_VERSIONS_NOT_DELETABLE_PG = (
    "CREATE TRIGGER trg_gov_cash_program_versions_no_delete BEFORE DELETE ON gov_cash_program_versions FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cash_program_no_borrable()",
    "CREATE TRIGGER trg_gov_cash_program_versions_no_truncate BEFORE TRUNCATE ON gov_cash_program_versions FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_cash_program_no_borrable()",
)

GOV_CASH_PROGRAM_HISTORY_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_cash_program_historia_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CASH_PROGRAM_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_cash_program_history_no_update BEFORE UPDATE ON gov_cash_program_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cash_program_historia_inmutable()",
    "CREATE TRIGGER trg_gov_cash_program_history_no_delete BEFORE DELETE ON gov_cash_program_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cash_program_historia_inmutable()",
    "CREATE TRIGGER trg_gov_cash_program_history_no_truncate BEFORE TRUNCATE ON gov_cash_program_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_cash_program_historia_inmutable()",
)

GOV_CASH_PROGRAM_LINES_IMMUTABLE_EXCEPT_BORRADOR_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_cash_line_solo_borrador() RETURNS TRIGGER AS $$ DECLARE version_estado TEXT; BEGIN IF TG_OP = 'DELETE' THEN SELECT estado INTO version_estado FROM gov_cash_program_versions WHERE id = OLD.version_id; ELSE SELECT estado INTO version_estado FROM gov_cash_program_versions WHERE id = NEW.version_id; END IF; IF version_estado IS DISTINCT FROM 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CASH_LINE_VERSION_NOT_BORRADOR', DETAIL = TG_OP; END IF; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_cash_program_lines_only_borrador BEFORE INSERT OR UPDATE OR DELETE ON gov_cash_program_lines FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cash_line_solo_borrador()",
)

GOV_CASH_PROGRAM_DECLARATIONS_IMMUTABLE_EXCEPT_BORRADOR_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_cash_declaracion_solo_borrador() RETURNS TRIGGER AS $$ DECLARE programa_estado TEXT; BEGIN IF TG_OP = 'DELETE' THEN SELECT p.estado INTO programa_estado FROM gov_cash_programs p WHERE p.id = OLD.program_id; ELSE SELECT p.estado INTO programa_estado FROM gov_cash_programs p WHERE p.id = NEW.program_id; END IF; IF programa_estado IS DISTINCT FROM 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CASH_DECLARATION_PROGRAM_NOT_BORRADOR', DETAIL = TG_OP; END IF; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_cash_program_declarations_only_borrador BEFORE INSERT OR UPDATE OR DELETE ON gov_cash_program_declarations FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cash_declaracion_solo_borrador()",
)


class GovernmentCashItem(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Rubro de caja de Tesorería de Gobierno (TRE-02): único por empresa y código; el tipo no cambia."""

    __tablename__ = "gov_cash_items"
    __scope__ = Scope.COMPANY

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo: Mapped[str] = mapped_column(String(11), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="ACTIVO", server_default="ACTIVO")

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_cash_items_company_id_codigo"),
        CheckConstraint(f"tipo IN ({en(TIPOS_RUBRO_CAJA)})", name="tipo"),
        CheckConstraint(f"estado IN ({en(ESTADOS_RUBRO_CAJA)})", name="estado"),
        CheckConstraint("version >= 1", name="version"),
    )


class GovernmentCashProgram(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Programa de caja de Tesorería de Gobierno (TRE-02)."""

    __tablename__ = "gov_cash_programs"
    __scope__ = Scope.COMPANY

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    ejercicio: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    mes_inicial: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    estado: Mapped[str] = mapped_column(String(11), nullable=False, default="BORRADOR", server_default="BORRADOR")
    cerrado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_cierre: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (

        Index(
            "uq_gov_cash_programs_company_ejercicio_moneda_activos",
            "company_id",
            "ejercicio",
            "moneda",
            unique=True,
            postgresql_where=text("estado <> 'DESCARTADO'"),
            sqlite_where=text("estado <> 'DESCARTADO'"),
        ),
        Index("ix_gov_cash_programs_company_estado", "company_id", "estado"),
        CheckConstraint(f"moneda IN ({en(MONEDAS_LIMITE)})", name="moneda"),
        CheckConstraint(f"estado IN ({en(ESTADOS_PROGRAMA_CAJA)})", name="estado"),
        CheckConstraint("mes_inicial BETWEEN 1 AND 12", name="mes_inicial"),
        CheckConstraint("(estado = 'CERRADO') = (cerrado_en IS NOT NULL AND motivo_cierre IS NOT NULL)", name="cierre_completo"),
        CheckConstraint("version >= 1", name="version"),
    )


class GovernmentCashProgramVersion(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Versión de un programa de caja (TRE-02)."""

    __tablename__ = "gov_cash_program_versions"
    __scope__ = Scope.COMPANY

    program_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_cash_programs.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    estado: Mapped[str] = mapped_column(String(11), nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    activada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    activada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("program_id", "numero", name="uq_gov_cash_program_versions_program_id_numero"),
        Index(
            "uq_gov_cash_program_versions_borrador_por_programa",
            "program_id",
            unique=True,
            postgresql_where=text("estado = 'BORRADOR'"),
            sqlite_where=text("estado = 'BORRADOR'"),
        ),
        Index(
            "uq_gov_cash_program_versions_vigente_por_programa",
            "program_id",
            unique=True,
            postgresql_where=text("estado = 'VIGENTE'"),
            sqlite_where=text("estado = 'VIGENTE'"),
        ),
        CheckConstraint(f"estado IN ({en(ESTADOS_VERSION_PROGRAMA_CAJA)})", name="estado"),
        CheckConstraint("numero >= 1", name="numero"),
        CheckConstraint("(estado IN ('BORRADOR', 'DESCARTADA')) = (activada_por IS NULL AND activada_en IS NULL) AND (estado IN ('VIGENTE', 'SUPERADA', 'CERRADA')) = (activada_por IS NOT NULL AND activada_en IS NOT NULL)", name="activacion_completa"),
    )


class GovernmentCashProgramDeclaration(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Declaración de disponibilidad inicial por cuenta vigente de TRE-01 (TRE-02)."""

    __tablename__ = "gov_cash_program_declarations"
    __scope__ = Scope.COMPANY

    program_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_cash_programs.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_bank_accounts.id"), nullable=False, index=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    fecha_corte: Mapped[date] = mapped_column(Date, nullable=False)
    fundamento: Mapped[str] = mapped_column(String(500), nullable=False)

    __table_args__ = (
        UniqueConstraint("program_id", "account_id", name="uq_gov_cash_program_declarations_programa_cuenta"),
        CheckConstraint("monto >= 0", name="monto"),
        CheckConstraint("length(fundamento) BETWEEN 10 AND 500", name="fundamento"),
    )


class GovernmentCashProgramLine(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Línea de un programa de caja por versión, rubro y mes (TRE-02)."""

    __tablename__ = "gov_cash_program_lines"
    __scope__ = Scope.COMPANY

    version_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_cash_program_versions.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_cash_items.id"), nullable=False, index=True)
    mes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint("version_id", "item_id", "mes", name="uq_gov_cash_program_lines_version_rubro_mes"),
        CheckConstraint("mes BETWEEN 1 AND 12", name="mes"),
        CheckConstraint("monto > 0", name="monto"),
    )


class GovernmentCashProgramHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia inmutable de las versiones de un programa de caja (TRE-02)."""

    __tablename__ = "gov_cash_program_history"
    __scope__ = Scope.COMPANY

    program_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_cash_programs.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    version_numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tipo: Mapped[str] = mapped_column(String(14), nullable=False)
    detalle: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        CheckConstraint(f"tipo IN ({en(TIPOS_HISTORIA_PROGRAMA_CAJA)})", name="tipo"),
    )


for _sentencia in GOV_CASH_PROGRAMS_NOT_DELETABLE_PG:
    event.listen(GovernmentCashProgram.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_CASH_PROGRAM_VERSIONS_NOT_DELETABLE_PG:
    event.listen(GovernmentCashProgramVersion.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_CASH_PROGRAM_HISTORY_IMMUTABLE_PG:
    event.listen(GovernmentCashProgramHistory.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_CASH_PROGRAM_LINES_IMMUTABLE_EXCEPT_BORRADOR_PG:
    event.listen(GovernmentCashProgramLine.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_CASH_PROGRAM_DECLARATIONS_IMMUTABLE_EXCEPT_BORRADOR_PG:
    event.listen(GovernmentCashProgramDeclaration.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


ESTADOS_POLITICA_CIERRE = ("BORRADOR", "VIGENTE", "RETIRADA")
ACCIONES_CIERRE = ("ORG02_CERRAR_ESTRUCTURA", "TRE02_CERRAR_PROGRAMA")
TIPOS_CONTROL_CIERRE = ("HALLAZGOS_ABIERTOS", "ACTOS_SIN_EFICACIA")
RIESGOS_MINIMOS_CIERRE = ("ALTO", "MEDIO", "BAJO")
EVENTOS_POLITICA_CIERRE = ("CREADA", "ACTUALIZADA", "CONTROL_ANADIDO", "CONTROL_RETIRADO", "ACTIVADA", "RETIRADA")


GOV_CLOSURE_POLICIES_NOT_EDITABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_cierre_politica_no_editable() RETURNS TRIGGER AS $$ "
    "BEGIN "
    "IF OLD.estado IN ('VIGENTE', 'RETIRADA') THEN "
    "IF NEW.estado <> 'RETIRADA' OR OLD.estado = 'RETIRADA' OR "
    "NEW.nombre IS DISTINCT FROM OLD.nombre OR "
    "NEW.fundamento IS DISTINCT FROM OLD.fundamento OR "
    "NEW.accion_cierre IS DISTINCT FROM OLD.accion_cierre OR "
    "NEW.vigente_desde IS DISTINCT FROM OLD.vigente_desde OR "
    "NEW.vigente_hasta IS DISTINCT FROM OLD.vigente_hasta THEN "
    "RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CLOSURE_POLICY_NOT_EDITABLE', DETAIL = TG_OP; "
    "END IF; "
    "END IF; "
    "RETURN NEW; "
    "END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_closure_policies_no_editar BEFORE UPDATE ON gov_closure_policies FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cierre_politica_no_editable()",
)

GOV_CLOSURE_POLICIES_NOT_DELETABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_cierre_politica_no_borrable() RETURNS TRIGGER AS $$ "
    "BEGIN "
    "IF OLD.estado <> 'BORRADOR' THEN "
    "RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CLOSURE_POLICY_NOT_DELETABLE', DETAIL = TG_OP; "
    "END IF; "
    "RETURN OLD; "
    "END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_closure_policies_no_delete BEFORE DELETE ON gov_closure_policies FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cierre_politica_no_borrable()",
    "CREATE TRIGGER trg_gov_closure_policies_no_truncate BEFORE TRUNCATE ON gov_closure_policies FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_cierre_politica_no_borrable()",
)

GOV_CLOSURE_CONTROLS_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_cierre_control_inmutable() RETURNS TRIGGER AS $$ "
    "DECLARE politica_estado TEXT; "
    "BEGIN "
    "IF TG_OP = 'UPDATE' OR TG_OP = 'DELETE' THEN "
    "SELECT estado INTO politica_estado FROM gov_closure_policies WHERE id = OLD.policy_id; "
    "ELSE "
    "SELECT estado INTO politica_estado FROM gov_closure_policies WHERE id = NEW.policy_id; "
    "END IF; "
    "IF politica_estado IS DISTINCT FROM 'BORRADOR' THEN "
    "RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CLOSURE_CONTROL_IMMUTABLE', DETAIL = TG_OP; "
    "END IF; "
    "IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; "
    "RETURN NEW; "
    "END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_closure_controls_no_insert BEFORE INSERT ON gov_closure_controls FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cierre_control_inmutable()",
    "CREATE TRIGGER trg_gov_closure_controls_no_update BEFORE UPDATE ON gov_closure_controls FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cierre_control_inmutable()",
    "CREATE TRIGGER trg_gov_closure_controls_no_delete BEFORE DELETE ON gov_closure_controls FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cierre_control_inmutable()",
)

GOV_CLOSURE_POLICY_HISTORY_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_cierre_historia_inmutable() RETURNS TRIGGER AS $$ "
    "BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CLOSURE_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_closure_policy_history_no_update BEFORE UPDATE ON gov_closure_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cierre_historia_inmutable()",
    "CREATE TRIGGER trg_gov_closure_policy_history_no_delete BEFORE DELETE ON gov_closure_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cierre_historia_inmutable()",
    "CREATE TRIGGER trg_gov_closure_policy_history_no_truncate BEFORE TRUNCATE ON gov_closure_policy_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_cierre_historia_inmutable()",
)


class GovernmentClosurePolicy(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Política de controles de cierre de Control Interno (CTL-10, GOV-CTL-012)."""

    __tablename__ = "gov_closure_policies"
    __scope__ = Scope.COMPANY

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(10), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    accion_cierre: Mapped[str] = mapped_column(String(32), nullable=False)
    fundamento: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="BORRADOR", server_default="BORRADOR")
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    activada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    activada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retirada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    retirada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_retiro: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_closure_policies_company_id_codigo"),
        CheckConstraint(f"estado IN ({en(ESTADOS_POLITICA_CIERRE)})", name="estado"),
        CheckConstraint(f"accion_cierre IN ({en(ACCIONES_CIERRE)})", name="accion_cierre"),
        CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        CheckConstraint(
            "(estado <> 'VIGENTE' OR (activada_por IS NOT NULL AND activada_en IS NOT NULL))",
            name="vigente_exige_activacion",
        ),
        CheckConstraint(
            "(estado <> 'RETIRADA' OR "
            "(retirada_por IS NOT NULL AND retirada_en IS NOT NULL AND motivo_retiro IS NOT NULL))",
            name="retirada_exige_retiro",
        ),
        Index(
            "uq_gov_closure_policies_company_accion_vigente",
            "company_id",
            "accion_cierre",
            unique=True,
            postgresql_where=text("estado = 'VIGENTE'"),
            sqlite_where=text("estado = 'VIGENTE'"),
        ),
    )


class GovernmentClosureControl(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Control material de cierre vinculado a una política (CTL-10, GOV-CTL-012)."""

    __tablename__ = "gov_closure_controls"
    __scope__ = Scope.COMPANY

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_closure_policies.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(24), nullable=False)
    riesgo_minimo: Mapped[str | None] = mapped_column(String(6), nullable=True)
    materialidad: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("policy_id", "tipo", name="uq_gov_closure_controls_policy_id_tipo"),
        CheckConstraint(f"tipo IN ({en(TIPOS_CONTROL_CIERRE)})", name="tipo"),
        CheckConstraint(
            "(tipo = 'ACTOS_SIN_EFICACIA' OR (riesgo_minimo IS NOT NULL "
            "AND riesgo_minimo IN ('ALTO', 'MEDIO', 'BAJO')))",
            name="riesgo_minimo_hallazgos",
        ),
        CheckConstraint(
            "(tipo <> 'ACTOS_SIN_EFICACIA' OR riesgo_minimo IS NULL)",
            name="riesgo_minimo_nulo_actos",
        ),
    )


class GovernmentClosurePolicyHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia inmutable de una política de controles de cierre (CTL-10, GOV-CTL-012)."""

    __tablename__ = "gov_closure_policy_history"
    __scope__ = Scope.COMPANY

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_closure_policies.id"), nullable=False, index=True)
    evento: Mapped[str] = mapped_column(String(24), nullable=False)
    detalle: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    usuario: Mapped[str | None] = mapped_column(String(36), nullable=True)
    instante: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())

    __table_args__ = (
        CheckConstraint(f"evento IN ({en(EVENTOS_POLITICA_CIERRE)})", name="evento"),
    )


for _sentencia in GOV_CLOSURE_POLICIES_NOT_EDITABLE_PG:
    event.listen(GovernmentClosurePolicy.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_CLOSURE_POLICIES_NOT_DELETABLE_PG:
    event.listen(GovernmentClosurePolicy.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_CLOSURE_CONTROLS_IMMUTABLE_PG:
    event.listen(GovernmentClosureControl.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_CLOSURE_POLICY_HISTORY_IMMUTABLE_PG:
    event.listen(GovernmentClosurePolicyHistory.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


ESTADOS_FUNCIONARIO = ("ACTIVO", "INACTIVO")
TIPOS_DOCUMENTO_FUNCIONARIO = ("V", "E", "P")
TIPOS_HISTORIA_FUNCIONARIO = ("CREADO", "EDITADO")
FIGURAS_ASIGNACION = ("TITULAR", "ENCARGADURIA", "SUPLENCIA", "COMISION_SERVICIO", "DELEGACION_ATRIBUCIONES", "DELEGACION_FIRMA")
GRUPOS_ASIGNACION = ("TITULARIDAD", "TEMPORAL", "DELEGACION")
ESTADOS_ASIGNACION = ("BORRADOR", "ACTIVO", "REVOCADO", "FINALIZADO", "DESCARTADO")
TIPOS_HISTORIA_ASIGNACION = ("CREADA", "EDITADA", "ACTIVADA", "DESCARTADA", "REVOCADA", "FINALIZADA", "AVOCADA")
ESTADOS_POLITICA_ASIGNACION = ("BORRADOR", "VIGENTE", "CERRADA")
TIPOS_EMISOR_ASIGNACION = ("CUALQUIERA", "CARGO", "COMPETENCIA")
AMBITOS_AUTORIZACION_ASIGNACION = ("TODAS", "MAXIMA_AUTORIDAD")
ETAPAS_DOCUMENTO_ASIGNACION = ("ACTIVACION", "REVOCACION")
EVENTOS_POLITICA_ASIGNACION = ("CREADA", "EDITADA", "ACTIVADA", "CERRADA", "SUSTITUIDA", "NUEVA_VERSION")


ESTADOS_VINCULO = ("BORRADOR", "ACTIVO", "CERRADO", "REVOCADO", "DESCARTADO")
TIPOS_HISTORIA_VINCULO = ("CREADO", "EDITADO", "ACTIVADO", "DESCARTADO", "CERRADO", "REVOCADO")

ESTADOS_COMISION = ("BORRADOR", "VIGENTE", "CERRADA", "DESCARTADA")
TIPOS_COMISION = ("PERMANENTE", "TEMPORAL")
FUNCIONES_MIEMBRO_COMISION = ("MIEMBRO", "SECRETARIO")
AREAS_COMISION = ("JURIDICA", "TECNICA", "ECONOMICO_FINANCIERA")
CONDICIONES_MIEMBRO_COMISION = ("PRINCIPAL", "SUPLENTE")
CAUSAS_FIN_MIEMBRO_COMISION = ("MUERTE_INCAPACIDAD", "DESPIDO_DESTITUCION", "RETIRO_RENUNCIA_REMOCION", "FIN_DESIGNACION")
CAUSALES_INHIBICION = ("INTERES", "AMISTAD_ENEMISTAD", "INTERVENCION_PREVIA", "SERVICIO_SUBORDINACION")
ESTADOS_INHIBICION = ("DECLARADA", "ACEPTADA", "RECHAZADA")
TIPOS_HISTORIA_COMISION = ("CREADA", "EDITADA", "DESCARTADA", "ACTIVADA", "CERRADA", "SNC_NOTIFICADA", "MIEMBRO_ANADIDO", "MIEMBRO_RETIRADO", "MIEMBRO_TERMINADO", "INHIBICION_DECLARADA", "INHIBICION_RESUELTA")
# Política de comisión (PROC-07/PROC-08-COMMISSION-POLICY): vocabulario de plataforma; los valores los elige el ente.
ESTADOS_POLITICA_COMISION = ("BORRADOR", "VIGENTE", "CERRADA")
TIPOS_COMISION_POLITICA = ("PERMANENTE", "TEMPORAL", "CUALQUIERA")
BASES_NORMATIVAS_COMISION = ("LCP_ART14", "NINGUNA")
TIPOS_MAYORIA = ("ABSOLUTE_COUNT", "SIMPLE_MAJORITY", "QUALIFIED_MAJORITY", "UNANIMITY")
BASES_DECISION_COMISION = ("MIEMBROS_CON_VOTO", "ASISTENTES_CON_VOTO")
FUNCIONES_REQUISITO_COMISION = ("MIEMBRO", "SECRETARIO")
CONDICIONES_REQUISITO_COMISION = ("PRINCIPAL", "SUPLENTE", "CUALQUIERA")
TIPOS_REQUISITO_COMISION = ("AREA", "CARGO", "UNIDAD", "COMPETENCIA", "FUNCIONARIO")
ETAPAS_DOCUMENTO_COMISION = ("CONSTITUCION", "APERTURA", "RECOMENDACION")
EVENTOS_POLITICA_COMISION = ("CREADA", "EDITADA", "ACTIVADA", "CERRADA", "SUSTITUIDA", "NUEVA_VERSION")
MODOS_ACTUACION_COMISION = ("COMISION", "UNIDAD_CONTRATANTE")
TIPOS_CONTRATACION = ("BIENES", "SERVICIOS", "OBRAS")
MODALIDADES_DECLARADAS = ("CONCURSO_ABIERTO", "CONCURSO_CERRADO", "CONSULTA_PRECIOS", "CONTRATACION_DIRECTA")
ESTADOS_EXPEDIENTE = ("ABIERTO", "CERRADO", "DESCARTADO")
ROLES_RESPONSABLE_EXPEDIENTE = ("RESPONSABLE", "REQUIRENTE", "SUSTANCIACION", "CUSTODIA")
ESTADOS_HITO = ("PREVISTO", "CUMPLIDO", "NO_APLICA")
CLASES_FOLIO = ("SOLICITUD", "AUTORIZACION_INICIO", "PLIEGO", "ACTOS_MOTIVADOS", "LLAMADO_INVITACION", "MODIFICACIONES_PLIEGO", "ACTA_RECEPCION", "OFERTAS", "INFORME_RECOMENDACION", "ADJUDICACION", "NOTIFICACION", "CONTRATO", "OTRO_SELECCION", "GARANTIAS", "ACTAS_EJECUCION", "MODIFICACION_CONTRATO", "FORMULARIOS_PAGO", "APROBACIONES_PAGO", "PAGOS", "FINIQUITO", "LIBERACION_GARANTIAS", "EVALUACION_CONTRATISTA", "OTRO_ADMINISTRACION")
CLASES_EVENTO_EXPEDIENTE = ("APERTURA", "DATOS", "RESPONSABLE", "COMISION", "ACTUACION", "DECISION", "DOCUMENTO", "ACTO", "HITO", "CIERRE", "DESCARTE", "OFERTA", "APERTURA_OFERTA", "EVALUACION", "RECOMENDACION", "RECHAZO_OFERTA", "ADJUDICACION", "DESIERTA", "TERMINACION", "NULIDAD", "GARANTIA", "CONTRATO")

ESTADOS_RECOMENDACION = ("EMITIDA", "SUSTITUIDA")
RESULTADOS_RECOMENDACION = ("ADJUDICAR", "DECLARAR_DESIERTA", "TERMINAR")
CAUSALES_DESIERTA = ("LCP113_1", "LCP113_2", "LCP113_3", "LCP113_4", "LCP113_5")  # LCP art. 113
CAUSALES_RECHAZO = ("LCP76_1", "LCP76_2", "LCP76_3", "LCP76_4", "LCP76_5", "LCP76_6", "LCP76_7", "LCP76_8", "RLCP102_1", "RLCP102_2", "RLCP102_3", "RLCP102_4", "RLCP102_5", "RLCP102_6")  # LCP art. 76 num. 1-8; RLCP art. 102 num. 1-6
RESULTADOS_DECISION = ("ADJUDICADA", "DESIERTA", "TERMINADA", "NULIDAD")  # LCP arts. 109, 113, 107, 112
ESTADOS_DECISION = ("VIGENTE", "ANULADA", "SUSTITUIDA")
CAUSALES_NULIDAD = ("INFORMACION_FALSA", "VIOLACION_LEGAL")  # LCP art. 112
CATEGORIAS_SEPARACION = ("OPERATIVO", "APROBADOR", "CONTROL_INTERNO", "AUDITORIA", "ADMINISTRACION_TECNICA")
ESTADOS_CATEGORIA_ROL = ("ACTIVA", "RETIRADA")
TIPOS_HISTORIA_CATEGORIA = ("AGREGADA", "RETIRADA")
TIPOS_HISTORIA_POLITICA = ("CAMBIADA",)


class GovernmentOfficial(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Identidad institucional de la persona que ejerce un cargo (OD-ORG04-02); no es usuario ni ficha de empleado."""
    __tablename__ = "gov_officials"
    __scope__ = Scope.COMPANY

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_officials_company_id_codigo"),
        UniqueConstraint("company_id", "tipo_documento", "numero_documento", name="uq_gov_officials_documento"),
        CheckConstraint(f"estado IN ({en(ESTADOS_FUNCIONARIO)})", name="estado"),
        CheckConstraint(f"tipo_documento IN ({en(TIPOS_DOCUMENTO_FUNCIONARIO)})", name="tipo_documento"),
        CheckConstraint("version >= 1", name="version"),
    )

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo_documento: Mapped[str] = mapped_column(String(1), nullable=False)
    numero_documento: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVO", server_default="ACTIVO")


class GovernmentOfficialHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia inmutable de un funcionario (ORG-04)."""
    __tablename__ = "gov_official_history"
    __scope__ = Scope.COMPANY

    __table_args__ = (
        CheckConstraint(f"tipo IN ({en(TIPOS_HISTORIA_FUNCIONARIO)})", name="tipo"),
    )

    official_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    detalle: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class GovernmentAssignment(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Quién ejerce un cargo, bajo qué figura, por qué acto y durante qué vigencia (ORG-04, GOV-ORG-004)."""
    __tablename__ = "gov_assignments"
    __scope__ = Scope.COMPANY

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_assignments_company_id_codigo"),
        CheckConstraint(f"figura IN ({en(FIGURAS_ASIGNACION)})", name="figura"),
        CheckConstraint(f"grupo IN ({en(GRUPOS_ASIGNACION)})", name="grupo"),
        CheckConstraint(f"status IN ({en(ESTADOS_ASIGNACION)})", name="status"),
        CheckConstraint("version >= 1", name="version"),
        CheckConstraint(
            "(figura = 'TITULAR' AND grupo = 'TITULARIDAD') OR "
            "(figura IN ('ENCARGADURIA','SUPLENCIA','COMISION_SERVICIO') AND grupo = 'TEMPORAL') OR "
            "(figura IN ('DELEGACION_ATRIBUCIONES','DELEGACION_FIRMA') AND grupo = 'DELEGACION')",
            name="grupo_de_figura",
        ),
        CheckConstraint("hasta IS NULL OR hasta >= desde", name="vigencia"),
        CheckConstraint("fin_efectivo IS NULL OR fin_efectivo >= desde", name="fin_tras_inicio"),
        CheckConstraint("figura NOT IN ('SUPLENCIA','COMISION_SERVICIO') OR hasta IS NOT NULL", name="temporal_con_fin"),
        CheckConstraint("grupo = 'TITULARIDAD' OR figura = 'ENCARGADURIA' OR cargo_origen_id IS NOT NULL", name="origen_requerido"),
        CheckConstraint("grupo <> 'DELEGACION' OR (rendicion IS NOT NULL AND declara_delegable = true)", name="delegacion_completa"),
        CheckConstraint("status NOT IN ('REVOCADO') OR (revocation_act_id IS NOT NULL AND fin_efectivo IS NOT NULL)", name="revocada_con_acto"),
        CheckConstraint("status <> 'FINALIZADO' OR (fin_efectivo IS NOT NULL AND motivo_fin IS NOT NULL)", name="finalizada_con_motivo"),
        CheckConstraint("status IN ('BORRADOR','DESCARTADO') OR activated_at IS NOT NULL", name="activada_fechada"),
    )

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    official_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=False, index=True)
    position_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=False, index=True)
    figura: Mapped[str] = mapped_column(String(24), nullable=False)
    grupo: Mapped[str] = mapped_column(String(16), nullable=False)
    cargo_origen_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=True)
    act_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=False, index=True)
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    fin_efectivo: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="BORRADOR", server_default="BORRADOR")
    fundamento: Mapped[str] = mapped_column(String(500), nullable=False)
    rendicion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    maxima_autoridad: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    autorizacion_especial: Mapped[str | None] = mapped_column(String(200), nullable=True)
    declara_delegable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    revocation_act_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=True)
    motivo_fin: Mapped[str | None] = mapped_column(String(500), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    policy_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_assignment_policies.id"), nullable=True, index=True)
    policy_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    regla: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class GovernmentAssignmentCompetency(UUIDMixin, TimestampMixin, Base):
    """Competencia delegada con copia del límite del cargo."""
    __tablename__ = "gov_assignment_competencies"
    __scope__ = Scope.COMPANY

    __table_args__ = (
        UniqueConstraint("assignment_id", "action", "subject", name="uq_gov_assignment_competencies_assignment_id_action_subject"),
        CheckConstraint(f"action IN ({en(ACCIONES_COMPETENCIA)})", name="action"),
        CheckConstraint(f"subject IN ({en(MATERIAS_COMPETENCIA)})", name="subject"),
        CheckConstraint(f"limit_type IN ({en(TIPOS_DE_LIMITE)})", name="limit_type"),
    )

    assignment_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_assignments.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    subject: Mapped[str] = mapped_column(String(16), nullable=False)
    limit_type: Mapped[str] = mapped_column(String(16), nullable=False)
    limit_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    limit_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)


class GovernmentAssignmentHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia inmutable de una asignación de cargo (ORG-04)."""
    __tablename__ = "gov_assignment_history"
    __scope__ = Scope.COMPANY

    __table_args__ = (
        CheckConstraint(f"tipo IN ({en(TIPOS_HISTORIA_ASIGNACION)})", name="tipo"),
    )

    assignment_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_assignments.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    detalle: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class GovernmentAssignmentPolicy(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Política de asignación del ente por figura (ORG-04-AUTHORITY-ASSIGNMENT-POLICY).

    INSTITUTIONAL_POLICY con versiones. Los pisos legales (LOAP, LEFP y LOPPM según el nivel) se aplican siempre
    y la política solo los endurece (OD-AP-02).
    """

    __tablename__ = "gov_assignment_policies"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    numero_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    figura: Mapped[str] = mapped_column(String(24), nullable=False)
    fundamento: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    act_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=True)
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="BORRADOR", server_default="BORRADOR")
    exige_fin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    max_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    acto_medio: Mapped[str | None] = mapped_column(String(16), nullable=True)
    emisor_tipo: Mapped[str] = mapped_column(String(12), nullable=False, default="CUALQUIERA", server_default="CUALQUIERA")
    emisor_position_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=True)
    emisor_competencia_accion: Mapped[str | None] = mapped_column(String(16), nullable=True)
    emisor_competencia_materia: Mapped[str | None] = mapped_column(String(16), nullable=True)
    autorizacion_requerida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    autorizacion_etiqueta: Mapped[str | None] = mapped_column(String(120), nullable=True)
    autorizacion_ambito: Mapped[str | None] = mapped_column(String(16), nullable=True)
    autorizacion_mas_de_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prohibe_avocacion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    version_anterior_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_assignment_policies.id"), nullable=True)
    activada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    activada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cerrada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_cierre: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", "numero_version", name="uq_gov_assignment_policies_version"),
        Index("uq_gov_assignment_policies_vigente", "company_id", "codigo", unique=True, postgresql_where=text("estado = 'VIGENTE'"), sqlite_where=text("estado = 'VIGENTE'")),
        CheckConstraint(f"estado IN ({en(ESTADOS_POLITICA_ASIGNACION)})", name="estado"),
        CheckConstraint(f"figura IN ({en(FIGURAS_ASIGNACION)})", name="figura"),
        CheckConstraint(f"acto_medio IS NULL OR acto_medio IN ({en(MEDIOS_EFICACIA)})", name="acto_medio"),
        CheckConstraint(f"emisor_tipo IN ({en(TIPOS_EMISOR_ASIGNACION)})", name="emisor_tipo"),
        CheckConstraint(f"emisor_competencia_accion IS NULL OR emisor_competencia_accion IN ({en(ACCIONES_COMPETENCIA)})", name="emisor_accion"),
        CheckConstraint(f"emisor_competencia_materia IS NULL OR emisor_competencia_materia IN ({en(MATERIAS_COMPETENCIA)})", name="emisor_materia"),
        CheckConstraint(
            "(emisor_tipo = 'CUALQUIERA' AND emisor_position_id IS NULL AND emisor_competencia_accion IS NULL AND emisor_competencia_materia IS NULL) OR "
            "(emisor_tipo = 'CARGO' AND emisor_position_id IS NOT NULL AND emisor_competencia_accion IS NULL AND emisor_competencia_materia IS NULL) OR "
            "(emisor_tipo = 'COMPETENCIA' AND emisor_position_id IS NULL AND emisor_competencia_accion IS NOT NULL AND emisor_competencia_materia IS NOT NULL)",
            name="emisor",
        ),
        CheckConstraint(f"autorizacion_ambito IS NULL OR autorizacion_ambito IN ({en(AMBITOS_AUTORIZACION_ASIGNACION)})", name="autorizacion_ambito"),
        CheckConstraint("autorizacion_requerida = false OR (autorizacion_etiqueta IS NOT NULL AND autorizacion_ambito IS NOT NULL)", name="autorizacion"),
        CheckConstraint("autorizacion_mas_de_dias IS NULL OR autorizacion_mas_de_dias >= 0", name="autorizacion_dias"),
        CheckConstraint("max_dias IS NULL OR max_dias >= 1", name="max_dias"),
        CheckConstraint("numero_version >= 1", name="numero_version"),
        CheckConstraint("version >= 1", name="version"),
        CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        CheckConstraint("estado = 'BORRADOR' OR fundamento IS NOT NULL", name="fundamento"),
        CheckConstraint("estado <> 'CERRADA' OR (cerrada_en IS NOT NULL AND motivo_cierre IS NOT NULL)", name="cerrada"),
    )


class GovernmentAssignmentPolicyCompetency(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Competencia que la política permite transferir (lista cerrada; ORG-03 sigue siendo la autoridad)."""

    __tablename__ = "gov_assignment_policy_competencies"
    __scope__ = Scope.COMPANY

    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_assignment_policies.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    accion: Mapped[str] = mapped_column(String(16), nullable=False)
    materia: Mapped[str] = mapped_column(String(16), nullable=False)

    __table_args__ = (
        UniqueConstraint("policy_id", "accion", "materia", name="uq_gov_assignment_policy_competencies_par"),
        CheckConstraint(f"accion IN ({en(ACCIONES_COMPETENCIA)})", name="accion"),
        CheckConstraint(f"materia IN ({en(MATERIAS_COMPETENCIA)})", name="materia"),
    )


class GovernmentAssignmentPolicyDocument(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Documento que la política exige al activar o al revocar una asignación."""

    __tablename__ = "gov_assignment_policy_documents"
    __scope__ = Scope.COMPANY

    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_assignment_policies.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    document_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_types.id"), nullable=False)
    etapa: Mapped[str] = mapped_column(String(12), nullable=False)
    obligatorio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    __table_args__ = (
        UniqueConstraint("policy_id", "document_type_id", "etapa", name="uq_gov_assignment_policy_documents_tipo"),
        CheckConstraint(f"etapa IN ({en(ETAPAS_DOCUMENTO_ASIGNACION)})", name="etapa"),
    )


class GovernmentAssignmentPolicyHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia inmutable de una política de asignación, con instantánea por evento."""

    __tablename__ = "gov_assignment_policy_history"
    __scope__ = Scope.COMPANY

    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_assignment_policies.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    evento: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    instantanea: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    __table_args__ = (
        CheckConstraint(f"evento IN ({en(EVENTOS_POLITICA_ASIGNACION)})", name="evento"),
    )


GOV_ASSIGNMENT_POLICY_HISTORY_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_politica_asignacion_historia_inmutable() RETURNS TRIGGER AS $$ "
    "BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_ASSIGNMENT_POLICY_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_assignment_policy_history_no_update BEFORE UPDATE ON gov_assignment_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_politica_asignacion_historia_inmutable()",
    "CREATE TRIGGER trg_gov_assignment_policy_history_no_delete BEFORE DELETE ON gov_assignment_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_politica_asignacion_historia_inmutable()",
    "CREATE TRIGGER trg_gov_assignment_policy_history_no_truncate BEFORE TRUNCATE ON gov_assignment_policy_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_politica_asignacion_historia_inmutable()",
)

for _sentencia in GOV_ASSIGNMENT_POLICY_HISTORY_IMMUTABLE_PG:
    event.listen(GovernmentAssignmentPolicyHistory.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


class GovernmentProcurementCommittee(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    __tablename__ = "gov_procurement_committees"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    objeto: Mapped[str | None] = mapped_column(String(500), nullable=True)
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    act_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="BORRADOR", server_default="BORRADOR")
    regla_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    snc_notificada_en: Mapped[date | None] = mapped_column(Date, nullable=True)
    snc_referencia: Mapped[str | None] = mapped_column(String(200), nullable=True)
    motivo_cierre: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fin_efectivo: Mapped[date | None] = mapped_column(Date, nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Política de la que nace y regla congelada al activarse (FR-CP-06). Sin política = regla histórica (OD-CP-04).
    policy_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_commission_policies.id"), nullable=True, index=True)
    policy_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    regla: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_committees_codigo"),
        CheckConstraint(f"status IN ({en(ESTADOS_COMISION)})", name="status"),
        CheckConstraint(f"tipo IN ({en(TIPOS_COMISION)})", name="tipo"),
        CheckConstraint("version >= 1", name="version"),
        CheckConstraint("hasta IS NULL OR hasta >= desde", name="vigencia"),
        CheckConstraint("tipo <> 'TEMPORAL' OR status IN ('BORRADOR','DESCARTADA') OR hasta IS NOT NULL", name="temporal_con_fin"),
        CheckConstraint("status IN ('BORRADOR','DESCARTADA') OR (act_id IS NOT NULL AND activated_at IS NOT NULL AND regla_version IS NOT NULL)", name="vigente_con_acto"),
        CheckConstraint("status <> 'CERRADA' OR (fin_efectivo IS NOT NULL AND motivo_cierre IS NOT NULL)", name="cerrada_con_fin"),
    )


class GovernmentProcurementCommitteeMember(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_committee_members"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    committee_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_committees.id"), nullable=False, index=True)
    official_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=False, index=True)
    funcion: Mapped[str] = mapped_column(String(16), nullable=False)
    area: Mapped[str | None] = mapped_column(String(24), nullable=True)
    condicion: Mapped[str] = mapped_column(String(16), nullable=False)
    suplente_de_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_committee_members.id"), nullable=True)
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    act_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=True)
    certificacion_snc: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fin_efectivo: Mapped[date | None] = mapped_column(Date, nullable=True)
    causa_fin: Mapped[str | None] = mapped_column(String(32), nullable=True)
    motivo_fin: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    preside: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))

    __table_args__ = (
        CheckConstraint("preside = false OR (funcion = 'MIEMBRO' AND condicion = 'PRINCIPAL')", name="preside"),
        Index("uq_gov_committee_presidente", "committee_id", unique=True, postgresql_where=text("fin_efectivo IS NULL AND preside"), sqlite_where=text("fin_efectivo IS NULL AND preside")),
        CheckConstraint(f"funcion IN ({en(FUNCIONES_MIEMBRO_COMISION)})", name="funcion"),
        CheckConstraint(f"condicion IN ({en(CONDICIONES_MIEMBRO_COMISION)})", name="condicion"),
        CheckConstraint(f"causa_fin IS NULL OR causa_fin IN ({en(CAUSAS_FIN_MIEMBRO_COMISION)})", name="causa_fin"),
        CheckConstraint("(funcion = 'SECRETARIO' AND area IS NULL) OR (funcion = 'MIEMBRO' AND area IN ('JURIDICA', 'TECNICA', 'ECONOMICO_FINANCIERA'))", name="area"),
        CheckConstraint("condicion = 'PRINCIPAL' OR funcion = 'SECRETARIO' OR suplente_de_id IS NOT NULL", name="suplente_de"),
        CheckConstraint("fin_efectivo IS NULL OR fin_efectivo >= desde", name="fin_tras_inicio"),
        CheckConstraint("(fin_efectivo IS NULL) = (causa_fin IS NULL)", name="fin_con_causa"),
        Index("uq_gov_committee_member_official", "committee_id", "official_id", unique=True, postgresql_where=text("fin_efectivo IS NULL"), sqlite_where=text("fin_efectivo IS NULL")),
        Index("uq_gov_committee_member_suplente", "suplente_de_id", unique=True, postgresql_where=text("fin_efectivo IS NULL AND suplente_de_id IS NOT NULL"), sqlite_where=text("fin_efectivo IS NULL AND suplente_de_id IS NOT NULL")),
        Index("uq_gov_committee_secretario", "committee_id", "condicion", unique=True, postgresql_where=text("fin_efectivo IS NULL AND funcion = 'SECRETARIO'"), sqlite_where=text("fin_efectivo IS NULL AND funcion = 'SECRETARIO'")),
    )


class GovernmentProcurementCommitteeConflict(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    __tablename__ = "gov_procurement_committee_conflicts"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    committee_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_committees.id"), nullable=False, index=True)
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_committee_members.id"), nullable=False, index=True)
    # Expediente en que se inhibe (FR-CP-07); aceptada, excluye al miembro de ese procedimiento.
    file_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=True, index=True)
    asunto: Mapped[str] = mapped_column(String(300), nullable=False)
    causal: Mapped[str] = mapped_column(String(32), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(1000), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    soporte: Mapped[str | None] = mapped_column(String(200), nullable=True)
    estado: Mapped[str] = mapped_column(String(16), nullable=False, default="DECLARADA", server_default="DECLARADA")
    motivo_resolucion: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    resuelta_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    resuelta_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(f"causal IN ({en(CAUSALES_INHIBICION)})", name="causal"),
        CheckConstraint(f"estado IN ({en(ESTADOS_INHIBICION)})", name="estado"),
        CheckConstraint("version >= 1", name="version"),
        CheckConstraint("estado = 'DECLARADA' OR (resuelta_por IS NOT NULL AND resuelta_en IS NOT NULL AND motivo_resolucion IS NOT NULL)", name="resuelta"),
    )


class GovernmentProcurementCommitteeHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_committee_history"
    __scope__ = Scope.COMPANY

    committee_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_committees.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(24), nullable=False)
    detalle: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        CheckConstraint(f"tipo IN ({en(TIPOS_HISTORIA_COMISION)})", name="tipo"),
    )


GOV_COMMITTEE_HISTORY_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_comision_historia_inmutable() RETURNS TRIGGER AS $$ "
    "BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_COMMITTEE_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_committee_history_no_update BEFORE UPDATE ON gov_procurement_committee_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_comision_historia_inmutable()",
    "CREATE TRIGGER trg_gov_committee_history_no_delete BEFORE DELETE ON gov_procurement_committee_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_comision_historia_inmutable()",
    "CREATE TRIGGER trg_gov_committee_history_no_truncate BEFORE TRUNCATE ON gov_procurement_committee_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_comision_historia_inmutable()",
)

for _sentencia in GOV_COMMITTEE_HISTORY_IMMUTABLE_PG:
    event.listen(GovernmentProcurementCommitteeHistory.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


class GovernmentCommissionPolicy(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Política de comisión del ente (PROC-07/PROC-08-COMMISSION-POLICY): composición, quórum, decisión y documentos.

    INSTITUTIONAL_POLICY con versiones; la base `LCP_ART14` añade el piso legal (LEGAL_MANDATORY) que no se rebaja.
    """

    __tablename__ = "gov_commission_policies"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    numero_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo_comision: Mapped[str] = mapped_column(String(16), nullable=False, default="CUALQUIERA", server_default="CUALQUIERA")
    aplica_apertura: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    aplica_recomendacion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    base_normativa: Mapped[str] = mapped_column(String(16), nullable=False, default="LCP_ART14", server_default="LCP_ART14")
    fundamento: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    act_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=True)
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="BORRADOR", server_default="BORRADOR")
    min_principales: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    max_principales: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exige_impar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    suplente_por_principal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    exige_secretario: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    exige_suplente_secretario: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    exige_presidente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    quorum_tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    quorum_cantidad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quorum_numerador: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quorum_denominador: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decision_tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    decision_cantidad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decision_numerador: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decision_denominador: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decision_base: Mapped[str] = mapped_column(String(20), nullable=False, default="MIEMBROS_CON_VOTO", server_default="MIEMBROS_CON_VOTO")
    presidente_vota: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    presidente_dirimente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    acto_requerido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    acto_medio: Mapped[str | None] = mapped_column(String(16), nullable=True)
    version_anterior_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_commission_policies.id"), nullable=True)
    activada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    activada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cerrada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_cierre: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", "numero_version", name="uq_gov_commission_policies_version"),
        Index("uq_gov_commission_policies_vigente", "company_id", "codigo", unique=True, postgresql_where=text("estado = 'VIGENTE'"), sqlite_where=text("estado = 'VIGENTE'")),
        CheckConstraint(f"estado IN ({en(ESTADOS_POLITICA_COMISION)})", name="estado"),
        CheckConstraint(f"tipo_comision IN ({en(TIPOS_COMISION_POLITICA)})", name="tipo_comision"),
        CheckConstraint(f"base_normativa IN ({en(BASES_NORMATIVAS_COMISION)})", name="base_normativa"),
        CheckConstraint(f"quorum_tipo IN ({en(TIPOS_MAYORIA)})", name="quorum_tipo"),
        CheckConstraint(f"decision_tipo IN ({en(TIPOS_MAYORIA)})", name="decision_tipo"),
        CheckConstraint(f"decision_base IN ({en(BASES_DECISION_COMISION)})", name="decision_base"),
        CheckConstraint(f"acto_medio IS NULL OR acto_medio IN ({en(MEDIOS_EFICACIA)})", name="acto_medio"),
        CheckConstraint("numero_version >= 1", name="numero_version"),
        CheckConstraint("version >= 1", name="version"),
        CheckConstraint("aplica_apertura OR aplica_recomendacion", name="aplica"),
        CheckConstraint("min_principales >= 1", name="min_principales"),
        CheckConstraint("max_principales IS NULL OR max_principales >= min_principales", name="max_principales"),
        CheckConstraint("quorum_tipo <> 'ABSOLUTE_COUNT' OR quorum_cantidad >= 1", name="quorum_cantidad"),
        CheckConstraint("quorum_tipo <> 'QUALIFIED_MAJORITY' OR (quorum_numerador >= 1 AND quorum_denominador >= 1 AND 2 * quorum_numerador > quorum_denominador AND quorum_numerador <= quorum_denominador)", name="quorum_fraccion"),
        CheckConstraint("decision_tipo <> 'ABSOLUTE_COUNT' OR decision_cantidad >= 1", name="decision_cantidad"),
        CheckConstraint("decision_tipo <> 'QUALIFIED_MAJORITY' OR (decision_numerador >= 1 AND decision_denominador >= 1 AND 2 * decision_numerador > decision_denominador AND decision_numerador <= decision_denominador)", name="decision_fraccion"),
        CheckConstraint("presidente_dirimente = false OR exige_presidente", name="dirimente"),
        CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        CheckConstraint("estado = 'BORRADOR' OR fundamento IS NOT NULL", name="fundamento"),
        CheckConstraint("estado <> 'CERRADA' OR (cerrada_en IS NOT NULL AND motivo_cierre IS NOT NULL)", name="cerrada"),
    )


class GovernmentCommissionPolicyRequirement(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Requisito de integración: cuántos miembros deben cumplir una condición paramétrica (FR-CP-03)."""

    __tablename__ = "gov_commission_policy_requirements"
    __scope__ = Scope.COMPANY

    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_commission_policies.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    etiqueta: Mapped[str] = mapped_column(String(200), nullable=False)
    funcion: Mapped[str] = mapped_column(String(16), nullable=False)
    condicion: Mapped[str] = mapped_column(String(16), nullable=False)
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    area: Mapped[str | None] = mapped_column(String(24), nullable=True)
    position_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=True)
    unit_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_units.id"), nullable=True)
    competencia_accion: Mapped[str | None] = mapped_column(String(16), nullable=True)
    competencia_materia: Mapped[str | None] = mapped_column(String(16), nullable=True)
    official_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=True)
    minimo: Mapped[int] = mapped_column(Integer, nullable=False)
    maximo: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint(f"funcion IN ({en(FUNCIONES_REQUISITO_COMISION)})", name="funcion"),
        CheckConstraint(f"condicion IN ({en(CONDICIONES_REQUISITO_COMISION)})", name="condicion"),
        CheckConstraint(f"tipo IN ({en(TIPOS_REQUISITO_COMISION)})", name="tipo"),
        CheckConstraint(f"area IS NULL OR area IN ({en(AREAS_COMISION)})", name="area"),
        CheckConstraint(f"competencia_accion IS NULL OR competencia_accion IN ({en(ACCIONES_COMPETENCIA)})", name="competencia_accion"),
        CheckConstraint(f"competencia_materia IS NULL OR competencia_materia IN ({en(MATERIAS_COMPETENCIA)})", name="competencia_materia"),
        CheckConstraint("orden >= 1", name="orden"),
        CheckConstraint("minimo >= 0", name="minimo"),
        CheckConstraint("maximo IS NULL OR maximo >= minimo", name="maximo"),
        CheckConstraint(
            "(tipo = 'AREA' AND area IS NOT NULL AND position_id IS NULL AND unit_id IS NULL AND competencia_accion IS NULL AND official_id IS NULL) OR "
            "(tipo = 'CARGO' AND position_id IS NOT NULL AND area IS NULL AND unit_id IS NULL AND competencia_accion IS NULL AND official_id IS NULL) OR "
            "(tipo = 'UNIDAD' AND unit_id IS NOT NULL AND area IS NULL AND position_id IS NULL AND competencia_accion IS NULL AND official_id IS NULL) OR "
            "(tipo = 'COMPETENCIA' AND competencia_accion IS NOT NULL AND competencia_materia IS NOT NULL AND area IS NULL AND position_id IS NULL AND unit_id IS NULL AND official_id IS NULL) OR "
            "(tipo = 'FUNCIONARIO' AND official_id IS NOT NULL AND area IS NULL AND position_id IS NULL AND unit_id IS NULL AND competencia_accion IS NULL)",
            name="referencia",
        ),
        UniqueConstraint("policy_id", "orden", name="uq_gov_commission_policy_requirements_orden"),
    )


class GovernmentCommissionPolicyDocument(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Documento exigido por la política en una etapa (FR-CP-01): constitución, apertura o recomendación."""

    __tablename__ = "gov_commission_policy_documents"
    __scope__ = Scope.COMPANY

    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_commission_policies.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    document_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_types.id"), nullable=False)
    etapa: Mapped[str] = mapped_column(String(14), nullable=False)
    obligatorio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    condicion: Mapped[str | None] = mapped_column(String(300), nullable=True)

    __table_args__ = (
        UniqueConstraint("policy_id", "document_type_id", "etapa", name="uq_gov_commission_policy_documents_tipo"),
        CheckConstraint(f"etapa IN ({en(ETAPAS_DOCUMENTO_COMISION)})", name="etapa"),
    )


class GovernmentCommissionPolicyHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia inmutable de una política de comisión, con instantánea por evento."""

    __tablename__ = "gov_commission_policy_history"
    __scope__ = Scope.COMPANY

    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_commission_policies.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    evento: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    instantanea: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    __table_args__ = (
        CheckConstraint(f"evento IN ({en(EVENTOS_POLITICA_COMISION)})", name="evento"),
    )


GOV_COMMISSION_POLICY_HISTORY_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_politica_comision_historia_inmutable() RETURNS TRIGGER AS $$ "
    "BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_COMMISSION_POLICY_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_commission_policy_history_no_update BEFORE UPDATE ON gov_commission_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_politica_comision_historia_inmutable()",
    "CREATE TRIGGER trg_gov_commission_policy_history_no_delete BEFORE DELETE ON gov_commission_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_politica_comision_historia_inmutable()",
    "CREATE TRIGGER trg_gov_commission_policy_history_no_truncate BEFORE TRUNCATE ON gov_commission_policy_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_politica_comision_historia_inmutable()",
)

for _sentencia in GOV_COMMISSION_POLICY_HISTORY_IMMUTABLE_PG:
    event.listen(GovernmentCommissionPolicyHistory.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

class GovernmentProcurementFile(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    __tablename__ = "gov_procurement_files"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    numero: Mapped[str] = mapped_column(String(40), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    objeto: Mapped[str] = mapped_column(String(1000), nullable=False)
    partes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    tipo_contratacion: Mapped[str] = mapped_column(String(16), nullable=False)
    modalidad_declarada: Mapped[str | None] = mapped_column(String(24), nullable=True)
    modalidad_fundamento: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    modalidad_fuente: Mapped[str | None] = mapped_column(String(300), nullable=True)
    unidad_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_units.id"), nullable=False, index=True)
    unidad_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    committee_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_committees.id"), nullable=True, index=True)
    comision_no_aplica_motivo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ABIERTO", server_default="ABIERTO")
    cierre_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    cierre_motivo: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    recepcion_concluida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recepcion_concluida_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    evaluacion_concluida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evaluacion_concluida_por: Mapped[str | None] = mapped_column(String(36), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "numero", name="uq_gov_procurement_files_numero"),
        CheckConstraint(f"status IN ({en(ESTADOS_EXPEDIENTE)})", name="status"),
        CheckConstraint(f"tipo_contratacion IN ({en(TIPOS_CONTRATACION)})", name="tipo_contratacion"),
        CheckConstraint(f"modalidad_declarada IS NULL OR modalidad_declarada IN ({en(MODALIDADES_DECLARADAS)})", name="modalidad"),
        CheckConstraint("modalidad_declarada IS NULL OR modalidad_fundamento IS NOT NULL", name="modalidad_con_fundamento"),
        CheckConstraint("committee_id IS NULL OR comision_no_aplica_motivo IS NULL", name="comision_o_motivo"),
        CheckConstraint("status = 'ABIERTO' OR (cierre_fecha IS NOT NULL AND cierre_motivo IS NOT NULL)", name="cierre_con_motivo"),
        CheckConstraint("version >= 1", name="version"),
    )


class GovernmentProcurementFileResponsible(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_file_responsibles"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=False, index=True)
    official_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=False, index=True)
    rol: Mapped[str] = mapped_column(String(16), nullable=False)
    funcionario_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    cargo_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    unidad_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    fin_efectivo: Mapped[date | None] = mapped_column(Date, nullable=True)
    motivo_fin: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        CheckConstraint(f"rol IN ({en(ROLES_RESPONSABLE_EXPEDIENTE)})", name="rol"),
        CheckConstraint("fin_efectivo IS NULL OR fin_efectivo >= desde", name="fin_tras_inicio"),
        CheckConstraint("(fin_efectivo IS NULL) = (motivo_fin IS NULL)", name="fin_con_motivo"),
        Index(
            "uq_gov_file_responsible_vigente",
            "file_id",
            "official_id",
            "rol",
            unique=True,
            postgresql_where=text("fin_efectivo IS NULL"),
            sqlite_where=text("fin_efectivo IS NULL"),
        ),
        Index(
            "uq_gov_file_principal_vigente",
            "file_id",
            unique=True,
            postgresql_where=text("fin_efectivo IS NULL AND rol = 'RESPONSABLE'"),
            sqlite_where=text("fin_efectivo IS NULL AND rol = 'RESPONSABLE'"),
        ),
    )


class GovernmentProcurementFileMilestone(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_file_milestones"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    fuente: Mapped[str | None] = mapped_column(String(300), nullable=True)
    fecha_prevista: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_real: Mapped[date | None] = mapped_column(Date, nullable=True)
    official_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=True)
    responsable_etiqueta: Mapped[str | None] = mapped_column(String(400), nullable=True)
    estado: Mapped[str] = mapped_column(String(16), nullable=False, default="PREVISTO", server_default="PREVISTO")
    motivo_no_aplica: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        CheckConstraint(f"estado IN ({en(ESTADOS_HITO)})", name="estado"),
        CheckConstraint("(estado = 'CUMPLIDO') = (fecha_real IS NOT NULL)", name="cumplido_con_fecha"),
        CheckConstraint("(estado = 'NO_APLICA') = (motivo_no_aplica IS NOT NULL)", name="no_aplica_con_motivo"),
    )


class GovernmentProcurementFileFolio(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_file_folios"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    clase: Mapped[str] = mapped_column(String(24), nullable=False)
    document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    document_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=True)
    act_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=True, index=True)
    etiqueta: Mapped[str] = mapped_column(String(400), nullable=False)
    tipo_etiqueta: Mapped[str] = mapped_column(String(120), nullable=False)
    version_numero: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fecha_documento: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_incorporacion: Mapped[date] = mapped_column(Date, nullable=False)
    reservado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    motivo_reserva: Mapped[str | None] = mapped_column(String(500), nullable=True)
    milestone_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_file_milestones.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("file_id", "numero", name="uq_gov_file_folio_numero"),
        CheckConstraint(f"clase IN ({en(CLASES_FOLIO)})", name="clase"),
        CheckConstraint("numero >= 1", name="numero"),
        CheckConstraint("(document_id IS NULL) <> (act_id IS NULL)", name="documento_o_acto"),
        CheckConstraint("reservado = false OR motivo_reserva IS NOT NULL", name="reserva_con_motivo"),
    )


class GovernmentProcurementFileEvent(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_file_events"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=False, index=True)
    secuencia: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    clase: Mapped[str] = mapped_column(String(16), nullable=False)
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    detalle: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    resultado: Mapped[str | None] = mapped_column(String(500), nullable=True)
    official_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=True)
    responsable_etiqueta: Mapped[str | None] = mapped_column(String(400), nullable=True)
    act_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=True)
    acto_etiqueta: Mapped[str | None] = mapped_column(String(400), nullable=True)
    folio_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_file_folios.id"), nullable=True)
    folio_etiqueta: Mapped[str | None] = mapped_column(String(400), nullable=True)
    milestone_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_file_milestones.id"), nullable=True)
    hito_etiqueta: Mapped[str | None] = mapped_column(String(200), nullable=True)
    estado_expediente: Mapped[str] = mapped_column(String(16), nullable=False)
    rectifica_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_file_events.id"), nullable=True)
    motivo: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    __table_args__ = (
        UniqueConstraint("file_id", "secuencia", name="uq_gov_file_event_secuencia"),
        CheckConstraint(f"clase IN ({en(CLASES_EVENTO_EXPEDIENTE)})", name="clase"),
        CheckConstraint("clase <> 'DECISION' OR resultado IS NOT NULL", name="decision_con_resultado"),
        CheckConstraint("rectifica_id IS NULL OR motivo IS NOT NULL", name="rectificacion_con_motivo"),
    )


_GOV_EXPEDIENTE_IMMUTABLE_DDL = (
    """
    CREATE OR REPLACE FUNCTION kontrol_gov_expediente_inmutable() RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'GOV_PROCUREMENT_FILE_IMMUTABLE';
    END;
    $$ LANGUAGE plpgsql;
    """,
    """
    CREATE TRIGGER trg_gov_file_folios_no_update BEFORE UPDATE ON gov_procurement_file_folios
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_expediente_inmutable();
    """,
    """
    CREATE TRIGGER trg_gov_file_folios_no_delete BEFORE DELETE ON gov_procurement_file_folios
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_expediente_inmutable();
    """,
    """
    CREATE TRIGGER trg_gov_file_folios_no_truncate BEFORE TRUNCATE ON gov_procurement_file_folios
        FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_expediente_inmutable();
    """,
    """
    CREATE TRIGGER trg_gov_file_events_no_update BEFORE UPDATE ON gov_procurement_file_events
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_expediente_inmutable();
    """,
    """
    CREATE TRIGGER trg_gov_file_events_no_delete BEFORE DELETE ON gov_procurement_file_events
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_expediente_inmutable();
    """,
    """
    CREATE TRIGGER trg_gov_file_events_no_truncate BEFORE TRUNCATE ON gov_procurement_file_events
        FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_expediente_inmutable();
    """,
)

for _indice, _sentencia in enumerate(_GOV_EXPEDIENTE_IMMUTABLE_DDL):
    if _indice == 0 or 1 <= _indice <= 3:
        event.listen(
            GovernmentProcurementFileFolio.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
    if _indice == 0 or _indice >= 4:
        event.listen(
            GovernmentProcurementFileEvent.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )


_GOV_OFFER_IMMUTABLE_DDL = (
    """
    CREATE OR REPLACE FUNCTION kontrol_gov_offer_immutable() RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'gov_procurement_offers are immutable';
    END;
    $$ LANGUAGE plpgsql;
    """,
    """
    CREATE TRIGGER trg_gov_offer_immutable_update
    BEFORE UPDATE ON gov_procurement_offers
    FOR EACH ROW EXECUTE FUNCTION kontrol_gov_offer_immutable();
    """,
    """
    CREATE TRIGGER trg_gov_offer_immutable_delete
    BEFORE DELETE ON gov_procurement_offers
    FOR EACH ROW EXECUTE FUNCTION kontrol_gov_offer_immutable();
    """,
    """
    CREATE TRIGGER trg_gov_offer_immutable_truncate
    BEFORE TRUNCATE ON gov_procurement_offers
    FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_offer_immutable();
    """,
    """
    CREATE TRIGGER trg_gov_offer_document_immutable_update
    BEFORE UPDATE ON gov_procurement_offer_documents
    FOR EACH ROW EXECUTE FUNCTION kontrol_gov_offer_immutable();
    """,
    """
    CREATE TRIGGER trg_gov_offer_document_immutable_delete
    BEFORE DELETE ON gov_procurement_offer_documents
    FOR EACH ROW EXECUTE FUNCTION kontrol_gov_offer_immutable();
    """,
    """
    CREATE TRIGGER trg_gov_offer_document_immutable_truncate
    BEFORE TRUNCATE ON gov_procurement_offer_documents
    FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_offer_immutable();
    """,
)


class GovernmentProcurementOffer(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_offers"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    oferente_nombre: Mapped[str] = mapped_column(String(300), nullable=False)
    oferente_documento: Mapped[str] = mapped_column(String(40), nullable=False)
    representante: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tipo_sobre: Mapped[str] = mapped_column(String(16), nullable=False)
    canal: Mapped[str] = mapped_column(String(24), nullable=False)
    recibida_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    official_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=False, index=True)
    receptor_etiqueta: Mapped[str] = mapped_column(String(400), nullable=False)
    condicion_sobre: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confidencial: Mapped[bool] = mapped_column(Boolean, nullable=False)
    fundamento_confidencialidad: Mapped[str] = mapped_column(String(300), nullable=False)
    modalidad_al_recibir: Mapped[str | None] = mapped_column(String(24), nullable=True)

    __table_args__ = (
        CheckConstraint("numero >= 1", name="numero"),
        CheckConstraint("tipo_sobre IN ('UNICO', 'CALIFICACION', 'OFERTA')", name="tipo_sobre"),
        CheckConstraint("canal IN ('ACTO_PUBLICO', 'UNIDAD_CONTRATANTE', 'MEDIO_ELECTRONICO')", name="canal"),
        UniqueConstraint("company_id", "file_id", "numero", name="uq_gov_procurement_offers_file_numero"),
        UniqueConstraint("company_id", "file_id", "oferente_documento", "tipo_sobre", name="uq_gov_procurement_offers_oferente_sobre"),
    )


class GovernmentProcurementOfferDocument(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_offer_documents"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    offer_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_offers.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    document_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=False, index=True)
    version_numero: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("document_id", name="uq_gov_procurement_offer_documents_document"),
    )


class GovernmentProcurementEvalMatrix(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    __tablename__ = "gov_procurement_eval_matrices"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(16), nullable=False)
    pliego_document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    pliego_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=False, index=True)
    pliego_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    transcripcion: Mapped[bool] = mapped_column(Boolean, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    __table_args__ = (
        CheckConstraint("estado IN ('BORRADOR', 'BLOQUEADA')", name="ck_gov_procurement_eval_matrices_estado"),
        CheckConstraint("version >= 1", name="ck_gov_procurement_eval_matrices_version"),
        UniqueConstraint("file_id", name="uq_gov_procurement_eval_matrices_file"),
    )


class GovernmentProcurementEvalCriterion(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_eval_criteria"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    matrix_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_eval_matrices.id"), nullable=False, index=True)
    aspecto: Mapped[str] = mapped_column(String(16), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    nombre: Mapped[str] = mapped_column(String(300), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    escala: Mapped[str] = mapped_column(String(16), nullable=False)
    puntaje_maximo: Mapped[Decimal | None] = mapped_column(Numeric(9, 2), nullable=True)
    ponderacion: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "aspecto IN ('TECNICO', 'ECONOMICO', 'LEGAL')",
            name="ck_gov_procurement_eval_criteria_aspecto",
        ),
        CheckConstraint("orden >= 1", name="ck_gov_procurement_eval_criteria_orden"),
        CheckConstraint(
            "escala IN ('PUNTAJE', 'CUMPLE')",
            name="ck_gov_procurement_eval_criteria_escala",
        ),
        CheckConstraint(
            "(escala = 'PUNTAJE' AND puntaje_maximo IS NOT NULL AND puntaje_maximo > 0) OR (escala = 'CUMPLE' AND puntaje_maximo IS NULL)",
            name="ck_gov_procurement_eval_criteria_puntaje",
        ),
        CheckConstraint(
            "ponderacion IS NULL OR ponderacion > 0",
            name="ck_gov_procurement_eval_criteria_ponderacion",
        ),
        UniqueConstraint(
            "matrix_id",
            "aspecto",
            "orden",
            name="uq_gov_procurement_eval_criteria_aspecto_orden",
        ),
    )


class GovernmentProcurementOpening(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_openings"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=False, index=True)
    committee_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_committees.id"), nullable=True, index=True)
    modo: Mapped[str] = mapped_column(String(20), nullable=False, default="COMISION", server_default="COMISION")
    regla: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    abierta_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acta_document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    acta_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=False, index=True)
    acta_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    observaciones: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    miembros_con_voto: Mapped[int | None] = mapped_column(Integer, nullable=True)
    asistentes_con_voto: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quorum_requerido: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint(f"modo IN ({en(MODOS_ACTUACION_COMISION)})", name="modo"),
        CheckConstraint(
            "(modo = 'COMISION' AND committee_id IS NOT NULL AND miembros_con_voto IS NOT NULL AND asistentes_con_voto IS NOT NULL AND quorum_requerido IS NOT NULL) OR "
            "(modo = 'UNIDAD_CONTRATANTE' AND committee_id IS NULL AND miembros_con_voto IS NULL AND asistentes_con_voto IS NULL AND quorum_requerido IS NULL)",
            name="modo_comision",
        ),
        CheckConstraint("numero >= 1", name="ck_gov_procurement_openings_numero"),
        CheckConstraint("miembros_con_voto >= 1", name="ck_gov_procurement_openings_miembros_con_voto"),
        CheckConstraint("asistentes_con_voto >= 1", name="ck_gov_procurement_openings_asistentes_con_voto"),
        CheckConstraint("quorum_requerido >= 1", name="ck_gov_procurement_openings_quorum_requerido"),
        UniqueConstraint("company_id", "file_id", "numero", name="uq_gov_procurement_openings_file_numero"),
    )


class GovernmentProcurementOpeningAttendee(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_opening_attendees"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    opening_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_openings.id"), nullable=False, index=True)
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_committee_members.id"), nullable=False, index=True)
    official_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=False, index=True)
    funcion: Mapped[str] = mapped_column(String(16), nullable=False)
    condicion: Mapped[str] = mapped_column(String(16), nullable=False)
    cuenta_voto: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "funcion IN ('MIEMBRO', 'SECRETARIO')",
            name="ck_gov_procurement_opening_attendees_funcion",
        ),
        CheckConstraint(
            "condicion IN ('PRINCIPAL', 'SUPLENTE')",
            name="ck_gov_procurement_opening_attendees_condicion",
        ),
        UniqueConstraint("opening_id", "member_id", name="uq_gov_procurement_opening_attendees_member"),
    )


class GovernmentProcurementOpeningResponsible(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Responsable del expediente que actúa en una apertura sin comisión (FR-CP-08, OD-CP-02)."""

    __tablename__ = "gov_procurement_opening_responsibles"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    opening_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_openings.id"), nullable=False, index=True)
    responsible_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_file_responsibles.id"), nullable=False, index=True)
    official_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=False, index=True)
    rol: Mapped[str] = mapped_column(String(16), nullable=False)

    __table_args__ = (
        CheckConstraint(f"rol IN ({en(ROLES_RESPONSABLE_EXPEDIENTE)})", name="rol"),
        UniqueConstraint("opening_id", "responsible_id", name="uq_gov_procurement_opening_responsibles"),
    )


class GovernmentProcurementOpeningOffer(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_opening_offers"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    opening_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_openings.id"), nullable=False, index=True)
    offer_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_offers.id"), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("offer_id", name="uq_gov_procurement_opening_offers_offer"),
    )


class GovernmentProcurementEvalContribution(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_eval_contributions"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    offer_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_offers.id"), nullable=False, index=True)
    criterion_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_eval_criteria.id"), nullable=False, index=True)
    matrix_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_eval_matrices.id"), nullable=False, index=True)
    matrix_version: Mapped[int] = mapped_column(Integer, nullable=False)
    member_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_committee_members.id"), nullable=True, index=True)
    # Sin comisión, evalúa un responsable del expediente (FR-CP-08, OD-CP-02).
    responsible_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_file_responsibles.id"), nullable=True, index=True)
    official_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=False, index=True)
    puntaje: Mapped[Decimal | None] = mapped_column(Numeric(9, 2), nullable=True)
    cumple: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    observacion: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    evidencia_document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    evidencia_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=True, index=True)
    reemplaza_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_eval_contributions.id"), nullable=True, index=True, unique=True)

    __table_args__ = (
        CheckConstraint("(member_id IS NULL) <> (responsible_id IS NULL)", name="actor"),
        CheckConstraint(
            "matrix_version >= 1",
            name="ck_gov_procurement_eval_contributions_matrix_version",
        ),
        CheckConstraint(
            "(puntaje IS NULL AND cumple IS NOT NULL) OR (puntaje IS NOT NULL AND cumple IS NULL)",
            name="ck_gov_procurement_eval_contributions_valor",
        ),
        CheckConstraint(
            "puntaje IS NULL OR puntaje >= 0",
            name="ck_gov_procurement_eval_contributions_puntaje",
        ),
        Index(
            "uq_gov_procurement_eval_contributions_raiz",
            "company_id",
            "offer_id",
            "criterion_id",
            "member_id",
            unique=True,
            postgresql_where=text("reemplaza_id IS NULL"),
            sqlite_where=text("reemplaza_id IS NULL"),
        ),
        Index(
            "uq_gov_procurement_eval_contributions_raiz_responsable",
            "company_id",
            "offer_id",
            "criterion_id",
            "responsible_id",
            unique=True,
            postgresql_where=text("reemplaza_id IS NULL AND responsible_id IS NOT NULL"),
            sqlite_where=text("reemplaza_id IS NULL AND responsible_id IS NOT NULL"),
        ),
    )


class GovernmentProcurementEvalResult(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_eval_results"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    offer_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_offers.id"), nullable=False, index=True)
    criterion_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_eval_criteria.id"), nullable=False, index=True)
    matrix_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_eval_matrices.id"), nullable=False, index=True)
    matrix_version: Mapped[int] = mapped_column(Integer, nullable=False)
    member_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_committee_members.id"), nullable=True, index=True)
    # Sin comisión, evalúa un responsable del expediente (FR-CP-08, OD-CP-02).
    responsible_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_file_responsibles.id"), nullable=True, index=True)
    official_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=False, index=True)
    puntaje: Mapped[Decimal | None] = mapped_column(Numeric(9, 2), nullable=True)
    cumple: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    observacion: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    evidencia_document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    evidencia_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=True, index=True)
    reemplaza_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_eval_results.id"), nullable=True, index=True, unique=True)

    __table_args__ = (
        CheckConstraint("(member_id IS NULL) <> (responsible_id IS NULL)", name="actor"),
        CheckConstraint(
            "matrix_version >= 1",
            name="ck_gov_procurement_eval_results_matrix_version",
        ),
        CheckConstraint(
            "(puntaje IS NULL AND cumple IS NOT NULL) OR (puntaje IS NOT NULL AND cumple IS NULL)",
            name="ck_gov_procurement_eval_results_valor",
        ),
        CheckConstraint(
            "puntaje IS NULL OR puntaje >= 0",
            name="ck_gov_procurement_eval_results_puntaje",
        ),
        Index(
            "uq_gov_procurement_eval_results_raiz",
            "company_id",
            "offer_id",
            "criterion_id",
            unique=True,
            postgresql_where=text("reemplaza_id IS NULL"),
            sqlite_where=text("reemplaza_id IS NULL"),
        ),
    )


_GOV_EVAL_CRITERIO_DDL = (
    """
    CREATE OR REPLACE FUNCTION kontrol_gov_eval_criterio_bloqueado()
    RETURNS trigger AS $$
    DECLARE
        v_estado varchar(16);
    BEGIN
        SELECT estado INTO v_estado
        FROM gov_procurement_eval_matrices
        WHERE id = COALESCE(NEW.matrix_id, OLD.matrix_id);
        IF v_estado = 'BLOQUEADA' THEN
            RAISE EXCEPTION 'La matriz está bloqueada';
        END IF;
        RETURN COALESCE(NEW, OLD);
    END;
    $$ LANGUAGE plpgsql;
    """,
    """
    CREATE TRIGGER trg_gov_eval_criterio_bloqueado_insert
    BEFORE INSERT ON gov_procurement_eval_criteria
    FOR EACH ROW EXECUTE FUNCTION kontrol_gov_eval_criterio_bloqueado();
    """,
    """
    CREATE TRIGGER trg_gov_eval_criterio_bloqueado_update
    BEFORE UPDATE ON gov_procurement_eval_criteria
    FOR EACH ROW EXECUTE FUNCTION kontrol_gov_eval_criterio_bloqueado();
    """,
    """
    CREATE TRIGGER trg_gov_eval_criterio_bloqueado_delete
    BEFORE DELETE ON gov_procurement_eval_criteria
    FOR EACH ROW EXECUTE FUNCTION kontrol_gov_eval_criterio_bloqueado();
    """,
)

_GOV_EVAL_IMMUTABLE_DDL = (
    """
    CREATE OR REPLACE FUNCTION kontrol_gov_eval_immutable()
    RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'Los registros de evaluación son inmutables';
    END;
    $$ LANGUAGE plpgsql;
    """,
)


event.listen(
    GovernmentProcurementOffer.__table__,
    "after_create",
    DDL(_GOV_OFFER_IMMUTABLE_DDL[0]).execute_if(dialect="postgresql"),
)
for _sentencia in _GOV_OFFER_IMMUTABLE_DDL[1:4]:
    event.listen(
        GovernmentProcurementOffer.__table__,
        "after_create",
        DDL(_sentencia).execute_if(dialect="postgresql"),
    )
for _sentencia in _GOV_OFFER_IMMUTABLE_DDL[4:7]:
    event.listen(
        GovernmentProcurementOfferDocument.__table__,
        "after_create",
        DDL(_sentencia).execute_if(dialect="postgresql"),
    )

_gov_eval_criterio_tabla = GovernmentProcurementEvalCriterion.__table__
event.listen(
    _gov_eval_criterio_tabla,
    "after_create",
    DDL(_GOV_EVAL_CRITERIO_DDL[0]).execute_if(dialect="postgresql"),
)
for _sentencia in _GOV_EVAL_CRITERIO_DDL[1:4]:
    event.listen(
        _gov_eval_criterio_tabla,
        "after_create",
        DDL(_sentencia).execute_if(dialect="postgresql"),
    )

class GovernmentProcurementRecommendation(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_recommendations"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=False, index=True)
    committee_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_committees.id"), nullable=True, index=True)
    modo: Mapped[str] = mapped_column(String(20), nullable=False, default="COMISION", server_default="COMISION")
    regla: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(16), nullable=False, default="EMITIDA", server_default="EMITIDA")
    resultado_recomendado: Mapped[str] = mapped_column(String(24), nullable=False)
    causal_desierta: Mapped[str | None] = mapped_column(String(16), nullable=True)
    motivacion: Mapped[str] = mapped_column(Text, nullable=False)
    examen_legal: Mapped[str] = mapped_column(Text, nullable=False)
    examen_financiero: Mapped[str] = mapped_column(Text, nullable=False)
    examen_tecnico: Mapped[str] = mapped_column(Text, nullable=False)
    resultado_matriz: Mapped[str] = mapped_column(Text, nullable=False)
    medidas_promocion: Mapped[str | None] = mapped_column(Text, nullable=True)
    matrix_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_eval_matrices.id"), nullable=False, index=True)
    matrix_version: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluacion_concluida_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    informe_storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    informe_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    informe_tamano: Mapped[int] = mapped_column(BigInteger, nullable=False)
    informe_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    emitida_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    emitida_por: Mapped[str] = mapped_column(String(36), nullable=False)
    official_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=True, index=True)
    sustituye_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_recommendations.id"), nullable=True, unique=True)
    motivo_sustitucion: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    sustituida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(f"modo IN ({en(MODOS_ACTUACION_COMISION)})", name="modo"),
        CheckConstraint("(modo = 'COMISION') = (committee_id IS NOT NULL)", name="modo_comision"),
        CheckConstraint(
            f"estado IN ({en(ESTADOS_RECOMENDACION)})",
            name="ck_gov_procurement_recommendations_estado",
        ),
        CheckConstraint(
            f"resultado_recomendado IN ({en(RESULTADOS_RECOMENDACION)})",
            name="ck_gov_procurement_recommendations_resultado_recomendado",
        ),
        CheckConstraint(
            "numero >= 1",
            name="ck_gov_procurement_recommendations_numero",
        ),
        CheckConstraint(
            "(causal_desierta IS NOT NULL) = (resultado_recomendado = 'DECLARAR_DESIERTA')",
            name="ck_gov_procurement_recommendations_causal_desierta_presencia",
        ),
        CheckConstraint(
            f"causal_desierta IS NULL OR causal_desierta IN ({en(CAUSALES_DESIERTA)})",
            name="ck_gov_procurement_recommendations_causal_desierta_valor",
        ),
        CheckConstraint(
            "(sustituye_id IS NULL) = (motivo_sustitucion IS NULL)",
            name="ck_gov_procurement_recommendations_sustitucion",
        ),
        CheckConstraint(
            "(estado = 'SUSTITUIDA') = (sustituida_en IS NOT NULL)",
            name="ck_gov_procurement_recommendations_sustituida_en",
        ),
        CheckConstraint(
            "matrix_version >= 1",
            name="ck_gov_procurement_recommendations_matrix_version",
        ),
        UniqueConstraint("company_id", "file_id", "numero", name="uq_gov_procurement_recommendations_company_file_numero"),
        Index(
            "uq_gov_procurement_recommendations_vigente",
            "file_id",
            unique=True,
            postgresql_where=text("estado = 'EMITIDA'"),
            sqlite_where=text("estado = 'EMITIDA'"),
        ),
    )


class GovernmentProcurementRecommendationSignatory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_recommendation_signatories"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    recommendation_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_recommendations.id"), nullable=False, index=True)
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_committee_members.id"), nullable=False, index=True)
    official_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=False, index=True)
    funcion: Mapped[str] = mapped_column(String(16), nullable=False)
    condicion: Mapped[str] = mapped_column(String(16), nullable=False)
    cuenta_voto: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (
        UniqueConstraint("recommendation_id", "member_id", name="uq_gov_proc_rec_signatories_member"),
    )


class GovernmentProcurementRecommendationResponsible(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Responsable del expediente que firma una recomendación sin comisión (FR-CP-09, OD-CP-02)."""

    __tablename__ = "gov_procurement_recommendation_responsibles"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    recommendation_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_recommendations.id"), nullable=False, index=True)
    responsible_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_file_responsibles.id"), nullable=False, index=True)
    official_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=False, index=True)
    rol: Mapped[str] = mapped_column(String(16), nullable=False)

    __table_args__ = (
        CheckConstraint(f"rol IN ({en(ROLES_RESPONSABLE_EXPEDIENTE)})", name="rol"),
        UniqueConstraint("recommendation_id", "responsible_id", name="uq_gov_proc_rec_responsibles"),
    )


class GovernmentProcurementRecommendationOption(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_recommendation_options"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    recommendation_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_recommendations.id"), nullable=False, index=True)
    offer_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_offers.id"), nullable=False, index=True)
    posicion: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "posicion BETWEEN 1 AND 3",
            name="ck_gov_procurement_recommendation_options_posicion",
        ),
        UniqueConstraint("recommendation_id", "posicion", name="uq_gov_proc_rec_options_posicion"),
        UniqueConstraint("recommendation_id", "offer_id", name="uq_gov_procurement_recommendation_options_recommendation_offer"),
    )


class GovernmentProcurementRecommendationRejection(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_recommendation_rejections"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    recommendation_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_recommendations.id"), nullable=False, index=True)
    offer_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_offers.id"), nullable=False, index=True)
    causal: Mapped[str] = mapped_column(String(16), nullable=False)
    motivacion: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            f"causal IN ({en(CAUSALES_RECHAZO)})",
            name="ck_gov_procurement_recommendation_rejections_causal",
        ),
        UniqueConstraint("recommendation_id", "offer_id", name="uq_gov_proc_rec_rejections_offer"),
    )


class GovernmentProcurementDecision(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_procurement_decisions"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    recommendation_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_recommendations.id"), nullable=True, index=True)
    resultado: Mapped[str] = mapped_column(String(16), nullable=False)
    offer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_offers.id"), nullable=True, index=True)
    posicion: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    causal_desierta: Mapped[str | None] = mapped_column(String(16), nullable=True)
    causal_nulidad: Mapped[str | None] = mapped_column(String(24), nullable=True)
    anula_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_decisions.id"), nullable=True, index=True)
    act_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=False, unique=True)
    cargo_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=False, index=True)
    motivacion: Mapped[str] = mapped_column(Text, nullable=False)
    decidida_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decidida_por: Mapped[str] = mapped_column(String(36), nullable=False)
    official_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=True, index=True)
    estado: Mapped[str] = mapped_column(String(16), nullable=False, default="VIGENTE", server_default="VIGENTE")
    conversion_autoridad: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    afectada_por_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("gov_procurement_decisions.id", deferrable=True, initially="DEFERRED"),
        nullable=True,
    )
    afectada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            f"resultado IN ({en(RESULTADOS_DECISION)})",
            name="ck_gov_procurement_decisions_resultado",
        ),
        CheckConstraint(
            f"estado IN ({en(ESTADOS_DECISION)})",
            name="ck_gov_procurement_decisions_estado",
        ),
        CheckConstraint(
            "numero >= 1",
            name="ck_gov_procurement_decisions_numero",
        ),
        CheckConstraint(
            "(offer_id IS NOT NULL) = (resultado = 'ADJUDICADA')",
            name="ck_gov_procurement_decisions_offer_presencia",
        ),
        CheckConstraint(
            "(offer_id IS NULL) = (posicion IS NULL)",
            name="ck_gov_procurement_decisions_posicion_presencia",
        ),
        CheckConstraint(
            "posicion IS NULL OR posicion BETWEEN 1 AND 3",
            name="ck_gov_procurement_decisions_posicion_valor",
        ),
        CheckConstraint(
            "(causal_desierta IS NOT NULL) = (resultado = 'DESIERTA')",
            name="ck_gov_procurement_decisions_causal_desierta_presencia",
        ),
        CheckConstraint(
            f"causal_desierta IS NULL OR causal_desierta IN ({en(CAUSALES_DESIERTA)})",
            name="ck_gov_procurement_decisions_causal_desierta_valor",
        ),
        CheckConstraint(
            "(causal_nulidad IS NOT NULL) = (resultado = 'NULIDAD')",
            name="ck_gov_procurement_decisions_causal_nulidad_presencia",
        ),
        CheckConstraint(
            f"causal_nulidad IS NULL OR causal_nulidad IN ({en(CAUSALES_NULIDAD)})",
            name="ck_gov_procurement_decisions_causal_nulidad_valor",
        ),
        CheckConstraint(
            "(anula_id IS NOT NULL) = (resultado = 'NULIDAD')",
            name="ck_gov_procurement_decisions_anula_presencia",
        ),
        CheckConstraint(
            "resultado = 'NULIDAD' OR recommendation_id IS NOT NULL",
            name="ck_gov_procurement_decisions_recommendation_presencia",
        ),
        CheckConstraint(
            "(estado = 'VIGENTE') = (afectada_por_id IS NULL)",
            name="ck_gov_procurement_decisions_afectada_por_presencia",
        ),
        CheckConstraint(
            "(afectada_por_id IS NULL) = (afectada_en IS NULL)",
            name="ck_gov_procurement_decisions_afectada_en_presencia",
        ),
        UniqueConstraint("company_id", "file_id", "numero", name="uq_gov_procurement_decisions_company_file_numero"),
        Index(
            "uq_gov_procurement_decisions_final",
            "file_id",
            unique=True,
            postgresql_where=text("estado = 'VIGENTE' AND resultado <> 'NULIDAD'"),
            sqlite_where=text("estado = 'VIGENTE' AND resultado <> 'NULIDAD'"),
        ),
    )


_GOV_DECISION_IMMUTABLE_DDL = (
    """
    CREATE OR REPLACE FUNCTION kontrol_gov_decision_immutable()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'Los registros de recomendación y decisión son inmutables';
    END;
    $$ LANGUAGE plpgsql;
    """,
)

_GOV_RECOMMENDATION_GUARD_DDL = (
    """
    CREATE OR REPLACE FUNCTION kontrol_gov_recommendation_guard()
    RETURNS TRIGGER AS $$
    BEGIN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'Los registros de recomendación son inmutables';
        END IF;
        IF TG_OP = 'TRUNCATE' THEN
            RAISE EXCEPTION 'Los registros de recomendación son inmutables';
        END IF;
        IF TG_OP = 'UPDATE' THEN
            IF OLD.estado = 'EMITIDA' AND NEW.estado = 'SUSTITUIDA' AND NEW.sustituida_en IS NOT NULL
               AND (to_jsonb(NEW) - 'estado' - 'sustituida_en' - 'updated_at') = (to_jsonb(OLD) - 'estado' - 'sustituida_en' - 'updated_at') THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'Los registros de recomendación son inmutables';
        END IF;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    """,
)

_GOV_DECISION_GUARD_DDL = (
    """
    CREATE OR REPLACE FUNCTION kontrol_gov_decision_guard()
    RETURNS TRIGGER AS $$
    BEGIN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'Los registros de decisión son inmutables';
        END IF;
        IF TG_OP = 'TRUNCATE' THEN
            RAISE EXCEPTION 'Los registros de decisión son inmutables';
        END IF;
        IF TG_OP = 'UPDATE' THEN
            IF OLD.estado = 'VIGENTE' AND NEW.estado IN ('ANULADA','SUSTITUIDA') AND NEW.afectada_por_id IS NOT NULL AND NEW.afectada_en IS NOT NULL
               AND (to_jsonb(NEW) - 'estado' - 'afectada_por_id' - 'afectada_en' - 'updated_at') = (to_jsonb(OLD) - 'estado' - 'afectada_por_id' - 'afectada_en' - 'updated_at') THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'Los registros de decisión son inmutables';
        END IF;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    """,
)

_gov_decision_immutable_modelos = (
    GovernmentProcurementRecommendationSignatory,
    GovernmentProcurementRecommendationOption,
    GovernmentProcurementRecommendationRejection,
)
for _modelo_decision in _gov_decision_immutable_modelos:
    _tabla = _modelo_decision.__table__
    _nombre_corto = _modelo_decision.__tablename__.split("_", 2)[-1]
    event.listen(
        _tabla,
        "after_create",
        DDL(_GOV_DECISION_IMMUTABLE_DDL[0]).execute_if(dialect="postgresql"),
    )
    for _accion, _momento in (
        ("update", "BEFORE UPDATE"),
        ("delete", "BEFORE DELETE"),
        ("truncate", "BEFORE TRUNCATE"),
    ):
        _trigger = f"""
        CREATE TRIGGER trg_{_nombre_corto}_immutable_{_accion}
        {_momento} ON {_modelo_decision.__tablename__}
        FOR EACH {"ROW" if _accion != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_decision_immutable();
        """
        event.listen(
            _tabla,
            "after_create",
            DDL(_trigger).execute_if(dialect="postgresql"),
        )

event.listen(
    GovernmentProcurementRecommendation.__table__,
    "after_create",
    DDL(_GOV_RECOMMENDATION_GUARD_DDL[0]).execute_if(dialect="postgresql"),
)
for _accion, _momento in (
    ("update", "BEFORE UPDATE"),
    ("delete", "BEFORE DELETE"),
    ("truncate", "BEFORE TRUNCATE"),
):
    _trigger = f"""
    CREATE TRIGGER trg_gov_procurement_recommendations_guard_{_accion}
    {_momento} ON gov_procurement_recommendations
    FOR EACH {"ROW" if _accion != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_recommendation_guard();
    """
    event.listen(
        GovernmentProcurementRecommendation.__table__,
        "after_create",
        DDL(_trigger).execute_if(dialect="postgresql"),
    )

event.listen(
    GovernmentProcurementDecision.__table__,
    "after_create",
    DDL(_GOV_DECISION_GUARD_DDL[0]).execute_if(dialect="postgresql"),
)
for _accion, _momento in (
    ("update", "BEFORE UPDATE"),
    ("delete", "BEFORE DELETE"),
    ("truncate", "BEFORE TRUNCATE"),
):
    _trigger = f"""
    CREATE TRIGGER trg_gov_procurement_decisions_guard_{_accion}
    {_momento} ON gov_procurement_decisions
    FOR EACH {"ROW" if _accion != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_decision_guard();
    """
    event.listen(
        GovernmentProcurementDecision.__table__,
        "after_create",
        DDL(_trigger).execute_if(dialect="postgresql"),
    )

_gov_eval_immutable_modelos = (
    GovernmentProcurementOpening,
    GovernmentProcurementOpeningAttendee,
    GovernmentProcurementOpeningOffer,
    GovernmentProcurementEvalContribution,
    GovernmentProcurementEvalResult,
)
for _modelo in _gov_eval_immutable_modelos:
    _tabla = _modelo.__table__
    _nombre_corto = _modelo.__tablename__.split("_", 2)[-1]
    event.listen(
        _tabla,
        "after_create",
        DDL(_GOV_EVAL_IMMUTABLE_DDL[0]).execute_if(dialect="postgresql"),
    )
    for _accion, _momento in (
        ("update", "BEFORE UPDATE"),
        ("delete", "BEFORE DELETE"),
        ("truncate", "BEFORE TRUNCATE"),
    ):
        _trigger = f"""
        CREATE TRIGGER trg_{_nombre_corto}_immutable_{_accion}
        {_momento} ON {_modelo.__tablename__}
        FOR EACH {"ROW" if _accion != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_eval_immutable();
        """
        event.listen(
            _tabla,
            "after_create",
            DDL(_trigger).execute_if(dialect="postgresql"),
        )


class GovernmentUserOfficialLink(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Vínculo entre una cuenta de usuario y un funcionario institucional (ORG-06, GOV-ORG-007)."""
    __tablename__ = "gov_user_official_links"
    __scope__ = Scope.COMPANY

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_user_official_links_codigo"),
        CheckConstraint(f"status IN ({en(ESTADOS_VINCULO)})", name="status"),
        CheckConstraint("version >= 1", name="version"),
        CheckConstraint("hasta IS NULL OR hasta >= desde", name="vigencia"),
        CheckConstraint("fin_efectivo IS NULL OR fin_efectivo >= desde", name="fin_tras_inicio"),
        CheckConstraint("status NOT IN ('CERRADO','REVOCADO') OR (fin_efectivo IS NOT NULL AND motivo_fin IS NOT NULL)", name="fin_con_motivo"),
        CheckConstraint("status IN ('BORRADOR','DESCARTADO') OR activated_at IS NOT NULL", name="activado_fechado"),
    )

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    official_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=False, index=True)
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    fin_efectivo: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="BORRADOR", server_default="BORRADOR")
    motivo: Mapped[str] = mapped_column(String(500), nullable=False)
    soporte: Mapped[str | None] = mapped_column(String(200), nullable=True)
    motivo_fin: Mapped[str | None] = mapped_column(String(500), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class GovernmentUserOfficialLinkHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia inmutable de vínculos cuenta-funcionario (ORG-06)."""
    __tablename__ = "gov_user_official_link_history"
    __scope__ = Scope.COMPANY

    __table_args__ = (
        CheckConstraint(f"tipo IN ({en(TIPOS_HISTORIA_VINCULO)})", name="tipo"),
    )

    link_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_user_official_links.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    detalle: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class GovernmentRoleCategory(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Categoría de separación de un rol (ORG-06)."""
    __tablename__ = "gov_role_categories"
    __scope__ = Scope.COMPANY

    __table_args__ = (
        CheckConstraint(f"categoria IN ({en(CATEGORIAS_SEPARACION)})", name="categoria"),
        CheckConstraint(f"status IN ({en(ESTADOS_CATEGORIA_ROL)})", name="status"),
        CheckConstraint("version >= 1", name="version"),
        CheckConstraint("hasta IS NULL OR hasta >= desde", name="vigencia"),
        CheckConstraint("status <> 'RETIRADA' OR hasta IS NOT NULL", name="retirada_con_fin"),
    )

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id"), nullable=False, index=True)
    categoria: Mapped[str] = mapped_column(String(32), nullable=False)
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVA", server_default="ACTIVA")
    motivo: Mapped[str] = mapped_column(String(500), nullable=False)


class GovernmentRoleCategoryHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia de categorías de rol (ORG-06)."""
    __tablename__ = "gov_role_category_history"
    __scope__ = Scope.COMPANY

    __table_args__ = (
        CheckConstraint(f"tipo IN ({en(TIPOS_HISTORIA_CATEGORIA)})", name="tipo"),
    )

    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_role_categories.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    detalle: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class GovernmentIdentityPolicy(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Política de exigencia de identidad institucional (ORG-06)."""
    __tablename__ = "gov_identity_policies"
    __scope__ = Scope.COMPANY

    __table_args__ = (
        UniqueConstraint("company_id", name="uq_gov_identity_policies_company_id"),
        CheckConstraint("version >= 1", name="version"),
    )

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    exige_identidad: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    motivo: Mapped[str | None] = mapped_column(String(500), nullable=True)


class GovernmentIdentityPolicyHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia de cambios en la política de identidad (ORG-06)."""
    __tablename__ = "gov_identity_policy_history"
    __scope__ = Scope.COMPANY

    __table_args__ = (
        CheckConstraint(f"tipo IN ({en(TIPOS_HISTORIA_POLITICA)})", name="tipo"),
    )

    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_identity_policies.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    detalle: Mapped[dict | None] = mapped_column(JSON, nullable=True)


GOV_OFFICIAL_HISTORY_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_funcionario_historia_inmutable() RETURNS TRIGGER AS $$ "
    "BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_OFFICIAL_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_official_history_no_update BEFORE UPDATE ON gov_official_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_funcionario_historia_inmutable()",
    "CREATE TRIGGER trg_gov_official_history_no_delete BEFORE DELETE ON gov_official_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_funcionario_historia_inmutable()",
    "CREATE TRIGGER trg_gov_official_history_no_truncate BEFORE TRUNCATE ON gov_official_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_funcionario_historia_inmutable()",
)

GOV_OFFICIALS_NOT_DELETABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_funcionario_no_borrable() RETURNS TRIGGER AS $$ "
    "BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_OFFICIAL_NOT_DELETABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_officials_no_delete BEFORE DELETE ON gov_officials FOR EACH ROW EXECUTE FUNCTION kontrol_gov_funcionario_no_borrable()",
    "CREATE TRIGGER trg_gov_officials_no_truncate BEFORE TRUNCATE ON gov_officials FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_funcionario_no_borrable()",
)

GOV_ASSIGNMENT_HISTORY_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_asignacion_historia_inmutable() RETURNS TRIGGER AS $$ "
    "BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_ASSIGNMENT_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_assignment_history_no_update BEFORE UPDATE ON gov_assignment_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_asignacion_historia_inmutable()",
    "CREATE TRIGGER trg_gov_assignment_history_no_delete BEFORE DELETE ON gov_assignment_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_asignacion_historia_inmutable()",
    "CREATE TRIGGER trg_gov_assignment_history_no_truncate BEFORE TRUNCATE ON gov_assignment_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_asignacion_historia_inmutable()",
)

GOV_ASSIGNMENTS_NOT_DELETABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_asignacion_no_borrable() RETURNS TRIGGER AS $$ "
    "BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_ASSIGNMENT_NOT_DELETABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_assignments_no_delete BEFORE DELETE ON gov_assignments FOR EACH ROW EXECUTE FUNCTION kontrol_gov_asignacion_no_borrable()",
    "CREATE TRIGGER trg_gov_assignments_no_truncate BEFORE TRUNCATE ON gov_assignments FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_asignacion_no_borrable()",
)

GOV_ASSIGNMENTS_NOT_EDITABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_asignacion_no_editable() RETURNS TRIGGER AS $$ "
    "BEGIN IF OLD.status <> 'BORRADOR' AND (NEW.official_id IS DISTINCT FROM OLD.official_id OR NEW.position_id IS DISTINCT FROM OLD.position_id OR NEW.figura IS DISTINCT FROM OLD.figura OR NEW.grupo IS DISTINCT FROM OLD.grupo OR NEW.cargo_origen_id IS DISTINCT FROM OLD.cargo_origen_id OR NEW.act_id IS DISTINCT FROM OLD.act_id OR NEW.desde IS DISTINCT FROM OLD.desde OR NEW.hasta IS DISTINCT FROM OLD.hasta OR NEW.fundamento IS DISTINCT FROM OLD.fundamento OR NEW.rendicion IS DISTINCT FROM OLD.rendicion OR NEW.company_id IS DISTINCT FROM OLD.company_id OR NEW.policy_id IS DISTINCT FROM OLD.policy_id OR NEW.policy_version IS DISTINCT FROM OLD.policy_version OR NEW.regla::text IS DISTINCT FROM OLD.regla::text) THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_ASSIGNMENT_NOT_EDITABLE'; END IF; IF OLD.status IN ('REVOCADO','FINALIZADO','DESCARTADO') AND (NEW.status IS DISTINCT FROM OLD.status OR NEW.fin_efectivo IS DISTINCT FROM OLD.fin_efectivo) THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_ASSIGNMENT_NOT_EDITABLE'; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_assignments_no_editable BEFORE UPDATE ON gov_assignments FOR EACH ROW EXECUTE FUNCTION kontrol_gov_asignacion_no_editable()",
)

GOV_ASSIGNMENT_COMPETENCIES_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_asignacion_competencia_inmutable() RETURNS TRIGGER AS $$ "
    "DECLARE v_status VARCHAR(16); "
    "BEGIN IF TG_OP = 'INSERT' THEN SELECT status INTO v_status FROM gov_assignments WHERE id = NEW.assignment_id; "
    "ELSIF TG_OP = 'UPDATE' THEN SELECT status INTO v_status FROM gov_assignments WHERE id = OLD.assignment_id; "
    "ELSE SELECT status INTO v_status FROM gov_assignments WHERE id = OLD.assignment_id; END IF; "
    "IF v_status IS DISTINCT FROM 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_ASSIGNMENT_COMPETENCY_IMMUTABLE'; END IF; "
    "IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_assignment_competencies_immutable BEFORE INSERT OR UPDATE OR DELETE ON gov_assignment_competencies FOR EACH ROW EXECUTE FUNCTION kontrol_gov_asignacion_competencia_inmutable()",
)

GOV_ASSIGNMENTS_EXCLUSION_PG = (
    "CREATE EXTENSION IF NOT EXISTS btree_gist",
    "ALTER TABLE gov_assignments ADD CONSTRAINT ex_gov_assignments_ocupacion EXCLUDE USING gist (position_id WITH =, grupo WITH =, daterange(desde, COALESCE(fin_efectivo, hasta), '[]') WITH &&) WHERE (status = 'ACTIVO' AND grupo IN ('TITULARIDAD', 'TEMPORAL'))",
    "ALTER TABLE gov_assignments ADD CONSTRAINT ex_gov_assignments_delegacion EXCLUDE USING gist (position_id WITH =, official_id WITH =, daterange(desde, COALESCE(fin_efectivo, hasta), '[]') WITH &&) WHERE (status = 'ACTIVO' AND grupo = 'DELEGACION')",
)

for _sentencia in GOV_OFFICIAL_HISTORY_IMMUTABLE_PG:
    event.listen(GovernmentOfficialHistory.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_OFFICIALS_NOT_DELETABLE_PG:
    event.listen(GovernmentOfficial.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_ASSIGNMENT_HISTORY_IMMUTABLE_PG:
    event.listen(GovernmentAssignmentHistory.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_ASSIGNMENTS_NOT_DELETABLE_PG:
    event.listen(GovernmentAssignment.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_ASSIGNMENTS_NOT_EDITABLE_PG:
    event.listen(GovernmentAssignment.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_ASSIGNMENT_COMPETENCIES_IMMUTABLE_PG:
    event.listen(GovernmentAssignmentCompetency.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_ASSIGNMENTS_EXCLUSION_PG:
    event.listen(GovernmentAssignment.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

GOV_LINK_HISTORY_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_vinculo_historia_inmutable() RETURNS TRIGGER AS $$ "
    "BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_LINK_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_link_history_no_update BEFORE UPDATE ON gov_user_official_link_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_vinculo_historia_inmutable()",
    "CREATE TRIGGER trg_gov_link_history_no_delete BEFORE DELETE ON gov_user_official_link_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_vinculo_historia_inmutable()",
    "CREATE TRIGGER trg_gov_link_history_no_truncate BEFORE TRUNCATE ON gov_user_official_link_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_vinculo_historia_inmutable()",
)

GOV_ROLE_CATEGORY_HISTORY_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_categoria_historia_inmutable() RETURNS TRIGGER AS $$ "
    "BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_ROLE_CATEGORY_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_role_category_history_no_update BEFORE UPDATE ON gov_role_category_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_categoria_historia_inmutable()",
    "CREATE TRIGGER trg_gov_role_category_history_no_delete BEFORE DELETE ON gov_role_category_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_categoria_historia_inmutable()",
    "CREATE TRIGGER trg_gov_role_category_history_no_truncate BEFORE TRUNCATE ON gov_role_category_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_categoria_historia_inmutable()",
)

GOV_POLICY_HISTORY_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_politica_historia_inmutable() RETURNS TRIGGER AS $$ "
    "BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_POLICY_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_policy_history_no_update BEFORE UPDATE ON gov_identity_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_politica_historia_inmutable()",
    "CREATE TRIGGER trg_gov_policy_history_no_delete BEFORE DELETE ON gov_identity_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_politica_historia_inmutable()",
    "CREATE TRIGGER trg_gov_policy_history_no_truncate BEFORE TRUNCATE ON gov_identity_policy_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_politica_historia_inmutable()",
)

GOV_LINKS_NOT_DELETABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_vinculo_no_borrable() RETURNS TRIGGER AS $$ "
    "BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_LINK_NOT_DELETABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_links_no_delete BEFORE DELETE ON gov_user_official_links FOR EACH ROW EXECUTE FUNCTION kontrol_gov_vinculo_no_borrable()",
    "CREATE TRIGGER trg_gov_links_no_truncate BEFORE TRUNCATE ON gov_user_official_links FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_vinculo_no_borrable()",
)

GOV_LINKS_NOT_EDITABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_vinculo_no_editable() RETURNS TRIGGER AS $$ "
    "BEGIN IF OLD.status <> 'BORRADOR' AND (NEW.user_id IS DISTINCT FROM OLD.user_id OR NEW.official_id IS DISTINCT FROM OLD.official_id OR NEW.desde IS DISTINCT FROM OLD.desde OR NEW.codigo IS DISTINCT FROM OLD.codigo) THEN "
    "RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_LINK_NOT_EDITABLE'; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_links_no_editable BEFORE UPDATE ON gov_user_official_links FOR EACH ROW EXECUTE FUNCTION kontrol_gov_vinculo_no_editable()",
)

GOV_LINKS_EXCLUSION_PG = (
    "CREATE EXTENSION IF NOT EXISTS btree_gist",
    "ALTER TABLE gov_user_official_links ADD CONSTRAINT ex_gov_links_cuenta EXCLUDE USING gist (company_id WITH =, user_id WITH =, daterange(desde, COALESCE(fin_efectivo, hasta), '[]') WITH &&) WHERE (status = 'ACTIVO')",
    "ALTER TABLE gov_user_official_links ADD CONSTRAINT ex_gov_links_funcionario EXCLUDE USING gist (company_id WITH =, official_id WITH =, daterange(desde, COALESCE(fin_efectivo, hasta), '[]') WITH &&) WHERE (status = 'ACTIVO')",
)

GOV_ROLE_CATEGORY_EXCLUSION_PG = (
    "CREATE EXTENSION IF NOT EXISTS btree_gist",
    "ALTER TABLE gov_role_categories ADD CONSTRAINT ex_gov_role_categories EXCLUDE USING gist (company_id WITH =, role_id WITH =, categoria WITH =, daterange(desde, hasta, '[]') WITH &&) WHERE (status = 'ACTIVA')",
)

for _sentencia in GOV_LINK_HISTORY_IMMUTABLE_PG:
    event.listen(GovernmentUserOfficialLinkHistory.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_ROLE_CATEGORY_HISTORY_IMMUTABLE_PG:
    event.listen(GovernmentRoleCategoryHistory.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_POLICY_HISTORY_IMMUTABLE_PG:
    event.listen(GovernmentIdentityPolicyHistory.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_LINKS_NOT_DELETABLE_PG:
    event.listen(GovernmentUserOfficialLink.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_LINKS_NOT_EDITABLE_PG:
    event.listen(GovernmentUserOfficialLink.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_LINKS_EXCLUSION_PG:
    event.listen(GovernmentUserOfficialLink.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_ROLE_CATEGORY_EXCLUSION_PG:
    event.listen(GovernmentRoleCategory.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


class GovernmentGuaranteeIssuer(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_guarantee_issuers"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    rif: Mapped[str] = mapped_column(String(20), nullable=False)
    bank_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_banks.id"), nullable=True, index=True)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="ACTIVO", server_default="ACTIVO")

    __table_args__ = (
        CheckConstraint(f"tipo IN ({en(TIPOS_EMISOR)})", name="ck_gov_guarantee_issuers_tipo"),
        CheckConstraint(f"estado IN ({en(ESTADOS_EMISOR)})", name="ck_gov_guarantee_issuers_estado"),
        CheckConstraint("(tipo = 'BANCO') = (bank_id IS NOT NULL)", name="ck_gov_guarantee_issuers_banco"),
        UniqueConstraint("company_id", "rif", name="uq_gov_guarantee_issuers_company_rif"),
    )


class GovernmentGuaranteeRequirement(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_guarantee_requirements"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    regla_codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    regla: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    etapa: Mapped[str] = mapped_column(String(24), nullable=False)
    nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    forma: Mapped[str] = mapped_column(String(16), nullable=False)
    porcentaje: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    monto_fijo: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    moneda: Mapped[str | None] = mapped_column(String(3), nullable=True)
    vigencia_minima_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    fundamento: Mapped[str] = mapped_column(String(1000), nullable=False)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    document_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=False, index=True)
    version_numero: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    registrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registrado_por: Mapped[str] = mapped_column(String(36), nullable=False)
    official_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=True, index=True)

    __table_args__ = (
        CheckConstraint(f"tipo IN ({en(TIPOS_GARANTIA)})", name="ck_gov_guarantee_requirements_tipo"),
        CheckConstraint(f"etapa IN ({en(ETAPAS_GARANTIA)})", name="ck_gov_guarantee_requirements_etapa"),
        CheckConstraint(f"forma IN ({en(FORMAS_GARANTIA)})", name="ck_gov_guarantee_requirements_forma"),
        CheckConstraint("numero >= 1", name="ck_gov_guarantee_requirements_numero"),
        CheckConstraint("(forma = 'PORCENTAJE') = (porcentaje IS NOT NULL)", name="ck_gov_guarantee_requirements_porcentaje_presencia"),
        CheckConstraint("(forma = 'MONTO_FIJO') = (monto_fijo IS NOT NULL)", name="ck_gov_guarantee_requirements_monto_presencia"),
        CheckConstraint("(forma = 'MONTO_FIJO') = (moneda IS NOT NULL)", name="ck_gov_guarantee_requirements_moneda_presencia"),
        CheckConstraint("porcentaje IS NULL OR (porcentaje > 0 AND porcentaje <= 100)", name="ck_gov_guarantee_requirements_porcentaje_valor"),
        CheckConstraint("monto_fijo IS NULL OR monto_fijo > 0", name="ck_gov_guarantee_requirements_monto_valor"),
        CheckConstraint(f"moneda IS NULL OR moneda IN ({en(MONEDAS_LIMITE)})", name="ck_gov_guarantee_requirements_moneda_valor"),
        CheckConstraint("tipo <> 'OTRA' OR nombre IS NOT NULL", name="ck_gov_guarantee_requirements_otra_nombre"),
        UniqueConstraint("company_id", "file_id", "numero", name="uq_gov_guarantee_requirements_company_file_numero"),
    )


class GovernmentGuaranteeInstrument(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_guarantee_instruments"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    requirement_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_guarantee_requirements.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    etapa: Mapped[str] = mapped_column(String(24), nullable=False)
    offer_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_offers.id"), nullable=False, index=True)
    decision_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_decisions.id"), nullable=True, index=True)
    issuer_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_guarantee_issuers.id"), nullable=False, index=True)
    referencia_emisor: Mapped[str] = mapped_column(String(60), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigente_hasta: Mapped[date] = mapped_column(Date, nullable=False)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    document_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=False, index=True)
    version_numero: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    observacion: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    origen: Mapped[str] = mapped_column(String(16), nullable=False, default="REGISTRO", server_default="REGISTRO")
    antecesor_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_guarantee_instruments.id"), nullable=True, unique=True)
    estado: Mapped[str] = mapped_column(String(16), nullable=False, default="REGISTRADA", server_default="REGISTRADA")
    afectada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    registrada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registrada_por: Mapped[str] = mapped_column(String(36), nullable=False)
    official_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=True, index=True)

    __table_args__ = (
        CheckConstraint(f"tipo IN ({en(TIPOS_GARANTIA)})", name="ck_gov_guarantee_instruments_tipo"),
        CheckConstraint(f"etapa IN ({en(ETAPAS_GARANTIA)})", name="ck_gov_guarantee_instruments_etapa"),
        CheckConstraint(f"origen IN ({en(ORIGENES_GARANTIA)})", name="ck_gov_guarantee_instruments_origen"),
        CheckConstraint(f"estado IN ({en(ESTADOS_GARANTIA)})", name="ck_gov_guarantee_instruments_estado"),
        CheckConstraint("numero >= 1", name="ck_gov_guarantee_instruments_numero"),
        CheckConstraint("monto > 0", name="ck_gov_guarantee_instruments_monto"),
        CheckConstraint(f"moneda IN ({en(MONEDAS_LIMITE)})", name="ck_gov_guarantee_instruments_moneda"),
        CheckConstraint("vigente_desde <= vigente_hasta", name="ck_gov_guarantee_instruments_vigencia"),
        CheckConstraint("fecha_emision <= vigente_hasta", name="ck_gov_guarantee_instruments_emision"),
        CheckConstraint("(origen = 'REGISTRO') = (antecesor_id IS NULL)", name="ck_gov_guarantee_instruments_antecesor"),
        CheckConstraint("(estado = 'REGISTRADA') = (afectada_en IS NULL)", name="ck_gov_guarantee_instruments_afectada"),
        UniqueConstraint("company_id", "file_id", "numero", name="uq_gov_guarantee_instruments_company_file_numero"),
        Index(
            "uq_gov_guarantee_instruments_emisor_referencia",
            "company_id",
            "issuer_id",
            "referencia_emisor",
            unique=True,
            postgresql_where=text("estado = 'REGISTRADA'"),
            sqlite_where=text("estado = 'REGISTRADA'"),
        ),
    )


class GovernmentGuaranteeEvent(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "gov_guarantee_events"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_guarantee_instruments.id"), nullable=False, index=True)
    accion: Mapped[str] = mapped_column(String(16), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    act_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=True, index=True)
    cargo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=True, index=True)
    document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    document_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=True)
    version_numero: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nuevo_instrument_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_guarantee_instruments.id"), nullable=True, index=True)
    monto: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    moneda: Mapped[str | None] = mapped_column(String(3), nullable=True)
    precondicion: Mapped[str | None] = mapped_column(String(24), nullable=True)
    precondicion_detalle: Mapped[str | None] = mapped_column(String(300), nullable=True)
    registrada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registrada_por: Mapped[str] = mapped_column(String(36), nullable=False)
    official_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=True, index=True)

    __table_args__ = (
        CheckConstraint(f"accion IN ({en(ACCIONES_GARANTIA)})", name="ck_gov_guarantee_events_accion"),
        CheckConstraint("(accion IN ('LIBERACION', 'EJECUCION')) = (act_id IS NOT NULL)", name="ck_gov_guarantee_events_acto"),
        CheckConstraint("accion = 'REGISTRO' OR motivo IS NOT NULL", name="ck_gov_guarantee_events_motivo"),
        CheckConstraint("(accion IN ('RENOVACION', 'SUSTITUCION')) = (nuevo_instrument_id IS NOT NULL)", name="ck_gov_guarantee_events_nuevo"),
        CheckConstraint("(accion = 'EJECUCION') = (monto IS NOT NULL)", name="ck_gov_guarantee_events_monto_presencia"),
        CheckConstraint("(monto IS NULL) = (moneda IS NULL)", name="ck_gov_guarantee_events_moneda_presencia"),
        CheckConstraint("monto IS NULL OR monto > 0", name="ck_gov_guarantee_events_monto_valor"),
        CheckConstraint("(accion = 'LIBERACION') = (precondicion IS NOT NULL)", name="ck_gov_guarantee_events_precondicion_presencia"),
        CheckConstraint(f"precondicion IS NULL OR precondicion IN ({en(PRECONDICIONES_LIBERACION)})", name="ck_gov_guarantee_events_precondicion_valor"),
        CheckConstraint("(document_id IS NULL) = (document_version_id IS NULL)", name="ck_gov_guarantee_events_documento"),
        Index(
            "uq_gov_guarantee_events_registro",
            "instrument_id",
            unique=True,
            postgresql_where=text("accion = 'REGISTRO'"),
            sqlite_where=text("accion = 'REGISTRO'"),
        ),
        Index(
            "uq_gov_guarantee_events_final",
            "instrument_id",
            unique=True,
            postgresql_where=text("accion <> 'REGISTRO'"),
            sqlite_where=text("accion <> 'REGISTRO'"),
        ),
    )


_GOV_GUARANTEE_IMMUTABLE_DDL = (
    """
    CREATE OR REPLACE FUNCTION kontrol_gov_guarantee_immutable()
    RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'Los requisitos y actuaciones de garantías son inmutables';
    END;
    $$ LANGUAGE plpgsql;
    """,
)

_GOV_GUARANTEE_INSTRUMENT_GUARD_DDL = (
    """
    CREATE OR REPLACE FUNCTION kontrol_gov_guarantee_instrument_guard()
    RETURNS trigger AS $$
    BEGIN
        IF TG_OP = 'DELETE' OR TG_OP = 'TRUNCATE' THEN
            RAISE EXCEPTION 'Las garantías no se borran';
        END IF;
        IF TG_OP = 'UPDATE' THEN
            IF OLD.estado = 'REGISTRADA'
               AND NEW.estado IN ('RENOVADA', 'SUSTITUIDA', 'LIBERADA', 'EJECUTADA')
               AND NEW.afectada_en IS NOT NULL
               AND (to_jsonb(NEW) - 'estado' - 'afectada_en' - 'updated_at') = (to_jsonb(OLD) - 'estado' - 'afectada_en' - 'updated_at') THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'La garantía registrada solo cambia una vez a su estado final';
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """,
)

_GOV_GUARANTEE_ISSUER_NO_DELETE_DDL = (
    """
    CREATE OR REPLACE FUNCTION kontrol_gov_guarantee_issuer_no_delete()
    RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'Los emisores de garantías no se borran';
    END;
    $$ LANGUAGE plpgsql;
    """,
)

_gov_guarantee_immutable_modelos = (
    GovernmentGuaranteeRequirement,
    GovernmentGuaranteeEvent,
)
for _modelo_garantia in _gov_guarantee_immutable_modelos:
    _tabla = _modelo_garantia.__table__
    _nombre_corto = _modelo_garantia.__tablename__.split("_", 1)[-1]
    event.listen(
        _tabla,
        "after_create",
        DDL(_GOV_GUARANTEE_IMMUTABLE_DDL[0]).execute_if(dialect="postgresql"),
    )
    for _accion, _momento in (
        ("update", "BEFORE UPDATE"),
        ("delete", "BEFORE DELETE"),
        ("truncate", "BEFORE TRUNCATE"),
    ):
        _trigger = f"""
        CREATE TRIGGER trg_{_nombre_corto}_immutable_{_accion}
        {_momento} ON {_modelo_garantia.__tablename__}
        FOR EACH {"ROW" if _accion != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_guarantee_immutable();
        """
        event.listen(
            _tabla,
            "after_create",
            DDL(_trigger).execute_if(dialect="postgresql"),
        )

class GovernmentRenditionFile(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    __tablename__ = "gov_rendition_files"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    numero_version: Mapped[int] = mapped_column(Integer, nullable=False)
    anterior_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_rendition_files.id"), nullable=True)
    denominacion: Mapped[str] = mapped_column(String(200), nullable=False)
    ejercicio: Mapped[int | None] = mapped_column(Integer, nullable=True)
    periodo_desde: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_hasta: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_corte: Mapped[date] = mapped_column(Date, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    assignment_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_assignments.id"), nullable=False, index=True)
    responsable: Mapped[dict] = mapped_column(JSON, nullable=False)
    responsable_official_id: Mapped[str] = mapped_column(String(36), nullable=False)
    estado: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    formado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    formado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    snapshot_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    informe_storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    informe_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    informe_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    participacion_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    participacion_oficio: Mapped[str | None] = mapped_column(String(100), nullable=True)
    participacion_registrada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    participacion_registrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    calificacion: Mapped[str | None] = mapped_column(String(10), nullable=True)
    calificacion_organo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    calificacion_informe_numero: Mapped[str | None] = mapped_column(String(50), nullable=True)
    calificacion_informe_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    calificacion_fundamento: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    calificacion_registrada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    calificacion_registrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fenecimiento_auto_numero: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fenecimiento_auto_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    fenecimiento_fundamento: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    fenecimiento_registrado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    fenecimiento_registrado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sustitucion_motivo: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", "numero_version", name="uq_gov_rendition_files_company_code_version"),
        CheckConstraint("numero_version >= 1", name="ck_gov_rendition_files_version_positive"),
        CheckConstraint("periodo_desde <= periodo_hasta", name="ck_gov_rendition_files_period"),
        CheckConstraint("fecha_corte >= periodo_desde AND fecha_corte <= periodo_hasta", name="ck_gov_rendition_files_corte"),
        CheckConstraint("estado IN ('EN_FORMACION', 'FORMADA', 'PARTICIPADA', 'CALIFICADA', 'FENECIDA', 'SUSTITUIDA')", name="ck_gov_rendition_files_estado"),
        CheckConstraint("estado = 'EN_FORMACION' OR (snapshot_sha256 IS NOT NULL AND informe_sha256 IS NOT NULL)", name="ck_gov_rendition_files_formada_hashes"),
        CheckConstraint("(estado IN ('CALIFICADA', 'FENECIDA')) = (calificacion IS NOT NULL)", name="ck_gov_rendition_files_calificacion"),
    )


class GovernmentRenditionPiece(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    __tablename__ = "gov_rendition_pieces"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_rendition_files.id"), nullable=False, index=True)
    audit_event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    ordinal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    proceso: Mapped[str] = mapped_column(String(16), nullable=False)
    accion: Mapped[str] = mapped_column(String(80), nullable=False)
    entidad: Mapped[str] = mapped_column(String(80), nullable=False)
    entidad_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    referencia: Mapped[str] = mapped_column(String(300), nullable=False)
    objeto: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    documentos: Mapped[list] = mapped_column(JSON, nullable=False)
    huella: Mapped[str] = mapped_column(String(64), nullable=False)
    incorporada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    incorporada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("file_id", "audit_event_id", name="uq_gov_rendition_pieces_file_event"),
        UniqueConstraint("file_id", "ordinal", name="uq_gov_rendition_pieces_file_ordinal"),
    )


_GOV_RENDITION_FILE_IMMUTABLE = """
CREATE OR REPLACE FUNCTION kontrol_gov_rendition_file_immutable()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Los expedientes de rendicion no se pueden eliminar';
    ELSIF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION 'Los expedientes de rendicion no se pueden truncar';
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.snapshot_sha256 IS NOT NULL THEN
            IF NEW.snapshot::text IS DISTINCT FROM OLD.snapshot::text
                OR NEW.snapshot_sha256 IS DISTINCT FROM OLD.snapshot_sha256
                OR NEW.informe_storage_key IS DISTINCT FROM OLD.informe_storage_key
                OR NEW.informe_sha256 IS DISTINCT FROM OLD.informe_sha256
                OR NEW.informe_bytes IS DISTINCT FROM OLD.informe_bytes
                OR NEW.denominacion IS DISTINCT FROM OLD.denominacion
                OR NEW.ejercicio IS DISTINCT FROM OLD.ejercicio
                OR NEW.periodo_desde IS DISTINCT FROM OLD.periodo_desde
                OR NEW.periodo_hasta IS DISTINCT FROM OLD.periodo_hasta
                OR NEW.fecha_corte IS DISTINCT FROM OLD.fecha_corte
                OR NEW.observaciones IS DISTINCT FROM OLD.observaciones
                OR NEW.assignment_id IS DISTINCT FROM OLD.assignment_id
                OR NEW.responsable::text IS DISTINCT FROM OLD.responsable::text
                OR NEW.responsable_official_id IS DISTINCT FROM OLD.responsable_official_id
                OR NEW.codigo IS DISTINCT FROM OLD.codigo
                OR NEW.numero_version IS DISTINCT FROM OLD.numero_version THEN
                RAISE EXCEPTION 'No se pueden modificar campos congelados de un expediente formado';
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

_GOV_RENDITION_PIECE_IMMUTABLE = """
CREATE OR REPLACE FUNCTION kontrol_gov_rendition_piece_immutable()
RETURNS TRIGGER AS $$
DECLARE
    v_estado TEXT;
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION 'Las piezas de rendicion no se pueden truncar';
    END IF;

    SELECT estado INTO v_estado
    FROM gov_rendition_files
    WHERE id = COALESCE(OLD.file_id, NEW.file_id);

    IF TG_OP = 'DELETE' THEN
        IF v_estado IS DISTINCT FROM 'EN_FORMACION' THEN
            RAISE EXCEPTION 'Solo se pueden eliminar piezas en formacion';
        END IF;
    ELSIF TG_OP = 'UPDATE' THEN
        -- Solo se permite cambiar ordinal si el padre esta en EN_FORMACION
        IF NEW.ordinal IS DISTINCT FROM OLD.ordinal THEN
            IF v_estado IS DISTINCT FROM 'EN_FORMACION' THEN
                RAISE EXCEPTION 'Solo se puede reordenar en formacion';
            END IF;
        ELSE
            -- Cualquier otro cambio esta prohibido
            RAISE EXCEPTION 'Las piezas de rendicion no se pueden actualizar';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

event.listen(
    GovernmentRenditionFile.__table__,
    "after_create",
    DDL(_GOV_RENDITION_FILE_IMMUTABLE).execute_if(dialect="postgresql"),
)

for _rend_file_action, _rend_file_momento in (
    ("update", "BEFORE UPDATE"),
    ("delete", "BEFORE DELETE"),
    ("truncate", "BEFORE TRUNCATE"),
):
    _rend_file_trigger = f"""
    CREATE TRIGGER trg_gov_rendition_files_immutable_{_rend_file_action}
    {_rend_file_momento} ON gov_rendition_files
    FOR EACH {"ROW" if _rend_file_action != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_rendition_file_immutable();
    """
    event.listen(
        GovernmentRenditionFile.__table__,
        "after_create",
        DDL(_rend_file_trigger).execute_if(dialect="postgresql"),
    )

event.listen(
    GovernmentRenditionPiece.__table__,
    "after_create",
    DDL(_GOV_RENDITION_PIECE_IMMUTABLE).execute_if(dialect="postgresql"),
)

for _rend_piece_action, _rend_piece_momento in (
    ("update", "BEFORE UPDATE"),
    ("delete", "BEFORE DELETE"),
    ("truncate", "BEFORE TRUNCATE"),
):
    _rend_piece_trigger = f"""
    CREATE TRIGGER trg_gov_rendition_pieces_immutable_{_rend_piece_action}
    {_rend_piece_momento} ON gov_rendition_pieces
    FOR EACH {"ROW" if _rend_piece_action != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_rendition_piece_immutable();
    """
    event.listen(
        GovernmentRenditionPiece.__table__,
        "after_create",
        DDL(_rend_piece_trigger).execute_if(dialect="postgresql"),
    )

event.listen(
    GovernmentGuaranteeInstrument.__table__,
    "after_create",
    DDL(_GOV_GUARANTEE_INSTRUMENT_GUARD_DDL[0]).execute_if(dialect="postgresql"),
)
for _accion, _momento in (
    ("update", "BEFORE UPDATE"),
    ("delete", "BEFORE DELETE"),
    ("truncate", "BEFORE TRUNCATE"),
):
    _trigger = f"""
    CREATE TRIGGER trg_gov_guarantee_instruments_guard_{_accion}
    {_momento} ON gov_guarantee_instruments
    FOR EACH {"ROW" if _accion != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_guarantee_instrument_guard();
    """
    event.listen(
        GovernmentGuaranteeInstrument.__table__,
        "after_create",
        DDL(_trigger).execute_if(dialect="postgresql"),
    )

event.listen(
    GovernmentGuaranteeIssuer.__table__,
    "after_create",
    DDL(_GOV_GUARANTEE_ISSUER_NO_DELETE_DDL[0]).execute_if(dialect="postgresql"),
)
for _accion, _momento in (
    ("delete", "BEFORE DELETE"),
    ("truncate", "BEFORE TRUNCATE"),
):
    _trigger = f"""
    CREATE TRIGGER trg_gov_guarantee_issuers_no_{_accion}
    {_momento} ON gov_guarantee_issuers
    FOR EACH {"ROW" if _accion != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_guarantee_issuer_no_delete();
    """
    event.listen(
        GovernmentGuaranteeIssuer.__table__,
        "after_create",
        DDL(_trigger).execute_if(dialect="postgresql"),
    )


class GovernmentHandoverAct(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    __tablename__ = "gov_handover_acts"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    ambito: Mapped[str] = mapped_column(String(10), nullable=False)
    unit_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    assignment_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_assignments.id"), nullable=False, index=True)
    saliente: Mapped[dict] = mapped_column(JSON, nullable=False)
    receptor_official_id: Mapped[str] = mapped_column(String(36), nullable=False)
    receptor_assignment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    receptor: Mapped[dict] = mapped_column(JSON, nullable=False)
    modalidad: Mapped[str] = mapped_column(String(24), nullable=False)
    testigos: Mapped[list] = mapped_column(JSON, nullable=False)
    auditor_official_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    motivo: Mapped[str] = mapped_column(String(1000), nullable=False)
    fundamento: Mapped[str] = mapped_column(String(1000), nullable=False)
    lugar: Mapped[str] = mapped_column(String(200), nullable=False)
    fecha_corte: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_suscripcion: Mapped[date | None] = mapped_column(Date, nullable=True)
    errores_deficiencias: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    suscrita_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    suscrita_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    snapshot_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    informe_storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    informe_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    informe_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remision_uai_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    remision_uai_registrada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    verificacion_numero: Mapped[str | None] = mapped_column(String(50), nullable=True)
    verificacion_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    verificacion_resultado: Mapped[str | None] = mapped_column(String(20), nullable=True)
    verificacion_fundamento: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    verificada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    verificada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "assignment_id", name="uq_gov_handover_acts_company_assignment"),
        CheckConstraint("estado IN ('BORRADOR', 'SUSCRITA', 'VERIFICADA')", name="ck_gov_handover_acts_estado"),
        CheckConstraint("ambito IN ('ENTE', 'UNIDAD')", name="ck_gov_handover_acts_ambito"),
        CheckConstraint("modalidad IN ('ENTREGA', 'LEVANTADA_POR_RECEPTOR')", name="ck_gov_handover_acts_modalidad"),
        CheckConstraint("estado = 'BORRADOR' OR (snapshot_sha256 IS NOT NULL AND informe_sha256 IS NOT NULL)", name="ck_gov_handover_acts_suscrita_hashes"),
        CheckConstraint("(estado = 'VERIFICADA') = (verificacion_resultado IS NOT NULL)", name="ck_gov_handover_acts_verificacion"),
        CheckConstraint("verificacion_resultado IS NULL OR verificacion_resultado IN ('CONFORME', 'CON_OBSERVACIONES')", name="ck_gov_handover_acts_verificacion_resultado"),
        CheckConstraint("modalidad <> 'LEVANTADA_POR_RECEPTOR' OR auditor_official_id IS NOT NULL", name="ck_gov_handover_acts_levantada_auditor"),
    )


class GovernmentHandoverAnnex(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    __tablename__ = "gov_handover_annexes"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    act_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_handover_acts.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(8), nullable=False)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    obligatorio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    generable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    incluir_generado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    documento_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    constancia: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    contenido: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    documentos: Mapped[list | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("act_id", "codigo", name="uq_gov_handover_annexes_act_codigo"),
        CheckConstraint("incluir_generado = false OR generable = true", name="ck_gov_handover_annexes_generable"),
    )


class GovernmentHandoverObservation(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    __tablename__ = "gov_handover_observations"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    act_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_handover_acts.id"), nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    texto: Mapped[str] = mapped_column(String(2000), nullable=False)
    registrada_por: Mapped[str] = mapped_column(String(36), nullable=False)
    registrada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


_GOV_HANDOVER_ACT_IMMUTABLE = """
CREATE OR REPLACE FUNCTION kontrol_gov_handover_act_immutable()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Las actas de entrega no se pueden eliminar';
    ELSIF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION 'Las actas de entrega no se pueden truncar';
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.snapshot_sha256 IS NOT NULL THEN
            IF NEW.motivo IS DISTINCT FROM OLD.motivo
                OR NEW.fundamento IS DISTINCT FROM OLD.fundamento
                OR NEW.lugar IS DISTINCT FROM OLD.lugar
                OR NEW.fecha_corte IS DISTINCT FROM OLD.fecha_corte
                OR NEW.saliente::text IS DISTINCT FROM OLD.saliente::text
                OR NEW.receptor::text IS DISTINCT FROM OLD.receptor::text
                OR NEW.testigos::text IS DISTINCT FROM OLD.testigos::text
                OR NEW.modalidad IS DISTINCT FROM OLD.modalidad
                OR NEW.assignment_id IS DISTINCT FROM OLD.assignment_id
                OR NEW.receptor_official_id IS DISTINCT FROM OLD.receptor_official_id
                OR NEW.auditor_official_id IS DISTINCT FROM OLD.auditor_official_id
                OR NEW.snapshot::text IS DISTINCT FROM OLD.snapshot::text
                OR NEW.snapshot_sha256 IS DISTINCT FROM OLD.snapshot_sha256
                OR NEW.informe_storage_key IS DISTINCT FROM OLD.informe_storage_key
                OR NEW.informe_sha256 IS DISTINCT FROM OLD.informe_sha256
                OR NEW.informe_bytes IS DISTINCT FROM OLD.informe_bytes
                OR NEW.fecha_suscripcion IS DISTINCT FROM OLD.fecha_suscripcion
                OR NEW.errores_deficiencias IS DISTINCT FROM OLD.errores_deficiencias
                OR NEW.codigo IS DISTINCT FROM OLD.codigo THEN
                RAISE EXCEPTION 'No se pueden modificar campos congelados de un acta suscrita';
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

_GOV_HANDOVER_ANNEX_IMMUTABLE = """
CREATE OR REPLACE FUNCTION kontrol_gov_handover_annex_immutable()
RETURNS TRIGGER AS $$
DECLARE
    v_estado TEXT;
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION 'Los anexos de actas no se pueden truncar';
    END IF;

    SELECT estado INTO v_estado
    FROM gov_handover_acts
    WHERE id = COALESCE(OLD.act_id, NEW.act_id);

    IF TG_OP = 'DELETE' THEN
        IF v_estado IS DISTINCT FROM 'BORRADOR' THEN
            RAISE EXCEPTION 'Solo se pueden eliminar anexos en borrador';
        END IF;
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        IF v_estado IS DISTINCT FROM 'BORRADOR' THEN
            RAISE EXCEPTION 'Los anexos no se pueden actualizar fuera de borrador';
        END IF;
        IF NEW.company_id IS DISTINCT FROM OLD.company_id
            OR NEW.act_id IS DISTINCT FROM OLD.act_id
            OR NEW.codigo IS DISTINCT FROM OLD.codigo THEN
            RAISE EXCEPTION 'Los anexos no pueden cambiar de acta, empresa ni código';
        END IF;
        RETURN NEW;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

_GOV_HANDOVER_OBSERVATION_IMMUTABLE = """
CREATE OR REPLACE FUNCTION kontrol_gov_handover_observation_immutable()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Las observaciones de actas no se pueden actualizar';
    ELSIF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Las observaciones de actas no se pueden eliminar';
    ELSIF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION 'Las observaciones de actas no se pueden truncar';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

event.listen(
    GovernmentHandoverAct.__table__,
    "after_create",
    DDL(_GOV_HANDOVER_ACT_IMMUTABLE).execute_if(dialect="postgresql"),
)

for _hand_act_action, _hand_act_momento in (
    ("update", "BEFORE UPDATE"),
    ("delete", "BEFORE DELETE"),
    ("truncate", "BEFORE TRUNCATE"),
):
    _hand_act_trigger = f"""
    CREATE TRIGGER trg_gov_handover_acts_immutable_{_hand_act_action}
    {_hand_act_momento} ON gov_handover_acts
    FOR EACH {"ROW" if _hand_act_action != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_handover_act_immutable();
    """
    event.listen(
        GovernmentHandoverAct.__table__,
        "after_create",
        DDL(_hand_act_trigger).execute_if(dialect="postgresql"),
    )

event.listen(
    GovernmentHandoverAnnex.__table__,
    "after_create",
    DDL(_GOV_HANDOVER_ANNEX_IMMUTABLE).execute_if(dialect="postgresql"),
)

for _hand_annex_action, _hand_annex_momento in (
    ("update", "BEFORE UPDATE"),
    ("delete", "BEFORE DELETE"),
    ("truncate", "BEFORE TRUNCATE"),
):
    _hand_annex_trigger = f"""
    CREATE TRIGGER trg_gov_handover_annexes_immutable_{_hand_annex_action}
    {_hand_annex_momento} ON gov_handover_annexes
    FOR EACH {"ROW" if _hand_annex_action != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_handover_annex_immutable();
    """
    event.listen(
        GovernmentHandoverAnnex.__table__,
        "after_create",
        DDL(_hand_annex_trigger).execute_if(dialect="postgresql"),
    )

event.listen(
    GovernmentHandoverObservation.__table__,
    "after_create",
    DDL(_GOV_HANDOVER_OBSERVATION_IMMUTABLE).execute_if(dialect="postgresql"),
)

for _hand_obs_action, _hand_obs_momento in (
    ("update", "BEFORE UPDATE"),
    ("delete", "BEFORE DELETE"),
    ("truncate", "BEFORE TRUNCATE"),
):
    _hand_obs_trigger = f"""
    CREATE TRIGGER trg_gov_handover_observations_immutable_{_hand_obs_action}
    {_hand_obs_momento} ON gov_handover_observations
    FOR EACH {"ROW" if _hand_obs_action != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_handover_observation_immutable();
    """
    event.listen(
        GovernmentHandoverObservation.__table__,
        "after_create",
        DDL(_hand_obs_trigger).execute_if(dialect="postgresql"),
    )


TIPOS_ALERTA_ATIPICA = ("DUPLICIDAD", "PROVEEDOR_RELACIONADO", "AUTOAPROBACION", "FRACCIONAMIENTO", "OVERRIDE_FRECUENTE")
RESULTADOS_REVISION_ALERTA = ("SIN_OBSERVACION", "REQUIERE_SEGUIMIENTO")
GOV_ATYPICAL_ALERT_REVIEWS_IMMUTABLE_PG: tuple[str, ...] = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_atypical_alert_review_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_ATYPICAL_ALERT_REVIEW_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$",
    "CREATE TRIGGER trg_gov_atypical_alert_reviews_no_update BEFORE UPDATE ON gov_atypical_alert_reviews FOR EACH ROW EXECUTE FUNCTION kontrol_gov_atypical_alert_review_inmutable()",
    "CREATE TRIGGER trg_gov_atypical_alert_reviews_no_delete BEFORE DELETE ON gov_atypical_alert_reviews FOR EACH ROW EXECUTE FUNCTION kontrol_gov_atypical_alert_review_inmutable()",
    "CREATE TRIGGER trg_gov_atypical_alert_reviews_no_truncate BEFORE TRUNCATE ON gov_atypical_alert_reviews FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_atypical_alert_review_inmutable()",
)


class GovernmentAtypicalAlertReview(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Revisión de Control Interno de una alerta de operación atípica (CTL-07); única e inmutable."""

    __tablename__ = "gov_atypical_alert_reviews"
    __scope__ = Scope.COMPANY
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    clave: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[str] = mapped_column(String(24), nullable=False)
    resultado: Mapped[str] = mapped_column(String(24), nullable=False)
    observacion: Mapped[str] = mapped_column(Text, nullable=False)
    resumen: Mapped[str] = mapped_column(String(1000), nullable=False)
    revisada_por: Mapped[str] = mapped_column(String(36), nullable=False)
    revisada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        UniqueConstraint("company_id", "clave", name="uq_gov_atypical_alert_reviews_clave"),
        CheckConstraint(f"tipo IN ({en(TIPOS_ALERTA_ATIPICA)})", name="tipo"),
        CheckConstraint(f"resultado IN ({en(RESULTADOS_REVISION_ALERTA)})", name="resultado"),
        CheckConstraint("length(observacion) >= 10", name="observacion"),
    )


for _sentencia in GOV_ATYPICAL_ALERT_REVIEWS_IMMUTABLE_PG:
    event.listen(GovernmentAtypicalAlertReview.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

SOPORTES_MONTO_OFERTA = ("DOCUMENTO_OFERTA", "ACTA_APERTURA")
GOV_OFFER_AMOUNTS_IMMUTABLE_PG: tuple[str, ...] = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_offer_amount_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_OFFER_AMOUNT_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$",
    "CREATE TRIGGER trg_gov_procurement_offer_amounts_no_update BEFORE UPDATE ON gov_procurement_offer_amounts FOR EACH ROW EXECUTE FUNCTION kontrol_gov_offer_amount_inmutable()",
    "CREATE TRIGGER trg_gov_procurement_offer_amounts_no_delete BEFORE DELETE ON gov_procurement_offer_amounts FOR EACH ROW EXECUTE FUNCTION kontrol_gov_offer_amount_inmutable()",
    "CREATE TRIGGER trg_gov_procurement_offer_amounts_no_truncate BEFORE TRUNCATE ON gov_procurement_offer_amounts FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_offer_amount_inmutable()",
)


class GovernmentProcurementOfferAmount(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Monto declarado en una oferta recibida (PROC-06, OMA); de solo inserción y versionado."""

    __tablename__ = "gov_procurement_offer_amounts"
    __scope__ = Scope.COMPANY
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    offer_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_offers.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    monto_sin_iva: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tributos: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_con_tributos: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    soporte_tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    soporte_document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    soporte_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=False)
    soporte_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    reemplaza_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_procurement_offer_amounts.id"), nullable=True)
    registrada_por: Mapped[str] = mapped_column(String(36), nullable=False)
    registrada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        UniqueConstraint("company_id", "offer_id", "version", name="uq_gov_procurement_offer_amounts_version"),
        UniqueConstraint("reemplaza_id", name="uq_gov_procurement_offer_amounts_reemplaza"),
        CheckConstraint("version >= 1", name="version"),
        CheckConstraint(f"moneda IN ({en(MONEDAS_LIMITE)})", name="moneda"),
        CheckConstraint("monto_sin_iva >= 0", name="monto_sin_iva"),
        CheckConstraint("tributos >= 0", name="tributos"),
        CheckConstraint("total_con_tributos > 0", name="total_con_tributos"),
        CheckConstraint(f"soporte_tipo IN ({en(SOPORTES_MONTO_OFERTA)})", name="soporte_tipo"),
        CheckConstraint("(version = 1 AND reemplaza_id IS NULL AND motivo IS NULL) OR (version > 1 AND reemplaza_id IS NOT NULL AND motivo IS NOT NULL AND length(motivo) >= 10)", name="correccion"),
    )


for _sentencia in GOV_OFFER_AMOUNTS_IMMUTABLE_PG:
    event.listen(GovernmentProcurementOfferAmount.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


# CNT-01 · Contrato u orden derivada de la adjudicación (GOV-CNT-001).

TIPOS_INSTRUMENTO_CONTRATO = ("CONTRATO", "ORDEN_COMPRA", "ORDEN_SERVICIO")  # LCP art. 6, num. 32
ESTADOS_CONTRATO = ("BORRADOR", "FORMALIZADO")
PREFIJOS_INSTRUMENTO_CONTRATO: dict[str, str] = {"CONTRATO": "CT", "ORDEN_COMPRA": "OC", "ORDEN_SERVICIO": "OS"}

class GovernmentContract(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Contrato u orden de compra o de servicio derivada de una adjudicación (CNT-01)."""
    __tablename__ = "gov_contracts"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=False, index=True)
    decision_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_decisions.id"), nullable=False)
    offer_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_offers.id"), nullable=False, index=True)
    act_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=False)
    amount_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_offer_amounts.id"), nullable=False)
    estado: Mapped[str] = mapped_column(String(12), nullable=False, default="BORRADOR", server_default="BORRADOR")
    tipo: Mapped[str | None] = mapped_column(String(16), nullable=True)
    codigo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    numero: Mapped[int | None] = mapped_column(Integer, nullable=True)
    anio: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    expediente_numero: Mapped[str] = mapped_column(String(40), nullable=False)
    objeto: Mapped[str] = mapped_column(String(1000), nullable=False)
    descripcion_complementaria: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    decision_referencia: Mapped[str] = mapped_column(String(10), nullable=False)
    decision_fecha: Mapped[date] = mapped_column(Date, nullable=False)
    acto_etiqueta: Mapped[str] = mapped_column(String(400), nullable=False)
    oferta_referencia: Mapped[str] = mapped_column(String(12), nullable=False)
    contratista_nombre: Mapped[str] = mapped_column(String(300), nullable=False)
    contratista_documento: Mapped[str] = mapped_column(String(40), nullable=False)
    contratista_representante: Mapped[str | None] = mapped_column(String(200), nullable=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    fecha_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    referencia_instrumento: Mapped[str | None] = mapped_column(String(120), nullable=True)
    document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True)
    document_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=True)
    documento_version_numero: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    documento_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    documento_titulo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    firmante_cargo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=True)
    firmante_cargo_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    firmante_funcionario_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fecha_formalizacion: Mapped[date | None] = mapped_column(Date, nullable=True)
    formalizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    formalizado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    huella: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_contracts_company_codigo"),
        UniqueConstraint("decision_id", name="uq_gov_contracts_decision"),
        CheckConstraint(f"estado IN ({en(ESTADOS_CONTRATO)})", name="estado"),
        CheckConstraint(f"tipo IS NULL OR tipo IN ({en(TIPOS_INSTRUMENTO_CONTRATO)})", name="tipo"),
        CheckConstraint("monto > 0", name="monto"),
        CheckConstraint("length(moneda) = 3", name="moneda"),
        CheckConstraint("numero IS NULL OR numero >= 1", name="numero"),
        CheckConstraint("fecha_fin IS NULL OR fecha_inicio IS NULL OR fecha_fin >= fecha_inicio", name="plazo"),
        CheckConstraint(
            "(estado = 'BORRADOR' AND codigo IS NULL AND numero IS NULL AND anio IS NULL AND fecha_formalizacion IS NULL AND formalizado_en IS NULL AND formalizado_por IS NULL AND snapshot IS NULL AND huella IS NULL) OR (estado = 'FORMALIZADO' AND tipo IS NOT NULL AND codigo IS NOT NULL AND numero IS NOT NULL AND anio IS NOT NULL AND fecha_inicio IS NOT NULL AND fecha_fin IS NOT NULL AND referencia_instrumento IS NOT NULL AND document_id IS NOT NULL AND document_version_id IS NOT NULL AND documento_sha256 IS NOT NULL AND firmante_cargo_id IS NOT NULL AND fecha_formalizacion IS NOT NULL AND formalizado_en IS NOT NULL AND formalizado_por IS NOT NULL AND snapshot IS NOT NULL AND huella IS NOT NULL)",
            name="completitud",
        ),
    )


class GovernmentContractBudgetAllocation(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Porción de una certificación de disponibilidad (BUD-06) asignada a un contrato (CNT-01). No consume la CDP."""
    __tablename__ = "gov_contract_budget_allocations"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contracts.id"), nullable=False, index=True)
    certificate_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_certificates.id"), nullable=False, index=True)
    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False)
    certificado_codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)

    __table_args__ = (
        UniqueConstraint("contract_id", "certificate_id", name="uq_gov_contract_budget_allocations_certificado"),
        CheckConstraint("monto > 0", name="monto"),
    )


class GovernmentContractGuarantee(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Garantía de PROC-10 vinculada a un contrato (CNT-01). No duplica la garantía."""
    __tablename__ = "gov_contract_guarantees"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contracts.id"), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_guarantee_instruments.id"), nullable=False, index=True)
    garantia_referencia: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        UniqueConstraint("contract_id", "instrument_id", name="uq_gov_contract_guarantees_instrumento"),
    )


GOV_CONTRACTS_GUARD_PG = (
    """CREATE OR REPLACE FUNCTION kontrol_gov_contract_guard() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' OR TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF OLD.estado = 'FORMALIZADO' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF NEW.company_id IS DISTINCT FROM OLD.company_id
        OR NEW.file_id IS DISTINCT FROM OLD.file_id
        OR NEW.decision_id IS DISTINCT FROM OLD.decision_id
        OR NEW.offer_id IS DISTINCT FROM OLD.offer_id
        OR NEW.act_id IS DISTINCT FROM OLD.act_id
        OR NEW.amount_id IS DISTINCT FROM OLD.amount_id
        OR NEW.expediente_numero IS DISTINCT FROM OLD.expediente_numero
        OR NEW.objeto IS DISTINCT FROM OLD.objeto
        OR NEW.decision_referencia IS DISTINCT FROM OLD.decision_referencia
        OR NEW.oferta_referencia IS DISTINCT FROM OLD.oferta_referencia
        OR NEW.contratista_nombre IS DISTINCT FROM OLD.contratista_nombre
        OR NEW.contratista_documento IS DISTINCT FROM OLD.contratista_documento
        OR NEW.monto IS DISTINCT FROM OLD.monto
        OR NEW.moneda IS DISTINCT FROM OLD.moneda THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql""",
    "CREATE TRIGGER trg_gov_contracts_guard BEFORE UPDATE OR DELETE ON gov_contracts FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_guard()",
    "CREATE TRIGGER trg_gov_contracts_no_truncate BEFORE TRUNCATE ON gov_contracts FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_guard()",
)

GOV_CONTRACT_LINKS_GUARD_FN_PG = """CREATE OR REPLACE FUNCTION kontrol_gov_contract_link_guard() RETURNS TRIGGER AS $$
DECLARE
    v_estado text;
BEGIN
    IF TG_OP = 'TRUNCATE' OR TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    SELECT estado INTO v_estado FROM gov_contracts WHERE id = (CASE WHEN TG_OP = 'DELETE' THEN OLD.contract_id ELSE NEW.contract_id END);
    IF v_estado = 'FORMALIZADO' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql"""

GOV_CONTRACT_BUDGET_ALLOCATIONS_GUARD_PG = (
    GOV_CONTRACT_LINKS_GUARD_FN_PG,
    "CREATE TRIGGER trg_gov_contract_budget_allocations_guard BEFORE INSERT OR UPDATE OR DELETE ON gov_contract_budget_allocations FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_link_guard()",
    "CREATE TRIGGER trg_gov_contract_budget_allocations_no_truncate BEFORE TRUNCATE ON gov_contract_budget_allocations FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_link_guard()",
)

GOV_CONTRACT_GUARANTEES_GUARD_PG = (
    GOV_CONTRACT_LINKS_GUARD_FN_PG,
    "CREATE TRIGGER trg_gov_contract_guarantees_guard BEFORE INSERT OR UPDATE OR DELETE ON gov_contract_guarantees FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_link_guard()",
    "CREATE TRIGGER trg_gov_contract_guarantees_no_truncate BEFORE TRUNCATE ON gov_contract_guarantees FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_link_guard()",
)

for _sentencia in GOV_CONTRACTS_GUARD_PG:
    event.listen(GovernmentContract.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_CONTRACT_BUDGET_ALLOCATIONS_GUARD_PG:
    event.listen(GovernmentContractBudgetAllocation.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_CONTRACT_GUARANTEES_GUARD_PG:
    event.listen(GovernmentContractGuarantee.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


# CNT-02 · Adendas, prórrogas, modificaciones y variaciones versionadas (GOV-CNT-002).

TIPOS_MODIFICACION_CONTRATO = ("ADENDA", "PRORROGA", "MODIFICACION", "VARIACION")  # LCP arts. 130–135
ESTADOS_MODIFICACION_CONTRATO = ("BORRADOR", "FORMALIZADA")
PREFIJOS_MODIFICACION_CONTRATO: dict[str, str] = {"ADENDA": "AD", "PRORROGA": "PR", "MODIFICACION": "MO", "VARIACION": "VA"}

COMPLETITUD_MODIFICACION_CONTRATO = (
    "(estado = 'BORRADOR' AND numero IS NULL AND codigo IS NULL AND monto_anterior IS NULL AND monto_nuevo IS NULL AND fecha_fin_anterior IS NULL AND fecha_fin_nueva IS NULL AND fecha_formalizacion IS NULL AND formalizado_en IS NULL AND formalizado_por IS NULL AND snapshot IS NULL AND huella IS NULL) OR (estado = 'FORMALIZADA' AND numero IS NOT NULL AND codigo IS NOT NULL AND motivo IS NOT NULL AND fecha_instrumento IS NOT NULL AND vigente_desde IS NOT NULL AND referencia_instrumento IS NOT NULL AND document_id IS NOT NULL AND document_version_id IS NOT NULL AND documento_sha256 IS NOT NULL AND monto_anterior IS NOT NULL AND monto_nuevo IS NOT NULL AND fecha_fin_anterior IS NOT NULL AND fecha_fin_nueva IS NOT NULL AND firmante_cargo_id IS NOT NULL AND fecha_formalizacion IS NOT NULL AND formalizado_en IS NOT NULL AND formalizado_por IS NOT NULL AND snapshot IS NOT NULL AND huella IS NOT NULL)"
)


class GovernmentContractAmendment(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Instrumento modificatorio formalizado sobre un contrato de CNT-01 (CNT-02). No modifica el contrato."""

    __tablename__ = "gov_contract_amendments"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contracts.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(12), nullable=False, default="BORRADOR", server_default="BORRADOR")
    tipo: Mapped[str] = mapped_column(String(14), nullable=False)
    numero: Mapped[int | None] = mapped_column(Integer, nullable=True)
    codigo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    previous_amendment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_contract_amendments.id"), nullable=True)
    base_numero: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    motivo: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    fecha_instrumento: Mapped[date | None] = mapped_column(Date, nullable=True)
    vigente_desde: Mapped[date | None] = mapped_column(Date, nullable=True)
    nueva_fecha_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    delta_monto: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    condiciones: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    referencia_instrumento: Mapped[str | None] = mapped_column(String(120), nullable=True)
    document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True)
    document_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=True)
    documento_version_numero: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    documento_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    documento_titulo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    monto_anterior: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    monto_nuevo: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    fecha_fin_anterior: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_fin_nueva: Mapped[date | None] = mapped_column(Date, nullable=True)
    firmante_cargo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=True)
    firmante_cargo_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    firmante_funcionario_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fecha_formalizacion: Mapped[date | None] = mapped_column(Date, nullable=True)
    formalizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    formalizado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    huella: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint("contract_id", "numero", name="uq_gov_contract_amendments_numero"),
        UniqueConstraint("company_id", "codigo", name="uq_gov_contract_amendments_codigo"),
        UniqueConstraint("previous_amendment_id", name="uq_gov_contract_amendments_previa"),
        Index("uq_gov_contract_amendments_borrador", "contract_id", unique=True, postgresql_where=text("estado = 'BORRADOR'"), sqlite_where=text("estado = 'BORRADOR'")),
        CheckConstraint(f"estado IN ({en(ESTADOS_MODIFICACION_CONTRATO)})", name="estado"),
        CheckConstraint(f"tipo IN ({en(TIPOS_MODIFICACION_CONTRATO)})", name="tipo"),
        CheckConstraint("numero IS NULL OR numero >= 1", name="numero"),
        CheckConstraint("base_numero >= 0", name="base"),
        CheckConstraint("delta_monto IS NULL OR delta_monto <> 0", name="delta"),
        CheckConstraint("length(moneda) = 3", name="moneda"),
        CheckConstraint("vigente_desde IS NULL OR fecha_instrumento IS NULL OR vigente_desde >= fecha_instrumento", name="fechas"),
        CheckConstraint("monto_nuevo IS NULL OR (monto_nuevo > 0 AND monto_nuevo = monto_anterior + COALESCE(delta_monto, 0))", name="montos"),
        CheckConstraint("fecha_fin_nueva IS NULL OR (nueva_fecha_fin IS NULL AND fecha_fin_nueva = fecha_fin_anterior) OR (nueva_fecha_fin IS NOT NULL AND nueva_fecha_fin > fecha_fin_anterior AND fecha_fin_nueva = nueva_fecha_fin)", name="plazo"),
        CheckConstraint(COMPLETITUD_MODIFICACION_CONTRATO, name="completitud"),
    )


class GovernmentContractAmendmentAllocation(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Cobertura adicional de una CDP (BUD-06) para una modificación de contrato (CNT-02). No consume la CDP."""

    __tablename__ = "gov_contract_amendment_allocations"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    amendment_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contract_amendments.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contracts.id"), nullable=False, index=True)
    certificate_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_certificates.id"), nullable=False, index=True)
    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False)
    certificado_codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)

    __table_args__ = (
        UniqueConstraint("amendment_id", "certificate_id", name="uq_gov_contract_amendment_allocations_certificado"),
        CheckConstraint("monto > 0", name="monto"),
    )


GOV_CONTRACT_AMENDMENTS_GUARD_PG = (
    """
CREATE OR REPLACE FUNCTION kontrol_gov_contract_amendment_guard() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_AMENDMENT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        IF OLD.estado <> 'BORRADOR' THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_AMENDMENT_IMMUTABLE', DETAIL = TG_OP;
        END IF;
        RETURN OLD;
    END IF;
    IF OLD.estado = 'FORMALIZADA'
        OR NEW.company_id IS DISTINCT FROM OLD.company_id
        OR NEW.contract_id IS DISTINCT FROM OLD.contract_id
        OR NEW.file_id IS DISTINCT FROM OLD.file_id
        OR NEW.moneda IS DISTINCT FROM OLD.moneda
        OR NEW.created_by IS DISTINCT FROM OLD.created_by THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_AMENDMENT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql
""",
    "CREATE TRIGGER trg_gov_contract_amendments_guard BEFORE UPDATE OR DELETE ON gov_contract_amendments FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_amendment_guard()",
    "CREATE TRIGGER trg_gov_contract_amendments_no_truncate BEFORE TRUNCATE ON gov_contract_amendments FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_amendment_guard()",
)

GOV_CONTRACT_AMENDMENT_ALLOCATIONS_GUARD_PG = (
    """
CREATE OR REPLACE FUNCTION kontrol_gov_contract_amendment_link_guard() RETURNS TRIGGER AS $$
DECLARE
    v_estado text;
BEGIN
    IF TG_OP = 'TRUNCATE' OR TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_AMENDMENT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    SELECT estado INTO v_estado FROM gov_contract_amendments WHERE id = (CASE WHEN TG_OP = 'DELETE' THEN OLD.amendment_id ELSE NEW.amendment_id END);
    IF v_estado = 'FORMALIZADA' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_AMENDMENT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql
""",
    "CREATE TRIGGER trg_gov_contract_amendment_allocations_guard BEFORE INSERT OR UPDATE OR DELETE ON gov_contract_amendment_allocations FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_amendment_link_guard()",
    "CREATE TRIGGER trg_gov_contract_amendment_allocations_no_truncate BEFORE TRUNCATE ON gov_contract_amendment_allocations FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_amendment_link_guard()",
)

for _sentencia in GOV_CONTRACT_AMENDMENTS_GUARD_PG:
    event.listen(GovernmentContractAmendment.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_CONTRACT_AMENDMENT_ALLOCATIONS_GUARD_PG:
    event.listen(GovernmentContractAmendmentAllocation.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


ESTADOS_SUPERVISOR_CONTRATO = ("VIGENTE", "SUSTITUIDA")


class GovernmentContractSupervisorAssignment(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Supervisor o responsable designado de un contrato formalizado (CNT-04, GOV-CNT-004; LCP art. 136)."""

    __tablename__ = "gov_contract_supervisors"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contracts.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(12), nullable=False, default="VIGENTE", server_default="VIGENTE")
    official_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=False)
    assignment_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_assignments.id"), nullable=False)
    position_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=False)
    unit_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_units.id"), nullable=False)
    act_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=False, index=True)
    funcionario_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    funcionario_documento: Mapped[str] = mapped_column(String(40), nullable=False)
    figura: Mapped[str] = mapped_column(String(24), nullable=False)
    cargo_codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    cargo_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    unidad_nombre: Mapped[str] = mapped_column(String(250), nullable=False)
    acto_etiqueta: Mapped[str] = mapped_column(String(400), nullable=False)
    acto_emisor_cargo: Mapped[str] = mapped_column(String(200), nullable=False)
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    motivo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sustituye_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_contract_supervisors.id"), nullable=True)
    sustituida_por_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_contract_supervisors.id", deferrable=True, initially="DEFERRED"), nullable=True)
    registrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registrado_por: Mapped[str] = mapped_column(String(36), nullable=False)

    __table_args__ = (
        UniqueConstraint("contract_id", "numero", name="uq_gov_contract_supervisors_numero"),
        Index(
            "uq_gov_contract_supervisors_vigente",
            "contract_id",
            unique=True,
            postgresql_where=text("estado = 'VIGENTE'"),
            sqlite_where=text("estado = 'VIGENTE'"),
        ),
        CheckConstraint(f"estado IN ({en(ESTADOS_SUPERVISOR_CONTRATO)})", name="estado"),
        CheckConstraint("numero >= 1", name="numero"),
        CheckConstraint("hasta IS NULL OR hasta >= desde", name="vigencia"),
        CheckConstraint("(estado = 'VIGENTE') = (hasta IS NULL AND sustituida_por_id IS NULL)", name="vigente_abierta"),
        CheckConstraint("sustituye_id IS NULL OR motivo IS NOT NULL", name="sustitucion_motivada"),
    )


GOV_CONTRACT_SUPERVISORS_GUARD_PG = (
    """
    CREATE OR REPLACE FUNCTION kontrol_gov_contract_supervisor_guard()
    RETURNS trigger AS $$
    BEGIN
        IF TG_OP IN ('DELETE','TRUNCATE') THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_SUPERVISOR_IMMUTABLE', DETAIL = TG_OP;
        END IF;
        IF TG_OP = 'UPDATE' THEN
            IF OLD.estado = 'VIGENTE' AND NEW.estado = 'SUSTITUIDA'
               AND NEW.hasta IS NOT NULL AND NEW.sustituida_por_id IS NOT NULL
               AND OLD.company_id IS NOT DISTINCT FROM NEW.company_id
               AND OLD.contract_id IS NOT DISTINCT FROM NEW.contract_id
               AND OLD.numero IS NOT DISTINCT FROM NEW.numero
               AND OLD.official_id IS NOT DISTINCT FROM NEW.official_id
               AND OLD.assignment_id IS NOT DISTINCT FROM NEW.assignment_id
               AND OLD.position_id IS NOT DISTINCT FROM NEW.position_id
               AND OLD.unit_id IS NOT DISTINCT FROM NEW.unit_id
               AND OLD.act_id IS NOT DISTINCT FROM NEW.act_id
               AND OLD.funcionario_nombre IS NOT DISTINCT FROM NEW.funcionario_nombre
               AND OLD.funcionario_documento IS NOT DISTINCT FROM NEW.funcionario_documento
               AND OLD.figura IS NOT DISTINCT FROM NEW.figura
               AND OLD.cargo_codigo IS NOT DISTINCT FROM NEW.cargo_codigo
               AND OLD.cargo_nombre IS NOT DISTINCT FROM NEW.cargo_nombre
               AND OLD.unidad_nombre IS NOT DISTINCT FROM NEW.unidad_nombre
               AND OLD.acto_etiqueta IS NOT DISTINCT FROM NEW.acto_etiqueta
               AND OLD.acto_emisor_cargo IS NOT DISTINCT FROM NEW.acto_emisor_cargo
               AND OLD.desde IS NOT DISTINCT FROM NEW.desde
               AND OLD.motivo IS NOT DISTINCT FROM NEW.motivo
               AND OLD.sustituye_id IS NOT DISTINCT FROM NEW.sustituye_id
               AND OLD.registrado_en IS NOT DISTINCT FROM NEW.registrado_en
               AND OLD.registrado_por IS NOT DISTINCT FROM NEW.registrado_por
               AND OLD.created_at IS NOT DISTINCT FROM NEW.created_at
               AND OLD.created_by IS NOT DISTINCT FROM NEW.created_by
            THEN
                RETURN NEW;
            ELSE
                RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_SUPERVISOR_IMMUTABLE', DETAIL = TG_OP;
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """,
    """
    CREATE OR REPLACE TRIGGER trg_gov_contract_supervisors_guard
    BEFORE UPDATE OR DELETE ON gov_contract_supervisors
    FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_supervisor_guard();
    """,
    """
    CREATE OR REPLACE TRIGGER trg_gov_contract_supervisors_no_truncate
    BEFORE TRUNCATE ON gov_contract_supervisors
    FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_supervisor_guard();
    """,
)

for _sentencia in GOV_CONTRACT_SUPERVISORS_GUARD_PG:
    event.listen(GovernmentContractSupervisorAssignment.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


GOV_CONTRACT_DOSSIER_PACKAGES_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_contract_dossier_package_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_DOSSIER_PACKAGE_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_contract_dossier_packages_no_update BEFORE UPDATE ON gov_contract_dossier_packages FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_dossier_package_inmutable()",
    "CREATE TRIGGER trg_gov_contract_dossier_packages_no_delete BEFORE DELETE ON gov_contract_dossier_packages FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_dossier_package_inmutable()",
    "CREATE TRIGGER trg_gov_contract_dossier_packages_no_truncate BEFORE TRUNCATE ON gov_contract_dossier_packages FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_dossier_package_inmutable()",
)

GOV_CONTRACT_DOSSIER_PACKAGE_VERIFICATIONS_IMMUTABLE_PG = (
    "CREATE OR REPLACE FUNCTION kontrol_gov_contract_dossier_package_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_DOSSIER_PACKAGE_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER trg_gov_contract_dossier_package_verifications_no_update BEFORE UPDATE ON gov_contract_dossier_package_verifications FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_dossier_package_inmutable()",
    "CREATE TRIGGER trg_gov_contract_dossier_package_verifications_no_delete BEFORE DELETE ON gov_contract_dossier_package_verifications FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_dossier_package_inmutable()",
    "CREATE TRIGGER trg_gov_contract_dossier_package_verifications_no_truncate BEFORE TRUNCATE ON gov_contract_dossier_package_verifications FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_dossier_package_inmutable()",
)


class GovernmentContractDossierPackage(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Paquete exportable del expediente contractual (CNT-08, GOV-CNT-009); inmutable."""

    __tablename__ = "gov_contract_dossier_packages"
    __scope__ = Scope.COMPANY

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contracts.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    numero_generacion: Mapped[int] = mapped_column(Integer, nullable=False)
    proposito: Mapped[str] = mapped_column(Text, nullable=False)
    version_manifiesto: Mapped[int] = mapped_column(Integer, nullable=False)
    corte: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    huella_manifiesto: Mapped[str] = mapped_column(String(64), nullable=False)
    huella_paquete: Mapped[str] = mapped_column(String(64), nullable=False)
    bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    clave_almacenamiento: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(String(80), nullable=False)
    eventos: Mapped[int] = mapped_column(Integer, nullable=False)
    documentos_incluidos: Mapped[int] = mapped_column(Integer, nullable=False)
    documentos_excluidos: Mapped[int] = mapped_column(Integer, nullable=False)
    archivos: Mapped[int] = mapped_column(Integer, nullable=False)
    manifiesto: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_contract_dossier_packages_company_id_codigo"),
        UniqueConstraint("contract_id", "numero_generacion", name="uq_gov_contract_dossier_packages_contract_id_numero_generacion"),
        UniqueConstraint("company_id", "idempotency_key", name="uq_gov_contract_dossier_packages_company_id_idempotency_key"),
        UniqueConstraint("clave_almacenamiento", name="uq_gov_contract_dossier_packages_clave_almacenamiento"),
        CheckConstraint("length(huella_manifiesto) = 64 AND length(huella_paquete) = 64", name="huellas"),
        CheckConstraint("bytes > 0", name="bytes"),
        CheckConstraint("eventos >= 0 AND documentos_incluidos >= 0 AND documentos_excluidos >= 0 AND archivos >= 0", name="contadores"),
        CheckConstraint("numero_generacion >= 1", name="numero_generacion"),
        CheckConstraint("version_manifiesto = 1", name="version_manifiesto"),
    )


class GovernmentContractDossierPackageVerification(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Verificación de integridad de una copia de un paquete del expediente contractual (CNT-08); inmutable."""

    __tablename__ = "gov_contract_dossier_package_verifications"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    package_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contract_dossier_packages.id"), nullable=False, index=True)
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


for _sentencia in GOV_CONTRACT_DOSSIER_PACKAGES_IMMUTABLE_PG:
    event.listen(GovernmentContractDossierPackage.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))

for _sentencia in GOV_CONTRACT_DOSSIER_PACKAGE_VERIFICATIONS_IMMUTABLE_PG:
    event.listen(GovernmentContractDossierPackageVerification.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))
# ---------------------------------------------------------------------------
# CNT-03 (GOV-CNT-003 + GOV-CNT-007): ejecución del contrato.
# ---------------------------------------------------------------------------

TIPOS_ACTUACION_EJECUCION = ("INICIO", "TERMINACION", "CIERRE")
APROBADORES_CIERRE = ("COMISION", "UNIDAD_CONTRATANTE")
ESTADOS_ELEMENTO_EJECUCION = ("VIGENTE", "ANULADO")
ESTADOS_ENTREGA = ("ENTREGADA", "CONFORME", "RECHAZADA")
ESTADOS_VALUACION = ("PRESENTADA", "CONFORMADA", "REPARADA", "ANULADA")
TIPOS_RECEPCION_CONTRATO = ("PARCIAL", "PROVISIONAL", "DEFINITIVA")
ESTADOS_DOCUMENTO_EJECUCION = ("CONFORME", "ANULADA")


class GovernmentContractExecutionAct(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Actuación de ejecución del contrato: inicio, terminación o cierre (CNT-03, GOV-CNT-003; LCP arts. 127, 147 y 151)."""

    __tablename__ = "gov_contract_execution_acts"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contracts.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    observacion: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    supervisor_assignment_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contract_supervisors.id"), nullable=False)
    supervisor_official_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=False)
    supervisor_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    document_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=False)
    documento_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    documento_titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    aprobacion_document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True)
    aprobacion_document_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=True)
    aprobacion_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    aprobacion_titulo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    evaluacion_document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True)
    evaluacion_document_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=True)
    evaluacion_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evaluacion_titulo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    aprobador_tipo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    aprobador_nombre: Mapped[str | None] = mapped_column(String(250), nullable=True)
    registrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registrado_por: Mapped[str] = mapped_column(String(36), nullable=False)

    __table_args__ = (
        UniqueConstraint("contract_id", "tipo", name="uq_gov_contract_execution_acts_tipo"),
        CheckConstraint(f"tipo IN ({en(TIPOS_ACTUACION_EJECUCION)})", name="tipo"),
        CheckConstraint(
            f"aprobador_tipo IS NULL OR aprobador_tipo IN ({en(APROBADORES_CIERRE)})", name="aprobador"
        ),
        CheckConstraint(
            "(tipo = 'CIERRE') = (aprobacion_document_id IS NOT NULL AND evaluacion_document_id IS NOT NULL "
            "AND aprobador_tipo IS NOT NULL AND aprobador_nombre IS NOT NULL)",
            name="cierre_completo",
        ),
        CheckConstraint(
            "aprobacion_document_id IS NULL OR aprobacion_document_id <> evaluacion_document_id",
            name="cierre_documentos_distintos",
        ),
    )


class GovernmentContractMilestone(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Hito de la ejecución del contrato (CNT-03, GOV-CNT-003)."""

    __tablename__ = "gov_contract_milestones"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contracts.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(500), nullable=False)
    fecha_prevista: Mapped[date] = mapped_column(Date, nullable=False)
    monto_previsto: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    porcentaje_previsto: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    obligatorio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="VIGENTE", server_default="VIGENTE")
    motivo_anulacion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    anulado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    anulado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    registrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registrado_por: Mapped[str] = mapped_column(String(36), nullable=False)

    __table_args__ = (
        UniqueConstraint("contract_id", "numero", name="uq_gov_contract_milestones_numero"),
        CheckConstraint("numero >= 1", name="numero"),
        CheckConstraint(f"estado IN ({en(ESTADOS_ELEMENTO_EJECUCION)})", name="estado"),
        CheckConstraint("monto_previsto IS NULL OR monto_previsto > 0", name="monto"),
        CheckConstraint(
            "porcentaje_previsto IS NULL OR (porcentaje_previsto > 0 AND porcentaje_previsto <= 100)",
            name="porcentaje",
        ),
        CheckConstraint(
            "(estado = 'ANULADO') = (motivo_anulacion IS NOT NULL AND anulado_en IS NOT NULL)",
            name="anulacion_motivada",
        ),
    )


class GovernmentContractDeliverable(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Entregable de un hito del contrato (CNT-03, GOV-CNT-003)."""

    __tablename__ = "gov_contract_deliverables"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contracts.id"), nullable=False, index=True)
    milestone_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("gov_contract_milestones.id"), nullable=True, index=True
    )
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(500), nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    obligatorio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="VIGENTE", server_default="VIGENTE")
    motivo_anulacion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    anulado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    anulado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    registrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registrado_por: Mapped[str] = mapped_column(String(36), nullable=False)

    __table_args__ = (
        UniqueConstraint("contract_id", "numero", name="uq_gov_contract_deliverables_numero"),
        CheckConstraint("numero >= 1", name="numero"),
        CheckConstraint(f"estado IN ({en(ESTADOS_ELEMENTO_EJECUCION)})", name="estado"),
        CheckConstraint(
            "(estado = 'ANULADO') = (motivo_anulacion IS NOT NULL AND anulado_en IS NOT NULL)",
            name="anulacion_motivada",
        ),
    )


class GovernmentContractDeliverableSubmission(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Entrega de un entregable del contrato (CNT-03, GOV-CNT-003)."""

    __tablename__ = "gov_contract_deliverable_submissions"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contracts.id"), nullable=False, index=True)
    deliverable_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gov_contract_deliverables.id"), nullable=False, index=True
    )
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_entrega: Mapped[date] = mapped_column(Date, nullable=False)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    document_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=False)
    documento_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    documento_titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    observacion_entrega: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="ENTREGADA", server_default="ENTREGADA")
    fecha_revision: Mapped[date | None] = mapped_column(Date, nullable=True)
    observacion_revision: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    supervisor_assignment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("gov_contract_supervisors.id"), nullable=True
    )
    supervisor_official_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=True)
    supervisor_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    revisado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revisado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    registrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registrado_por: Mapped[str] = mapped_column(String(36), nullable=False)

    __table_args__ = (
        UniqueConstraint("deliverable_id", "numero", name="uq_gov_contract_submissions_numero"),
        Index(
            "uq_gov_contract_submissions_abierta",
            "deliverable_id",
            unique=True,
            postgresql_where=text("estado = 'ENTREGADA'"),
            sqlite_where=text("estado = 'ENTREGADA'"),
        ),
        Index(
            "uq_gov_contract_submissions_conforme",
            "deliverable_id",
            unique=True,
            postgresql_where=text("estado = 'CONFORME'"),
            sqlite_where=text("estado = 'CONFORME'"),
        ),
        CheckConstraint(f"estado IN ({en(ESTADOS_ENTREGA)})", name="estado"),
        CheckConstraint("numero >= 1", name="numero"),
        CheckConstraint(
            "(estado = 'ENTREGADA') = (fecha_revision IS NULL AND supervisor_assignment_id IS NULL AND revisado_en IS NULL)",
            name="revision",
        ),
        CheckConstraint("estado <> 'RECHAZADA' OR observacion_revision IS NOT NULL", name="rechazo_motivado"),
        CheckConstraint("fecha_revision IS NULL OR fecha_revision >= fecha_entrega", name="fechas"),
    )


class GovernmentContractValuation(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Valuación de obra o de servicios del contrato (CNT-03, GOV-CNT-003; LCP arts. 142-143)."""

    __tablename__ = "gov_contract_valuations"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contracts.id"), nullable=False, index=True)
    milestone_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gov_contract_milestones.id"), nullable=False, index=True
    )
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    periodo_desde: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_hasta: Mapped[date] = mapped_column(Date, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    document_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=False)
    documento_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    documento_titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    estado: Mapped[str] = mapped_column(String(12), nullable=False, default="PRESENTADA", server_default="PRESENTADA")
    fecha_conformidad: Mapped[date | None] = mapped_column(Date, nullable=True)
    acumulado: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    reparos: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    motivo_anulacion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    supervisor_assignment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("gov_contract_supervisors.id"), nullable=True
    )
    supervisor_official_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=True)
    supervisor_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    resuelto_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resuelto_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    registrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registrado_por: Mapped[str] = mapped_column(String(36), nullable=False)

    __table_args__ = (
        UniqueConstraint("contract_id", "numero", name="uq_gov_contract_valuations_numero"),
        CheckConstraint(f"estado IN ({en(ESTADOS_VALUACION)})", name="estado"),
        CheckConstraint("numero >= 1", name="numero"),
        CheckConstraint("monto > 0", name="monto"),
        CheckConstraint("length(moneda) = 3", name="moneda"),
        CheckConstraint("periodo_desde <= periodo_hasta AND periodo_hasta <= fecha", name="periodo"),
        CheckConstraint(
            "estado <> 'PRESENTADA' OR (fecha_conformidad IS NULL AND supervisor_assignment_id IS NULL)",
            name="presentada",
        ),
        CheckConstraint(
            "estado <> 'CONFORMADA' OR (fecha_conformidad IS NOT NULL AND acumulado IS NOT NULL "
            "AND supervisor_assignment_id IS NOT NULL)",
            name="conformada",
        ),
        CheckConstraint(
            "estado <> 'REPARADA' OR (reparos IS NOT NULL AND fecha_conformidad IS NOT NULL "
            "AND supervisor_assignment_id IS NOT NULL)",
            name="reparada",
        ),
        CheckConstraint("estado <> 'ANULADA' OR motivo_anulacion IS NOT NULL", name="anulada"),
        CheckConstraint("fecha_conformidad IS NULL OR fecha_conformidad >= fecha", name="conformidad"),
    )


class GovernmentContractReceipt(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Recepción parcial, provisional o definitiva del contrato (CNT-03, GOV-CNT-003; LCP arts. 146-150)."""

    __tablename__ = "gov_contract_receipts"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contracts.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    document_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=False)
    documento_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    documento_titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    observacion: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    supervisor_assignment_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contract_supervisors.id"), nullable=False)
    supervisor_official_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=False)
    supervisor_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    representante_cargo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=True)
    representante_cargo_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fin_garantia: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="CONFORME", server_default="CONFORME")
    motivo_anulacion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    anulado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    anulado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    registrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registrado_por: Mapped[str] = mapped_column(String(36), nullable=False)

    __table_args__ = (
        UniqueConstraint("contract_id", "numero", name="uq_gov_contract_receipts_numero"),
        Index(
            "uq_gov_contract_receipts_definitiva",
            "contract_id",
            unique=True,
            postgresql_where=text("tipo = 'DEFINITIVA' AND estado = 'CONFORME'"),
            sqlite_where=text("tipo = 'DEFINITIVA' AND estado = 'CONFORME'"),
        ),
        Index(
            "uq_gov_contract_receipts_provisional",
            "contract_id",
            unique=True,
            postgresql_where=text("tipo = 'PROVISIONAL' AND estado = 'CONFORME'"),
            sqlite_where=text("tipo = 'PROVISIONAL' AND estado = 'CONFORME'"),
        ),
        CheckConstraint(f"tipo IN ({en(TIPOS_RECEPCION_CONTRATO)})", name="tipo"),
        CheckConstraint(f"estado IN ({en(ESTADOS_DOCUMENTO_EJECUCION)})", name="estado"),
        CheckConstraint("numero >= 1", name="numero"),
        CheckConstraint("(tipo = 'PROVISIONAL') = (fin_garantia IS NOT NULL)", name="garantia"),
        CheckConstraint("fin_garantia IS NULL OR fin_garantia >= fecha", name="garantia_fecha"),
        CheckConstraint(
            "(representante_cargo_id IS NULL) = (representante_cargo_nombre IS NULL)", name="representante"
        ),
        CheckConstraint(
            "(estado = 'ANULADA') = (motivo_anulacion IS NOT NULL AND anulado_en IS NOT NULL)",
            name="anulacion_motivada",
        ),
    )


class GovernmentContractReceiptMilestone(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Hitos asociados a una recepción del contrato (CNT-03, GOV-CNT-003)."""

    __tablename__ = "gov_contract_receipt_milestones"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contracts.id"), nullable=False, index=True)
    receipt_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contract_receipts.id"), nullable=False, index=True)
    milestone_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gov_contract_milestones.id"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint("receipt_id", "milestone_id", name="uq_gov_contract_receipt_milestones"),
    )


class GovernmentContractInvoice(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Factura vinculada a un hito y a una recepción conforme del contrato (CNT-03, GOV-CNT-007; LCP art. 141; RLCP art. 177)."""

    __tablename__ = "gov_contract_invoices"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contracts.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    numero_documento: Mapped[str] = mapped_column(String(40), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    milestone_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gov_contract_milestones.id"), nullable=False, index=True
    )
    receipt_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contract_receipts.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    document_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=False)
    documento_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    documento_titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    fecha_conformidad: Mapped[date] = mapped_column(Date, nullable=False)
    supervisor_assignment_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contract_supervisors.id"), nullable=False)
    supervisor_official_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_officials.id"), nullable=False)
    supervisor_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="CONFORME", server_default="CONFORME")
    motivo_anulacion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    anulado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    anulado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    registrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registrado_por: Mapped[str] = mapped_column(String(36), nullable=False)

    __table_args__ = (
        UniqueConstraint("contract_id", "numero", name="uq_gov_contract_invoices_numero"),
        Index(
            "uq_gov_contract_invoices_documento",
            "contract_id",
            "numero_documento",
            unique=True,
            postgresql_where=text("estado = 'CONFORME'"),
            sqlite_where=text("estado = 'CONFORME'"),
        ),
        CheckConstraint(f"estado IN ({en(ESTADOS_DOCUMENTO_EJECUCION)})", name="estado"),
        CheckConstraint("numero >= 1", name="numero"),
        CheckConstraint("monto > 0", name="monto"),
        CheckConstraint("length(moneda) = 3", name="moneda"),
        CheckConstraint("fecha_conformidad >= fecha", name="conformidad"),
        CheckConstraint(
            "(estado = 'ANULADA') = (motivo_anulacion IS NOT NULL AND anulado_en IS NOT NULL)",
            name="anulacion_motivada",
        ),
    )


GOV_CONTRACT_EXEC_GUARD_FUNCION_PG = """
CREATE OR REPLACE FUNCTION kontrol_gov_contract_exec_guard()
RETURNS trigger AS $$
BEGIN
    IF TG_OP IN ('DELETE','TRUNCATE') THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_EXEC_IMMUTABLE', DETAIL = TG_TABLE_NAME || ' ' || TG_OP;
    END IF;
    IF TG_NARGS = 3
       AND (to_jsonb(OLD) ->> 'estado') = TG_ARGV[0]
       AND (to_jsonb(NEW) ->> 'estado') = ANY (string_to_array(TG_ARGV[1], ','))
       AND (to_jsonb(OLD) - string_to_array(TG_ARGV[2], ',')) = (to_jsonb(NEW) - string_to_array(TG_ARGV[2], ','))
    THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_EXEC_IMMUTABLE', DETAIL = TG_TABLE_NAME || ' ' || TG_OP;
END;
$$ LANGUAGE plpgsql;
"""

GOV_CONTRACT_EXEC_GUARDS: tuple[tuple[str, str], ...] = (
    ("gov_contract_execution_acts", ""),
    ("gov_contract_milestones", "'VIGENTE', 'ANULADO', 'estado,motivo_anulacion,anulado_en,anulado_por,version,updated_at'"),
    ("gov_contract_deliverables", "'VIGENTE', 'ANULADO', 'estado,motivo_anulacion,anulado_en,anulado_por,version,updated_at'"),
    (
        "gov_contract_deliverable_submissions",
        "'ENTREGADA', 'CONFORME,RECHAZADA', 'estado,fecha_revision,observacion_revision,supervisor_assignment_id,supervisor_official_id,supervisor_nombre,revisado_en,revisado_por,version,updated_at'",
    ),
    (
        "gov_contract_valuations",
        "'PRESENTADA', 'CONFORMADA,REPARADA,ANULADA', 'estado,fecha_conformidad,acumulado,reparos,motivo_anulacion,supervisor_assignment_id,supervisor_official_id,supervisor_nombre,resuelto_en,resuelto_por,version,updated_at'",
    ),
    ("gov_contract_receipts", "'CONFORME', 'ANULADA', 'estado,motivo_anulacion,anulado_en,anulado_por,version,updated_at'"),
    ("gov_contract_receipt_milestones", ""),
    ("gov_contract_invoices", "'CONFORME', 'ANULADA', 'estado,motivo_anulacion,anulado_en,anulado_por,version,updated_at'"),
)


def gov_contract_exec_guard_ddl(tabla: str, argumentos: str) -> tuple[str, str]:
    """Devuelve los dos triggers de inmutabilidad de la ejecución del contrato para una tabla."""
    return (
        f"CREATE OR REPLACE TRIGGER trg_{tabla}_guard BEFORE UPDATE OR DELETE ON {tabla} "
        f"FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_exec_guard({argumentos});",
        f"CREATE OR REPLACE TRIGGER trg_{tabla}_no_truncate BEFORE TRUNCATE ON {tabla} "
        f"FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_exec_guard();",
    )


GOV_CONTRACT_EXEC_CLASES = (
    GovernmentContractExecutionAct,
    GovernmentContractMilestone,
    GovernmentContractDeliverable,
    GovernmentContractDeliverableSubmission,
    GovernmentContractValuation,
    GovernmentContractReceipt,
    GovernmentContractReceiptMilestone,
    GovernmentContractInvoice,
)

for _clase_ejecucion, (_tabla_ejecucion, _argumentos_ejecucion) in zip(
    GOV_CONTRACT_EXEC_CLASES, GOV_CONTRACT_EXEC_GUARDS, strict=True
):
    event.listen(
        _clase_ejecucion.__table__,
        "after_create",
        DDL(GOV_CONTRACT_EXEC_GUARD_FUNCION_PG).execute_if(dialect="postgresql"),
    )
    for _sentencia in gov_contract_exec_guard_ddl(_tabla_ejecucion, _argumentos_ejecucion):
        event.listen(
            _clase_ejecucion.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql")
        )


FUENTES_POLITICA_ALERTA = ("CONTRATO", "HITO", "ENTREGABLE")


class GovernmentContractAlertPolicy(UUIDMixin, TimestampMixin, Base):
    """Preaviso institucional de las alertas de vencimiento (CNT-09, GOV-CNT-010). Solo decide cuándo se llama a crear_alerta; el motor es la Spec 047."""

    __tablename__ = "gov_contract_alert_policies"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "fuente", name="uq_gov_contract_alert_policies_company_fuente"),
        CheckConstraint(f"fuente IN ({en(FUENTES_POLITICA_ALERTA)})", name="fuente"),
        CheckConstraint("dias_anticipacion IS NULL OR (dias_anticipacion >= 1 AND dias_anticipacion <= 365)", name="dias"),
        CheckConstraint("activo = false OR dias_anticipacion IS NOT NULL", name="activo_dias"),
    )

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    fuente: Mapped[str] = mapped_column(String(12), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    dias_anticipacion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actualizado_por: Mapped[str] = mapped_column(String(36), nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

# CNT-07 · Extinción jurídica anticipada de un contrato (GOV-CNT-008).

FIGURAS_TERMINACION_CONTRATO = ("RESCISION_NO_IMPUTABLE", "RESOLUCION_MUTUO_ACUERDO", "RESCISION_IMPUTABLE")  # LCP art. 145
CAUSALES_TERMINACION_CONTRATO = ("INTERES_DEL_CONTRATANTE", "CIRCUNSTANCIAS_ACONSEJABLES", "LCP_155_1", "LCP_155_2", "LCP_155_3", "LCP_155_4", "LCP_155_5", "LCP_155_6", "LCP_155_7", "LCP_155_8", "LCP_155_9", "CLAUSULA_CONTRATO")  # LCP 152, 154, 155; RLCP 193
ESTADOS_TERMINACION_CONTRATO = ("BORRADOR", "FORMALIZADA")


class GovernmentContractTermination(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Extinción jurídica anticipada de un contrato de CNT-01 (CNT-07, GOV-CNT-008). No modifica el contrato."""

    __tablename__ = "gov_contract_terminations"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_contracts.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_procurement_files.id"), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(12), nullable=False, default="BORRADOR", server_default="BORRADOR")
    figura: Mapped[str] = mapped_column(String(32), nullable=False)
    causal: Mapped[str | None] = mapped_column(String(32), nullable=True)
    causal_referencia: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hechos: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    fundamento: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    act_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=True)
    apertura_act_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=True)
    document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True)
    document_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("document_versions.id"), nullable=True)
    documento_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    documento_titulo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    conclusion_alcance: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    conclusion_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_acto: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_eficacia: Mapped[date | None] = mapped_column(Date, nullable=True)
    codigo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    huella: Mapped[str | None] = mapped_column(String(64), nullable=True)
    formalizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    formalizado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_contract_terminations_codigo"),
        Index("uq_gov_contract_terminations_borrador", "contract_id", unique=True, postgresql_where=text("estado = 'BORRADOR'"), sqlite_where=text("estado = 'BORRADOR'")),
        Index("uq_gov_contract_terminations_formalizada", "contract_id", unique=True, postgresql_where=text("estado = 'FORMALIZADA'"), sqlite_where=text("estado = 'FORMALIZADA'")),
        CheckConstraint(f"estado IN ({en(ESTADOS_TERMINACION_CONTRATO)})", name="estado"),
        CheckConstraint(f"figura IN ({en(FIGURAS_TERMINACION_CONTRATO)})", name="figura"),
        CheckConstraint(f"causal IS NULL OR causal IN ({en(CAUSALES_TERMINACION_CONTRATO)})", name="causal"),
        CheckConstraint("(conclusion_hasta IS NULL) = (conclusion_alcance IS NULL)", name="conclusion"),
        CheckConstraint("estado <> 'FORMALIZADA' OR (causal IS NOT NULL AND hechos IS NOT NULL AND fundamento IS NOT NULL AND act_id IS NOT NULL AND fecha_acto IS NOT NULL AND fecha_eficacia IS NOT NULL AND codigo IS NOT NULL AND huella IS NOT NULL AND formalizado_en IS NOT NULL)", name="completitud"),
        CheckConstraint("conclusion_hasta IS NULL OR fecha_eficacia IS NULL OR conclusion_hasta > fecha_eficacia", name="conclusion_fecha"),
    )


GOV_CONTRACT_TERMINATIONS_GUARD_PG = (
    """
CREATE OR REPLACE FUNCTION kontrol_gov_contract_termination_guard() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_TERMINATION_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        IF OLD.estado <> 'BORRADOR' THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_TERMINATION_IMMUTABLE', DETAIL = TG_OP;
        END IF;
        RETURN OLD;
    END IF;
    IF OLD.estado = 'FORMALIZADA'
        OR NEW.company_id IS DISTINCT FROM OLD.company_id
        OR NEW.contract_id IS DISTINCT FROM OLD.contract_id
        OR NEW.file_id IS DISTINCT FROM OLD.file_id
        OR NEW.created_by IS DISTINCT FROM OLD.created_by THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_TERMINATION_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql
""",
    "CREATE TRIGGER trg_gov_contract_terminations_guard BEFORE UPDATE OR DELETE ON gov_contract_terminations FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_termination_guard()",
    "CREATE TRIGGER trg_gov_contract_terminations_no_truncate BEFORE TRUNCATE ON gov_contract_terminations FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_termination_guard()",
)

for _sentencia in GOV_CONTRACT_TERMINATIONS_GUARD_PG:
    event.listen(GovernmentContractTermination.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))


ESTADOS_POLITICA_CAUSADO = ("BORRADOR", "VIGENTE", "CERRADA")
DISPARADORES_CAUSADO = ("RECEIPT_ACCEPTED", "VALUATION_APPROVED", "DELIVERY_ACCEPTED", "INVOICE_CONFORMED", "DOCUMENTARY")
TIPOS_REGLA_CAUSADO = ("INSTITUTIONAL_POLICY", "LEGAL_MANDATORY")
ETAPAS_DOCUMENTO_CAUSADO = ("PREPARACION", "FORMALIZACION")
ESTADOS_CAUSADO = ("BORRADOR", "FORMALIZADO", "ANULADO")
TIPOS_EVIDENCIA_CAUSADO = ("CONTRACT_RECEIPT", "CONTRACT_VALUATION", "CONTRACT_DELIVERY", "CONTRACT_INVOICE", "DOCUMENT")
TIPOS_FUENTE_CAUSADO = ("CONTRACT", "PROCUREMENT_FILE", "OTHER")


class GovernmentBudgetCauseSettings(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Configuración del ente para el causado (BUD-09): patrón de numeración."""

    __tablename__ = "gov_budget_cause_settings"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    patron: Mapped[str] = mapped_column(String(60), nullable=False)

    __table_args__ = (
        UniqueConstraint("company_id", name="uq_gov_budget_cause_settings_company_id"),
        CheckConstraint("length(patron) BETWEEN 9 AND 60", name="patron"),
    )


class GovernmentBudgetCausingPolicy(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Política de causado por tipo de gasto (BUD-09, INSTITUTIONAL_POLICY del ente)."""

    __tablename__ = "gov_budget_causing_policies"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    tipo_gasto: Mapped[str] = mapped_column(String(40), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    disparador: Mapped[str] = mapped_column(String(24), nullable=False)
    requiere_recepcion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    requiere_valuacion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    requiere_conformidad: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    competencia_accion: Mapped[str] = mapped_column(String(16), nullable=False, default="CAUSAR", server_default="CAUSAR")
    competencia_materia: Mapped[str] = mapped_column(String(16), nullable=False, default="PRESUPUESTO", server_default="PRESUPUESTO")
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    fundamento: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    act_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=True)
    tipo_regla: Mapped[str] = mapped_column(String(24), nullable=False, default="INSTITUTIONAL_POLICY", server_default="INSTITUTIONAL_POLICY")
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="BORRADOR", server_default="BORRADOR")
    activada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    activada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cerrada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_cierre: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_budget_causing_policies_company_id_codigo"),
        CheckConstraint(f"estado IN ({en(ESTADOS_POLITICA_CAUSADO)})", name="estado"),
        CheckConstraint(f"disparador IN ({en(DISPARADORES_CAUSADO)})", name="disparador"),
        CheckConstraint(f"tipo_regla IN ({en(TIPOS_REGLA_CAUSADO)})", name="tipo_regla"),
        CheckConstraint(f"competencia_accion IN ({en(ACCIONES_COMPETENCIA)})", name="competencia_accion"),
        CheckConstraint(f"competencia_materia IN ({en(MATERIAS_COMPETENCIA)})", name="competencia_materia"),
        CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        CheckConstraint("estado = 'BORRADOR' OR fundamento IS NOT NULL", name="fundamento"),
    )


class GovernmentBudgetCausingPolicyDocument(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Documento exigido por una política de causado (RequiredDocument)."""

    __tablename__ = "gov_budget_causing_policy_documents"
    __scope__ = Scope.COMPANY

    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_causing_policies.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    document_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_types.id"), nullable=False)
    obligatorio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    etapa: Mapped[str] = mapped_column(String(14), nullable=False)
    condicion: Mapped[str | None] = mapped_column(String(300), nullable=True)

    __table_args__ = (
        UniqueConstraint("policy_id", "document_type_id", name="uq_gov_budget_causing_policy_docs_type"),
        CheckConstraint(f"etapa IN ({en(ETAPAS_DOCUMENTO_CAUSADO)})", name="etapa"),
    )


class GovernmentBudgetCausingPolicyHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia inmutable de una política de causado."""

    __tablename__ = "gov_budget_causing_policy_history"
    __scope__ = Scope.COMPANY

    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_causing_policies.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    evento: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    instantanea: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class GovernmentBudgetCause(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Causado presupuestario (BUD-09, GOV-BUD-013): obligación exigible contra un compromiso. No es pago ni asiento contable."""

    __tablename__ = "gov_budget_causes"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False, index=True)
    commitment_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_commitments.id"), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_causing_policies.id"), nullable=False, index=True)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(12), nullable=False, default="BORRADOR", server_default="BORRADOR")
    numero: Mapped[int | None] = mapped_column(Integer, nullable=True)
    codigo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    fecha_efectiva: Mapped[date] = mapped_column(Date, nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    concepto: Mapped[str] = mapped_column(String(500), nullable=False)
    beneficiario: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_resource_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    autoridad_cargo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=True)
    autoridad_cargo_codigo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    autoridad_cargo_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    autoridad_unidad: Mapped[str | None] = mapped_column(String(250), nullable=True)
    autoridad_funcionario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    autoridad_funcionario_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    formalizado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    formalizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    huella: Mapped[str | None] = mapped_column(String(64), nullable=True)
    anulado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    anulado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_anulacion: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_budget_causes_company_id_codigo"),
        UniqueConstraint("year_id", "numero", name="uq_gov_budget_causes_year_id_numero"),
        CheckConstraint(f"estado IN ({en(ESTADOS_CAUSADO)})", name="estado"),
        CheckConstraint("monto > 0", name="monto"),
        CheckConstraint("length(moneda) = 3", name="moneda"),
        CheckConstraint(f"source_resource_type IS NULL OR source_resource_type IN ({en(TIPOS_FUENTE_CAUSADO)})", name="fuente"),
        CheckConstraint("(source_resource_type IS NULL) = (source_resource_id IS NULL)", name="fuente_par"),
        CheckConstraint(
            "estado = 'BORRADOR' OR (numero IS NOT NULL AND codigo IS NOT NULL AND formalizado_por IS NOT NULL AND formalizado_en IS NOT NULL AND snapshot IS NOT NULL AND huella IS NOT NULL AND autoridad_cargo_id IS NOT NULL)",
            name="completitud",
        ),
        CheckConstraint("(estado = 'ANULADO') = (anulado_por IS NOT NULL AND anulado_en IS NOT NULL AND motivo_anulacion IS NOT NULL)", name="anulacion"),
    )


class GovernmentBudgetCauseLine(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Imputación de un causado a una línea del compromiso (partida)."""

    __tablename__ = "gov_budget_cause_lines"
    __scope__ = Scope.COMPANY

    cause_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_causes.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    commitment_line_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_commitment_lines.id"), nullable=False, index=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint("cause_id", "commitment_line_id", name="uq_gov_budget_cause_lines_cause_id_commitment_line_id"),
        CheckConstraint("monto > 0", name="monto"),
    )


class GovernmentBudgetCauseEvidence(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Evidencia tipada de un causado (referencia + instantánea, sin copia mutable)."""

    __tablename__ = "gov_budget_cause_evidences"
    __scope__ = Scope.COMPANY

    cause_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_causes.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        UniqueConstraint("cause_id", "resource_type", "resource_id", name="uq_gov_budget_cause_evidences_recurso"),
        CheckConstraint(f"resource_type IN ({en(TIPOS_EVIDENCIA_CAUSADO)})", name="resource_type"),
    )


class GovernmentBudgetCauseHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia append-only del causado."""

    __tablename__ = "gov_budget_cause_history"
    __scope__ = Scope.COMPANY

    cause_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_causes.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    evento: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    instantanea: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


GOV_BUDGET_CAUSES_GUARD_PG = (
    """
CREATE OR REPLACE FUNCTION kontrol_gov_budget_cause_guard() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CAUSE_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        IF OLD.estado <> 'BORRADOR' THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CAUSE_IMMUTABLE', DETAIL = TG_OP;
        END IF;
        RETURN OLD;
    END IF;
    IF OLD.estado = 'ANULADO' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CAUSE_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF OLD.estado = 'FORMALIZADO' THEN
        IF NOT (NEW.estado = 'ANULADO'
            AND NEW.anulado_por IS DISTINCT FROM OLD.anulado_por
            AND NEW.anulado_en IS DISTINCT FROM OLD.anulado_en
            AND NEW.motivo_anulacion IS DISTINCT FROM OLD.motivo_anulacion
            AND NEW.version IS DISTINCT FROM OLD.version
            AND NEW.updated_at IS DISTINCT FROM OLD.updated_at
            AND NEW.numero IS NOT DISTINCT FROM OLD.numero
            AND NEW.codigo IS NOT DISTINCT FROM OLD.codigo
            AND NEW.fecha_efectiva IS NOT DISTINCT FROM OLD.fecha_efectiva
            AND NEW.moneda IS NOT DISTINCT FROM OLD.moneda
            AND NEW.monto IS NOT DISTINCT FROM OLD.monto
            AND NEW.concepto IS NOT DISTINCT FROM OLD.concepto
            AND NEW.beneficiario IS NOT DISTINCT FROM OLD.beneficiario
            AND NEW.source_resource_type IS NOT DISTINCT FROM OLD.source_resource_type
            AND NEW.source_resource_id IS NOT DISTINCT FROM OLD.source_resource_id
            AND NEW.autoridad_cargo_id IS NOT DISTINCT FROM OLD.autoridad_cargo_id
            AND NEW.autoridad_cargo_codigo IS NOT DISTINCT FROM OLD.autoridad_cargo_codigo
            AND NEW.autoridad_cargo_nombre IS NOT DISTINCT FROM OLD.autoridad_cargo_nombre
            AND NEW.autoridad_unidad IS NOT DISTINCT FROM OLD.autoridad_unidad
            AND NEW.autoridad_funcionario_id IS NOT DISTINCT FROM OLD.autoridad_funcionario_id
            AND NEW.autoridad_funcionario_nombre IS NOT DISTINCT FROM OLD.autoridad_funcionario_nombre
            AND NEW.formalizado_por IS NOT DISTINCT FROM OLD.formalizado_por
            AND NEW.formalizado_en IS NOT DISTINCT FROM OLD.formalizado_en
            AND NEW.snapshot::text IS NOT DISTINCT FROM OLD.snapshot::text
            AND NEW.huella IS NOT DISTINCT FROM OLD.huella
            AND NEW.policy_id IS NOT DISTINCT FROM OLD.policy_id
            AND NEW.policy_version IS NOT DISTINCT FROM OLD.policy_version
            AND NEW.year_id IS NOT DISTINCT FROM OLD.year_id) THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CAUSE_IMMUTABLE', DETAIL = TG_OP;
        END IF;
    END IF;
    IF NEW.company_id IS DISTINCT FROM OLD.company_id
        OR NEW.year_id IS DISTINCT FROM OLD.year_id
        OR NEW.commitment_id IS DISTINCT FROM OLD.commitment_id
        OR NEW.created_by IS DISTINCT FROM OLD.created_by THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CAUSE_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql
""",
    "CREATE TRIGGER trg_gov_budget_causes_guard BEFORE UPDATE OR DELETE ON gov_budget_causes FOR EACH ROW EXECUTE FUNCTION kontrol_gov_budget_cause_guard()",
    "CREATE TRIGGER trg_gov_budget_causes_no_truncate BEFORE TRUNCATE ON gov_budget_causes FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_budget_cause_guard()",
    """
CREATE OR REPLACE FUNCTION kontrol_gov_budget_cause_children_guard() RETURNS TRIGGER AS $$
DECLARE
    v_estado TEXT;
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CAUSE_CHILDREN_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CAUSE_CHILDREN_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    SELECT estado INTO v_estado FROM gov_budget_causes WHERE id = COALESCE(NEW.cause_id, OLD.cause_id);
    IF v_estado IS DISTINCT FROM 'BORRADOR' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CAUSE_CHILDREN_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql
""",
    "CREATE TRIGGER trg_gov_budget_cause_lines_guard BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_cause_lines FOR EACH ROW EXECUTE FUNCTION kontrol_gov_budget_cause_children_guard()",
    "CREATE TRIGGER trg_gov_budget_cause_lines_no_truncate BEFORE TRUNCATE ON gov_budget_cause_lines FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_budget_cause_children_guard()",
    "CREATE TRIGGER trg_gov_budget_cause_evidences_guard BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_cause_evidences FOR EACH ROW EXECUTE FUNCTION kontrol_gov_budget_cause_children_guard()",
    "CREATE TRIGGER trg_gov_budget_cause_evidences_no_truncate BEFORE TRUNCATE ON gov_budget_cause_evidences FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_budget_cause_children_guard()",
    "CREATE TRIGGER trg_gov_budget_cause_history_guard BEFORE UPDATE OR DELETE ON gov_budget_cause_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
    "CREATE TRIGGER trg_gov_budget_cause_history_no_truncate BEFORE TRUNCATE ON gov_budget_cause_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
    "CREATE TRIGGER trg_gov_budget_causing_policy_history_guard BEFORE UPDATE OR DELETE ON gov_budget_causing_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
    "CREATE TRIGGER trg_gov_budget_causing_policy_history_no_truncate BEFORE TRUNCATE ON gov_budget_causing_policy_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
)

def _registrar_sentencia_en_tabla(sentencia: str, tabla: str) -> bool:
    return f" ON {tabla} " in sentencia

for _sentencia in GOV_BUDGET_CAUSES_GUARD_PG:
    if "CREATE OR REPLACE FUNCTION kontrol_gov_budget_cause_children_guard" in _sentencia:
        event.listen(
            GovernmentBudgetCauseLine.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
        event.listen(
            GovernmentBudgetCauseEvidence.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
    elif _registrar_sentencia_en_tabla(_sentencia, "gov_budget_cause_lines"):
        event.listen(
            GovernmentBudgetCauseLine.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
    elif _registrar_sentencia_en_tabla(_sentencia, "gov_budget_cause_evidences"):
        event.listen(
            GovernmentBudgetCauseEvidence.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
    elif _registrar_sentencia_en_tabla(_sentencia, "gov_budget_cause_history"):
        event.listen(
            GovernmentBudgetCauseHistory.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
    elif _registrar_sentencia_en_tabla(_sentencia, "gov_budget_causing_policy_history"):
        event.listen(
            GovernmentBudgetCausingPolicyHistory.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
    else:
        event.listen(
            GovernmentBudgetCause.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )


ESTADOS_POLITICA_ORDEN_PAGO = ("BORRADOR", "VIGENTE", "CERRADA")
TIPOS_REGLA_ORDEN_PAGO = ("INSTITUTIONAL_POLICY", "OPERATIONAL_CONFIGURATION", "LEGAL_MANDATORY")
ETAPAS_DOCUMENTO_ORDEN_PAGO = ("EMISION",)
ESTADOS_ORDEN_PAGO = ("BORRADOR", "EMITIDA", "ANULADA")


class GovernmentPaymentOrderSettings(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Configuración del ente para la orden de pago (TRE-03): patrón de numeración."""

    __tablename__ = "gov_payment_order_settings"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    patron: Mapped[str] = mapped_column(String(60), nullable=False, default="{ANIO}-{NUMERO:5}")

    __table_args__ = (
        UniqueConstraint("company_id", name="uq_gov_payment_order_settings_company_id"),
    )


class GovernmentPaymentOrderPolicy(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Política de orden de pago del ente (TRE-03, GOV-TRE-003)."""

    __tablename__ = "gov_payment_order_policies"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo_gasto: Mapped[str | None] = mapped_column(String(40), nullable=True)
    requiere_expediente_completo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    competencia_accion: Mapped[str] = mapped_column(String(16), nullable=False, default="ORDENAR_PAGO", server_default="ORDENAR_PAGO")
    competencia_materia: Mapped[str] = mapped_column(String(16), nullable=False, default="TESORERIA", server_default="TESORERIA")
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    fundamento: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    act_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=True)
    tipo_regla: Mapped[str] = mapped_column(String(26), nullable=False, default="INSTITUTIONAL_POLICY", server_default="INSTITUTIONAL_POLICY")
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="BORRADOR", server_default="BORRADOR")
    activada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    activada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cerrada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_cierre: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_payment_order_policies_company_codigo"),
        CheckConstraint(f"estado IN ({en(ESTADOS_POLITICA_ORDEN_PAGO)})", name="estado"),
        CheckConstraint(f"tipo_regla IN ({en(TIPOS_REGLA_ORDEN_PAGO)})", name="tipo_regla"),
        CheckConstraint(f"competencia_accion IN ({en(ACCIONES_COMPETENCIA)})", name="competencia_accion"),
        CheckConstraint(f"competencia_materia IN ({en(MATERIAS_COMPETENCIA)})", name="competencia_materia"),
        CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        CheckConstraint("estado = 'BORRADOR' OR fundamento IS NOT NULL", name="fundamento"),
    )


class GovernmentPaymentOrderPolicyDocument(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Documento exigido por una política de orden de pago (RequiredDocument)."""

    __tablename__ = "gov_payment_order_policy_documents"
    __scope__ = Scope.COMPANY

    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_payment_order_policies.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    document_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_types.id"), nullable=False)
    obligatorio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    etapa: Mapped[str] = mapped_column(String(10), nullable=False, default="EMISION", server_default="EMISION")
    condicion: Mapped[str | None] = mapped_column(String(300), nullable=True)

    __table_args__ = (
        UniqueConstraint("policy_id", "document_type_id", name="uq_gov_payment_order_policy_docs_type"),
        CheckConstraint(f"etapa IN ({en(ETAPAS_DOCUMENTO_ORDEN_PAGO)})", name="etapa"),
    )


class GovernmentPaymentOrderPolicyHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia inmutable de una política de orden de pago."""

    __tablename__ = "gov_payment_order_policy_history"
    __scope__ = Scope.COMPANY

    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_payment_order_policies.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    evento: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    instantanea: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class GovernmentPaymentOrder(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Orden de pago (TRE-03, GOV-TRE-003): instrucción de pago contra causados formalizados."""

    __tablename__ = "gov_payment_orders"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    year_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_years.id"), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_payment_order_policies.id"), nullable=False, index=True)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="BORRADOR", server_default="BORRADOR")
    numero: Mapped[int | None] = mapped_column(Integer, nullable=True)
    codigo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    fecha_orden: Mapped[date] = mapped_column(Date, nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    concepto: Mapped[str] = mapped_column(String(500), nullable=False)
    beneficiario: Mapped[str | None] = mapped_column(String(200), nullable=True)
    autoridad_cargo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=True)
    autoridad_cargo_codigo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    autoridad_cargo_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    autoridad_unidad: Mapped[str | None] = mapped_column(String(250), nullable=True)
    autoridad_funcionario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    autoridad_funcionario_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    emitida_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    emitida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    huella: Mapped[str | None] = mapped_column(String(64), nullable=True)
    anulada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    anulada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_anulacion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    anulacion_cargo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_payment_orders_company_codigo"),
        UniqueConstraint("year_id", "numero", name="uq_gov_payment_orders_year_numero"),
        CheckConstraint(f"estado IN ({en(ESTADOS_ORDEN_PAGO)})", name="estado"),
        CheckConstraint("monto > 0", name="monto"),
        CheckConstraint("length(moneda) = 3", name="moneda"),
        CheckConstraint(
            "estado = 'BORRADOR' OR (beneficiario IS NOT NULL AND codigo IS NOT NULL AND emitida_por IS NOT NULL AND emitida_en IS NOT NULL AND huella IS NOT NULL)",
            name="emision",
        ),
        CheckConstraint("(estado = 'ANULADA') = (anulada_por IS NOT NULL AND anulada_en IS NOT NULL AND motivo_anulacion IS NOT NULL)", name="anulacion"),
    )


class GovernmentPaymentOrderLine(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Imputación de una orden de pago a un causado."""

    __tablename__ = "gov_payment_order_lines"
    __scope__ = Scope.COMPANY

    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_payment_orders.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    cause_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_budget_causes.id"), nullable=False, index=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint("order_id", "cause_id", name="uq_gov_payment_order_lines_order_cause"),
        CheckConstraint("monto > 0", name="monto"),
    )


class GovernmentPaymentOrderDocument(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Documento aportado a una orden de pago en emisión."""

    __tablename__ = "gov_payment_order_documents"
    __scope__ = Scope.COMPANY

    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_payment_orders.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    document_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_types.id"), nullable=False)
    document_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        UniqueConstraint("order_id", "document_id", name="uq_gov_payment_order_documents_order_doc"),
    )


class GovernmentPaymentOrderHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia append-only de la orden de pago."""

    __tablename__ = "gov_payment_order_history"
    __scope__ = Scope.COMPANY

    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_payment_orders.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    evento: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    instantanea: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


GOV_PAYMENT_ORDERS_GUARD_PG = (
    """
CREATE OR REPLACE FUNCTION kontrol_gov_payment_order_guard() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_ORDER_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        IF OLD.estado <> 'BORRADOR' THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_ORDER_IMMUTABLE', DETAIL = TG_OP;
        END IF;
        RETURN OLD;
    END IF;
    IF OLD.estado = 'ANULADA' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_ORDER_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF OLD.estado = 'EMITIDA' THEN
        IF NOT (NEW.estado = 'ANULADA'
            AND NEW.anulada_por IS DISTINCT FROM OLD.anulada_por
            AND NEW.anulada_en IS DISTINCT FROM OLD.anulada_en
            AND NEW.motivo_anulacion IS DISTINCT FROM OLD.motivo_anulacion
            AND NEW.anulacion_cargo_id IS DISTINCT FROM OLD.anulacion_cargo_id
            AND NEW.version IS DISTINCT FROM OLD.version
            AND NEW.updated_at IS DISTINCT FROM OLD.updated_at
            AND NEW.numero IS NOT DISTINCT FROM OLD.numero
            AND NEW.codigo IS NOT DISTINCT FROM OLD.codigo
            AND NEW.fecha_orden IS NOT DISTINCT FROM OLD.fecha_orden
            AND NEW.moneda IS NOT DISTINCT FROM OLD.moneda
            AND NEW.monto IS NOT DISTINCT FROM OLD.monto
            AND NEW.concepto IS NOT DISTINCT FROM OLD.concepto
            AND NEW.beneficiario IS NOT DISTINCT FROM OLD.beneficiario
            AND NEW.autoridad_cargo_id IS NOT DISTINCT FROM OLD.autoridad_cargo_id
            AND NEW.autoridad_cargo_codigo IS NOT DISTINCT FROM OLD.autoridad_cargo_codigo
            AND NEW.autoridad_cargo_nombre IS NOT DISTINCT FROM OLD.autoridad_cargo_nombre
            AND NEW.autoridad_unidad IS NOT DISTINCT FROM OLD.autoridad_unidad
            AND NEW.autoridad_funcionario_id IS NOT DISTINCT FROM OLD.autoridad_funcionario_id
            AND NEW.autoridad_funcionario_nombre IS NOT DISTINCT FROM OLD.autoridad_funcionario_nombre
            AND NEW.emitida_por IS NOT DISTINCT FROM OLD.emitida_por
            AND NEW.emitida_en IS NOT DISTINCT FROM OLD.emitida_en
            AND NEW.snapshot::text IS NOT DISTINCT FROM OLD.snapshot::text
            AND NEW.huella IS NOT DISTINCT FROM OLD.huella
            AND NEW.policy_id IS NOT DISTINCT FROM OLD.policy_id
            AND NEW.policy_version IS NOT DISTINCT FROM OLD.policy_version
            AND NEW.year_id IS NOT DISTINCT FROM OLD.year_id) THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_ORDER_IMMUTABLE', DETAIL = TG_OP;
        END IF;
    END IF;
    IF NEW.company_id IS DISTINCT FROM OLD.company_id
        OR NEW.year_id IS DISTINCT FROM OLD.year_id
        OR NEW.policy_id IS DISTINCT FROM OLD.policy_id
        OR NEW.policy_version IS DISTINCT FROM OLD.policy_version
        OR NEW.created_by IS DISTINCT FROM OLD.created_by THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_ORDER_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql
""",
    "CREATE TRIGGER trg_gov_payment_orders_guard BEFORE UPDATE OR DELETE ON gov_payment_orders FOR EACH ROW EXECUTE FUNCTION kontrol_gov_payment_order_guard()",
    "CREATE TRIGGER trg_gov_payment_orders_no_truncate BEFORE TRUNCATE ON gov_payment_orders FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_payment_order_guard()",
    """
CREATE OR REPLACE FUNCTION kontrol_gov_payment_order_children_guard() RETURNS TRIGGER AS $$
DECLARE
    v_estado TEXT;
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_ORDER_CHILDREN_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_ORDER_CHILDREN_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    SELECT estado INTO v_estado FROM gov_payment_orders WHERE id = COALESCE(NEW.order_id, OLD.order_id);
    IF v_estado IS DISTINCT FROM 'BORRADOR' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_ORDER_CHILDREN_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql
""",
    "CREATE TRIGGER trg_gov_payment_order_lines_guard BEFORE INSERT OR UPDATE OR DELETE ON gov_payment_order_lines FOR EACH ROW EXECUTE FUNCTION kontrol_gov_payment_order_children_guard()",
    "CREATE TRIGGER trg_gov_payment_order_lines_no_truncate BEFORE TRUNCATE ON gov_payment_order_lines FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_payment_order_children_guard()",
    "CREATE TRIGGER trg_gov_payment_order_documents_guard BEFORE INSERT OR UPDATE OR DELETE ON gov_payment_order_documents FOR EACH ROW EXECUTE FUNCTION kontrol_gov_payment_order_children_guard()",
    "CREATE TRIGGER trg_gov_payment_order_documents_no_truncate BEFORE TRUNCATE ON gov_payment_order_documents FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_payment_order_children_guard()",
    "CREATE TRIGGER trg_gov_payment_order_history_guard BEFORE UPDATE OR DELETE ON gov_payment_order_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
    "CREATE TRIGGER trg_gov_payment_order_history_no_truncate BEFORE TRUNCATE ON gov_payment_order_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
    "CREATE TRIGGER trg_gov_payment_order_policy_history_guard BEFORE UPDATE OR DELETE ON gov_payment_order_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
    "CREATE TRIGGER trg_gov_payment_order_policy_history_no_truncate BEFORE TRUNCATE ON gov_payment_order_policy_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
)


def _registrar_sentencia_tre03_en_tabla(sentencia: str, tabla: str) -> bool:
    return f" ON {tabla} " in sentencia


for _sentencia in GOV_PAYMENT_ORDERS_GUARD_PG:
    if "CREATE OR REPLACE FUNCTION kontrol_gov_payment_order_children_guard" in _sentencia:
        event.listen(
            GovernmentPaymentOrderLine.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
        event.listen(
            GovernmentPaymentOrderDocument.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
    elif _registrar_sentencia_tre03_en_tabla(_sentencia, "gov_payment_order_lines"):
        event.listen(
            GovernmentPaymentOrderLine.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
    elif _registrar_sentencia_tre03_en_tabla(_sentencia, "gov_payment_order_documents"):
        event.listen(
            GovernmentPaymentOrderDocument.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
    elif _registrar_sentencia_tre03_en_tabla(_sentencia, "gov_payment_order_history"):
        event.listen(
            GovernmentPaymentOrderHistory.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
    elif _registrar_sentencia_tre03_en_tabla(_sentencia, "gov_payment_order_policy_history"):
        event.listen(
            GovernmentPaymentOrderPolicyHistory.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
    else:
        event.listen(
            GovernmentPaymentOrder.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )


ESTADOS_MEDIO_PAGO = ("ACTIVO", "INACTIVO")
ESTADOS_POLITICA_PAGO = ("BORRADOR", "VIGENTE", "CERRADA")
CONTROLES_DUPLICADO_PAGO = ("BLOQUEAR", "ADVERTIR")
ETAPAS_DOCUMENTO_PAGO = ("PREPARAR", "AUTORIZAR", "REGISTRAR", "ANULAR")
ESTADOS_PAGO = ("BORRADOR", "PENDIENTE_AUTORIZACION", "AUTORIZADO", "REGISTRADO", "RECHAZADO", "ANULADO")
ESTADOS_PAGO_EN_TRAMITE = ("PENDIENTE_AUTORIZACION", "AUTORIZADO")
ESTADOS_PAGO_ACTIVOS = ("PENDIENTE_AUTORIZACION", "AUTORIZADO", "REGISTRADO")
DECISIONES_APROBACION_PAGO = ("APROBADA", "RECHAZADA")


class GovernmentPaymentSettings(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Configuración del ente para el pago (TRE-04): patrón de numeración."""

    __tablename__ = "gov_payment_settings"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    patron: Mapped[str] = mapped_column(String(60), nullable=False, default="{ANIO}-{NUMERO:5}")

    __table_args__ = (
        UniqueConstraint("company_id", name="uq_gov_payment_settings_company_id"),
    )


class GovernmentPaymentMethod(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Medio de pago del ente (TRE-04)."""

    __tablename__ = "gov_payment_methods"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="ACTIVO", server_default="ACTIVO")
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    exige_referencia: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    referencia_unica: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    patron_referencia: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fundamento: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_payment_methods_company_codigo"),
        CheckConstraint(f"estado IN ({en(ESTADOS_MEDIO_PAGO)})", name="estado"),
        CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        CheckConstraint("referencia_unica = false OR exige_referencia = true", name="referencia_unica"),
    )


class GovernmentPaymentPolicy(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Política de pago del ente (TRE-04, GOV-TRE-004)."""

    __tablename__ = "gov_payment_policies"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    numero_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    version_anterior_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_payment_policies.id"), nullable=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    permite_pago_parcial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    preparador_competencia_accion: Mapped[str | None] = mapped_column(String(16), nullable=True)
    preparador_competencia_materia: Mapped[str | None] = mapped_column(String(16), nullable=True)
    exige_cargo_autorizado_cuenta: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    control_duplicado: Mapped[str] = mapped_column(String(10), nullable=False, default="BLOQUEAR", server_default="BLOQUEAR")
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    fundamento: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    act_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_acts.id"), nullable=True)
    tipo_regla: Mapped[str] = mapped_column(String(26), nullable=False, default="INSTITUTIONAL_POLICY", server_default="INSTITUTIONAL_POLICY")
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="BORRADOR", server_default="BORRADOR")
    activada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    activada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cerrada_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_cierre: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", "numero_version", name="uq_gov_payment_policies_company_codigo_version"),
        CheckConstraint(f"estado IN ({en(ESTADOS_POLITICA_PAGO)})", name="estado"),
        CheckConstraint(f"tipo_regla IN ({en(TIPOS_REGLA_ORDEN_PAGO)})", name="tipo_regla"),
        CheckConstraint(f"control_duplicado IN ({en(CONTROLES_DUPLICADO_PAGO)})", name="control_duplicado"),
        CheckConstraint(f"moneda IN ({en(MONEDAS_LIMITE)})", name="moneda"),
        CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        CheckConstraint("estado = 'BORRADOR' OR fundamento IS NOT NULL", name="fundamento"),
        CheckConstraint("(preparador_competencia_accion IS NULL) = (preparador_competencia_materia IS NULL)", name="preparador"),
        CheckConstraint(f"preparador_competencia_accion IS NULL OR preparador_competencia_accion IN ({en(ACCIONES_COMPETENCIA)})", name="preparador_accion"),
        CheckConstraint(f"preparador_competencia_materia IS NULL OR preparador_competencia_materia IN ({en(MATERIAS_COMPETENCIA)})", name="preparador_materia"),
        CheckConstraint("numero_version >= 1", name="numero_version"),
    )


class GovernmentPaymentPolicyMethod(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Medio habilitado por una política de pago."""

    __tablename__ = "gov_payment_policy_methods"
    __scope__ = Scope.COMPANY

    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_payment_policies.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    method_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_payment_methods.id"), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("policy_id", "method_id", name="uq_gov_payment_policy_methods_policy_method"),
    )


class GovernmentPaymentPolicyBand(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Banda de aprobación de una política de pago (ApprovalBand)."""

    __tablename__ = "gov_payment_policy_bands"
    __scope__ = Scope.COMPANY

    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_payment_policies.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    monto_desde: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    monto_hasta: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    requisitos: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        UniqueConstraint("policy_id", "orden", name="uq_gov_payment_policy_bands_policy_orden"),
        CheckConstraint("monto_desde >= 0", name="desde"),
        CheckConstraint("monto_hasta IS NULL OR monto_hasta > monto_desde", name="hasta"),
    )


class GovernmentPaymentPolicyDocument(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Documento exigido por una política de pago."""

    __tablename__ = "gov_payment_policy_documents"
    __scope__ = Scope.COMPANY

    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_payment_policies.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    document_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_types.id"), nullable=False)
    etapa: Mapped[str] = mapped_column(String(10), nullable=False)
    obligatorio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    __table_args__ = (
        UniqueConstraint("policy_id", "document_type_id", "etapa", name="uq_gov_payment_policy_documents_type_etapa"),
        CheckConstraint(f"etapa IN ({en(ETAPAS_DOCUMENTO_PAGO)})", name="etapa"),
    )


class GovernmentPaymentPolicyHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia inmutable de una política de pago."""

    __tablename__ = "gov_payment_policy_history"
    __scope__ = Scope.COMPANY

    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_payment_policies.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    evento: Mapped[str] = mapped_column(String(32), nullable=False)
    numero_version: Mapped[int] = mapped_column(Integer, nullable=False)
    instantanea: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class GovernmentPayment(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Pago de una orden de pago (TRE-04, GOV-TRE-004/005/010)."""

    __tablename__ = "gov_payments"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_payment_orders.id"), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_payment_policies.id"), nullable=False, index=True)
    policy_numero_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    policy_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    estado: Mapped[str] = mapped_column(String(22), nullable=False, default="BORRADOR", server_default="BORRADOR")
    numero: Mapped[int | None] = mapped_column(Integer, nullable=True)
    codigo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    fecha_pago: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_valor: Mapped[date | None] = mapped_column(Date, nullable=True)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_bank_accounts.id"), nullable=False, index=True)
    method_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_payment_methods.id"), nullable=False, index=True)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    concepto: Mapped[str] = mapped_column(String(500), nullable=False)
    referencia_externa: Mapped[str | None] = mapped_column(String(120), nullable=True)
    referencia_clave: Mapped[str | None] = mapped_column(String(120), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    registro_idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    documentos_preparar: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    preparador_cargo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=True)
    preparador_cargo_codigo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    preparador_cargo_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    preparador_funcionario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    preparador_funcionario_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    enviado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    enviado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    aprobaciones_requeridas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duplicado_confirmado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    motivo_duplicado: Mapped[str | None] = mapped_column(String(500), nullable=True)
    registrado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    registrado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rechazado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    rechazado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_rechazo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    anulado_por: Mapped[str | None] = mapped_column(String(36), nullable=True)
    anulado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_anulacion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    huella: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "codigo", name="uq_gov_payments_company_codigo"),
        Index("uq_gov_payments_idempotency", "company_id", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL"), sqlite_where=text("idempotency_key IS NOT NULL")),
        Index("uq_gov_payments_registro_idempotency", "company_id", "registro_idempotency_key", unique=True, postgresql_where=text("registro_idempotency_key IS NOT NULL"), sqlite_where=text("registro_idempotency_key IS NOT NULL")),
        Index("uq_gov_payments_referencia", "company_id", "method_id", "referencia_clave", unique=True, postgresql_where=text("referencia_clave IS NOT NULL"), sqlite_where=text("referencia_clave IS NOT NULL")),
        CheckConstraint(f"estado IN ({en(ESTADOS_PAGO)})", name="estado"),
        CheckConstraint("monto > 0", name="monto"),
        CheckConstraint("length(moneda) = 3", name="moneda"),
        CheckConstraint("estado IN ('BORRADOR', 'ANULADO') OR (codigo IS NOT NULL AND enviado_por IS NOT NULL AND enviado_en IS NOT NULL AND policy_numero_version IS NOT NULL AND policy_snapshot IS NOT NULL AND aprobaciones_requeridas IS NOT NULL)", name="envio"),
        CheckConstraint("(estado = 'REGISTRADO') = (registrado_por IS NOT NULL AND registrado_en IS NOT NULL AND fecha_valor IS NOT NULL)", name="registro"),
        CheckConstraint("(estado = 'RECHAZADO') = (rechazado_por IS NOT NULL AND rechazado_en IS NOT NULL AND motivo_rechazo IS NOT NULL)", name="rechazo"),
        CheckConstraint("(estado = 'ANULADO') = (anulado_por IS NOT NULL AND anulado_en IS NOT NULL AND motivo_anulacion IS NOT NULL)", name="anulacion"),
        CheckConstraint("referencia_clave IS NULL OR estado = 'REGISTRADO'", name="referencia_clave"),
        CheckConstraint("duplicado_confirmado = false OR motivo_duplicado IS NOT NULL", name="duplicado"),
        CheckConstraint("aprobaciones_requeridas IS NULL OR aprobaciones_requeridas >= 1", name="aprobaciones"),
    )


class GovernmentPaymentApproval(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Autorización individual de un pago (maker-checker)."""

    __tablename__ = "gov_payment_approvals"
    __scope__ = Scope.COMPANY

    payment_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_payments.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    cargo_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_positions.id"), nullable=False)
    cargo_codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    cargo_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    unidad: Mapped[str | None] = mapped_column(String(250), nullable=True)
    funcionario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    funcionario_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    requisito_indice: Mapped[int | None] = mapped_column(Integer, nullable=True)
    competencia_accion: Mapped[str | None] = mapped_column(String(16), nullable=True)
    competencia_materia: Mapped[str | None] = mapped_column(String(16), nullable=True)
    decision: Mapped[str] = mapped_column(String(10), nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    policy_numero_version: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("payment_id", "actor_id", name="uq_gov_payment_approvals_payment_actor"),
        CheckConstraint(f"decision IN ({en(DECISIONES_APROBACION_PAGO)})", name="decision"),
        CheckConstraint("decision = 'APROBADA' OR motivo IS NOT NULL", name="motivo"),
        CheckConstraint("decision = 'RECHAZADA' OR requisito_indice IS NOT NULL", name="requisito"),
    )


class GovernmentPaymentDocument(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Documento aportado a un pago."""

    __tablename__ = "gov_payment_documents"
    __scope__ = Scope.COMPANY

    payment_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_payments.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    etapa: Mapped[str] = mapped_column(String(10), nullable=False)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    document_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_types.id"), nullable=False)
    document_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        UniqueConstraint("payment_id", "document_id", "etapa", name="uq_gov_payment_documents_payment_doc_etapa"),
        CheckConstraint(f"etapa IN ({en(ETAPAS_DOCUMENTO_PAGO)})", name="etapa"),
    )


class GovernmentPaymentHistory(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Historia append-only de un pago."""

    __tablename__ = "gov_payment_history"
    __scope__ = Scope.COMPANY

    payment_id: Mapped[str] = mapped_column(String(36), ForeignKey("gov_payments.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    evento: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    instantanea: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


GOV_PAYMENTS_GUARD_PG = (
    """
CREATE OR REPLACE FUNCTION kontrol_gov_payment_guard() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF OLD.estado IN ('REGISTRADO','RECHAZADO','ANULADO') THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF NEW.company_id IS DISTINCT FROM OLD.company_id
        OR NEW.order_id IS DISTINCT FROM OLD.order_id
        OR NEW.created_by IS DISTINCT FROM OLD.created_by
        OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql
""",
    "CREATE TRIGGER trg_gov_payments_guard BEFORE UPDATE OR DELETE ON gov_payments FOR EACH ROW EXECUTE FUNCTION kontrol_gov_payment_guard()",
    "CREATE TRIGGER trg_gov_payments_no_truncate BEFORE TRUNCATE ON gov_payments FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_payment_guard()",
    "CREATE TRIGGER trg_gov_payment_approvals_guard BEFORE UPDATE OR DELETE ON gov_payment_approvals FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
    "CREATE TRIGGER trg_gov_payment_approvals_no_truncate BEFORE TRUNCATE ON gov_payment_approvals FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
    "CREATE TRIGGER trg_gov_payment_documents_guard BEFORE UPDATE OR DELETE ON gov_payment_documents FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
    "CREATE TRIGGER trg_gov_payment_documents_no_truncate BEFORE TRUNCATE ON gov_payment_documents FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
    "CREATE TRIGGER trg_gov_payment_history_guard BEFORE UPDATE OR DELETE ON gov_payment_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
    "CREATE TRIGGER trg_gov_payment_history_no_truncate BEFORE TRUNCATE ON gov_payment_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
    "CREATE TRIGGER trg_gov_payment_policy_history_guard BEFORE UPDATE OR DELETE ON gov_payment_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
    "CREATE TRIGGER trg_gov_payment_policy_history_no_truncate BEFORE TRUNCATE ON gov_payment_policy_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()",
)


def _registrar_sentencia_tre04_en_tabla(sentencia: str, tabla: str) -> bool:
    return f" ON {tabla} " in sentencia


for _sentencia in GOV_PAYMENTS_GUARD_PG:
    if "CREATE OR REPLACE FUNCTION kontrol_gov_payment_guard" in _sentencia:
        event.listen(
            GovernmentPayment.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
    elif _registrar_sentencia_tre04_en_tabla(_sentencia, "gov_payment_approvals"):
        event.listen(
            GovernmentPaymentApproval.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
    elif _registrar_sentencia_tre04_en_tabla(_sentencia, "gov_payment_documents"):
        event.listen(
            GovernmentPaymentDocument.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
    elif _registrar_sentencia_tre04_en_tabla(_sentencia, "gov_payment_history"):
        event.listen(
            GovernmentPaymentHistory.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
    elif _registrar_sentencia_tre04_en_tabla(_sentencia, "gov_payment_policy_history"):
        event.listen(
            GovernmentPaymentPolicyHistory.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
    else:
        event.listen(
            GovernmentPayment.__table__,
            "after_create",
            DDL(_sentencia).execute_if(dialect="postgresql"),
        )
