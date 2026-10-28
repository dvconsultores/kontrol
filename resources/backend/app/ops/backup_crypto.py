"""Cifrado autenticado en flujo para artefactos de copia de KONTROL.

Usa AES-256-GCM en construcción STREAM (Hoang, Reyhanitabar, Rogaway y Vizár,
2015; la de age y Tink). Detecta clave errónea, manipulación, reordenamiento,
truncado y cambio de cabecera. La clave es externa y nunca se escribe. El texto
en claro se escribe a `dst` progresivamente; si se lanza una excepción, quien
llama DEBE descartar `dst`.
"""

from __future__ import annotations

import base64
import io
import os
import secrets
from collections.abc import Mapping
from typing import Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"KBKS1"
SEGMENT_SIZE = 1024 * 1024
KEY_ENV = "KONTROL_BACKUP_KEY"
KEY_BYTES = 32
NONCE_PREFIX_BYTES = 7
TAG_BYTES = 16
MAX_SEGMENTS = 2**32 - 1

_MIN_SEGMENT_SIZE = 1
_MAX_SEGMENT_SIZE = 2**31


class ByteReader(Protocol):
    """Fuente de bytes: basta con `read`."""

    def read(self, size: int = -1, /) -> bytes: ...


class ByteWriter(Protocol):
    """Destino de bytes: basta con `write`."""

    def write(self, data: bytes, /) -> int: ...


