"""Registro de ejecuciones del planificador de plataforma (Spec 047 · ADR-D0-015).

# Spec 047 · Planificador de plataforma

Es de la instalación: cada cliente tiene su propia pila, su propia base y su
propio temporizador (R-D0-15-9). No guarda mensajes ni secretos: solo estados,
contadores y códigos de error.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.scope import Scope
from app.shared.mixins import TimestampMixin, UUIDMixin

ESTADOS_TICK = ("STARTED", "COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED", "SKIPPED_OVERLAP")
ESTADOS_MANEJADOR = ("COMPLETED", "FAILED", "DISABLED")
POLITICAS_RECUPERACION = ("DRAIN", "LATEST_WINDOW", "EFFECT_ONCE", "DUE_RETRY", "OWNER_IDEMPOTENT")


def en(valores: tuple[str, ...]) -> str:
    """Lista SQL de literales para una restricción de valores permitidos."""
    return ", ".join(f"'{v}'" for v in valores)


_CONTADORES = ("items_seen >= 0 AND items_processed >= 0 "
               "AND items_skipped >= 0 AND items_failed >= 0")


class SchedulerRun(UUIDMixin, TimestampMixin, Base):
    """Un tick. El solapado también queda escrito, con `SKIPPED_OVERLAP`."""

    __tablename__ = "scheduler_runs"
    __scope__ = Scope.INSTALLATION
    __table_args__ = (
        UniqueConstraint("correlation_id", name="uq_scheduler_runs_correlation_id"),
        CheckConstraint(f"status IN ({en(ESTADOS_TICK)})", name="status"),
        CheckConstraint(_CONTADORES, name="counters"),
    )

    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    #: El «ahora» lógico con el que corrieron los manejadores.
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    items_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    items_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    items_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    items_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)


class SchedulerHandlerRun(UUIDMixin, TimestampMixin, Base):
    """Lo que hizo un manejador dentro de un tick."""

    __tablename__ = "scheduler_handler_runs"
    __scope__ = Scope.INSTALLATION
    __table_args__ = (
        UniqueConstraint("run_id", "handler_code", name="uq_scheduler_handler_runs_run_handler"),
        CheckConstraint(f"status IN ({en(ESTADOS_MANEJADOR)})", name="status"),
        CheckConstraint(f"catch_up IN ({en(POLITICAS_RECUPERACION)})", name="catch_up"),
        CheckConstraint(_CONTADORES, name="counters"),
    )

    run_id: Mapped[str] = mapped_column(ForeignKey("scheduler_runs.id"), nullable=False, index=True)
    handler_code: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_spec: Mapped[str] = mapped_column(String(8), nullable=False)
    catch_up: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    items_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    items_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    items_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    items_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
