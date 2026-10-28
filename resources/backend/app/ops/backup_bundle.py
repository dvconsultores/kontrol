"""Implementación del formato de paquete de respaldo `.kbk`.

El paquete contiene una cabecera en claro, un manifiesto cifrado y autenticado,
la base de datos cifrada y objetos cifrados. Los nombres de miembro están
limitados a valores fijos y la lectura nunca extrae datos al disco.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.ops.backup_crypto import ByteReader, ByteWriter, decrypt_bytes, decrypt_stream, encrypt_bytes, encrypt_stream

FORMAT_VERSION = 1
BUNDLE_SUFFIX = ".kbk"
HEADER_MEMBER = "header.json"
MANIFEST_MEMBER = "manifest.enc"
DATABASE_MEMBER = "database.enc"
OBJECT_MEMBER_RE = re.compile(r"^objects/(\d{6})\.enc$")
REF_RE = re.compile(r"^[A-Za-z0-9_\-.]+(/[A-Za-z0-9_\-.]+)*$")
MANIFEST_KEYS = (
    "format_version",
    "backup_id",
    "created_at_utc",
    "product_version",
    "alembic_revision",
    "installation_id",
    "tenants",
    "database",
    "objects",
    "counts",
    "tables",
    "audit",
    "license",
    "required_external_secrets",
    "encryption",
    "consistency_mode",
)


class BundleError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class BundleHeader:
    format_version: int
    backup_id: str
    created_at_utc: str
    segment_size: int

    def to_bytes(self) -> bytes:
        payload = {
            "format_version": self.format_version,
            "backup_id": self.backup_id,
            "created_at_utc": self.created_at_utc,
            "cipher": "AES-256-GCM-STREAM",
            "segment_size": self.segment_size,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> BundleHeader:
        try:
            payload = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BundleError("BUNDLE_FORMAT_INVALID", "Cabecera del paquete inválida.") from exc
        if not isinstance(payload, dict):
            raise BundleError("BUNDLE_FORMAT_INVALID", "Cabecera del paquete inválida.")
        required = {"format_version", "backup_id", "created_at_utc", "cipher", "segment_size"}
        if not required.issubset(payload):
            raise BundleError("BUNDLE_FORMAT_INVALID", "Cabecera del paquete inválida.")
        if payload["cipher"] != "AES-256-GCM-STREAM":
            raise BundleError("BUNDLE_FORMAT_INVALID", "Cabecera del paquete inválida.")
        if not isinstance(payload["format_version"], int) or payload["format_version"] != FORMAT_VERSION:
            raise BundleError("BUNDLE_FORMAT_INVALID", "Cabecera del paquete inválida.")
        if not isinstance(payload["backup_id"], str) or not isinstance(payload["created_at_utc"], str):
            raise BundleError("BUNDLE_FORMAT_INVALID", "Cabecera del paquete inválida.")
        if not isinstance(payload["segment_size"], int):
            raise BundleError("BUNDLE_FORMAT_INVALID", "Cabecera del paquete inválida.")
        return cls(
            format_version=payload["format_version"],
            backup_id=payload["backup_id"],
            created_at_utc=payload["created_at_utc"],
            segment_size=payload["segment_size"],
        )


def member_aad(header_bytes: bytes, member: str) -> bytes:
    return b"KONTROL-BACKUP\x00" + header_bytes + b"\x00" + member.encode()


def object_member(seq: int) -> str:
    if not 1 <= seq <= 999999:
        raise ValueError("seq fuera de rango")
    return f"objects/{seq:06d}.enc"


def is_safe_ref(ref: str) -> bool:
    if not REF_RE.fullmatch(ref):
        return False
    parts = ref.split("/")
    if any(part in {".", ".."} for part in parts):
        return False
    if "//" in ref or "\\" in ref or ref.startswith("/"):
        return False
    return True


def _is_hex64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value)


def _validate_common(m: object) -> dict[str, object]:
    if not isinstance(m, dict):
        raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
    return m


def validate_manifest(m: object, *, header: BundleHeader) -> dict[str, object]:
    manifest = _validate_common(m)
    missing = [key for key in MANIFEST_KEYS if key not in manifest]
    if missing:
        raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
    if manifest["format_version"] != FORMAT_VERSION:
        raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
    if manifest["backup_id"] != header.backup_id:
        raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")

    database = manifest.get("database")
    if not isinstance(database, dict):
        raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
    if database.get("member") != DATABASE_MEMBER:
        raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
    if not _is_hex64(database.get("sha256")):
        raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
    if not isinstance(database.get("size"), int) or isinstance(database.get("size"), bool) or database["size"] < 0:
        raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")

    objects = manifest.get("objects")
    if not isinstance(objects, list):
        raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
    seen_seqs: set[int] = set()
    for obj in objects:
        if not isinstance(obj, dict):
            raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
        seq = obj.get("seq")
        if not isinstance(seq, int) or isinstance(seq, bool) or not 1 <= seq <= 999999:
            raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
        if seq in seen_seqs:
            raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
        seen_seqs.add(seq)
        if obj.get("kind") not in {"document", "export"}:
            raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
        ref = obj.get("ref")
        if not isinstance(ref, str) or not is_safe_ref(ref):
            raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
        if not isinstance(obj.get("db_id"), str):
            raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
        if not isinstance(obj.get("size"), int) or isinstance(obj.get("size"), bool) or obj["size"] < 0:
            raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
        if not _is_hex64(obj.get("sha256")):
            raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
    return manifest


class _Sha256Reader:
    def __init__(self, src: ByteReader) -> None:
        self._src = src
        self._hash = hashlib.sha256()

    def read(self, size: int = -1) -> bytes:
        data = self._src.read(size)
        if data:
            self._hash.update(data)
        return data

    def hexdigest(self) -> str:
        return self._hash.hexdigest()


class _Sha256Writer:
    def __init__(self, dst: ByteWriter) -> None:
        self._dst = dst
        self._hash = hashlib.sha256()

    def write(self, data: bytes) -> int:
        written = self._dst.write(data)
        if written:
            self._hash.update(data[:written])
        return written

    def hexdigest(self) -> str:
        return self._hash.hexdigest()


class BundleWriter:
    def __init__(self, path: Path, key: bytes, header: BundleHeader) -> None:
        self.path = path
        self.key = key
        self.header = header
        self.header_bytes = header.to_bytes()
        self._members: set[str] = set()
        self._manifest_added = False
        self._failed = False
        try:
            self._tar: tarfile.TarFile | None = tarfile.open(path, "x:")
        except FileExistsError as exc:
            raise BundleError("BUNDLE_EXISTS", "El fichero de paquete ya existe.") from exc
        try:
            self._add_header()
        except BaseException:
            self._delete_partial()
            raise

    def __enter__(self) -> BundleWriter:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if exc_type is not None:
            self._failed = True
        self.close()

    def _tar_abierto(self) -> tarfile.TarFile:
        if self._tar is None:
            raise BundleError("BUNDLE_FORMAT_INVALID", "Formato de paquete inválido.")
        return self._tar

    def _add_header(self) -> None:
        data = self.header_bytes
        info = tarfile.TarInfo(HEADER_MEMBER)
        info.size = len(data)
        info.mode = 0o600
        info.mtime = 0
        self._tar_abierto().addfile(info, io.BytesIO(data))
        self._members.add(HEADER_MEMBER)

    def _valid_member_name(self, name: str) -> bool:
        if name == DATABASE_MEMBER:
            return True
        if OBJECT_MEMBER_RE.fullmatch(name):
            return True
        return False

    def add_member(self, name: str, src: ByteReader) -> tuple[int, str]:
        if not self._valid_member_name(name):
            raise BundleError("BUNDLE_MEMBER_INVALID", "Miembro del paquete inválido.")
        if name in self._members:
            raise BundleError("BUNDLE_MEMBER_INVALID", "Miembro del paquete inválido.")
        reader = _Sha256Reader(src)
        with tempfile.TemporaryFile() as tmp:
            size = encrypt_stream(
                self.key,
                reader,
                tmp,
                aad=member_aad(self.header_bytes, name),
                segment_size=self.header.segment_size,
            )
            tmp.seek(0, io.SEEK_END)
            encrypted_size = tmp.tell()
            tmp.seek(0)
            info = tarfile.TarInfo(name)
            info.size = encrypted_size
            info.mode = 0o600
            info.mtime = 0
            self._tar_abierto().addfile(info, tmp)
        self._members.add(name)
        return size, reader.hexdigest()

    def add_manifest(self, manifest: dict[str, object]) -> None:
        validated = validate_manifest(manifest, header=self.header)
        data = json.dumps(validated, sort_keys=True, separators=(",", ":")).encode("utf-8")
        encrypted = encrypt_bytes(self.key, data, aad=member_aad(self.header_bytes, MANIFEST_MEMBER))
        info = tarfile.TarInfo(MANIFEST_MEMBER)
        info.size = len(encrypted)
        info.mode = 0o600
        info.mtime = 0
        self._tar_abierto().addfile(info, io.BytesIO(encrypted))
        self._members.add(MANIFEST_MEMBER)
        self._manifest_added = True

    def _delete_partial(self) -> None:
        if self._tar is not None:
            # el tar parcial se descarta; no debe ocultar la excepción original
            with contextlib.suppress(OSError, tarfile.TarError):
                self._tar.close()
        self.path.unlink(missing_ok=True)
        self._tar = None

    def close(self) -> None:
        try:
            if self._failed:
                self._delete_partial()
                return
            if not self._manifest_added:
                self._delete_partial()
                raise BundleError("BUNDLE_MANIFEST_INVALID", "El manifiesto no fue añadido al paquete.")
            self._tar_abierto().close()
        finally:
            self._tar = None


class BundleReader:
    def __init__(self, path: Path, key: bytes) -> None:
        self.path = path
        self.key = key
        try:
            self._tar: tarfile.TarFile | None = tarfile.open(path, "r:")
        except (tarfile.TarError, OSError) as exc:
            raise BundleError("BUNDLE_FORMAT_INVALID", "Formato de paquete inválido.") from exc
        self._member_names: set[str] = set()
        self._object_members: dict[int, tarfile.TarInfo] = {}
        try:
            self._validate_members()
            self.header_bytes = self._read_member_bytes(HEADER_MEMBER)
            self.header = BundleHeader.from_bytes(self.header_bytes)
            try:
                manifest_blob = self._read_member_bytes(MANIFEST_MEMBER)
                manifest_data = decrypt_bytes(
                    self.key,
                    manifest_blob,
                    aad=member_aad(self.header_bytes, MANIFEST_MEMBER),
                )
                parsed = json.loads(manifest_data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.") from exc
            self.manifest = validate_manifest(parsed, header=self.header)
            self._cross_check_objects()
        except BaseException:
            self.close()
            raise

    def __enter__(self) -> BundleReader:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def _tar_abierto(self) -> tarfile.TarFile:
        if self._tar is None:
            raise BundleError("BUNDLE_FORMAT_INVALID", "Formato de paquete inválido.")
        return self._tar

    def _validate_members(self) -> None:
        try:
            members = self._tar_abierto().getmembers()
        except (tarfile.TarError, EOFError) as exc:
            raise BundleError("BUNDLE_FORMAT_INVALID", "Formato de paquete inválido.") from exc
        seen: set[str] = set()
        for member in members:
            if not member.isreg():
                raise BundleError("BUNDLE_MEMBER_INVALID", "Miembro del paquete inválido.")
            name = member.name
            if name == HEADER_MEMBER or name == MANIFEST_MEMBER or name == DATABASE_MEMBER:
                pass
            else:
                match = OBJECT_MEMBER_RE.fullmatch(name)
                if match:
                    seq = int(match.group(1))
                    self._object_members[seq] = member
                else:
                    raise BundleError("BUNDLE_MEMBER_INVALID", "Miembro del paquete inválido.")
            if name in seen:
                raise BundleError("BUNDLE_MEMBER_INVALID", "Miembro del paquete inválido.")
            seen.add(name)
            self._member_names.add(name)
        if HEADER_MEMBER not in self._member_names:
            raise BundleError("BUNDLE_MEMBER_MISSING", "Falta un miembro obligatorio del paquete.")
        if MANIFEST_MEMBER not in self._member_names:
            raise BundleError("BUNDLE_MEMBER_MISSING", "Falta un miembro obligatorio del paquete.")
        if DATABASE_MEMBER not in self._member_names:
            raise BundleError("BUNDLE_MEMBER_MISSING", "Falta un miembro obligatorio del paquete.")

    def _read_member_bytes(self, name: str) -> bytes:
        member = self._tar_abierto().getmember(name)
        f = self._tar_abierto().extractfile(member)
        if f is None:
            raise BundleError("BUNDLE_FORMAT_INVALID", "Formato de paquete inválido.")
        try:
            with f:
                return f.read()
        except (tarfile.TarError, EOFError) as exc:
            raise BundleError("BUNDLE_FORMAT_INVALID", "Formato de paquete inválido.") from exc

    def _cross_check_objects(self) -> None:
        manifest_objects = self.manifest.get("objects")
        if not isinstance(manifest_objects, list):
            raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
        manifest_seqs: set[int] = set()
        for obj in manifest_objects:
            if not isinstance(obj, dict):
                raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
            seq = obj.get("seq")
            if not isinstance(seq, int):
                raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
            manifest_seqs.add(seq)
        tar_seqs = set(self._object_members.keys())
        if tar_seqs - manifest_seqs:
            raise BundleError("BUNDLE_MEMBER_INVALID", "Miembro del paquete inválido.")
        if manifest_seqs - tar_seqs:
            raise BundleError("BUNDLE_MEMBER_MISSING", "Falta un miembro obligatorio del paquete.")

    def decrypt_member(self, name: str, dst: ByteWriter) -> tuple[int, str]:
        if name not in self._member_names:
            raise BundleError("BUNDLE_MEMBER_MISSING", "Falta un miembro obligatorio del paquete.")
        member = self._tar_abierto().getmember(name)
        src = self._tar_abierto().extractfile(member)
        if src is None:
            raise BundleError("BUNDLE_FORMAT_INVALID", "Formato de paquete inválido.")
        writer = _Sha256Writer(dst)
        try:
            with src:
                size = decrypt_stream(
                    self.key,
                    src,
                    writer,
                    aad=member_aad(self.header_bytes, name),
                )
        except (tarfile.TarError, EOFError) as exc:
            raise BundleError("BUNDLE_FORMAT_INVALID", "Formato de paquete inválido.") from exc
        return size, writer.hexdigest()

    def verify(self, workdir: Path) -> VerifiedBundle:
        if not workdir.exists() or not workdir.is_dir():
            raise BundleError("BUNDLE_FORMAT_INVALID", "Directorio de trabajo inválido.")
        if any(workdir.iterdir()):
            raise BundleError("BUNDLE_FORMAT_INVALID", "Directorio de trabajo inválido.")

        database_path = workdir / "database.dump"
        with database_path.open("wb") as dst:
            db_size, db_sha = self.decrypt_member(DATABASE_MEMBER, dst)
        database = self.manifest.get("database")
        if not isinstance(database, dict):
            raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
        if db_size != database.get("size") or db_sha.lower() != str(database.get("sha256")).lower():
            raise BundleError("BUNDLE_HASH_MISMATCH", "El contenido del paquete no coincide con el manifiesto.")

        objects_dir = workdir / "objects"
        objects_dir.mkdir()
        object_paths: dict[int, Path] = {}
        manifest_objects = self.manifest.get("objects")
        if not isinstance(manifest_objects, list):
            raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
        for obj in manifest_objects:
            if not isinstance(obj, dict):
                raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
            seq = obj.get("seq")
            if not isinstance(seq, int):
                raise BundleError("BUNDLE_MANIFEST_INVALID", "Manifiesto inválido.")
            member_name = object_member(seq)
            obj_path = objects_dir / f"{seq:06d}"
            with obj_path.open("wb") as dst:
                obj_size, obj_sha = self.decrypt_member(member_name, dst)
            if obj_size != obj.get("size") or obj_sha.lower() != str(obj.get("sha256")).lower():
                raise BundleError("BUNDLE_HASH_MISMATCH", "El contenido del paquete no coincide con el manifiesto.")
            object_paths[seq] = obj_path

        return VerifiedBundle(manifest=self.manifest, database_path=database_path, object_paths=object_paths)

    def close(self) -> None:
        if self._tar is not None:
            try:
                self._tar.close()
            except tarfile.TarError:
                pass
            self._tar = None


@dataclass(frozen=True)
class VerifiedBundle:
    manifest: dict[str, object]
    database_path: Path
    object_paths: dict[int, Path]
