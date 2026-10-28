"""Pruebas del formato de paquete de respaldo `.kbk`.

Verifican escritura, lectura, integridad, rechazo de claves incorrectas,
manipulaciones y seguridad frente a rutas o miembros no permitidos.
"""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest

from app.ops.backup_bundle import (
    DATABASE_MEMBER,
    FORMAT_VERSION,
    HEADER_MEMBER,
    MANIFEST_MEMBER,
    BundleError,
    BundleHeader,
    BundleReader,
    BundleWriter,
    is_safe_ref,
    member_aad,
    object_member,
)
from app.ops.backup_crypto import BackupCryptoError, encrypt_bytes, generate_key_text, parse_key_text


def _manifest(
    header: BundleHeader,
    db_sha: str,
    db_size: int,
    objetos: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "format_version": FORMAT_VERSION,
        "backup_id": header.backup_id,
        "created_at_utc": header.created_at_utc,
        "product_version": "test",
        "alembic_revision": "rev",
        "installation_id": "install",
        "tenants": [],
        "database": {"member": DATABASE_MEMBER, "sha256": db_sha, "size": db_size},
        "objects": objetos,
        "counts": {},
        "tables": {},
        "audit": {},
        "license": {},
        "required_external_secrets": [],
        "encryption": {},
        "consistency_mode": "test",
    }


