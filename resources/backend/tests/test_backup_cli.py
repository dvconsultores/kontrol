"""Pruebas de la CLI de copia y restauración verificadas (Spec 001 · AD-B10)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ops import backup as backup_cli
from app.ops.backup_bundle import BundleError
from app.ops.backup_create import BackupResult
from app.ops.backup_crypto import BackupCryptoError, generate_key_text
from app.ops.backup_pg import BackupError
from app.ops.backup_restore import RestoreError

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND = REPO_ROOT / "resources" / "backend"


@pytest.mark.parametrize(
    "exc_class, code, expected",
    [
        (BackupCryptoError, "BACKUP_DECRYPT_FAILED", backup_cli.EXIT_WRONG_KEY),
        (BackupCryptoError, "BACKUP_FORMAT_INVALID", backup_cli.EXIT_BUNDLE_INVALID),
        (BackupCryptoError, "BACKUP_KEY_MISSING", backup_cli.EXIT_EXTERNAL_SECRET),
        (BackupCryptoError, "BACKUP_KEY_INVALID", backup_cli.EXIT_EXTERNAL_SECRET),
        (BackupCryptoError, "BACKUP_KEY_FILE_PERMISSIVE", backup_cli.EXIT_EXTERNAL_SECRET),
        (BundleError, "BUNDLE_EXISTS", backup_cli.EXIT_OPERATIONAL),
        (BundleError, "BUNDLE_FORMAT_INVALID", backup_cli.EXIT_BUNDLE_INVALID),
        (BundleError, "BUNDLE_MEMBER_INVALID", backup_cli.EXIT_BUNDLE_INVALID),
        (BundleError, "BUNDLE_MEMBER_MISSING", backup_cli.EXIT_BUNDLE_INVALID),
        (BundleError, "BUNDLE_MANIFEST_INVALID", backup_cli.EXIT_BUNDLE_INVALID),
        (BundleError, "BUNDLE_HASH_MISMATCH", backup_cli.EXIT_BUNDLE_INVALID),
        (RestoreError, "FOREIGN_BACKUP", backup_cli.EXIT_FOREIGN),
        (RestoreError, "TARGET_NOT_EMPTY", backup_cli.EXIT_TARGET_NOT_EMPTY),
        (RestoreError, "ALEMBIC_INCOMPATIBLE", backup_cli.EXIT_ALEMBIC),
        (RestoreError, "RESTORE_REQUIRES_UPGRADE", backup_cli.EXIT_ALEMBIC),
        (RestoreError, "EXTERNAL_SECRET_MISMATCH", backup_cli.EXIT_EXTERNAL_SECRET),
        (RestoreError, "PG_RESTORE_FAILED", backup_cli.EXIT_RESTORE_FAILED),
        (RestoreError, "RESTORE_VERIFICATION_FAILED", backup_cli.EXIT_RESTORE_FAILED),
        (BackupError, "BACKUP_INCONSISTENT", backup_cli.EXIT_INCONSISTENT),
        (BackupError, "PG_TOOLS_MISSING", backup_cli.EXIT_OPERATIONAL),
        (BackupError, "PG_TOOLS_INCOMPATIBLE", backup_cli.EXIT_OPERATIONAL),
        (BackupError, "PG_DUMP_FAILED", backup_cli.EXIT_OPERATIONAL),
        (BackupError, "INSTALLATION_INVALID", backup_cli.EXIT_OPERATIONAL),
        (BackupCryptoError, "UNKNOWN", backup_cli.EXIT_OPERATIONAL),
        (BundleError, "UNKNOWN", backup_cli.EXIT_BUNDLE_INVALID),
        (RestoreError, "UNKNOWN", backup_cli.EXIT_OPERATIONAL),
        (BackupError, "UNKNOWN", backup_cli.EXIT_OPERATIONAL),
    ],
)
def test_exit_code_for(
    exc_class: type[BackupCryptoError]
    | type[BundleError]
    | type[RestoreError]
    | type[BackupError],
    code: str,
    expected: int,
) -> None:
    """CLI-01: tabla de códigos de salida para excepciones de copia."""
    exc = exc_class(code, "test")
    assert backup_cli.exit_code_for(exc) == expected


@pytest.fixture
def key_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> str:
    key = generate_key_text()
    monkeypatch.setenv("KONTROL_BACKUP_KEY", key)
    return key


def test_create_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    key_env: str,
) -> None:
    """CLI-02: crear una copia con clave de entorno produce JSON OK sin filtrar la clave."""
    result = BackupResult(
        backup_id="bkp-123",
        path=tmp_path / "bundle.tar.gz.enc",
        created_at_utc="2024-01-01T00:00:00Z",
        objects=11,
        documents=2,
        exports=3,
        purged=4,
        duration_s=5.5,
        snapshot_at_utc="2024-01-01T00:00:00Z",
    )

    def fake_create_backup(**kwargs: object) -> BackupResult:
        return result

    monkeypatch.setattr(backup_cli, "create_backup", fake_create_backup)
    code = backup_cli.main(["create", "--dest", str(tmp_path)])
    captured = capsys.readouterr()
    assert code == backup_cli.EXIT_OK
    lines = captured.out.strip().splitlines()
    payload = json.loads(lines[-1])
    assert payload["status"] == "OK"
    assert payload["backup_id"] == "bkp-123"
    assert key_env not in captured.out
    assert key_env not in captured.err


@pytest.mark.parametrize(
    "command_args, exc, expected_exit",
    [
        (["create", "--dest", "d"], BundleError("BUNDLE_FORMAT_INVALID", "mal"), backup_cli.EXIT_BUNDLE_INVALID),
        (["verify", "bundle"], BackupCryptoError("BACKUP_DECRYPT_FAILED", "mal"), backup_cli.EXIT_WRONG_KEY),
        (["restore", "bundle", "--expected-installation-id", "i"], RestoreError("FOREIGN_BACKUP", "mal"), backup_cli.EXIT_FOREIGN),
        (["restore", "bundle", "--expected-installation-id", "i"], RestoreError("TARGET_NOT_EMPTY", "mal"), backup_cli.EXIT_TARGET_NOT_EMPTY),
        (["restore", "bundle", "--expected-installation-id", "i"], RestoreError("ALEMBIC_INCOMPATIBLE", "mal"), backup_cli.EXIT_ALEMBIC),
        (["restore", "bundle", "--expected-installation-id", "i"], RestoreError("EXTERNAL_SECRET_MISMATCH", "mal"), backup_cli.EXIT_EXTERNAL_SECRET),
        (["restore", "bundle", "--expected-installation-id", "i"], RestoreError("PG_RESTORE_FAILED", "mal"), backup_cli.EXIT_RESTORE_FAILED),
        (["create", "--dest", "d"], BackupError("BACKUP_INCONSISTENT", "mal"), backup_cli.EXIT_INCONSISTENT),
    ],
)
def test_failure_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    key_env: str,
    command_args: list[str],
    exc: BaseException,
    expected_exit: int,
) -> None:
    """CLI-03: los fallos de las operaciones de copia devuelven JSON FAILED y su código de salida."""
    def raise_exc(*args: object, **kwargs: object) -> None:
        raise exc

    if command_args[0] == "create":
        monkeypatch.setattr(backup_cli, "create_backup", raise_exc)
    elif command_args[0] == "restore":
        monkeypatch.setattr(backup_cli, "restore_backup", raise_exc)
    else:
        monkeypatch.setattr(backup_cli, "BundleReader", raise_exc)

    code = backup_cli.main(command_args)
    captured = capsys.readouterr()
    assert code == expected_exit
    payload = json.loads(captured.out.strip().splitlines()[-1])
    assert payload["status"] == "FAILED"
    assert payload["code"] == getattr(exc, "code", "UNKNOWN")
    assert payload["exit_code"] == expected_exit
    assert key_env not in captured.out
    assert key_env not in captured.err


def test_missing_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI-04: sin KONTROL_BACKUP_KEY se devuelve BACKUP_KEY_MISSING y salida 7."""
    monkeypatch.delenv("KONTROL_BACKUP_KEY", raising=False)
    code = backup_cli.main(["create", "--dest", str(tmp_path)])
    captured = capsys.readouterr()
    assert code == backup_cli.EXIT_EXTERNAL_SECRET
    payload = json.loads(captured.out.strip().splitlines()[-1])
    assert payload["code"] == "BACKUP_KEY_MISSING"


