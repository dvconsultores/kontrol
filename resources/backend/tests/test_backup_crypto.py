"""Tests de primitiva de cifrado autenticado para copias (Spec 001 · AD-B3)."""

from __future__ import annotations

import base64
import io
import os

import pytest

from app.ops.backup_crypto import (
    MAGIC,
    SEGMENT_SIZE,
    BackupCryptoError,
    decrypt_bytes,
    decrypt_stream,
    encrypt_bytes,
    encrypt_stream,
    generate_key_text,
    load_key,
    parse_key_text,
)


def _encrypt(key: bytes, data: bytes, *, aad: bytes, segment_size: int = 16) -> bytes:
    src = io.BytesIO(data)
    dst = io.BytesIO()
    encrypt_stream(key, src, dst, aad=aad, segment_size=segment_size)
    return dst.getvalue()


def _decrypt(key: bytes, blob: bytes, *, aad: bytes) -> bytes:
    src = io.BytesIO(blob)
    dst = io.BytesIO()
    decrypt_stream(key, src, dst, aad=aad)
    return dst.getvalue()


class NoSeek:
    """Flujo de bytes no buscable para pruebas."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._data) - self._pos
        chunk = self._data[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk


@pytest.mark.parametrize("length", [0, 1, 15, 16, 17, 48, 50])
def test_roundtrip_small_segments(length: int) -> None:
    """BC-01 ida y vuelta con segment_size=16."""
    key = os.urandom(32)
    data = os.urandom(length)
    blob = _encrypt(key, data, aad=b"paquete/miembro", segment_size=16)
    assert _decrypt(key, blob, aad=b"paquete/miembro") == data


def test_roundtrip_default_large() -> None:
    """BC-01 ida y vuelta con tamaño por defecto para 3 MiB + 5 bytes."""
    key = os.urandom(32)
    data = os.urandom(3 * 1024 * 1024 + 5)
    src = io.BytesIO(data)
    dst = io.BytesIO()
    encrypt_stream(key, src, dst, aad=b"paquete/miembro")
    blob = dst.getvalue()
    assert len(blob) > len(data)
    assert _decrypt(key, blob, aad=b"paquete/miembro") == data


def test_wrong_key_fails() -> None:
    """BC-02 clave errónea produce BACKUP_DECRYPT_FAILED."""
    key = os.urandom(32)
    other = os.urandom(32)
    blob = _encrypt(key, b"contenido", aad=b"aad")
    with pytest.raises(BackupCryptoError) as exc:
        _decrypt(other, blob, aad=b"aad")
    assert exc.value.code == "BACKUP_DECRYPT_FAILED"


def test_bit_flip_fails() -> None:
    """BC-03 un bit cambiado en mitad del cifrado produce BACKUP_DECRYPT_FAILED."""
    key = os.urandom(32)
    blob = bytearray(_encrypt(key, b"contenido de prueba", aad=b"aad"))
    blob[len(blob) // 2] ^= 0x01
    with pytest.raises(BackupCryptoError) as exc:
        _decrypt(key, bytes(blob), aad=b"aad")
    assert exc.value.code == "BACKUP_DECRYPT_FAILED"


def test_truncated_last_segment_fails() -> None:
    """BC-04 quitar el último segmento completo produce BACKUP_DECRYPT_FAILED."""
    key = os.urandom(32)
    data = os.urandom(48)
    blob = _encrypt(key, data, aad=b"aad", segment_size=16)
    # cabecera: 5 + 4 + 7 = 16; 3 segmentos de 32 bytes = 96.
    truncated = blob[:-32]
    with pytest.raises(BackupCryptoError) as exc:
        _decrypt(key, truncated, aad=b"aad")
    assert exc.value.code == "BACKUP_DECRYPT_FAILED"


def test_truncated_one_byte_fails() -> None:
    """BC-04 quitar 1 byte del final produce BACKUP_DECRYPT_FAILED."""
    key = os.urandom(32)
    blob = _encrypt(key, b"contenido", aad=b"aad", segment_size=16)
    with pytest.raises(BackupCryptoError) as exc:
        _decrypt(key, blob[:-1], aad=b"aad")
    assert exc.value.code == "BACKUP_DECRYPT_FAILED"


def test_reordered_segments_fail() -> None:
    """BC-05 reordenar dos segmentos intermedios produce BACKUP_DECRYPT_FAILED."""
    key = os.urandom(32)
    data = os.urandom(48)
    blob = _encrypt(key, data, aad=b"aad", segment_size=16)
    header = blob[:16]
    segments = [blob[i : i + 32] for i in range(16, len(blob), 32)]
    assert len(segments) == 3
    reordered = header + segments[1] + segments[0] + segments[2]
    with pytest.raises(BackupCryptoError) as exc:
        _decrypt(key, reordered, aad=b"aad")
    assert exc.value.code == "BACKUP_DECRYPT_FAILED"


def test_different_aad_fails() -> None:
    """BC-06 AAD distinto al descifrar produce BACKUP_DECRYPT_FAILED."""
    key = os.urandom(32)
    blob = _encrypt(key, b"contenido", aad=b"aad-uno")
    with pytest.raises(BackupCryptoError) as exc:
        _decrypt(key, blob, aad=b"aad-dos")
    assert exc.value.code == "BACKUP_DECRYPT_FAILED"


def test_tampered_header_fails() -> None:
    """BC-07 cabecera manipulada (nonce_prefix o segment_size) produce error."""
    key = os.urandom(32)
    blob = bytearray(_encrypt(key, b"contenido", aad=b"aad", segment_size=16))

    blob_nonce = bytearray(blob)
    blob_nonce[10] ^= 0x01
    with pytest.raises(BackupCryptoError) as exc:
        _decrypt(key, bytes(blob_nonce), aad=b"aad")
    assert exc.value.code in {"BACKUP_DECRYPT_FAILED", "BACKUP_FORMAT_INVALID"}

    blob_size = bytearray(blob)
    blob_size[7] ^= 0x01
    with pytest.raises(BackupCryptoError) as exc:
        _decrypt(key, bytes(blob_size), aad=b"aad")
    assert exc.value.code in {"BACKUP_DECRYPT_FAILED", "BACKUP_FORMAT_INVALID"}


def test_bad_magic_fails() -> None:
    """BC-07 magia distinta produce BACKUP_FORMAT_INVALID."""
    key = os.urandom(32)
    blob = bytearray(_encrypt(key, b"contenido", aad=b"aad", segment_size=16))
    blob[0] ^= 0x01
    assert bytes(blob[:5]) != MAGIC
    with pytest.raises(BackupCryptoError) as exc:
        _decrypt(key, bytes(blob), aad=b"aad")
    assert exc.value.code == "BACKUP_FORMAT_INVALID"


def test_appended_bytes_fail() -> None:
    """BC-08 bytes añadidos al final producen BACKUP_DECRYPT_FAILED."""
    key = os.urandom(32)
    blob = _encrypt(key, b"contenido", aad=b"aad", segment_size=16)
    with pytest.raises(BackupCryptoError) as exc:
        _decrypt(key, blob + b"\x00", aad=b"aad")
    assert exc.value.code == "BACKUP_DECRYPT_FAILED"


def test_encryptions_are_randomized() -> None:
    """BC-09 dos cifrados del mismo texto con la misma clave producen salidas distintas."""
    key = os.urandom(32)
    data = b"mismo texto"
    blob1 = _encrypt(key, data, aad=b"aad")
    blob2 = _encrypt(key, data, aad=b"aad")
    assert blob1 != blob2


def test_load_key_from_environ() -> None:
    """BC-10 load_key desde environ devuelve 32 bytes."""
    text = generate_key_text()
    key = load_key(environ={"KONTROL_BACKUP_KEY": text})
    assert isinstance(key, bytes)
    assert len(key) == 32


def test_load_key_missing() -> None:
    """BC-10 load_key sin variable produce BACKUP_KEY_MISSING."""
    with pytest.raises(BackupCryptoError) as exc:
        load_key(environ={})
    assert exc.value.code == "BACKUP_KEY_MISSING"


def test_load_key_invalid() -> None:
    """BC-10 load_key con texto inválido o de 16 bytes produce BACKUP_KEY_INVALID."""
    with pytest.raises(BackupCryptoError) as exc:
        load_key(environ={"KONTROL_BACKUP_KEY": "¡no es base64!"})
    assert exc.value.code == "BACKUP_KEY_INVALID"

    key16 = os.urandom(16).hex()
    with pytest.raises(BackupCryptoError) as exc:
        load_key(environ={"KONTROL_BACKUP_KEY": key16})
    assert exc.value.code == "BACKUP_KEY_INVALID"


def test_load_key_from_file(tmp_path) -> None:
    """BC-10 load_key desde fichero 0600 funciona; 0644 produce BACKUP_KEY_FILE_PERMISSIVE."""
    text = generate_key_text()
    f = tmp_path / "key"
    f.write_text(text, encoding="utf-8")
    os.chmod(f, 0o600)
    key = load_key(key_file=str(f))
    assert len(key) == 32

    os.chmod(f, 0o644)
    with pytest.raises(BackupCryptoError) as exc:
        load_key(key_file=str(f))
    assert exc.value.code == "BACKUP_KEY_FILE_PERMISSIVE"


def test_parse_key_text_rejects_short_and_long() -> None:
    """BC-10 parse_key_text rechaza longitudes distintas de 32 bytes."""
    for length in (16, 31, 33):
        raw = os.urandom(length)
        text = base64.urlsafe_b64encode(raw).decode().rstrip("=")
        with pytest.raises(BackupCryptoError) as exc:
            parse_key_text(text)
        assert exc.value.code == "BACKUP_KEY_INVALID"


def test_error_messages_do_not_contain_key_text() -> None:
    """BC-11 ningún mensaje de BackupCryptoError contiene el texto de la clave."""
    key_text = generate_key_text()
    key = parse_key_text(key_text)
    other_key = os.urandom(32)

    scenarios = [
        lambda: _decrypt(other_key, _encrypt(key, b"x", aad=b"a"), aad=b"a"),
        lambda: _decrypt(key, bytearray(_encrypt(key, b"x", aad=b"a"))[:-1], aad=b"a"),
        lambda: _decrypt(key, _encrypt(key, b"x", aad=b"a"), aad=b"b"),
        lambda: _decrypt(key, b"KBKS0" + b"\x00" * 11, aad=b"a"),
        lambda: _decrypt(key, _encrypt(key, b"x", aad=b"a") + b"\x00", aad=b"a"),
        lambda: load_key(environ={}),
        lambda: load_key(environ={"KONTROL_BACKUP_KEY": "no-base64"}),
    ]
    for scenario in scenarios:
        with pytest.raises(BackupCryptoError) as exc:
            scenario()
        assert key_text not in str(exc.value)
        assert key.hex() not in str(exc.value)


def test_bytes_wrappers_roundtrip_and_aad() -> None:
    """BC-12 encrypt_bytes/decrypt_bytes ida y vuelta y AAD distinto fallan."""
    key = os.urandom(32)
    data = os.urandom(100)
    blob = encrypt_bytes(key, data, aad=b"aad")
    assert decrypt_bytes(key, blob, aad=b"aad") == data
    with pytest.raises(BackupCryptoError) as exc:
        decrypt_bytes(key, blob, aad=b"otro")
    assert exc.value.code == "BACKUP_DECRYPT_FAILED"


def test_default_segment_size_is_1mib() -> None:
    """BC-01 SEGMENT_SIZE es 1 MiB."""
    assert SEGMENT_SIZE == 1024 * 1024


def test_encrypt_stream_invalid_segment_size() -> None:
    """BC-13 encrypt_stream con segment_size=0 produce BACKUP_FORMAT_INVALID."""
    key = os.urandom(32)
    src = io.BytesIO(b"contenido")
    dst = io.BytesIO()
    with pytest.raises(BackupCryptoError) as exc:
        encrypt_stream(key, src, dst, aad=b"aad", segment_size=0)
    assert exc.value.code == "BACKUP_FORMAT_INVALID"


def test_decrypt_stream_non_seekable() -> None:
    """BC-14 decrypt_stream funciona con un flujo no buscable."""
    key = os.urandom(32)
    data = os.urandom(48)
    blob = _encrypt(key, data, aad=b"aad", segment_size=16)
    non_seekable = NoSeek(blob)
    assert not hasattr(non_seekable, "seek")
    dst = io.BytesIO()
    processed = decrypt_stream(key, non_seekable, dst, aad=b"aad")
    assert processed == len(data)
    assert dst.getvalue() == data
