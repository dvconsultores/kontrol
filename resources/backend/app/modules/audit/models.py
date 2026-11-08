"""Módulo de auditoría: AuditEvent append-only (data-model.md §2.4, ADR-012).

La inmutabilidad se garantiza en la base con disparadores `AUDIT_EVENT_IMMUTABLE`
(OD-AUD-05, RNF-GOV-004, FR-001-262); SQLite no tiene TRUNCATE, por eso el
catálogo de disparadores de SQLite solo cubre UPDATE y DELETE. PostgreSQL es la
autoridad.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DDL, JSON, DateTime, ForeignKey, Index, String, event
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.scope import Scope
from app.shared.mixins import TimestampMixin, UUIDMixin

#: Disparadores de inmutabilidad para PostgreSQL (autoridad de auditoría). Una sentencia por cadena;
#: sin el carácter `%` porque SQLAlchemy `DDL` aplica formato `%`.
AUDIT_IMMUTABLE_PG: tuple[str, ...] = (
    "CREATE OR REPLACE FUNCTION kontrol_audit_events_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'AUDIT_EVENT_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$",
    "CREATE TRIGGER trg_audit_events_no_update BEFORE UPDATE ON audit_events FOR EACH ROW EXECUTE FUNCTION kontrol_audit_events_inmutable()",
    "CREATE TRIGGER trg_audit_events_no_delete BEFORE DELETE ON audit_events FOR EACH ROW EXECUTE FUNCTION kontrol_audit_events_inmutable()",
    "CREATE TRIGGER trg_audit_events_no_truncate BEFORE TRUNCATE ON audit_events FOR EACH STATEMENT EXECUTE FUNCTION kontrol_audit_events_inmutable()",
)

#: Equivalentes soportados en SQLite (no dispone de TRUNCATE).
AUDIT_IMMUTABLE_SQLITE: tuple[str, ...] = (
    "CREATE TRIGGER trg_audit_events_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'AUDIT_EVENT_IMMUTABLE'); END",
    "CREATE TRIGGER trg_audit_events_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'AUDIT_EVENT_IMMUTABLE'); END",
)


class AuditEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "audit_events"
    __scope__ = Scope.TENANT
    __table_args__ = (Index("ix_audit_events_tenant_event_time", "tenant_id", "event_time"),)

    tenant_id: Mapped[str | None] = mapped_column(ForeignKey("tenants.id"), nullable=True, index=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="API")
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    institutional_context: Mapped[dict[str, Any] | None] = mapped_column(
        JSON(none_as_null=True), nullable=True
    )


for _sentencia in AUDIT_IMMUTABLE_PG:
    event.listen(AuditEvent.__table__, "after_create", DDL(_sentencia).execute_if(dialect="postgresql"))
for _sentencia in AUDIT_IMMUTABLE_SQLITE:
    event.listen(AuditEvent.__table__, "after_create", DDL(_sentencia).execute_if(dialect="sqlite"))
