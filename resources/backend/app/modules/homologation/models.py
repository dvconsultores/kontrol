"""Módulo de homologación fiscal y liberación de versión (011).

HomologationRecord (acto formal), HomologationEvent (append-only) y
ReleaseVersion (liberación con gates). Reutiliza la identidad de instalación
y el modo de licencia de 001.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import CreatedByMixin, TimestampMixin, UUIDMixin


class HomologationRecord(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Acto de homologación de una versión fiscal (FR-011-001/002/003).

    Solo se considera HOMOLOGADO (derivado) si el estado es APPROVED y existe
    acto formal (DOC-01 §5: no declarar homologado sin acto formal y versión
    fiscal aprobada).
    """

    __tablename__ = "homologation_records"

    installation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fiscal_version: Mapped[str] = mapped_column(String(32), nullable=False)
    modality: Mapped[str] = mapped_column(String(32), nullable=False, default="E_FACTURA")
    formal_act_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    evaluated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class HomologationEvent(UUIDMixin, TimestampMixin, Base):
    """Evento append-only de homologación o liberación (FR-011-004/013).

    `source` distingue HOMOLOGATION de RELEASE; `entity_id` referencia la
    entidad (record o release) y garantiza trazabilidad y conservación.
    """

    __tablename__ = "homologation_events"

    installation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="HOMOLOGATION")
    homologation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ReleaseVersion(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Versión del producto y su liberación a producción (FR-011-010..013).

    La liberación (RELEASED) exige homologación documentada y aprobada, gates
    verdes y licencia válida; en caso contrario queda BLOCKED con razones.
    """

    __tablename__ = "release_versions"
    __table_args__ = (
        UniqueConstraint("installation_id", "version", name="uq_release_versions_inst_version"),
    )

    installation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    changelog: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    gates: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    homologation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    blocked_reasons: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    released_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
