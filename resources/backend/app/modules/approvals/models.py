"""Modelos del motor de aprobaciones (Spec 045, `data-model.md`).

Siete entidades. Todas llevan `company_id` y se filtran por alcance (ADR-011,
Constitución P11). Importes en `Numeric` (ADR-016); fechas con timezone (P21).

Nada de negocio se codifica aquí: umbrales, niveles, roles y tipos de proceso
son datos (Constitución P8).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
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
from app.shared.mixins import CreatedByMixin, TimestampMixin, UUIDMixin

# --------------------------------------------------------------------------- #
# Configuración
# --------------------------------------------------------------------------- #


class ApprovalPolicy(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Política versionada por empresa y tipo de proceso (FR-045-001)."""

    __tablename__ = "approval_policies"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "process_type", "version", name="uq_approval_policies_company_process_version"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    process_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")  # DRAFT/ACTIVE/CLOSED
    requires_segregation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_self_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    distinct_actors_across_levels: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    base_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")


class ApprovalRule(UUIDMixin, TimestampMixin, Base):
    """Condición de disparo dentro de una política (FR-045-002).

    `conditions` es una lista de predicados tipados `{field, operator, value}`
    combinados con AND. El OR se expresa con varias reglas (CL-045-04).
    `condition_fields` es la base de la huella de obsolescencia (CL-045-05).
    """

    __tablename__ = "approval_rules"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "policy_id → approval_policies"

    policy_id: Mapped[str] = mapped_column(ForeignKey("approval_policies.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    conditions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    condition_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_exception: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    risk_class: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ApprovalLevel(UUIDMixin, TimestampMixin, Base):
    """Nivel requerido por una regla (FR-045-003)."""

    __tablename__ = "approval_levels"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "rule_id → approval_rules"

    rule_id: Mapped[str] = mapped_column(ForeignKey("approval_rules.id"), nullable=False, index=True)
    level_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    resolver_type: Mapped[str] = mapped_column(String(32), nullable=False)  # ROLE/USER/SCOPE_OWNER
    resolver_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    quorum_type: Mapped[str] = mapped_column(String(16), nullable=False, default="ANY")  # ANY/ALL/N_OF_M
    quorum_n: Mapped[int | None] = mapped_column(Integer, nullable=True)
    can_delegate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sla_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)


# --------------------------------------------------------------------------- #
# Solicitud
# --------------------------------------------------------------------------- #


class ApprovalRequest(UUIDMixin, TimestampMixin, Base):
    """Solicitud de aprobación con snapshot de política y huella (FR-045-020).

    El snapshot congela la política aplicada: cambiarla después NO altera esta
    solicitud (`ADR-D0-002` R-D0-02-3, Constitución P5/P23).
    """

    __tablename__ = "approval_requests"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        # Impide dos solicitudes vivas para el mismo documento y la misma huella
        # (FR-045-053). Índice parcial: sólo cubre las no terminales.
        Index(
            "uq_approval_requests_open_document",
            "company_id", "document_type", "document_id", "fingerprint",
            unique=True,
            postgresql_where=text("status IN ('PENDING','IN_REVIEW')"),
            sqlite_where=text("status IN ('PENDING','IN_REVIEW')"),
        ),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    process_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    policy_id: Mapped[str | None] = mapped_column(ForeignKey("approval_policies.id"), nullable=True)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    policy_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fingerprint_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    amount_base: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    base_currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    rate_snapshot: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)
    requested_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    current_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)


class ApprovalStep(UUIDMixin, TimestampMixin, Base):
    """Paso (nivel) de una solicitud. `version` da control optimista (FR-045-054)."""

    __tablename__ = "approval_steps"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "request_id → approval_requests"

    request_id: Mapped[str] = mapped_column(ForeignKey("approval_requests.id"), nullable=False, index=True)
    level_order: Mapped[int] = mapped_column(Integer, nullable=False)
    quorum_type: Mapped[str] = mapped_column(String(16), nullable=False, default="ANY")
    quorum_n: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eligible_actors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class ApprovalDecision(UUIDMixin, TimestampMixin, Base):
    """Decisión sobre un paso. Append-only: no se edita ni se borra (P5)."""

    __tablename__ = "approval_decisions"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "step_id → approval_steps"
    __table_args__ = (
        # Un actor no decide dos veces sobre el mismo paso (INV-06).
        UniqueConstraint("step_id", "actor_id", name="uq_approval_decisions_step_actor"),
    )

    step_id: Mapped[str] = mapped_column(ForeignKey("approval_steps.id"), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    on_behalf_of_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    delegation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)  # APPROVE/REJECT/RETURN/CANCEL
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApprovalDelegation(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Delegación acotada en ámbito y vigencia (FR-045-042..046)."""

    __tablename__ = "approval_delegations"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    grantor_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    grantee_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scope_process_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scope_branch_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    scope_cost_center_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_temporary_substitution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ApprovalEvent(UUIDMixin, TimestampMixin, Base):
    """Evento de dominio del motor (FR-045-066).

    Se registra para consumo futuro de la Spec 047 (notificaciones). El motor
    NO notifica: emite. No conoce a 047.
    """

    __tablename__ = "approval_events"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    step_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
