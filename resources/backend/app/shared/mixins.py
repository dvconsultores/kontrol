"""Mixins comunes del modelo (UUID, auditoría, versionado)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=utcnow, nullable=False)


class CreatedByMixin:
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class VersionMixin:
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False, server_default="1")


class CodeMixin:
    code: Mapped[str] = mapped_column(String(64), nullable=False)


class NameMixin:
    name: Mapped[str] = mapped_column(String(200), nullable=False)


class StatusMixin:
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


def as_dict(instance: Any) -> dict[str, Any]:
    return {c.name: getattr(instance, c.name) for c in instance.__table__.columns}
