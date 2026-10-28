"""Pruebas de restauración verificada. Solo se ejecutan contra PostgreSQL."""

from __future__ import annotations

import base64
import os
import secrets
import shutil
from collections.abc import Callable, Iterator
from pathlib import Path

import psycopg2
import pytest
from backup_mundo import MundoCopia, borrar_base, crear_base, es_postgres, migrar, sembrar
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine, text

import app.ops.backup_restore as br
from app.core.config import get_settings
from app.ops.backup_bundle import BundleError, BundleReader
from app.ops.backup_create import create_backup
from app.ops.backup_crypto import BackupCryptoError, generate_key_text, parse_key_text
from app.ops.backup_pg import pg_connect_kwargs, pg_tool, table_fingerprints
from app.ops.backup_restore import RestoreError, restore_backup

pytestmark = pytest.mark.skipif(
    not es_postgres(), reason="restauración real: solo PostgreSQL"
)

pg_bin = os.environ.get("KONTROL_PG_BIN_DIR")


def _tablas_publicas(url: str) -> int:
    conn = psycopg2.connect(**pg_connect_kwargs(url))
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
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
            return int(resultado[0]) if resultado is not None else 0
    finally:
        conn.rollback()
        conn.close()


def _huellas(url: str) -> dict[str, dict[str, object]]:
    conn = psycopg2.connect(**pg_connect_kwargs(url))
    try:
        with conn.cursor() as cur:
            return table_fingerprints(cur)
    finally:
        conn.rollback()
        conn.close()


def _crear_copia(
    mundo_url: str, storage_root: Path, destino: Path
) -> tuple[Path, bytes]:
    key = parse_key_text(generate_key_text())
    resultado = create_backup(
        db_url=mundo_url,
        storage_root=storage_root,
        destination_dir=destino,
        key=key,
        pg_bin_dir=pg_bin,
        audit=False,
    )
    return resultado.path, key


def _manifest_tablas(bundle_path: Path, key: bytes) -> dict[str, object]:
    with BundleReader(bundle_path, key) as reader:
        tablas = reader.manifest.get("tables")
        assert isinstance(tablas, dict)
        return tablas


def _preparar(
    tmp_path: Path, prefijo: str
) -> tuple[MundoCopia, Path, bytes, str, str]:
    """Siembra y crea una copia; devuelve mundo, copia, clave y URLs."""
    orig_url = crear_base(f"{prefijo}_orig")
    dst_url = crear_base(f"{prefijo}_dst")
    try:
        migrar(orig_url)
        base_orig = tmp_path / f"{prefijo}_orig"
        base_orig.mkdir()
        mundo = sembrar(orig_url, base_orig)
        backup_dir = tmp_path / f"{prefijo}_backup"
        backup_dir.mkdir()
        bundle_path, key = _crear_copia(orig_url, mundo.storage_root, backup_dir)
        return mundo, bundle_path, key, orig_url, dst_url
    except Exception:
        borrar_base(orig_url)
        borrar_base(dst_url)
        raise


@pytest.fixture
def anillo_ajeno(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[], None]]:
    """Sustituye temporalmente el anillo MFA por uno ajeno."""

    def activar() -> None:
        anillo = (
            f"totro{secrets.token_hex(4)}:"
            + base64.urlsafe_b64encode(os.urandom(32)).decode()
        )
        monkeypatch.setenv("KONTROL_MFA_KEYS", anillo)
        get_settings.cache_clear()

    yield activar
    monkeypatch.undo()
    get_settings.cache_clear()