class BackupCryptoError(Exception):
    """Error de copia cifrada con código estable y mensaje en español."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _read_exact(src: ByteReader, size: int) -> bytes:
    data = src.read(size)
    if len(data) != size:
        raise BackupCryptoError(
            "BACKUP_FORMAT_INVALID", "Formato de copia inválido: flujo incompleto."
        )
    return data


def generate_key_text() -> str:
    """Genera una clave de 256 bits como texto base64url sin relleno."""
    return base64.urlsafe_b64encode(secrets.token_bytes(KEY_BYTES)).decode().rstrip("=")


def parse_key_text(texto: str) -> bytes:
    """Convierte texto de clave base64url a bytes de 32 bytes."""
    cleaned = texto.strip()
    if not cleaned:
        raise BackupCryptoError("BACKUP_KEY_INVALID", "Clave de copia inválida.")
    padding = "=" * ((4 - len(cleaned) % 4) % 4)
    try:
        key = base64.urlsafe_b64decode(cleaned + padding)
    except ValueError:
        raise BackupCryptoError("BACKUP_KEY_INVALID", "Clave de copia inválida.") from None
    if len(key) != KEY_BYTES:
        raise BackupCryptoError("BACKUP_KEY_INVALID", "Clave de copia inválida.")
    return key


def load_key(
    *, key_file: str | None = None, environ: Mapping[str, str] | None = None
) -> bytes:
    """Carga la clave desde fichero o variable de entorno. Nunca desde línea de órdenes."""
    if key_file is not None:
        stat = os.stat(key_file)
        if stat.st_mode & 0o077:
            raise BackupCryptoError(
                "BACKUP_KEY_FILE_PERMISSIVE",
                "El fichero de clave tiene permisos demasiado abiertos.",
            )
        with open(key_file, encoding="utf-8") as fh:
            return parse_key_text(fh.read())

    env = os.environ if environ is None else environ
    text = env.get(KEY_ENV, "")
    if not text:
        raise BackupCryptoError(
            "BACKUP_KEY_MISSING", "Falta la variable de entorno KONTROL_BACKUP_KEY."
        )
    return parse_key_text(text)


def _make_nonce(nonce_prefix: bytes, counter: int, last: bool) -> bytes:
    flag = 0x01 if last else 0x00
    return nonce_prefix + counter.to_bytes(4, "big") + bytes([flag])


def _stream_header(segment_size: int, nonce_prefix: bytes) -> bytes:
    return MAGIC + segment_size.to_bytes(4, "big") + nonce_prefix


def encrypt_stream(
    key: bytes,
    src: ByteReader,
    dst: ByteWriter,
    *,
    aad: bytes,
    segment_size: int = SEGMENT_SIZE,
) -> int:
    """Cifra `src` en `dst` con AES-256-GCM STREAM. Devuelve bytes en claro procesados."""
    if len(key) != KEY_BYTES:
        raise BackupCryptoError("BACKUP_KEY_INVALID", "Clave de copia inválida.")
    if not _MIN_SEGMENT_SIZE <= segment_size <= _MAX_SEGMENT_SIZE:
        raise BackupCryptoError("BACKUP_FORMAT_INVALID", "Formato de copia inválido.")

    nonce_prefix = secrets.token_bytes(NONCE_PREFIX_BYTES)
    header = _stream_header(segment_size, nonce_prefix)
    dst.write(header)

    aesgcm = AESGCM(key)
    counter = 0
    processed = 0
    current = src.read(segment_size)
    if not current:
        nonce = _make_nonce(nonce_prefix, counter, True)
        encrypted = aesgcm.encrypt(nonce, b"", header + aad)
        dst.write(encrypted)
        return 0

    while current:
        next_chunk = src.read(segment_size)
        last = not next_chunk
        nonce = _make_nonce(nonce_prefix, counter, last)
        encrypted = aesgcm.encrypt(nonce, current, header + aad)
        dst.write(encrypted)
        processed += len(current)
        counter += 1
        current = next_chunk

    return processed


def decrypt_stream(key: bytes, src: ByteReader, dst: ByteWriter, *, aad: bytes) -> int:
    """Descifra un flujo cifrado con encrypt_stream. Devuelve bytes en claro escritos."""
    if len(key) != KEY_BYTES:
        raise BackupCryptoError("BACKUP_KEY_INVALID", "Clave de copia inválida.")

    try:
        magic = _read_exact(src, len(MAGIC))
    except BackupCryptoError:
        raise BackupCryptoError(
            "BACKUP_FORMAT_INVALID", "Formato de copia inválido: cabecera incompleta."
        ) from None

    if magic != MAGIC:
        raise BackupCryptoError("BACKUP_FORMAT_INVALID", "Formato de copia inválido.")

    try:
        segment_size_raw = _read_exact(src, 4)
        nonce_prefix = _read_exact(src, NONCE_PREFIX_BYTES)
    except BackupCryptoError:
        raise BackupCryptoError(
            "BACKUP_FORMAT_INVALID", "Formato de copia inválido: cabecera incompleta."
        ) from None

    segment_size = int.from_bytes(segment_size_raw, "big")
    if not _MIN_SEGMENT_SIZE <= segment_size <= _MAX_SEGMENT_SIZE:
        raise BackupCryptoError("BACKUP_FORMAT_INVALID", "Formato de copia inválido.")

    header = _stream_header(segment_size, nonce_prefix)
    aesgcm = AESGCM(key)
    chunk_size = segment_size + TAG_BYTES

    counter = 0
    processed = 0

    current = src.read(chunk_size)
    if not current:
        raise BackupCryptoError("BACKUP_DECRYPT_FAILED", "No se pudo descifrar la copia.")

    while True:
        if counter > MAX_SEGMENTS:
            raise BackupCryptoError("BACKUP_FORMAT_INVALID", "Formato de copia inválido.")

        if len(current) < TAG_BYTES:
            raise BackupCryptoError("BACKUP_DECRYPT_FAILED", "No se pudo descifrar la copia.")

        next_chunk = src.read(chunk_size)
        last = not next_chunk

        if not last and len(current) != chunk_size:
            raise BackupCryptoError("BACKUP_DECRYPT_FAILED", "No se pudo descifrar la copia.")

        nonce = _make_nonce(nonce_prefix, counter, last)
        try:
            plaintext = aesgcm.decrypt(nonce, current, header + aad)
        except InvalidTag:
            raise BackupCryptoError("BACKUP_DECRYPT_FAILED", "No se pudo descifrar la copia.") from None

        dst.write(plaintext)
        processed += len(plaintext)
        counter += 1

        if last:
            break
        current = next_chunk

    return processed


def encrypt_bytes(key: bytes, data: bytes, *, aad: bytes) -> bytes:
    """Cifra bytes en memoria y devuelve el blob cifrado."""
    src = io.BytesIO(data)
    dst = io.BytesIO()
    encrypt_stream(key, src, dst, aad=aad)
    return dst.getvalue()


def decrypt_bytes(key: bytes, blob: bytes, *, aad: bytes) -> bytes:
    """Descifra un blob en memoria y devuelve los bytes en claro."""
    src = io.BytesIO(blob)
    dst = io.BytesIO()
    decrypt_stream(key, src, dst, aad=aad)
    return dst.getvalue()
