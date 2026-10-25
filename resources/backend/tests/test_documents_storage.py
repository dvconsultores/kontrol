"""Conformidad del almacenamiento documental (Spec 046, T-046-109).

El mismo contrato, ejercido contra **cada** proveedor disponible. La utilidad
de la abstracción no es que exista una clase abstracta: es que dos
implementaciones distintas se comporten igual ante las mismas preguntas.

La línea base solo tiene el proveedor de sistema de archivos: el adaptador
compatible con S3 se retiró (OD-S3-01) y una configuración `KONTROL_S3_*` hace
fallar el arranque (pruebas S3N).
"""

from __future__ import annotations

import hashlib
import io

import pytest

from app.modules.documents.storage import (
    FilesystemStorageProvider,
    StorageError,
    generate_storage_key,
)

CONTENT = b"contenido de conformidad" * 40
CHECKSUM = hashlib.sha256(CONTENT).hexdigest()


def _filesystem(tmp_path) -> FilesystemStorageProvider:
    return FilesystemStorageProvider(tmp_path / "conformidad")


@pytest.fixture
def provider(tmp_path):
    return _filesystem(tmp_path)


def test_escribir_devuelve_tamano_y_huella_calculados_al_escribir(provider):
    key = generate_storage_key("co-1")
    size, checksum = provider.put(key, io.BytesIO(CONTENT))
    assert size == len(CONTENT)
    assert checksum == CHECKSUM
    provider.delete(key)


def test_leer_devuelve_los_mismos_bytes(provider):
    key = generate_storage_key("co-1")
    provider.put(key, io.BytesIO(CONTENT))
    try:
        with provider.open(key) as handle:
            assert handle.read() == CONTENT
    finally:
        provider.delete(key)


def test_existe_y_tamano_coinciden_con_lo_escrito(provider):
    key = generate_storage_key("co-1")
    assert provider.exists(key) is False
    provider.put(key, io.BytesIO(CONTENT))
    try:
        assert provider.exists(key) is True
        assert provider.size(key) == len(CONTENT)
    finally:
        provider.delete(key)
    assert provider.exists(key) is False


def test_verificar_distingue_el_objeto_correcto_del_alterado(provider):
    key = generate_storage_key("co-1")
    provider.put(key, io.BytesIO(CONTENT))
    try:
        assert provider.verify(key, CHECKSUM) is True
        assert provider.verify(key, "0" * 64) is False
    finally:
        provider.delete(key)


def test_un_objeto_ausente_no_se_confunde_con_uno_vacio(provider):
    key = generate_storage_key("co-1")
    assert provider.verify(key, CHECKSUM) is False
    with pytest.raises(StorageError):
        provider.open(key)
    with pytest.raises(StorageError):
        provider.size(key)


def test_borrar_dos_veces_no_es_un_error(provider):
    key = generate_storage_key("co-1")
    provider.put(key, io.BytesIO(CONTENT))
    provider.delete(key)
    provider.delete(key)          # idempotente
    assert provider.exists(key) is False


def test_una_clave_que_escapa_se_rechaza(provider):
    for key in ("../fuera.bin", "/absoluta.bin", ""):
        with pytest.raises(StorageError):
            provider.put(key, io.BytesIO(CONTENT))


def test_el_estado_no_expone_rutas_ni_credenciales(provider):
    health = provider.health()
    assert health["provider"] == provider.name
    assert health["writable"] is True
    texto = str(health).lower()
    for leak in ("password", "secret", "access_key", "token", "/home/", "http"):
        assert leak not in texto, leak
