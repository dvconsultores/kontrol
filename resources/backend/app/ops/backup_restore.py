"""Restauración verificada de una copia de seguridad de Kontrol.

Orden de pasos:
1. Preparar herramienta `pg_restore` y directorio de trabajo temporal.
2. Verificar el paquete completo antes de tocar el destino.
3. Comprobar la identidad de la instalación.
4. Comprobar la compatibilidad de la revisión de Alembic.
5. Comprobar que la base de datos de destino está vacía.
6. Comprobar que el almacén de destino está vacío o no existe.
7. Comprobar la clave de instalación reprovisionada.
8. Restaurar la base de datos con `pg_restore`.
9. Restaurar el almacén en un directorio de staging y moverlo a su destino.
10. Verificar el destino restaurado.
11. Verificar los secretos MFA externos.
12. Finalizar revocando sesiones y registrando auditoría.
13. Devolver el resultado.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import psycopg2
from cryptography.hazmat.primitives import serialization
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session as OrmSession

import app
from alembic import config as alembic_config
from alembic import script as alembic_script
from alembic.util.exc import CommandError
from app.modules.documents.storage import FilesystemStorageProvider
from app.modules.identity_access.mfa_crypto import (
    MfaDecryptError,
    MfaUnavailable,
    decrypt_secret,
)
from app.modules.licensing.service import INSTALLATION_PRIVATE_KEY_FILENAME
from app.ops.backup_bundle import BundleReader, is_safe_ref
from app.ops.backup_pg import (
    audit_triggers,
    check_tool_compatible,
    libpq_env,
    pg_connect_kwargs,
    pg_tool,
    server_version_num,
    table_fingerprints,
)
from app.shared.audit import record_audit
from app.shared.audit_catalog import catalog


class RestoreError(Exception):
    """Error de restauración con código de negocio."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


EXPECTED_AUDIT_TRIGGERS = [
    "trg_audit_events_no_delete",
    "trg_audit_events_no_truncate",
    "trg_audit_events_no_update",
]
INSTALLATION_KEY_FILE = INSTALLATION_PRIVATE_KEY_FILENAME


@dataclass(frozen=True)
class RestoreResult:
    """Resultado de una restauración verificada."""

    backup_id: str
    installation_id: str
    alembic_revision: str
    objects_restored: int
    tables: int
    sessions_revoked: int
    duration_s: float
    status: str


def _texto(valor: object, *, contexto: str) -> str:
    """Extrae un valor textual del manifiesto."""
    if isinstance(valor, str):
        return valor
    raise RestoreError(
        "RESTORE_VERIFICATION_FAILED",
        f"Tipo inesperado en el manifiesto para {contexto}",
    )


def _entero(valor: object, *, contexto: str) -> int:
    """Extrae un valor entero del manifiesto."""
    if isinstance(valor, int) and not isinstance(valor, bool):
        return valor
    raise RestoreError(
        "RESTORE_VERIFICATION_FAILED",
        f"Tipo inesperado en el manifiesto para {contexto}",
    )


def _objetos(manifest: dict[str, object]) -> list[dict[str, object]]:
    """Extrae la lista de objetos del manifiesto."""
    objetos = manifest.get("objects")
    if not isinstance(objetos, list):
        raise RestoreError(
            "RESTORE_VERIFICATION_FAILED",
            "El manifiesto no contiene una lista de objetos",
        )
    resultado: list[dict[str, object]] = []
    for obj in objetos:
        if not isinstance(obj, dict):
            raise RestoreError(
                "RESTORE_VERIFICATION_FAILED",
                "El manifiesto contiene un objeto inválido",
            )
        resultado.append(obj)
    return resultado


def _tablas(manifest: dict[str, object]) -> dict[str, object]:
    """Extrae el diccionario de huellas de tablas del manifiesto."""
    tablas = manifest.get("tables")
    if not isinstance(tablas, dict):
        raise RestoreError(
            "RESTORE_VERIFICATION_FAILED",
            "El manifiesto no contiene las huellas de tablas",
        )
    return tablas


