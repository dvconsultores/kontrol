"""Modelo de gestión documental transversal (Spec 046).

Cuatro entidades con responsabilidades distintas, deliberadamente **no**
fusionadas (R-046-1):

- `Document`        — el documento lógico; sobrevive a sus archivos.
- `DocumentVersion` — una versión histórica; reemplazar no puede destruir.
- `StoredFile`      — el binario, con su hash y su proveedor; puede compartirse.
- `DocumentLink`    — el vínculo con una entidad de cualquier dominio.

`StoredFile` **evoluciona** `file_metadata`, que existía con los cuatro campos
correctos y cero consumidores (ADR-D0-008: `SAFE_MIGRATION`).

Ningún tipo documental ni extensión aparece codificado: todo es dato (P8).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.scope import Scope
from app.shared.mixins import CreatedByMixin, StatusMixin, TimestampMixin, UUIDMixin, VersionMixin

#: Estados del **documento**. `EXPIRED` no está: se deriva de `expiration_date`
#: (FR-046-061). Persistirlo exigiría un proceso que lo mantuviera y crearía el
#: desfase clásico entre la fecha y la etiqueta.
DOCUMENT_STATUSES: tuple[str, ...] = ("DRAFT", "ACTIVE", "SUPERSEDED", "ARCHIVED", "REVOKED")

#: Estado de **seguridad del archivo**, distinto del estado del documento
#: (FR-046-062). Un permiso vigente cuyo PDF está en cuarentena es un estado
#: real que una sola columna no podría expresar.
FILE_SECURITY_STATUSES: tuple[str, ...] = (
    "PENDING_SCAN", "CLEAN", "INFECTED", "SCAN_FAILED", "SKIPPED",
)

#: Disponibilidad del binario.
FILE_STATUSES: tuple[str, ...] = ("AVAILABLE", "QUARANTINED", "PURGED")

#: Marcas del legado. Ninguna crea documento: solo anota (R-046-5).
LEGACY_MARKS: tuple[str, ...] = (
    "VALID_MANAGED_FILE", "EXTERNAL_REFERENCE", "MISSING_FILE",
    "UNVERIFIED_LEGACY", "LEGACY_HASH_WITHOUT_FILE", "MIGRATION_BLOCKER",
)


class DocumentCategory(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, Base):
    """Agrupación para navegar y para permisos gruesos. **Nace vacía.**"""

    __tablename__ = "document_categories"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_document_categories_company_code"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class DocumentType(UUIDMixin, TimestampMixin, CreatedByMixin, StatusMixin, VersionMixin, Base):
    """Donde vive la política. **Nace vacío.**

    `allowed_mime_types` vacío significa **ningún tipo admitido**, no todos: un
    valor por defecto permisivo es la clase de decisión que convierte un
    repositorio en un vector de distribución.
    """

    __tablename__ = "document_types"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_document_types_company_code"),
        CheckConstraint("versioning_policy IN ('VERSIONED','SINGLE')",
                        name="ck_document_types_versioning"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    category_id: Mapped[str | None] = mapped_column(
        ForeignKey("document_categories.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    allowed_mime_types: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=list)
    allowed_extensions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=list)
    max_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    versioning_policy: Mapped[str] = mapped_column(
        String(16), nullable=False, default="VERSIONED", server_default="VERSIONED")
    requires_expiration: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false")
    metadata_schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metadata_schema_version: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=1, server_default="1")
    #: Capacidad de retención, **sin plazos por defecto** (ESC-046-03). El
    #: encargo prohíbe inventar plazos legales.
    retention_policy: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    audit_downloads: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false")
    scan_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true")
    #: Tipos que pueden mostrarse en línea. Vacío = todo se descarga, que es el
    #: valor seguro por defecto.
    inline_preview_mimes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=list)


class StoredFile(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """El binario. Evoluciona `file_metadata`.

    `storage_key` es **opaca** y la genera el servidor: no se deriva del nombre
    del archivo, de la empresa ni del tercero, y no se expone en ninguna
    respuesta (R-046-3, R-D0-08-2).
    """

    __tablename__ = "stored_files"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        CheckConstraint(
            "security_status IN ('PENDING_SCAN','CLEAN','INFECTED','SCAN_FAILED','SKIPPED')",
            name="ck_stored_files_security"),
        CheckConstraint("status IN ('AVAILABLE','QUARANTINED','PURGED')",
                        name="ck_stored_files_status"),
        Index("ix_stored_files_sha256", "sha256"),
    )

    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    #: MIME **efectivo**: el detectado cuando se acepta.
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    #: Lo que dijo el cliente. Se conserva, no se cree (FR-046-043).
    declared_mime: Mapped[str | None] = mapped_column(String(120), nullable=True)
    #: Lo que dicen los bytes.
    detected_mime: Mapped[str | None] = mapped_column(String(120), nullable=True)
    extension: Mapped[str | None] = mapped_column(String(16), nullable=True)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    storage_provider: Mapped[str] = mapped_column(
        String(32), nullable=False, default="FILESYSTEM", server_default="FILESYSTEM")
    security_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="PENDING_SCAN", server_default="PENDING_SCAN")
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="AVAILABLE", server_default="AVAILABLE")
    uploaded_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Document(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """El documento lógico."""

    __tablename__ = "documents"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT','ACTIVE','SUPERSEDED','ARCHIVED','REVOKED')",
            name="ck_documents_status"),
        # Una referencia externa no tiene archivo administrado, y viceversa.
        CheckConstraint(
            "(is_managed = true AND external_url IS NULL) OR "
            "(is_managed = false AND external_url IS NOT NULL)",
            name="ck_documents_external"),
        Index("ix_documents_company_status", "company_id", "status"),
        Index("ix_documents_company_type", "company_id", "document_type_id"),
        Index("ix_documents_company_expiration", "company_id", "expiration_date"),
        # Número externo único por empresa y tipo **solo cuando existe**: dos
        # documentos sin número no colisionan.
        Index("uq_documents_company_type_number",
              "company_id", "document_type_id", "document_number", unique=True,
              postgresql_where=text("document_number IS NOT NULL"),
              sqlite_where=text("document_number IS NOT NULL")),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    document_type_id: Mapped[str] = mapped_column(
        ForeignKey("document_types.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Número del documento externo. **Sin unicidad global** (§70).
    document_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    issuer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    issued_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    #: Base de `EXPIRED`, que es **derivado** (FR-046-061).
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    doc_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metadata_schema_version: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_managed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true")
    current_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DRAFT", server_default="DRAFT")


class DocumentVersion(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Una versión. Inmutable una vez superada o congelada."""

    __tablename__ = "document_versions"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_versions_number"),
        # Una sola versión vigente por documento.
        Index("uq_document_versions_active", "document_id", unique=True,
              postgresql_where=text("status = 'ACTIVE'"),
              sqlite_where=text("status = 'ACTIVE'")),
        CheckConstraint("status IN ('ACTIVE','SUPERSEDED')", name="ck_document_versions_status"),
    )

    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    #: Correlativo asignado por el **servidor** (FR-046-004).
    version_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    stored_file_id: Mapped[str] = mapped_column(ForeignKey("stored_files.id"), nullable=False)
    replacement_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Copia deliberada del hash del archivo: si el binario se purgara por
    #: retención, la versión conservaría la prueba de qué contenía.
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ACTIVE", server_default="ACTIVE")


