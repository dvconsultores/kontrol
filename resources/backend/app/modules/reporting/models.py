"""Modelos de reportes y auditoría (009, data-model.md).

Centro de información: exportaciones auditadas, trabajos asíncronos y catálogo
de reportes. Los reportes se **reconstruyen** desde eventos y documentos de
003-008 (nunca tablas editables); la auditoría reutiliza `AuditEvent` de 001.

Invariantes (Constitución P4/P5, DOC-01 §1/§5):
- Saldos, libros y estados se reconstruyen desde eventos auditables.
- Las exportaciones son auditadas (quién, cuándo, qué, filtros).
- 009 consume datos de 003-008 en lectura; no duplica su lógica.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import CreatedByMixin, TimestampMixin, UUIDMixin


class ReportDefinition(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "report_definitions"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    report_key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    # EXECUTIVE / OPERATIONAL / FINANCIAL / FISCAL / REGULATORY
    enabled: Mapped[str] = mapped_column(String(8), nullable=False, default="true")


class ReportExport(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "report_exports"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    report_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(8), nullable=False, default="CSV")  # CSV / PDF
    filters: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    file_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exported_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DONE")


class ReportJob(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "report_jobs"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    report_key: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    # PENDING / RUNNING / DONE / FAILED
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