def _write_bundle(
    path: Path,
    key: bytes,
    header: BundleHeader,
    db: bytes,
    objects: list[tuple[int, str, str, bytes]],
) -> None:
    manifest_objects: list[dict[str, object]] = []
    with BundleWriter(path, key, header) as writer:
        writer.add_member(DATABASE_MEMBER, io.BytesIO(db))
        for seq, kind, ref, data in objects:
            writer.add_member(object_member(seq), io.BytesIO(data))
            manifest_objects.append(
                {
                    "seq": seq,
                    "kind": kind,
                    "ref": ref,
                    "db_id": f"id-{seq}",
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        writer.add_manifest(_manifest(header, hashlib.sha256(db).hexdigest(), len(db), manifest_objects))


def _read_key() -> bytes:
    return parse_key_text(generate_key_text())


def test_bb01_escribir_y_leer(tmp_path: Path) -> None:
    """BB-01 escribir y leer: base de 5000 bytes y 3 objetos (uno de 0 bytes)."""
    key = _read_key()
    header = BundleHeader(FORMAT_VERSION, "backup-1", "2025-01-01T00:00:00Z", 1024)
    bundle_path = tmp_path / "backup.kbk"
    db = b"d" * 5000
    objects = [
        (1, "document", "tenant/doc1", b"a" * 100),
        (2, "export", "tenant/export1", b"b" * 200),
        (3, "document", "tenant/empty", b""),
    ]
    _write_bundle(bundle_path, key, header, db, objects)

    with tarfile.open(bundle_path, "r:") as tar:
        for member in tar.getmembers():
            f = tar.extractfile(member)
            assert f is not None
            encrypted_size = member.size
            if member.name == DATABASE_MEMBER:
                assert encrypted_size > len(db)
            elif member.name.startswith("objects/"):
                match = member.name.removeprefix("objects/").removesuffix(".enc")
                seq = int(match)
                plain = dict((item[0], item[3]) for item in objects)[seq]
                assert encrypted_size > len(plain)

    with BundleReader(bundle_path, key) as reader:
        workdir = tmp_path / "verify"
        workdir.mkdir()
        verified = reader.verify(workdir)
        assert verified.database_path.read_bytes() == db
        assert set(verified.object_paths.keys()) == {1, 2, 3}
        assert verified.object_paths[3].read_bytes() == b""
        assert verified.manifest == reader.manifest


def test_bb02_clave_erronea_al_abrir(tmp_path: Path) -> None:
    """BB-02 clave errónea al abrir."""
    key = _read_key()
    wrong_key = _read_key()
    header = BundleHeader(FORMAT_VERSION, "backup-2", "2025-01-01T00:00:00Z", 1024)
    bundle_path = tmp_path / "backup.kbk"
    _write_bundle(bundle_path, key, header, b"data", [])
    with pytest.raises(BackupCryptoError) as exc_info:
        BundleReader(bundle_path, wrong_key)
    assert exc_info.value.code == "BACKUP_DECRYPT_FAILED"


def test_bb03_miembro_objeto_manipulado(tmp_path: Path) -> None:
    """BB-03 miembro de objeto manipulado."""
    key = _read_key()
    header = BundleHeader(FORMAT_VERSION, "backup-3", "2025-01-01T00:00:00Z", 1024)
    bundle_path = tmp_path / "backup.kbk"
    db = b"database-data"
    obj_data = b"object-data"
    _write_bundle(
        bundle_path,
        key,
        header,
        db,
        [(1, "document", "tenant/doc", obj_data)],
    )

    tmp_tar = tmp_path / "tampered.tar"
    with tarfile.open(bundle_path, "r:") as src, tarfile.open(tmp_tar, "w:") as dst:
        for member in src.getmembers():
            f = src.extractfile(member)
            data = f.read() if f is not None else b""
            if member.name == object_member(1):
                data = bytearray(data)
                data[-1] ^= 0x01
                data = bytes(data)
            info = tarfile.TarInfo(member.name)
            info.size = len(data)
            info.mode = 0o600
            info.mtime = 0
            dst.addfile(info, io.BytesIO(data))
    tmp_tar.replace(bundle_path)

    with BundleReader(bundle_path, key) as reader:
        workdir = tmp_path / "verify"
        workdir.mkdir()
        with pytest.raises(BackupCryptoError) as exc_info:
            reader.verify(workdir)
        assert exc_info.value.code == "BACKUP_DECRYPT_FAILED"


def _build_tar_missing_database(path: Path, key: bytes, header: BundleHeader) -> None:
    header_bytes = header.to_bytes()
    manifest = _manifest(header, "0" * 64, 0, [])
    manifest_data = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest_enc = encrypt_bytes(key, manifest_data, aad=member_aad(header_bytes, MANIFEST_MEMBER))
    with tarfile.open(path, "w:") as tar:
        info = tarfile.TarInfo(HEADER_MEMBER)
        info.size = len(header_bytes)
        info.mode = 0o600
        info.mtime = 0
        tar.addfile(info, io.BytesIO(header_bytes))
        info = tarfile.TarInfo(MANIFEST_MEMBER)
        info.size = len(manifest_enc)
        info.mode = 0o600
        info.mtime = 0
        tar.addfile(info, io.BytesIO(manifest_enc))


def test_bb04_falta_database_enc(tmp_path: Path) -> None:
    """BB-04 falta database.enc."""
    key = _read_key()
    header = BundleHeader(FORMAT_VERSION, "backup-4", "2025-01-01T00:00:00Z", 1024)
    bundle_path = tmp_path / "backup.kbk"
    _build_tar_missing_database(bundle_path, key, header)
    with pytest.raises(BundleError) as exc_info:
        BundleReader(bundle_path, key)
    assert exc_info.value.code == "BUNDLE_MEMBER_MISSING"


@pytest.mark.parametrize("evil_name", ["../evil", "/abs", "objects/../x.enc"])
def test_bb05_miembro_extra_ruta_insegura(tmp_path: Path, evil_name: str) -> None:
    """BB-05 miembro extra con ruta insegura."""
    key = _read_key()
    header = BundleHeader(FORMAT_VERSION, "backup-5", "2025-01-01T00:00:00Z", 1024)
    bundle_path = tmp_path / "backup.kbk"
    _write_bundle(bundle_path, key, header, b"db", [])
    tmp_tar = tmp_path / "tampered.tar"
    with tarfile.open(bundle_path, "r:") as src, tarfile.open(tmp_tar, "w:") as dst:
        for member in src.getmembers():
            f = src.extractfile(member)
            data = f.read() if f is not None else b""
            info = tarfile.TarInfo(member.name)
            info.size = len(data)
            info.mode = 0o600
            info.mtime = 0
            dst.addfile(info, io.BytesIO(data))
        evil = tarfile.TarInfo(evil_name)
        evil.size = 1
        evil.mode = 0o600
        evil.mtime = 0
        dst.addfile(evil, io.BytesIO(b"x"))
    tmp_tar.replace(bundle_path)
    with pytest.raises(BundleError) as exc_info:
        BundleReader(bundle_path, key)
    assert exc_info.value.code == "BUNDLE_MEMBER_INVALID"


def test_bb06_miembro_symlink(tmp_path: Path) -> None:
    """BB-06 miembro symlink."""
    key = _read_key()
    header = BundleHeader(FORMAT_VERSION, "backup-6", "2025-01-01T00:00:00Z", 1024)
    bundle_path = tmp_path / "backup.kbk"
    _write_bundle(bundle_path, key, header, b"db", [])
    tmp_tar = tmp_path / "tampered.tar"
    with tarfile.open(bundle_path, "r:") as src, tarfile.open(tmp_tar, "w:") as dst:
        for member in src.getmembers():
            f = src.extractfile(member)
            data = f.read() if f is not None else b""
            info = tarfile.TarInfo(member.name)
            info.size = len(data)
            info.mode = 0o600
            info.mtime = 0
            dst.addfile(info, io.BytesIO(data))
        symlink = tarfile.TarInfo("link")
        symlink.type = tarfile.SYMTYPE
        symlink.linkname = "target"
        dst.addfile(symlink)
    tmp_tar.replace(bundle_path)
    with pytest.raises(BundleError) as exc_info:
        BundleReader(bundle_path, key)
    assert exc_info.value.code == "BUNDLE_MEMBER_INVALID"


def test_bb07_miembro_duplicado(tmp_path: Path) -> None:
    """BB-07 miembro duplicado."""
    key = _read_key()
    header = BundleHeader(FORMAT_VERSION, "backup-7", "2025-01-01T00:00:00Z", 1024)
    bundle_path = tmp_path / "backup.kbk"
    _write_bundle(bundle_path, key, header, b"db", [])
    tmp_tar = tmp_path / "tampered.tar"
    with tarfile.open(bundle_path, "r:") as src, tarfile.open(tmp_tar, "w:") as dst:
        for member in src.getmembers():
            f = src.extractfile(member)
            data = f.read() if f is not None else b""
            info = tarfile.TarInfo(member.name)
            info.size = len(data)
            info.mode = 0o600
            info.mtime = 0
            dst.addfile(info, io.BytesIO(data))
            if member.name == HEADER_MEMBER:
                info2 = tarfile.TarInfo(member.name)
                info2.size = len(data)
                info2.mode = 0o600
                info2.mtime = 0
                dst.addfile(info2, io.BytesIO(data))
    tmp_tar.replace(bundle_path)
    with pytest.raises(BundleError) as exc_info:
        BundleReader(bundle_path, key)
    assert exc_info.value.code == "BUNDLE_MEMBER_INVALID"


@pytest.mark.parametrize("bad_ref", ["../etc/x", "/abs", "a//b", "a\\b"])
def test_bb08_manifiesto_ref_inseguro(tmp_path: Path, bad_ref: str) -> None:
    """BB-08 manifiesto con ref inseguro."""
    key = _read_key()
    header = BundleHeader(FORMAT_VERSION, "backup-8", "2025-01-01T00:00:00Z", 1024)
    bundle_path = tmp_path / "backup.kbk"
    with pytest.raises(BundleError) as exc_info:
        with BundleWriter(bundle_path, key, header) as writer:
            writer.add_member(DATABASE_MEMBER, io.BytesIO(b"db"))
            writer.add_member(object_member(1), io.BytesIO(b"obj"))
            manifest = _manifest(
                header,
                "0" * 64,
                2,
                [{"seq": 1, "kind": "document", "ref": bad_ref, "db_id": "id", "size": 3, "sha256": "0" * 64}],
            )
            writer.add_manifest(manifest)
    assert exc_info.value.code == "BUNDLE_MANIFEST_INVALID"
    assert not bundle_path.exists()


def test_bb09_manifiesto_sha256_objeto_distinto(tmp_path: Path) -> None:
    """BB-09 manifiesto con sha256 de un objeto distinto del real."""
    key = _read_key()
    header = BundleHeader(FORMAT_VERSION, "backup-9", "2025-01-01T00:00:00Z", 1024)
    bundle_path = tmp_path / "backup.kbk"
    db = b"database"
    obj = b"object"
    manifest = _manifest(
        header,
        hashlib.sha256(db).hexdigest(),
        len(db),
        [{"seq": 1, "kind": "document", "ref": "tenant/doc", "db_id": "id", "size": len(obj), "sha256": "0" * 64}],
    )
    with BundleWriter(bundle_path, key, header) as writer:
        writer.add_member(DATABASE_MEMBER, io.BytesIO(db))
        writer.add_member(object_member(1), io.BytesIO(obj))
        writer.add_manifest(manifest)
    with BundleReader(bundle_path, key) as reader:
        workdir = tmp_path / "verify"
        workdir.mkdir()
        with pytest.raises(BundleError) as exc_info:
            reader.verify(workdir)
        assert exc_info.value.code == "BUNDLE_HASH_MISMATCH"


def test_bb10_cabecera_trasplantada(tmp_path: Path) -> None:
    """BB-10 cabecera de otro paquete trasplantada."""
    key = _read_key()
    header_a = BundleHeader(FORMAT_VERSION, "backup-a", "2025-01-01T00:00:00Z", 1024)
    header_b = BundleHeader(FORMAT_VERSION, "backup-b", "2025-01-01T00:00:00Z", 1024)
    bundle_a = tmp_path / "a.kbk"
    bundle_b = tmp_path / "b.kbk"
    _write_bundle(bundle_a, key, header_a, b"data-a", [])
    _write_bundle(bundle_b, key, header_b, b"data-b", [])

    with tarfile.open(bundle_b, "r:") as src:
        f = src.extractfile(HEADER_MEMBER)
        assert f is not None
        header_b_bytes = f.read()
    tmp_tar = tmp_path / "tampered.tar"
    with tarfile.open(bundle_a, "r:") as src, tarfile.open(tmp_tar, "w:") as dst:
        for member in src.getmembers():
            if member.name == HEADER_MEMBER:
                data = header_b_bytes
            else:
                f = src.extractfile(member)
                data = f.read() if f is not None else b""
            info = tarfile.TarInfo(member.name)
            info.size = len(data)
            info.mode = 0o600
            info.mtime = 0
            dst.addfile(info, io.BytesIO(data))
    tmp_tar.replace(bundle_a)
    with pytest.raises((BackupCryptoError, BundleError)):
        BundleReader(bundle_a, key)


def test_bb11_writer_ruta_existente_y_parcial(tmp_path: Path) -> None:
    """BB-11 BundleWriter sobre ruta existente, excepción y cierre sin manifiesto."""
    key = _read_key()
    header = BundleHeader(FORMAT_VERSION, "backup-11", "2025-01-01T00:00:00Z", 1024)
    bundle_path = tmp_path / "backup.kbk"
    bundle_path.write_bytes(b"existing")
    with pytest.raises(BundleError) as exc_info:
        BundleWriter(bundle_path, key, header)
    assert exc_info.value.code == "BUNDLE_EXISTS"

    bundle_path.unlink()
    with pytest.raises(RuntimeError):
        with BundleWriter(bundle_path, key, header) as writer:
            writer.add_member(DATABASE_MEMBER, io.BytesIO(b"data"))
            raise RuntimeError("boom")
    assert not bundle_path.exists()

    with pytest.raises(BundleError) as exc_info:
        with BundleWriter(bundle_path, key, header) as writer:
            writer.add_member(DATABASE_MEMBER, io.BytesIO(b"data"))
    assert exc_info.value.code == "BUNDLE_MANIFEST_INVALID"
    assert not bundle_path.exists()


def test_bb12_objeto_sin_entrada_y_entrada_sin_miembro(tmp_path: Path) -> None:
    """BB-12 objeto en tar sin entrada en manifiesto y entrada sin miembro."""
    key = _read_key()
    header = BundleHeader(FORMAT_VERSION, "backup-12", "2025-01-01T00:00:00Z", 1024)
    bundle_path = tmp_path / "backup.kbk"

    manifest_without_obj = _manifest(header, hashlib.sha256(b"db").hexdigest(), 2, [])
    with BundleWriter(bundle_path, key, header) as writer:
        writer.add_member(DATABASE_MEMBER, io.BytesIO(b"db"))
        writer.add_member(object_member(1), io.BytesIO(b"obj"))
        writer.add_manifest(manifest_without_obj)
    with pytest.raises(BundleError) as exc_info:
        BundleReader(bundle_path, key)
    assert exc_info.value.code == "BUNDLE_MEMBER_INVALID"

    bundle_path.unlink()
    manifest_with_missing = _manifest(
        header,
        hashlib.sha256(b"db").hexdigest(),
        2,
        [
            {
                "seq": 1,
                "kind": "document",
                "ref": "tenant/doc",
                "db_id": "id",
                "size": 3,
                "sha256": hashlib.sha256(b"obj").hexdigest(),
            }
        ],
    )
    with BundleWriter(bundle_path, key, header) as writer:
        writer.add_member(DATABASE_MEMBER, io.BytesIO(b"db"))
        writer.add_manifest(manifest_with_missing)
    with pytest.raises(BundleError) as exc_info:
        BundleReader(bundle_path, key)
    assert exc_info.value.code == "BUNDLE_MEMBER_MISSING"


def test_bb13_workdir_no_vacio(tmp_path: Path) -> None:
    """BB-13 verify con workdir no vacío."""
    key = _read_key()
    header = BundleHeader(FORMAT_VERSION, "backup-13", "2025-01-01T00:00:00Z", 1024)
    bundle_path = tmp_path / "backup.kbk"
    _write_bundle(bundle_path, key, header, b"db", [])
    workdir = tmp_path / "verify"
    workdir.mkdir()
    (workdir / "existing").write_bytes(b"x")
    with BundleReader(bundle_path, key) as reader:
        with pytest.raises(BundleError) as exc_info:
            reader.verify(workdir)
        assert exc_info.value.code == "BUNDLE_FORMAT_INVALID"


def test_bb14_sin_datos_en_claro(tmp_path: Path) -> None:
    """BB-14 el fichero .kbk no contiene en claro ninguna de las cadenas sintéticas."""
    key = _read_key()
    header = BundleHeader(FORMAT_VERSION, "backup-14", "2025-01-01T00:00:00Z", 1024)
    bundle_path = tmp_path / "backup.kbk"
    db = b"SECRET-DATABASE-CONTENT"
    obj1 = b"SECRET-OBJECT-ONE"
    obj2 = b"SECRET-OBJECT-TWO"
    _write_bundle(
        bundle_path,
        key,
        header,
        db,
        [
            (1, "document", "tenant/one", obj1),
            (2, "export", "tenant/two", obj2),
        ],
    )
    raw = bundle_path.read_bytes()
    for marca in (db, obj1, obj2):
        assert marca not in raw


@pytest.mark.parametrize(
    "ref",
    [
        "report-ventas-20261028123000-0a1b2c3d4e5f.csv",
        "report-libro_ventas-20261028123000-0a1b2c3d4e5f.pdf",
        "2026/10/28/Ab-_x9Zq",
        "tenant/doc",
    ],
)
def test_is_safe_ref_bb15_accepts_product_refs(ref: str) -> None:
    """BB-15: is_safe_ref acepta referencias reales del producto."""
    assert is_safe_ref(ref) is True


@pytest.mark.parametrize(
    "ref",
    [
        ".",
        "..",
        "../x.csv",
        "a/../b",
        "a/./b",
        "/abs.csv",
        "a//b",
        "a\\b",
        "",
        "a/b/",
    ],
)
def test_is_safe_ref_bb16_rejects_unsafe_refs(ref: str) -> None:
    """BB-16: is_safe_ref rechaza referencias inseguras."""
    assert is_safe_ref(ref) is False


@pytest.mark.parametrize(
    "miembro", ("header.json", "database.enc", "objects/000001.enc", "manifest.enc")
)
def test_bundle_bb17_truncated_bundle_raises_bundle_error(
    tmp_path: Path, miembro: str
) -> None:
    """BB-17: un paquete truncado dentro de cualquier miembro falla con un error del paquete, nunca de tarfile."""
    key = _read_key()
    header = BundleHeader(FORMAT_VERSION, "backup-17", "2025-01-01T00:00:00Z", 1024)
    completo = tmp_path / "completo.kbk"
    _write_bundle(
        completo,
        key,
        header,
        b"d" * 20000,
        [(1, "document", "tenant/doc", b"o" * 30000)],
    )
    with tarfile.open(completo, "r:") as tar:
        m = tar.getmember(miembro)
    corte = m.offset_data + m.size // 2
    data = completo.read_bytes()
    truncado = tmp_path / "truncado.kbk"
    truncado.write_bytes(data[:corte])
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    with pytest.raises((BundleError, BackupCryptoError)):
        with BundleReader(truncado, key) as r:
            r.verify(workdir)


def test_bb18_manifest_sin_tablas(tmp_path: Path) -> None:
    """BB-18: mata el mutante «omit manifest verification» al leer."""
    key = _read_key()
    header = BundleHeader(FORMAT_VERSION, "backup-18", "2025-01-01T00:00:00Z", 1024)
    header_bytes = header.to_bytes()
    manifest = _manifest(
        header,
        db_sha=hashlib.sha256(b"db").hexdigest(),
        db_size=2,
        objetos=[],
    )
    del manifest["tables"]

    bundle_path = tmp_path / "bundle.kbk"
    with tarfile.open(bundle_path, "w:") as tar:
        for name, data in (
            (HEADER_MEMBER, header_bytes),
            (
                MANIFEST_MEMBER,
                encrypt_bytes(
                    key,
                    json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode(),
                    aad=member_aad(header_bytes, MANIFEST_MEMBER),
                ),
            ),
            (
                DATABASE_MEMBER,
                encrypt_bytes(key, b"db", aad=member_aad(header_bytes, DATABASE_MEMBER)),
            ),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o600
            info.mtime = 0
            tar.addfile(info, io.BytesIO(data))

    with pytest.raises(BundleError) as exc_info:
        BundleReader(bundle_path, key)
    assert exc_info.value.code == "BUNDLE_MANIFEST_INVALID"


def test_bb19_hash_tamano_database(tmp_path: Path) -> None:
    """BB-19: mata el mutante «omit DB hash»."""
    key = _read_key()
    header = BundleHeader(FORMAT_VERSION, "backup-19", "2025-01-01T00:00:00Z", 1024)
    db = b"database-real"

    # Variante 1: sha incorrecto, tamaño correcto.
    bundle_hash_path = tmp_path / "bundle-hash.kbk"
    manifest_hash = _manifest(
        header,
        db_sha="0" * 64,
        db_size=len(db),
        objetos=[],
    )
    with BundleWriter(bundle_hash_path, key, header) as writer:
        writer.add_member(DATABASE_MEMBER, io.BytesIO(db))
        writer.add_manifest(manifest_hash)

    with BundleReader(bundle_hash_path, key) as reader:
        workdir = tmp_path / "verify-hash"
        workdir.mkdir()
        with pytest.raises(BundleError) as exc_info:
            reader.verify(workdir)
        assert exc_info.value.code == "BUNDLE_HASH_MISMATCH"

    # Variante 2: sha correcto, tamaño incorrecto.
    bundle_size_path = tmp_path / "bundle-size.kbk"
    manifest_size = _manifest(
        header,
        db_sha=hashlib.sha256(db).hexdigest(),
        db_size=len(db) + 1,
        objetos=[],
    )
    with BundleWriter(bundle_size_path, key, header) as writer:
        writer.add_member(DATABASE_MEMBER, io.BytesIO(db))
        writer.add_manifest(manifest_size)

    with BundleReader(bundle_size_path, key) as reader:
        workdir = tmp_path / "verify-size"
        workdir.mkdir()
        with pytest.raises(BundleError) as exc_info:
            reader.verify(workdir)
        assert exc_info.value.code == "BUNDLE_HASH_MISMATCH"