class DocumentLink(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """El vínculo con una entidad de cualquier dominio.

    `resource_type` se valida contra el **registro cerrado** de tipos de
    recurso: no admite texto libre, porque sin saber sobre qué entidad se
    autoriza, autorizar es imposible (FR-046-022).
    """

    __tablename__ = "document_links"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("document_id", "resource_type", "resource_id", "role",
                         name="uq_document_links_unique"),
        Index("ix_document_links_resource", "resource_type", "resource_id"),
        Index("ix_document_links_document", "document_id"),
    )

    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="ATTACHMENT",
                                      server_default="ATTACHMENT")
    document_type_id: Mapped[str | None] = mapped_column(
        ForeignKey("document_types.id"), nullable=True)
    #: **Versión congelada.** Cuando la entidad consumidora se vuelve inmutable,
    #: el vínculo deja de apuntar a «la última» y pasa a apuntar a **esta**.
    #: Es lo que satisface el contrato de la Spec 045 (FR-046-100).
    frozen_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_frozen: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false")


class FileSecurityScan(UUIDMixin, TimestampMixin, Base):
    """Resultado del análisis. Existe solo si hay analizador."""

    __tablename__ = "file_security_scans"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "stored_file_id → stored_files"

    stored_file_id: Mapped[str] = mapped_column(
        ForeignKey("stored_files.id"), nullable=False, index=True)
    scanner: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[str] = mapped_column(String(24), nullable=False)
    signature: Mapped[str | None] = mapped_column(String(200), nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LegacyDocumentReference(UUIDMixin, TimestampMixin, Base):
    """Anotación del legado. **No es un documento.**

    Registra qué columna heredada contiene una referencia documental y cómo se
    clasificó, sin crear ningún `Document`: una URL, una ruta o un hash sueltos
    no bastan para afirmar que existe un archivo (R-046-5, FR-046-111).
    """

    __tablename__ = "legacy_document_references"
    #: De la instalación heredada que se está clasificando, no de un tenant: la
    #: anotación se escribe **antes** de saber a quién pertenece la fila
    #: original, y por eso `company_id` admite nulo (es el caso MC-D).
    __scope__ = Scope.INSTALLATION
    __table_args__ = (
        UniqueConstraint("source_table", "source_column", "source_row_id",
                         name="uq_legacy_document_references"),
    )

    source_table: Mapped[str] = mapped_column(String(64), nullable=False)
    source_column: Mapped[str] = mapped_column(String(64), nullable=False)
    source_row_id: Mapped[str] = mapped_column(String(36), nullable=False)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    #: El texto original, **intacto**.
    raw_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Solo se rellena si el binario se localizó y se verificó.
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