def _hash_fichero(path: Path) -> tuple[str, int]:
    """Calcula el hash sha256 y el tamaño de un fichero por trozos."""
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def _public_key_sha256(private_key_pem: bytes) -> str:
    """Devuelve el hash sha256 de la clave pública en formato del producto."""
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return hashlib.sha256(public_pem.encode("utf-8")).hexdigest()


def _limpiar_destino(
    target_db_url: str,
    target_storage_root: Path,
    staging: Path,
    *,
    storage_creado: bool,
) -> None:
    """Limpia el destino tras un fallo ocurrido después de validar que estaba vacío."""
    conn = psycopg2.connect(**pg_connect_kwargs(target_db_url))
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    finally:
        conn.close()

    if staging.exists():
        shutil.rmtree(staging)

    if storage_creado and target_storage_root.exists():
        shutil.rmtree(target_storage_root)


def restore_backup(
    *,
    bundle_path: Path,
    key: bytes,
    target_db_url: str,
    target_storage_root: Path,
    target_installation_volume: Path,
    expected_installation_id: str,
    pg_bin_dir: str | None = None,
    workdir_parent: Path | None = None,
    finalize: bool = True,
) -> RestoreResult:
    """Restaura una copia verificada en un destino vacío."""
    t0 = time.monotonic()
    pg_restore = pg_tool("pg_restore", pg_bin_dir)
    workdir = Path(tempfile.mkdtemp(prefix="kontrol-restore-", dir=workdir_parent))

    try:
        with BundleReader(bundle_path, key) as reader:
            vb = reader.verify(workdir)
            manifest = vb.manifest
            database_path = vb.database_path
            object_paths = vb.object_paths

        backup_id = _texto(manifest["backup_id"], contexto="backup_id")
        installation_id = _texto(manifest["installation_id"], contexto="installation_id")
        alembic_revision = _texto(manifest["alembic_revision"], contexto="alembic_revision")
        manifest_tablas = _tablas(manifest)
        manifest_objetos = _objetos(manifest)
        staging = target_storage_root.parent / (
            f"{target_storage_root.name}.restoring-{backup_id}"
        )
        storage_creado = False

        # 3. Identidad de la instalación.
        if installation_id != expected_installation_id:
            raise RestoreError("FOREIGN_BACKUP", "La copia no pertenece a esta instalación")

        # 4. Compatibilidad de Alembic.
        ini = Path(app.__file__).resolve().parents[1] / "alembic.ini"
        cfg = alembic_config.Config(str(ini))
        script_dir = alembic_script.ScriptDirectory.from_config(cfg)
        try:
            revision = script_dir.get_revision(alembic_revision)
        except CommandError:
            raise RestoreError(
                "ALEMBIC_INCOMPATIBLE",
                "La revisión de Alembic de la copia no existe en esta versión",
            ) from None
        if revision is None:
            raise RestoreError(
                "ALEMBIC_INCOMPATIBLE",
                "La revisión de Alembic de la copia no existe en esta versión",
            )
        if alembic_revision not in script_dir.get_heads():
            raise RestoreError(
                "RESTORE_REQUIRES_UPGRADE",
                "La copia no corresponde a una cabeza de Alembic",
            )

        # 5. Destino de base de datos.
        conn = psycopg2.connect(**pg_connect_kwargs(target_db_url))
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                check_tool_compatible(pg_restore, server_version_num(cur))
                cur.execute(
                    """
                    SELECT count(*)
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public'
                      AND c.relkind IN ('r','v','m','S','p','f')
                    """
                )
                resultado = cur.fetchone()
                if resultado is None or int(resultado[0]) > 0:
                    raise RestoreError(
                        "TARGET_NOT_EMPTY", "La base de datos de destino no está vacía"
                    )
        finally:
            conn.close()

        # 6. Destino de almacén.
        if target_storage_root.exists():
            if not target_storage_root.is_dir() or any(target_storage_root.iterdir()):
                raise RestoreError(
                    "TARGET_NOT_EMPTY", "El almacén de destino no está vacío"
                )
        if staging.exists():
            raise RestoreError(
                "TARGET_NOT_EMPTY", "El directorio de staging ya existe"
            )

        # 7. Clave de instalación reprovisionada.
        expected_public_sha256 = manifest.get("installation_public_key_sha256")
        if expected_public_sha256 is not None:
            expected_public_sha256 = _texto(
                expected_public_sha256, contexto="installation_public_key_sha256"
            )
            key_file = target_installation_volume / INSTALLATION_KEY_FILE
            if not key_file.exists():
                raise RestoreError(
                    "EXTERNAL_SECRET_MISMATCH",
                    "Falta la clave de instalación reprovisionada",
                )
            if _public_key_sha256(key_file.read_bytes()) != expected_public_sha256:
                raise RestoreError(
                    "EXTERNAL_SECRET_MISMATCH",
                    "La clave de instalación reprovisionada no coincide",
                )

        # 8. Restauración de base de datos.
        try:
            env = {**os.environ, **libpq_env(target_db_url)}
            pgdatabase = _texto(env["PGDATABASE"], contexto="PGDATABASE")
            resultado_subprocess = subprocess.run(
                [
                    pg_restore,
                    "--no-owner",
                    "--no-privileges",
                    "--exit-on-error",
                    "--single-transaction",
                    f"--dbname={pgdatabase}",
                    str(database_path),
                ],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if resultado_subprocess.returncode != 0:
                raise RestoreError(
                    "PG_RESTORE_FAILED", "pg_restore terminó con error"
                )

            # 9. Almacén en staging.
            staging.mkdir(parents=True)
            objects_restored = 0
            for obj in manifest_objetos:
                seq = obj.get("seq")
                if not isinstance(seq, int) or isinstance(seq, bool):
                    raise RestoreError(
                        "RESTORE_VERIFICATION_FAILED",
                        "El objeto del manifiesto no tiene una secuencia válida",
                    )
                if seq not in object_paths:
                    raise RestoreError(
                        "RESTORE_VERIFICATION_FAILED",
                        "El objeto del manifiesto no existe en el paquete",
                    )
                ref = _texto(obj["ref"], contexto="ref")
                kind = _texto(obj["kind"], contexto="kind")
                if not is_safe_ref(ref):
                    raise RestoreError(
                        "RESTORE_VERIFICATION_FAILED",
                        "Referencia de objeto no segura",
                    )
                if kind == "document":
                    destino = FilesystemStorageProvider(
                        staging / "documents"
                    )._resolve(ref)
                elif kind == "export":
                    destino = (staging / "exports" / ref).resolve()
                    exports_root = (staging / "exports").resolve()
                    if not str(destino).startswith(str(exports_root) + os.sep):
                        raise RestoreError(
                            "RESTORE_VERIFICATION_FAILED",
                            "Referencia de exportación fuera del almacén",
                        )
                else:
                    raise RestoreError(
                        "RESTORE_VERIFICATION_FAILED",
                        "Tipo de objeto desconocido",
                    )
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(object_paths[seq], destino)
                os.chmod(destino, 0o600)
                actual_sha256, actual_size = _hash_fichero(destino)
                expected_sha256 = _texto(obj["sha256"], contexto="sha256")
                expected_size = _entero(obj["size"], contexto="size")
                if actual_sha256 != expected_sha256 or actual_size != expected_size:
                    raise RestoreError(
                        "RESTORE_VERIFICATION_FAILED",
                        "El objeto restaurado no coincide con el manifiesto",
                    )
                objects_restored += 1

            if target_storage_root.exists():
                target_storage_root.rmdir()
            os.replace(staging, target_storage_root)
            storage_creado = True

            # 10. Verificación posterior.
            verify_conn = psycopg2.connect(**pg_connect_kwargs(target_db_url))
            try:
                with verify_conn.cursor() as cur:
                    cur.execute("SELECT version_num FROM alembic_version")
                    row = cur.fetchone()
                    if row is None or _texto(row[0], contexto="alembic_version") != alembic_revision:
                        raise RestoreError(
                            "RESTORE_VERIFICATION_FAILED",
                            "La revisión de Alembic restaurada no coincide",
                        )
                    if table_fingerprints(cur) != manifest_tablas:
                        raise RestoreError(
                            "RESTORE_VERIFICATION_FAILED",
                            "Las huellas de tablas no coinciden",
                        )
                    if audit_triggers(cur) != EXPECTED_AUDIT_TRIGGERS:
                        raise RestoreError(
                            "RESTORE_VERIFICATION_FAILED",
                            "Los triggers de auditoría no coinciden",
                        )
                    cur.execute(
                        """
                        SELECT installation_uuid
                        FROM installations
                        ORDER BY created_at, id
                        LIMIT 1
                        """
                    )
                    row = cur.fetchone()
                    if row is None or _texto(row[0], contexto="installation_uuid") != expected_installation_id:
                        raise RestoreError(
                            "RESTORE_VERIFICATION_FAILED",
                            "La instalación restaurada no coincide",
                        )
                    cur.execute(
                        "SELECT DISTINCT action, entity_type FROM audit_events"
                    )
                    catalog_set = set(catalog().keys())
                    for action, entity_type in cur.fetchall():
                        if (_texto(action, contexto="action"), _texto(entity_type, contexto="entity_type")) not in catalog_set:
                            raise RestoreError(
                                "RESTORE_VERIFICATION_FAILED",
                                "Acción de auditoría desconocida",
                            )
            finally:
                verify_conn.rollback()
                verify_conn.close()

            # 11. Secretos MFA.
            mfa_conn = psycopg2.connect(**pg_connect_kwargs(target_db_url))
            try:
                with mfa_conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT DISTINCT ON (key_id) key_id, tenant_id, user_id, id, secret_ciphertext
                        FROM mfa_factors
                        WHERE key_id IS NOT NULL
                        ORDER BY key_id, id
                        """
                    )
                    for key_id, tenant_id, user_id, factor_id, ciphertext in cur.fetchall():
                        try:
                            decrypt_secret(
                                _texto(key_id, contexto="key_id"),
                                bytes(ciphertext),
                                aad=f"{_texto(tenant_id, contexto='tenant_id')}|{_texto(user_id, contexto='user_id')}|{_texto(factor_id, contexto='factor_id')}",
                            )
                        except (MfaUnavailable, MfaDecryptError):
                            raise RestoreError(
                                "EXTERNAL_SECRET_MISMATCH",
                                "No se pudo desbloquear un secreto MFA",
                            ) from None
            finally:
                mfa_conn.rollback()
                mfa_conn.close()

            # 12. Finalización.
            sessions_revoked = 0
            if finalize:
                engine = create_engine(target_db_url)
                db = OrmSession(engine)
                try:
                    resultado_update = db.execute(
                        text(
                            """
                            UPDATE sessions
                            SET revoked_at = now()
                            WHERE revoked_at IS NULL
                            RETURNING id
                            """
                        )
                    )
                    sessions_revoked = len(resultado_update.all())
                    cur_audit = db.execute(
                        text("SELECT id FROM installations ORDER BY created_at, id LIMIT 1")
                    )
                    installation_pk = cur_audit.scalar_one()
                    tenant_ids = db.execute(
                        text("SELECT id FROM tenants")
                    ).scalars().all()
                    for tenant_id in tenant_ids:
                        record_audit(
                            db,
                            action="INSTALLATION_RESTORED",
                            entity_type="Installation",
                            entity_id=str(installation_pk),
                            tenant_id=tenant_id,
                            source="CLI",
                            after={
                                "backup_id": backup_id,
                                "backup_created_at": manifest["created_at_utc"],
                                "sessions_revoked": sessions_revoked,
                            },
                        )
                    db.commit()
                finally:
                    db.close()
                    engine.dispose()

            return RestoreResult(
                backup_id=backup_id,
                installation_id=installation_id,
                alembic_revision=alembic_revision,
                objects_restored=objects_restored,
                tables=len(manifest_tablas),
                sessions_revoked=sessions_revoked,
                duration_s=time.monotonic() - t0,
                status="RESTORED",
            )
        except RestoreError:
            _limpiar_destino(
                target_db_url,
                target_storage_root,
                staging,
                storage_creado=storage_creado,
            )
            raise
        except Exception:  # noqa: BLE001 - el contrato exige limpiar y relanzar aquí
            _limpiar_destino(
                target_db_url,
                target_storage_root,
                staging,
                storage_creado=storage_creado,
            )
            raise RestoreError(
                "RESTORE_VERIFICATION_FAILED",
                "Error durante la restauración",
            ) from None
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
