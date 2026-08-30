"""Modelo de gestión documental transversal (Spec 046, F1).

Crea las 7 entidades documentales y **evoluciona** `file_metadata` a
`stored_files`: la tabla existía con `sha256`, `storage_key`, `mime_type` y
`size` —los cuatro campos correctos— y **cero consumidores**, de modo que se
extiende sin backfill, tal como `ADR-D0-008` anticipó (`SAFE_MIGRATION`).

Migración de **esquema pura**: válida en modo offline (`alembic upgrade --sql`).
La anotación del legado va en `0024`, que sí lee datos.

Ningún tipo documental, categoría o extensión se crea aquí: los catálogos nacen
vacíos y son dato de cada empresa (P8).

Revision ID: 0023_document_model
Revises: 0022_uom_backfill
Create Date: 2026-08-30
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0023_document_model"
down_revision = "0022_uom_backfill"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Catálogo ---
    op.create_table(
        "document_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "code", name="uq_document_categories_company_code"),
    )
    op.create_index("ix_document_categories_company_id", "document_categories", ["company_id"])

    op.create_table(
        "document_types",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("document_categories.id"), nullable=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("allowed_mime_types", sa.JSON(), nullable=True),
        sa.Column("allowed_extensions", sa.JSON(), nullable=True),
        sa.Column("max_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("versioning_policy", sa.String(16), nullable=False, server_default="VERSIONED"),
        sa.Column("requires_expiration", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata_schema", sa.JSON(), nullable=True),
        sa.Column("metadata_schema_version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("retention_policy", sa.JSON(), nullable=True),
        sa.Column("audit_downloads", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("scan_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("inline_preview_mimes", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "code", name="uq_document_types_company_code"),
        sa.CheckConstraint("versioning_policy IN ('VERSIONED','SINGLE')",
                           name="ck_document_types_versioning"),
    )
    op.create_index("ix_document_types_company_id", "document_types", ["company_id"])

    # --- file_metadata evoluciona a stored_files ---
    op.rename_table("file_metadata", "stored_files")
    if op.get_bind().dialect.name == "postgresql":
        # PostgreSQL conserva los nombres de índice y restricción al renombrar.
        op.execute("ALTER INDEX pk_file_metadata RENAME TO pk_stored_files")
        op.execute("ALTER INDEX ix_file_metadata_company_id RENAME TO ix_stored_files_company_id")
        op.execute("ALTER INDEX uq_file_metadata_storage_key RENAME TO uq_stored_files_storage_key")
    for column in (
        sa.Column("declared_mime", sa.String(120), nullable=True),
        sa.Column("detected_mime", sa.String(120), nullable=True),
        sa.Column("extension", sa.String(16), nullable=True),
        sa.Column("storage_provider", sa.String(32), nullable=False, server_default="FILESYSTEM"),
        sa.Column("security_status", sa.String(24), nullable=False, server_default="PENDING_SCAN"),
        sa.Column("status", sa.String(32), nullable=False, server_default="AVAILABLE"),
        sa.Column("uploaded_by", sa.String(36), nullable=True),
    ):
        op.add_column("stored_files", column)
    op.create_check_constraint(
        "ck_stored_files_security", "stored_files",
        "security_status IN ('PENDING_SCAN','CLEAN','INFECTED','SCAN_FAILED','SKIPPED')")
    op.create_check_constraint("ck_stored_files_status", "stored_files",
                               "status IN ('AVAILABLE','QUARANTINED','PURGED')")
    op.create_index("ix_stored_files_sha256", "stored_files", ["sha256"])

    # --- Documento, versión y vínculo ---
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("document_type_id", sa.String(36), sa.ForeignKey("document_types.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("document_number", sa.String(120), nullable=True),
        sa.Column("issuer", sa.String(200), nullable=True),
        sa.Column("issued_at", sa.Date(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("expiration_date", sa.Date(), nullable=True),
        sa.Column("doc_metadata", sa.JSON(), nullable=True),
        sa.Column("metadata_schema_version", sa.BigInteger(), nullable=True),
        sa.Column("external_url", sa.String(500), nullable=True),
        sa.Column("is_managed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("current_version_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('DRAFT','ACTIVE','SUPERSEDED','ARCHIVED','REVOKED')",
                           name="ck_documents_status"),
        sa.CheckConstraint(
            "(is_managed = true AND external_url IS NULL) OR "
            "(is_managed = false AND external_url IS NOT NULL)", name="ck_documents_external"),
    )
    op.create_index("ix_documents_company_id", "documents", ["company_id"])
    op.create_index("ix_documents_company_status", "documents", ["company_id", "status"])
    op.create_index("ix_documents_company_type", "documents", ["company_id", "document_type_id"])
    op.create_index("ix_documents_company_expiration", "documents",
                    ["company_id", "expiration_date"])
    op.create_index("uq_documents_company_type_number", "documents",
                    ["company_id", "document_type_id", "document_number"], unique=True,
                    postgresql_where=sa.text("document_number IS NOT NULL"),
                    sqlite_where=sa.text("document_number IS NOT NULL"))

    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("version_number", sa.BigInteger(), nullable=False),
        sa.Column("stored_file_id", sa.String(36), sa.ForeignKey("stored_files.id"), nullable=False),
        sa.Column("replacement_reason", sa.Text(), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("metadata_snapshot", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("document_id", "version_number", name="uq_document_versions_number"),
        sa.CheckConstraint("status IN ('ACTIVE','SUPERSEDED')", name="ck_document_versions_status"),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    # Una sola versión vigente por documento: impide dos V2 en concurrencia.
    op.create_index("uq_document_versions_active", "document_versions", ["document_id"],
                    unique=True, postgresql_where=sa.text("status = 'ACTIVE'"),
                    sqlite_where=sa.text("status = 'ACTIVE'"))

    op.create_table(
        "document_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="ATTACHMENT"),
        sa.Column("document_type_id", sa.String(36), sa.ForeignKey("document_types.id"), nullable=True),
        sa.Column("frozen_version_id", sa.String(36), nullable=True),
        sa.Column("is_frozen", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("document_id", "resource_type", "resource_id", "role",
                            name="uq_document_links_unique"),
    )
    op.create_index("ix_document_links_company_id", "document_links", ["company_id"])
    op.create_index("ix_document_links_resource", "document_links",
                    ["resource_type", "resource_id"])
    op.create_index("ix_document_links_document", "document_links", ["document_id"])

    op.create_table(
        "file_security_scans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("stored_file_id", sa.String(36), sa.ForeignKey("stored_files.id"), nullable=False),
        sa.Column("scanner", sa.String(64), nullable=False),
        sa.Column("result", sa.String(24), nullable=False),
        sa.Column("signature", sa.String(200), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_file_security_scans_stored_file_id", "file_security_scans",
                    ["stored_file_id"])

    op.create_table(
        "legacy_document_references",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_table", sa.String(64), nullable=False),
        sa.Column("source_column", sa.String(64), nullable=False),
        sa.Column("source_row_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=True),
        sa.Column("raw_value", sa.String(500), nullable=True),
        sa.Column("classification", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_table", "source_column", "source_row_id",
                            name="uq_legacy_document_references"),
    )
    op.create_index("ix_legacy_document_references_company_id", "legacy_document_references",
                    ["company_id"])


def downgrade() -> None:
    op.drop_table("legacy_document_references")
    op.drop_table("file_security_scans")
    op.drop_table("document_links")
    op.drop_table("document_versions")
    op.drop_table("documents")
    op.drop_index("ix_stored_files_sha256", table_name="stored_files")
    op.drop_constraint("ck_stored_files_status", "stored_files", type_="check")
    op.drop_constraint("ck_stored_files_security", "stored_files", type_="check")
    for column in ("uploaded_by", "status", "security_status", "storage_provider",
                   "extension", "detected_mime", "declared_mime"):
        op.drop_column("stored_files", column)
    op.rename_table("stored_files", "file_metadata")
    op.drop_table("document_types")
    op.drop_table("document_categories")