def test_usage_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI-05: los errores de uso devuelven SystemExit con EXIT_OPERATIONAL."""
    with pytest.raises(SystemExit) as excinfo:
        backup_cli.main(["create", "--key", "x", "--dest", "d"])
    assert excinfo.value.code == backup_cli.EXIT_OPERATIONAL

    with pytest.raises(SystemExit) as excinfo:
        backup_cli.main(["frobnicar"])
    assert excinfo.value.code == backup_cli.EXIT_OPERATIONAL


def test_verify_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    key_env: str,
) -> None:
    """CLI-06: verify con un BundleReader doble devuelve JSON OK con installation_id."""
    class FakeBundleReader:
        def __init__(self, path: Path, key: bytes) -> None:
            self.manifest = {
                "backup_id": "bkp-123",
                "installation_id": "inst-1",
                "alembic_revision": "rev1",
                "objects": [1, 2, 3],
            }

        def __enter__(self) -> FakeBundleReader:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        def verify(self, workdir: Path) -> None:
            return None

    monkeypatch.setattr(backup_cli, "BundleReader", FakeBundleReader)
    code = backup_cli.main(["verify", "bundle"])
    captured = capsys.readouterr()
    assert code == backup_cli.EXIT_OK
    payload = json.loads(captured.out.strip().splitlines()[-1])
    assert payload["status"] == "OK"
    assert payload["installation_id"] == "inst-1"
    assert payload["objects"] == 3


def test_shell_scripts_contract() -> None:
    """CLI-07: los scripts de envoltorio invocan app.ops.backup y no contienen secretos ni herramientas prohibidas."""
    for script_name in ("backup.sh", "restore.sh"):
        script = (REPO_ROOT / "scripts" / script_name).read_text()
        assert "-m app.ops.backup" in script
        assert "openssl" not in script
        assert "pass:" not in script
        assert "pg_dump" not in script
        assert "docker" not in script


def test_kontrol_contract() -> None:
    """CLI-07: kontrol.py pasa KONTROL_BACKUP_KEY por nombre de entorno y usa app.ops.backup."""
    source = (REPO_ROOT / "kontrol.py").read_text()
    assert '"-e", "KONTROL_BACKUP_KEY"' in source
    assert '"app.ops.backup"' in source
    assert "KONTROL_BACKUP_KEY=" not in source