def test_br01_ida_y_vuelta(tmp_path: Path) -> None:
    """Restaura completa con finalización y verificación posterior."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br01")
    try:
        dst_base = tmp_path / "br01_dst"
        dst_base.mkdir()
        volumen = dst_base / "volume"
        volumen.mkdir()
        clave_destino = volumen / "installation_private_key.pem"
        shutil.copy(mundo.volume / "installation_private_key.pem", clave_destino)
        clave_destino.chmod(0o600)

        borrar_base(orig_url)
        shutil.rmtree(mundo.storage_root.parent)

        result = restore_backup(
            bundle_path=bundle_path,
            key=key,
            target_db_url=dst_url,
            target_storage_root=dst_base / "storage",
            target_installation_volume=volumen,
            expected_installation_id=mundo.installation_id,
            pg_bin_dir=pg_bin,
            finalize=True,
        )

        assert result.status == "RESTORED"
        assert result.installation_id == mundo.installation_id

        for storage_key, content in mundo.documentos.items():
            destino = dst_base / "storage" / "documents" / storage_key
            assert destino.read_bytes() == content

        fingerprint_dst = _huellas(dst_url)
        manifest_huellas = _manifest_tablas(bundle_path, key)
        fingerprint_dst = {
            k: v
            for k, v in fingerprint_dst.items()
            if k not in {"audit_events", "sessions"}
        }
        manifest_huellas = {
            k: v
            for k, v in manifest_huellas.items()
            if k not in {"audit_events", "sessions"}
        }
        assert fingerprint_dst == manifest_huellas

        engine = create_engine(dst_url)
        with engine.connect() as conn:
            vigentes = conn.execute(
                text("SELECT count(*) FROM sessions WHERE revoked_at IS NULL")
            ).scalar_one()
            assert vigentes == 0
            eventos = conn.execute(
                text(
                    "SELECT count(DISTINCT tenant_id) FROM audit_events "
                    "WHERE action = 'INSTALLATION_RESTORED'"
                )
            ).scalar_one()
            assert eventos == len(mundo.tenant_ids)
        engine.dispose()
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br02_clave_erronea(tmp_path: Path) -> None:
    """Clave incorrecta no altera el destino."""
    mundo, bundle_path, _, orig_url, dst_url = _preparar(tmp_path, "br02")
    try:
        wrong_key = parse_key_text(generate_key_text())
        with pytest.raises(BackupCryptoError) as exc_info:
            restore_backup(
                bundle_path=bundle_path,
                key=wrong_key,
                target_db_url=dst_url,
                target_storage_root=tmp_path / "br02-storage",
                target_installation_volume=mundo.volume,
                expected_installation_id=mundo.installation_id,
                pg_bin_dir=pg_bin,
                finalize=False,
            )
        assert exc_info.value.code == "BACKUP_DECRYPT_FAILED"
        assert _tablas_publicas(dst_url) == 0
        assert not (tmp_path / "br02-storage").exists()
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br03_copia_ajena(tmp_path: Path) -> None:
    """Identidad distinta provoca FOREIGN_BACKUP."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br03")
    try:
        with pytest.raises(RestoreError) as exc_info:
            restore_backup(
                bundle_path=bundle_path,
                key=key,
                target_db_url=dst_url,
                target_storage_root=tmp_path / "br03-storage",
                target_installation_volume=mundo.volume,
                expected_installation_id="OTRA-INSTALACION",
                pg_bin_dir=pg_bin,
                finalize=False,
            )
        assert exc_info.value.code == "FOREIGN_BACKUP"
        assert _tablas_publicas(dst_url) == 0
        assert not (tmp_path / "br03-storage").exists()
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br04_destino_con_tabla_marca(tmp_path: Path) -> None:
    """Base destino no vacía provoca TARGET_NOT_EMPTY."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br04")
    try:
        conn = psycopg2.connect(**pg_connect_kwargs(dst_url))
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE marca(x int); INSERT INTO marca VALUES (1);")
        conn.close()

        with pytest.raises(RestoreError) as exc_info:
            restore_backup(
                bundle_path=bundle_path,
                key=key,
                target_db_url=dst_url,
                target_storage_root=tmp_path / "br04-storage",
                target_installation_volume=mundo.volume,
                expected_installation_id=mundo.installation_id,
                pg_bin_dir=pg_bin,
                finalize=False,
            )
        assert exc_info.value.code == "TARGET_NOT_EMPTY"

        conn = psycopg2.connect(**pg_connect_kwargs(dst_url))
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM marca;")
            resultado = cur.fetchone()
            assert resultado is not None and resultado[0] == 1
        conn.close()
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br05_raiz_almacen_no_vacia(tmp_path: Path) -> None:
    """Raíz de almacén con contenido provoca TARGET_NOT_EMPTY."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br05")
    try:
        dst_storage = tmp_path / "br05-storage"
        dst_storage.mkdir()
        marker = dst_storage / "marca.txt"
        marker.write_text("no borrar")

        with pytest.raises(RestoreError) as exc_info:
            restore_backup(
                bundle_path=bundle_path,
                key=key,
                target_db_url=dst_url,
                target_storage_root=dst_storage,
                target_installation_volume=mundo.volume,
                expected_installation_id=mundo.installation_id,
                pg_bin_dir=pg_bin,
                finalize=False,
            )
        assert exc_info.value.code == "TARGET_NOT_EMPTY"
        assert marker.read_text() == "no borrar"
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br06_clave_instalacion_incorrecta(tmp_path: Path) -> None:
    """Clave de instalación ausente o de otro par provoca EXTERNAL_SECRET_MISMATCH."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br06")
    try:
        volumen_vacio = tmp_path / "br06-volumen-vacio"
        volumen_vacio.mkdir()
        with pytest.raises(RestoreError) as exc_info:
            restore_backup(
                bundle_path=bundle_path,
                key=key,
                target_db_url=dst_url,
                target_storage_root=tmp_path / "br06-storage",
                target_installation_volume=volumen_vacio,
                expected_installation_id=mundo.installation_id,
                pg_bin_dir=pg_bin,
                finalize=False,
            )
        assert exc_info.value.code == "EXTERNAL_SECRET_MISMATCH"
        assert _tablas_publicas(dst_url) == 0
        assert not (tmp_path / "br06-storage").exists()
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br07_anillo_mfa_distinto(
    tmp_path: Path, anillo_ajeno: Callable[[], None]
) -> None:
    """Anillo MFA distinto provoca EXTERNAL_SECRET_MISMATCH y deja destino limpio."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br07")
    try:
        anillo_ajeno()
        backup_id = bundle_path.name.removeprefix("kontrol-backup-").removesuffix(".kbk")
        dst_storage = tmp_path / "br07-storage"
        with pytest.raises(RestoreError) as exc_info:
            restore_backup(
                bundle_path=bundle_path,
                key=key,
                target_db_url=dst_url,
                target_storage_root=dst_storage,
                target_installation_volume=mundo.volume,
                expected_installation_id=mundo.installation_id,
                pg_bin_dir=pg_bin,
                finalize=False,
            )
        assert exc_info.value.code == "EXTERNAL_SECRET_MISMATCH"
        assert _tablas_publicas(dst_url) == 0
        assert not dst_storage.exists()
        assert not dst_storage.parent.joinpath(
            f"{dst_storage.name}.restoring-{backup_id}"
        ).exists()
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br08_paquete_truncado(tmp_path: Path) -> None:
    """Paquete truncado provoca error y no altera el destino."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br08")
    try:
        truncado = tmp_path / "br08-truncado.kbk"
        data = bundle_path.read_bytes()
        truncado.write_bytes(data[: len(data) // 2])

        with pytest.raises((BundleError, BackupCryptoError)):
            restore_backup(
                bundle_path=truncado,
                key=key,
                target_db_url=dst_url,
                target_storage_root=tmp_path / "br08-storage",
                target_installation_volume=mundo.volume,
                expected_installation_id=mundo.installation_id,
                pg_bin_dir=pg_bin,
                finalize=False,
            )
        assert _tablas_publicas(dst_url) == 0
        assert not (tmp_path / "br08-storage").exists()
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br09_revision_alembic_desconocida(tmp_path: Path) -> None:
    """Revisión desconocida provoca ALEMBIC_INCOMPATIBLE."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br09")
    try:
        conn = psycopg2.connect(**pg_connect_kwargs(orig_url))
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("UPDATE alembic_version SET version_num = 'deadbeef0000';")
        conn.close()

        backup_dir = tmp_path / "br09-backup-revision"
        backup_dir.mkdir()
        bundle_path2, key2 = _crear_copia(orig_url, mundo.storage_root, backup_dir)

        with pytest.raises(RestoreError) as exc_info:
            restore_backup(
                bundle_path=bundle_path2,
                key=key2,
                target_db_url=dst_url,
                target_storage_root=tmp_path / "br09-storage",
                target_installation_volume=mundo.volume,
                expected_installation_id=mundo.installation_id,
                pg_bin_dir=pg_bin,
                finalize=False,
            )
        assert exc_info.value.code == "ALEMBIC_INCOMPATIBLE"
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br10_fallo_verificacion_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fallo en triggers de auditoría provoca RESTORE_VERIFICATION_FAILED y limpia."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br10")
    try:
        monkeypatch.setattr(br, "audit_triggers", lambda cur: [])

        dst_storage = tmp_path / "br10-storage"
        with pytest.raises(RestoreError) as exc_info:
            restore_backup(
                bundle_path=bundle_path,
                key=key,
                target_db_url=dst_url,
                target_storage_root=dst_storage,
                target_installation_volume=mundo.volume,
                expected_installation_id=mundo.installation_id,
                pg_bin_dir=pg_bin,
                finalize=False,
            )
        assert exc_info.value.code == "RESTORE_VERIFICATION_FAILED"
        assert _tablas_publicas(dst_url) == 0
        assert not dst_storage.exists()
        assert not dst_storage.parent.joinpath(
            f"{dst_storage.name}.restoring-{bundle_path.stem}"
        ).exists()
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br11_triggers_rechazan_modificaciones(tmp_path: Path) -> None:
    """Los triggers de auditoría impiden UPDATE y DELETE en audit_events."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br11")
    try:
        dst_base = tmp_path / "br11-dst"
        dst_base.mkdir()
        volumen = dst_base / "volume"
        volumen.mkdir()
        clave_destino = volumen / "installation_private_key.pem"
        shutil.copy(mundo.volume / "installation_private_key.pem", clave_destino)
        clave_destino.chmod(0o600)

        restore_backup(
            bundle_path=bundle_path,
            key=key,
            target_db_url=dst_url,
            target_storage_root=dst_base / "storage",
            target_installation_volume=volumen,
            expected_installation_id=mundo.installation_id,
            pg_bin_dir=pg_bin,
            finalize=False,
        )

        conn = psycopg2.connect(**pg_connect_kwargs(dst_url))
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                with pytest.raises(psycopg2.Error):
                    cur.execute("UPDATE audit_events SET reason='x';")
                with pytest.raises(psycopg2.Error):
                    cur.execute("DELETE FROM audit_events;")
        finally:
            conn.close()
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br12_sin_workdir_residual(tmp_path: Path) -> None:
    """La función no deja workdir residual en éxito ni en fallo."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br12")
    try:
        workdir_parent = tmp_path / "br12-workdirs"
        workdir_parent.mkdir()

        with pytest.raises(RestoreError):
            restore_backup(
                bundle_path=bundle_path,
                key=key,
                target_db_url=dst_url,
                target_storage_root=tmp_path / "br12-storage-fallo",
                target_installation_volume=mundo.volume,
                expected_installation_id="OTRA",
                pg_bin_dir=pg_bin,
                workdir_parent=workdir_parent,
                finalize=False,
            )
        assert list(workdir_parent.iterdir()) == []

        dst_base = tmp_path / "br12-dst"
        dst_base.mkdir()
        volumen = dst_base / "volume"
        volumen.mkdir()
        clave_destino = volumen / "installation_private_key.pem"
        shutil.copy(mundo.volume / "installation_private_key.pem", clave_destino)
        clave_destino.chmod(0o600)
        restore_backup(
            bundle_path=bundle_path,
            key=key,
            target_db_url=dst_url,
            target_storage_root=dst_base / "storage",
            target_installation_volume=volumen,
            expected_installation_id=mundo.installation_id,
            pg_bin_dir=pg_bin,
            workdir_parent=workdir_parent,
            finalize=False,
        )
        assert list(workdir_parent.iterdir()) == []
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br15_sesion_revocada(tmp_path: Path) -> None:
    """Tras la restauración finalizada, la sesión sembrada queda revocada."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br15")
    try:
        dst_base = tmp_path / "br15-dst"
        dst_base.mkdir()
        volumen = dst_base / "volume"
        volumen.mkdir()
        clave_destino = volumen / "installation_private_key.pem"
        shutil.copy(mundo.volume / "installation_private_key.pem", clave_destino)
        clave_destino.chmod(0o600)

        result = restore_backup(
            bundle_path=bundle_path,
            key=key,
            target_db_url=dst_url,
            target_storage_root=dst_base / "storage",
            target_installation_volume=volumen,
            expected_installation_id=mundo.installation_id,
            pg_bin_dir=pg_bin,
            finalize=True,
        )
        assert result.status == "RESTORED"

        conn = psycopg2.connect(**pg_connect_kwargs(dst_url))
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM sessions WHERE revoked_at IS NULL;"
                )
                resultado = cur.fetchone()
                assert resultado is not None and resultado[0] == 0
        finally:
            conn.close()
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br16_storage_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BR-16: mata el mutante «omit storage hash» al restaurar."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br16")

    try:

        def copia_corrupta(
            src: object, dst: object, *args: object, **kwargs: object
        ) -> object:
            Path(str(dst)).write_bytes(b"corrupto")
            return dst

        monkeypatch.setattr(br.shutil, "copyfile", copia_corrupta)

        with pytest.raises(RestoreError) as exc_info:
            restore_backup(
                bundle_path=bundle_path,
                key=key,
                target_db_url=dst_url,
                target_storage_root=tmp_path / "br16-storage",
                target_installation_volume=mundo.volume,
                expected_installation_id=mundo.installation_id,
                pg_bin_dir=pg_bin,
                finalize=False,
            )
        assert exc_info.value.code == "RESTORE_VERIFICATION_FAILED"
        assert _tablas_publicas(dst_url) == 0
        assert not (tmp_path / "br16-storage").exists()
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br17_revision_no_resuelve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BR-17: mata el mutante «skip Alembic check», revisión que no resuelve."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br17")

    monkeypatch.setattr(
        br.alembic_script.ScriptDirectory,
        "get_revision",
        lambda self, rev: None,
    )

    try:
        with pytest.raises(RestoreError) as exc_info:
            restore_backup(
                bundle_path=bundle_path,
                key=key,
                target_db_url=dst_url,
                target_storage_root=tmp_path / "br17-storage",
                target_installation_volume=mundo.volume,
                expected_installation_id=mundo.installation_id,
                pg_bin_dir=pg_bin,
                finalize=False,
            )
        assert exc_info.value.code == "ALEMBIC_INCOMPATIBLE"
        assert _tablas_publicas(dst_url) == 0
        assert not (tmp_path / "br17-storage").exists()
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br18_revision_no_es_cabeza(
    tmp_path: Path,
) -> None:
    """BR-18: mata el mutante «skip Alembic check», no es cabeza."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br18")

    try:
        engine = create_engine(orig_url)
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE alembic_version SET version_num = "
                    "'0060_spec003_admin_split'"
                )
            )
        engine.dispose()

        nuevo_dir = tmp_path / "br18-copia"
        nuevo_dir.mkdir()
        nuevo_bundle, nueva_clave = _crear_copia(
            orig_url, mundo.storage_root, nuevo_dir
        )

        with pytest.raises(RestoreError) as exc_info:
            restore_backup(
                bundle_path=nuevo_bundle,
                key=nueva_clave,
                target_db_url=dst_url,
                target_storage_root=tmp_path / "br18-storage",
                target_installation_volume=mundo.volume,
                expected_installation_id=mundo.installation_id,
                pg_bin_dir=pg_bin,
                finalize=False,
            )
        assert exc_info.value.code == "RESTORE_REQUIRES_UPGRADE"
        assert _tablas_publicas(dst_url) == 0
        assert not (tmp_path / "br18-storage").exists()
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br19_clave_externa_distinta(
    tmp_path: Path,
) -> None:
    """BR-19: mata el mutante «skip external-key check», par distinto."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br19")

    private_key = Ed25519PrivateKey.generate()
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    volumen_nuevo = tmp_path / "br19-volumen"
    volumen_nuevo.mkdir()
    key_path = volumen_nuevo / "installation_private_key.pem"
    key_path.write_bytes(pem)
    os.chmod(key_path, 0o600)

    try:
        with pytest.raises(RestoreError) as exc_info:
            restore_backup(
                bundle_path=bundle_path,
                key=key,
                target_db_url=dst_url,
                target_storage_root=tmp_path / "br19-storage",
                target_installation_volume=volumen_nuevo,
                expected_installation_id=mundo.installation_id,
                pg_bin_dir=pg_bin,
                finalize=False,
            )
        assert exc_info.value.code == "EXTERNAL_SECRET_MISMATCH"
        assert _tablas_publicas(dst_url) == 0
        assert not (tmp_path / "br19-storage").exists()
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br20_pg_restore_falla(
    tmp_path: Path,
) -> None:
    """BR-20: mata el mutante «ignore failed restore step», rc de pg_restore."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br20")

    falso = tmp_path / "pgfalso"
    falso.mkdir()
    restore_script = falso / "pg_restore"
    restore_script.write_text(
        f'#!/bin/sh\nif [ "$1" = "--version" ]; then exec '
        f'"{pg_tool("pg_restore", pg_bin)}" --version; fi\nexit 1\n'
    )
    os.chmod(restore_script, 0o755)

    try:
        with pytest.raises(RestoreError) as exc_info:
            restore_backup(
                bundle_path=bundle_path,
                key=key,
                target_db_url=dst_url,
                target_storage_root=tmp_path / "br20-storage",
                target_installation_volume=mundo.volume,
                expected_installation_id=mundo.installation_id,
                pg_bin_dir=str(falso),
                finalize=False,
            )
        assert exc_info.value.code == "PG_RESTORE_FAILED"
        assert _tablas_publicas(dst_url) == 0
        assert not (tmp_path / "br20-storage").exists()
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br21_huellas_vacias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BR-21: mata el mutante «report success before verification», huellas."""
    mundo, bundle_path, key, orig_url, dst_url = _preparar(tmp_path, "br21")

    monkeypatch.setattr(br, "table_fingerprints", lambda cur: {})

    try:
        with pytest.raises(RestoreError) as exc_info:
            restore_backup(
                bundle_path=bundle_path,
                key=key,
                target_db_url=dst_url,
                target_storage_root=tmp_path / "br21-storage",
                target_installation_volume=mundo.volume,
                expected_installation_id=mundo.installation_id,
                pg_bin_dir=pg_bin,
                finalize=False,
            )
        assert exc_info.value.code == "RESTORE_VERIFICATION_FAILED"
        assert _tablas_publicas(dst_url) == 0
        assert not (tmp_path / "br21-storage").exists()
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)


def test_br22_escritura_concurrente(tmp_path: Path) -> None:
    """BR-22: una escritura concurrente con la copia no entra en el volcado; la restauración verifica
    las huellas de la misma instantánea. Mata M06-26."""
    mundo, _bundle, _key, orig_url, dst_url = _preparar(tmp_path, "br22")
    try:
        def escribir_en_paralelo() -> None:
            conn = psycopg2.connect(**pg_connect_kwargs(orig_url))
            try:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute("UPDATE tenants SET name = name || ' (concurrente)'")
            finally:
                conn.close()

        key = parse_key_text(generate_key_text())
        destino = tmp_path / "br22-backup"
        destino.mkdir()
        resultado = create_backup(
            db_url=orig_url,
            storage_root=mundo.storage_root,
            destination_dir=destino,
            key=key,
            pg_bin_dir=pg_bin,
            audit=False,
            after_snapshot=escribir_en_paralelo,
        )
        restaurado = restore_backup(
            bundle_path=resultado.path,
            key=key,
            target_db_url=dst_url,
            target_storage_root=tmp_path / "br22-storage",
            target_installation_volume=mundo.volume,
            expected_installation_id=mundo.installation_id,
            pg_bin_dir=pg_bin,
            finalize=False,
        )
        assert restaurado.status == "RESTORED"

        conn = psycopg2.connect(**pg_connect_kwargs(dst_url))
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM tenants WHERE name LIKE '%(concurrente)'")
                assert cur.fetchone()[0] == 0
        finally:
            conn.close()
    finally:
        borrar_base(orig_url)
        borrar_base(dst_url)
