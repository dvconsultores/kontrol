"""CLI operativa de copias de seguridad y restauración.

Uso:
    python -m app.ops.backup create --dest DIR [--key-file PATH] [--pg-bin-dir DIR] [--no-audit] [--no-ledger]
    python -m app.ops.backup verify BUNDLE [--key-file PATH] [--no-audit] [--no-ledger]
    python -m app.ops.backup hold BACKUP_ID
    python -m app.ops.backup release BACKUP_ID
    python -m app.ops.backup restore BUNDLE --expected-installation-id ID [--key-file PATH] [--pg-bin-dir DIR] [--storage-root DIR] [--installation-volume DIR]

La clave de copia se obtiene exclusivamente de la variable de entorno
``KONTROL_BACKUP_KEY`` o de un fichero ``--key-file`` con permisos 0600.
Nunca se admite la clave como argumento de línea de órdenes.

Códigos de salida estables:
    0  éxito
    1  error operacional
    2  paquete de copia inválido
    3  copia cifrada con clave incorrecta o paquete no descifrable
    4  copia de otra instalación
    5  destino de restauración no vacío
    6  migración Alembic incompatible o restauración que requiere actualización
    7  clave ausente, inválida o con permisos inseguros, o secreto externo distinto
    8  fallo de restauración o de su verificación
    9  copia inconsistente
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

from app.core.config import get_settings
from app.ops.backup_bundle import BundleError, BundleReader
from app.ops.backup_create import BackupResult, audit_backup_event, create_backup
from app.ops.backup_crypto import BackupCryptoError, load_key
from app.ops.backup_job import copia_manual, identificador_de_paquete, registrar_verificacion, retener_copia
from app.ops.backup_pg import BackupError
from app.ops.backup_restore import RestoreError, restore_backup

EXIT_OK = 0
EXIT_OPERATIONAL = 1
EXIT_BUNDLE_INVALID = 2
EXIT_WRONG_KEY = 3
EXIT_FOREIGN = 4
EXIT_TARGET_NOT_EMPTY = 5
EXIT_ALEMBIC = 6
EXIT_EXTERNAL_SECRET = 7
EXIT_RESTORE_FAILED = 8
EXIT_INCONSISTENT = 9


def exit_code_for(exc: BaseException) -> int:
    """Devuelve el código de salida estable para una excepción de copia."""
    if isinstance(exc, BackupCryptoError):
        if exc.code == "BACKUP_DECRYPT_FAILED":
            return EXIT_WRONG_KEY
        if exc.code == "BACKUP_FORMAT_INVALID":
            return EXIT_BUNDLE_INVALID
        if exc.code in {
            "BACKUP_KEY_MISSING",
            "BACKUP_KEY_INVALID",
            "BACKUP_KEY_FILE_PERMISSIVE",
        }:
            return EXIT_EXTERNAL_SECRET
        return EXIT_OPERATIONAL

    if isinstance(exc, BundleError):
        if exc.code == "BUNDLE_EXISTS":
            return EXIT_OPERATIONAL
        return EXIT_BUNDLE_INVALID

    if isinstance(exc, RestoreError):
        if exc.code == "FOREIGN_BACKUP":
            return EXIT_FOREIGN
        if exc.code == "TARGET_NOT_EMPTY":
            return EXIT_TARGET_NOT_EMPTY
        if exc.code in {"ALEMBIC_INCOMPATIBLE", "RESTORE_REQUIRES_UPGRADE"}:
            return EXIT_ALEMBIC
        if exc.code == "EXTERNAL_SECRET_MISMATCH":
            return EXIT_EXTERNAL_SECRET
        if exc.code in {"PG_RESTORE_FAILED", "RESTORE_VERIFICATION_FAILED"}:
            return EXIT_RESTORE_FAILED
        return EXIT_OPERATIONAL

    if isinstance(exc, BackupError):
        if exc.code == "BACKUP_INCONSISTENT":
            return EXIT_INCONSISTENT
        return EXIT_OPERATIONAL

    return EXIT_OPERATIONAL


class _Parser(argparse.ArgumentParser):
    """ArgumentParser que usa EXIT_OPERATIONAL para errores de uso."""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        sys.stderr.write(f"{self.prog}: error: {message}\n")
        raise SystemExit(EXIT_OPERATIONAL)


def _build_parser() -> _Parser:
    parser = _Parser(prog="python -m app.ops.backup", allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)

    create_p = sub.add_parser("create", help="Crea una copia de seguridad", allow_abbrev=False)
    create_p.add_argument("--dest", required=True, help="Directorio de destino")
    create_p.add_argument("--key-file", help="Fichero con la clave de copia")
    create_p.add_argument("--pg-bin-dir", help="Directorio de binarios de PostgreSQL")
    create_p.add_argument("--no-audit", action="store_true", help="No registrar auditoría")
    create_p.add_argument("--no-ledger", action="store_true", help="No registrar en el ledger (uso interno del planificador)")

    verify_p = sub.add_parser("verify", help="Verifica un paquete de copia", allow_abbrev=False)
    verify_p.add_argument("bundle", help="Ruta del paquete de copia")
    verify_p.add_argument("--key-file", help="Fichero con la clave de copia")
    verify_p.add_argument("--no-audit", action="store_true", help="No registra evento de auditoría")
    verify_p.add_argument("--no-ledger", action="store_true", help="No registrar en el ledger (uso interno del planificador)")

    hold_p = sub.add_parser("hold", help="Retiene una copia", allow_abbrev=False)
    hold_p.add_argument("backup_id", help="Identificador de la copia")

    release_p = sub.add_parser("release", help="Suelta la retención de una copia", allow_abbrev=False)
    release_p.add_argument("backup_id", help="Identificador de la copia")

    restore_p = sub.add_parser("restore", help="Restaura una copia de seguridad", allow_abbrev=False)
    restore_p.add_argument("bundle", help="Ruta del paquete de copia")
    restore_p.add_argument("--expected-installation-id", required=True, help="ID de instalación esperado")
    restore_p.add_argument("--key-file", help="Fichero con la clave de copia")
    restore_p.add_argument("--pg-bin-dir", help="Directorio de binarios de PostgreSQL")
    restore_p.add_argument("--storage-root", help="Directorio raíz de almacenamiento")
    restore_p.add_argument("--installation-volume", help="Volumen de instalación")

    return parser


def _pg_bin_dir(args: argparse.Namespace) -> str | None:
    if getattr(args, "pg_bin_dir", None):
        return args.pg_bin_dir
    return os.environ.get("KONTROL_PG_BIN_DIR")


def _print_line(message: str) -> None:
    print(message)


def _print_result(result: dict[str, object]) -> None:
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    settings = get_settings()
    command = args.command

    try:
        if command in {"hold", "release"}:
            encontrada = retener_copia(settings.db_url, args.backup_id, command == "hold")
            _print_result({"command": command, "status": "OK" if encontrada else "NOT_FOUND", "backup_id": args.backup_id})
            return EXIT_OK if encontrada else EXIT_OPERATIONAL

        key = load_key(key_file=args.key_file)

        if command == "create":
            _print_line(f"Creando copia en {args.dest}...")

            def _crear() -> BackupResult:
                return create_backup(
                    db_url=settings.db_url,
                    storage_root=Path(settings.storage_path),
                    destination_dir=Path(args.dest),
                    key=key,
                    pg_bin_dir=_pg_bin_dir(args),
                    audit=not args.no_audit,
                )

            if args.no_ledger:
                creado = _crear()
            else:
                with copia_manual(settings.db_url) as registro:
                    creado = _crear()
                    registro.creada(creado.backup_id, creado.snapshot_at_utc, creado.path, creado.duration_s)
            _print_line(f"Copia creada: {creado.path}")
            _print_result(
                {
                    "command": command,
                    "status": "OK",
                    "backup_id": creado.backup_id,
                    "path": str(creado.path),
                    "objects": creado.objects,
                    "documents": creado.documents,
                    "exports": creado.exports,
                    "purged": creado.purged,
                    "duration_s": creado.duration_s,
                    "snapshot_at_utc": creado.snapshot_at_utc,
                }
            )
            return EXIT_OK

        if command == "verify":
            _print_line(f"Verificando paquete {args.bundle}...")
            with tempfile.TemporaryDirectory() as tmpdir:
                workdir = Path(tmpdir)
                with BundleReader(Path(args.bundle), key) as reader:
                    manifest = reader.manifest
                    reader.verify(workdir)
                    backup_id = str(manifest["backup_id"])
                    installation_id = str(manifest["installation_id"])
                    alembic_revision = str(manifest.get("alembic_revision", ""))
                    objetos = manifest.get("objects", [])
                    objects = len(objetos) if isinstance(objetos, list) else 0
                    if not args.no_ledger:
                        registrar_verificacion(settings.db_url, backup_id, True, None)
                    audited = False
                    if not getattr(args, "no_audit", False):
                        audited = audit_backup_event(
                            settings.db_url,
                            action="INSTALLATION_BACKUP_VERIFIED",
                            after={"backup_id": backup_id, "objects": objects},
                        )
                    _print_line(f"Paquete verificado: {backup_id}")
                    _print_result(
                        {
                            "command": command,
                            "status": "OK",
                            "backup_id": backup_id,
                            "installation_id": installation_id,
                            "alembic_revision": alembic_revision,
                            "objects": objects,
                            "audited": audited,
                        }
                    )
            return EXIT_OK

        if command == "restore":
            _print_line(f"Restaurando paquete {args.bundle}...")
            restaurado = restore_backup(
                bundle_path=Path(args.bundle),
                key=key,
                target_db_url=settings.db_url,
                target_storage_root=Path(args.storage_root or settings.storage_path),
                target_installation_volume=Path(
                    args.installation_volume or settings.installation_volume_path
                ),
                expected_installation_id=args.expected_installation_id,
                pg_bin_dir=_pg_bin_dir(args),
            )
            _print_line(f"Instalación restaurada: {restaurado.installation_id}")
            _print_result(
                {
                    "command": command,
                    "status": "RESTORED",
                    "backup_id": restaurado.backup_id,
                    "installation_id": restaurado.installation_id,
                    "alembic_revision": restaurado.alembic_revision,
                    "objects_restored": restaurado.objects_restored,
                    "tables": restaurado.tables,
                    "sessions_revoked": restaurado.sessions_revoked,
                    "duration_s": restaurado.duration_s,
                }
            )
            return EXIT_OK

        return EXIT_OPERATIONAL
    except (BackupCryptoError, BundleError, RestoreError, BackupError) as exc:
        code = getattr(exc, "code", "UNKNOWN")
        exit_code = exit_code_for(exc)
        if command == "verify" and not getattr(args, "no_ledger", False):
            registrar_verificacion(settings.db_url, identificador_de_paquete(Path(args.bundle)), False, str(code))
        if command == "verify" and not getattr(args, "no_audit", False):
            audit_backup_event(
                settings.db_url,
                action="INSTALLATION_BACKUP_VERIFY_FAILED",
                after={"backup_id": Path(args.bundle).stem, "error_code": str(code)},
            )
        _print_result(
            {
                "command": command,
                "status": "FAILED",
                "code": str(code),
                "message": str(exc),
                "exit_code": exit_code,
            }
        )
        return exit_code

    return EXIT_OPERATIONAL


if __name__ == "__main__":
    sys.exit(main())
