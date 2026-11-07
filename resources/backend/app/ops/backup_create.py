"""Creación de una copia de seguridad consistente de la base y sus objetos.

La copia se apoya en una instantánea exportada por PostgreSQL. La base se
vuelca con ``pg_dump`` y los documentos y exportaciones referenciados en esa
misma instantánea se copian dentro del paquete cifrado.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import __version__
from app.modules.documents.storage import FilesystemStorageProvider, StorageError
from app.ops.backup_bundle import (
    BUNDLE_SUFFIX,
    DATABASE_MEMBER,
    FORMAT_VERSION,
    BundleHeader,
    BundleWriter,
    is_safe_ref,
    object_member,
)
from app.ops.backup_crypto import SEGMENT_SIZE
from app.ops.backup_pg import (
    BackupError,
    check_tool_compatible,
    libpq_env,
    pg_connect_kwargs,
    pg_tool,
    server_version_num,
    table_fingerprints,
)
from app.shared.audit import record_audit


@dataclass(frozen=True)
class BackupResult:
    """Resultado de una copia de seguridad creada."""

    backup_id: str
    path: Path
    created_at_utc: str
    objects: int
    documents: int
    exports: int
    purged: int
    duration_s: float
    snapshot_at_utc: str


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _resolve_document(
    provider: FilesystemStorageProvider,
    ref: str,
) -> Path:
    try:
        return provider._resolve(ref)
    except StorageError as exc:
        raise BackupError(
            "BACKUP_INCONSISTENT",
            "Referencia de documento no válida",
        ) from exc


def _resolve_export(storage_root: Path, ref: str) -> Path:
    export_root = storage_root / "exports"
    resolved_root = export_root.resolve()
    candidate = (export_root / ref).resolve()
    if resolved_root not in candidate.parents:
        raise BackupError(
            "BACKUP_INCONSISTENT",
            "La exportación escapa de su raíz",
        )
    return candidate


def audit_backup_event(db_url: str, *, action: str, after: dict[str, object]) -> bool:
    """Registra un evento de auditoría de copia en todos los tenants de la instalación.

    Devuelve True si se registró al menos un evento de auditoría. Si no hay
    instalación o tenants, o si falla la base de datos, devuelve False.
    """
    engine = create_engine(db_url)
    try:
        with Session(engine) as session:
            installation_row = session.execute(
                text("SELECT id FROM installations ORDER BY created_at, id LIMIT 1")
            ).first()
            if installation_row is None:
                return False

            installation_id_value = str(installation_row[0])

            tenant_rows = session.execute(text("SELECT id FROM tenants ORDER BY id")).all()
            if not tenant_rows:
                return False

            for tenant_row in tenant_rows:
                record_audit(
                    session,
                    action=action,
                    entity_type="Installation",
                    entity_id=installation_id_value,
                    tenant_id=str(tenant_row[0]),
                    company_id=None,
                    source="CLI",
                    after=after,
                )
            session.commit()
            return True
    except SQLAlchemyError:
        return False
    finally:
        engine.dispose()


def create_backup(
    *,
    db_url: str,
    storage_root: Path,
    destination_dir: Path,
    key: bytes,
    pg_bin_dir: str | None = None,
    segment_size: int = SEGMENT_SIZE,
    after_snapshot: Callable[[], None] | None = None,
    audit: bool = True,
) -> BackupResult:
    """Crea un paquete ``.kbk`` consistente con una instantánea PostgreSQL."""
    t0 = monotonic()
    pg_dump = pg_tool("pg_dump", pg_bin_dir)
    created = datetime.now(UTC)
    backup_id = f"{created:%Y%m%dT%H%M%SZ}-{secrets.token_hex(4)}"
    bundle_path = destination_dir / f"kontrol-backup-{backup_id}{BUNDLE_SUFFIX}"

    conn = psycopg2.connect(**pg_connect_kwargs(db_url))
    engine = None
    try:
        conn.set_session(isolation_level="REPEATABLE READ", readonly=True)
        cur = conn.cursor()
        try:
            check_tool_compatible(pg_dump, server_version_num(cur))
            cur.execute("SELECT pg_export_snapshot(), now()")
            snapshot_row = cur.fetchone()
            if snapshot_row is None:
                raise BackupError(
                    "PG_DUMP_FAILED",
                    "No se pudo exportar la instantánea",
                )
            snapshot_id, snapshot_at = snapshot_row
            snapshot_at_utc = snapshot_at.astimezone(UTC).isoformat()

            if after_snapshot is not None:
                after_snapshot()

            fingerprints = table_fingerprints(cur)
            cur.execute("SELECT version_num FROM alembic_version")
            alembic_row = cur.fetchone()
            alembic_revision = alembic_row[0] if alembic_row else None

            cur.execute(
                "SELECT id, installation_uuid, public_key "
                "FROM installations ORDER BY created_at, id LIMIT 1"
            )
            installation_row = cur.fetchone()
            if installation_row is None:
                raise BackupError(
                    "INSTALLATION_INVALID",
                    "No existe ninguna instalación",
                )
            installation_db_id, installation_uuid, installation_public_key = (
                installation_row
            )

            cur.execute(
                "SELECT id, code FROM tenants "
                "WHERE installation_id = %s ORDER BY id",
                (installation_db_id,),
            )
            tenants = [
                {"id": str(row[0]), "code": row[1]} for row in cur.fetchall()
            ]

            cur.execute(
                "SELECT license_id, mode, period_end, last_reliable_date, verified_at "
                "FROM license_states WHERE installation_id = %s",
                (installation_uuid,),
            )
            license_states = []
            for row in cur.fetchall():
                license_states.append(
                    {
                        "license_id": row[0],
                        "mode": row[1],
                        "period_end": _utc_iso(row[2]),
                        "last_reliable_date": _utc_iso(row[3]),
                        "verified_at": _utc_iso(row[4]),
                    }
                )

            cur.execute("SELECT count(*), max(event_time) FROM audit_events")
            audit_row = cur.fetchone()
            if audit_row is None:
                raise BackupError(
                    "PG_DUMP_FAILED",
                    "No se pudo leer audit_events",
                )
            audit_rows, audit_last_event_time = audit_row
            audit_info = {
                "rows": int(audit_rows),
                "last_event_time": _utc_iso(audit_last_event_time),
            }

            cur.execute(
                "SELECT id, storage_key, size, sha256, status "
                "FROM stored_files ORDER BY id"
            )
            stored_files = [
                dict(
                    zip(
                        ("id", "storage_key", "size", "sha256", "status"),
                        row,
                        strict=True,
                    )
                )
                for row in cur.fetchall()
            ]

            cur.execute(
                "SELECT id, file_ref FROM report_exports "
                "WHERE file_ref IS NOT NULL AND status = 'DONE' ORDER BY id"
            )
            report_exports = [
                {"id": row[0], "file_ref": row[1]} for row in cur.fetchall()
            ]

            manifest_objects: list[dict[str, object]] = []
            documents = 0
            exports = 0
            purged = 0
            seq = 1
            document_root = storage_root / "documents"
            document_provider = FilesystemStorageProvider(document_root)

            header = BundleHeader(
                FORMAT_VERSION,
                backup_id,
                created.isoformat(),
                segment_size,
            )
            with BundleWriter(bundle_path, key, header) as writer:
                for stored in stored_files:
                    if stored["status"] == "PURGED":
                        purged += 1
                        continue

                    if stored["status"] not in {"AVAILABLE", "QUARANTINED"}:
                        raise BackupError(
                            "BACKUP_INCONSISTENT",
                            "Estado de stored_file no esperado",
                        )
                    storage_key = stored["storage_key"]
                    if not isinstance(storage_key, str) or not is_safe_ref(
                        storage_key
                    ):
                        raise BackupError(
                            "BACKUP_INCONSISTENT",
                            "Referencia de documento no segura",
                        )
                    object_path = _resolve_document(
                        document_provider,
                        storage_key,
                    )
                    if not object_path.exists():
                        raise BackupError(
                            "BACKUP_INCONSISTENT",
                            "Un objeto referenciado por la instantánea no está",
                        )
                    with object_path.open("rb") as fh:
                        size, sha256 = writer.add_member(
                            object_member(seq),
                            fh,
                        )
                    if size != stored["size"] or sha256 != stored["sha256"]:
                        raise BackupError(
                            "BACKUP_INCONSISTENT",
                            "El objeto no coincide con su metadato",
                        )
                    manifest_objects.append(
                        {
                            "seq": seq,
                            "kind": "document",
                            "ref": storage_key,
                            "db_id": str(stored["id"]),
                            "size": size,
                            "sha256": sha256,
                        }
                    )
                    seq += 1
                    documents += 1

                for export in report_exports:
                    ref = export["file_ref"]
                    if not isinstance(ref, str) or not is_safe_ref(ref):
                        raise BackupError(
                            "BACKUP_INCONSISTENT",
                            "Referencia de exportación no segura",
                        )
                    export_path = _resolve_export(storage_root, ref)
                    if not export_path.exists():
                        raise BackupError(
                            "BACKUP_INCONSISTENT",
                            "Un objeto referenciado por la instantánea no está",
                        )
                    with export_path.open("rb") as fh:
                        size, sha256 = writer.add_member(
                            object_member(seq),
                            fh,
                        )
                    manifest_objects.append(
                        {
                            "seq": seq,
                            "kind": "export",
                            "ref": ref,
                            "db_id": str(export["id"]),
                            "size": size,
                            "sha256": sha256,
                        }
                    )
                    seq += 1
                    exports += 1

                proc = subprocess.Popen(
                    [
                        pg_dump,
                        "--format=custom",
                        "--no-owner",
                        "--no-privileges",
                        f"--snapshot={snapshot_id}",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    env={**os.environ, **libpq_env(db_url)},
                )
                try:
                    assert proc.stdout is not None
                    database_size, database_sha256 = writer.add_member(
                        DATABASE_MEMBER,
                        proc.stdout,
                    )
                    rc = proc.wait()
                    if rc != 0:
                        raise BackupError(
                            "PG_DUMP_FAILED",
                            "pg_dump terminó con error",
                        )
                finally:
                    if proc.poll() is None:
                        proc.kill()
                        proc.wait()

                manifest = {
                    "format_version": FORMAT_VERSION,
                    "backup_id": backup_id,
                    "created_at_utc": created.isoformat(),
                    "product_version": __version__,
                    "alembic_revision": alembic_revision,
                    "installation_id": installation_uuid,
                    "installation_public_key_sha256": (
                        hashlib.sha256(
                            installation_public_key.encode("utf-8")
                        ).hexdigest()
                        if installation_public_key
                        else None
                    ),
                    "tenants": tenants,
                    "database": {
                        "member": DATABASE_MEMBER,
                        "sha256": database_sha256,
                        "size": database_size,
                    },
                    "objects": manifest_objects,
                    "counts": {
                        "documents": documents,
                        "exports": exports,
                        "purged": purged,
                        "tables": len(fingerprints),
                    },
                    "tables": fingerprints,
                    "audit": audit_info,
                    "license": license_states,
                    "required_external_secrets": [
                        "KONTROL_BACKUP_KEY",
                        "KONTROL_MFA_KEYS",
                        "INSTALLATION_PRIVATE_KEY",
                        "KONTROL_SECRET_KEY",
                        "LICENSE_TRUST_ANCHOR",
                        "DATABASE_CREDENTIALS",
                    ],
                    "encryption": {
                        "cipher": "AES-256-GCM-STREAM",
                        "segment_size": segment_size,
                        "key_source": "external",
                    },
                    "consistency_mode": "DB_SNAPSHOT_WITH_IMMUTABLE_OBJECTS",
                    "snapshot_at_utc": snapshot_at_utc,
                }
                writer.add_manifest(manifest)
        finally:
            cur.close()

        if audit:
            engine = create_engine(db_url)
            try:
                with Session(engine) as session:
                    for tenant in tenants:
                        record_audit(
                            session,
                            action="INSTALLATION_BACKUP_CREATED",
                            entity_type="Installation",
                            entity_id=str(installation_db_id),
                            tenant_id=str(tenant["id"]),
                            company_id=None,
                            source="CLI",
                            after={
                                "backup_id": backup_id,
                                "objects": len(manifest_objects),
                                "consistency_mode": (
                                    "DB_SNAPSHOT_WITH_IMMUTABLE_OBJECTS"
                                ),
                            },
                        )
                    session.commit()
            finally:
                engine.dispose()

        duration_s = monotonic() - t0
        return BackupResult(
            backup_id=backup_id,
            path=bundle_path,
            created_at_utc=created.isoformat(),
            objects=len(manifest_objects),
            documents=documents,
            exports=exports,
            purged=purged,
            duration_s=duration_s,
            snapshot_at_utc=snapshot_at_utc,
        )
    except psycopg2.Error as exc:
        raise BackupError(
            "PG_DUMP_FAILED",
            "Error de PostgreSQL durante la copia",
        ) from exc
    finally:
        conn.rollback()
        conn.close()
        if engine is not None:
            engine.dispose()
