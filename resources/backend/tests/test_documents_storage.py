"""Conformidad del almacenamiento documental (Spec 046, T-046-109).

El mismo contrato, ejercido contra **cada** proveedor disponible. La utilidad
de la abstracción no es que exista una clase abstracta: es que dos
implementaciones distintas se comporten igual ante las mismas preguntas.

El proveedor de sistema de archivos se ejercita siempre. El compatible con S3
solo cuando el entorno declara un servicio real (`KONTROL_S3_ENDPOINT`); en
otro caso se **omite y se dice**, porque un doble de prueba no demostraría
conformidad con nada.
"""

from __future__ import annotations

import hashlib
import io
import os

import pytest

from app.modules.documents.storage import (
    FilesystemStorageProvider,
    S3CompatibleStorageProvider,
    StorageError,
    generate_storage_key,
)

CONTENT = b"contenido de conformidad" * 40
CHECKSUM = hashlib.sha256(CONTENT).hexdigest()


def _filesystem(tmp_path) -> FilesystemStorageProvider:
    return FilesystemStorageProvider(tmp_path / "conformidad")


def _s3() -> S3CompatibleStorageProvider | None:
    bucket = os.environ.get("KONTROL_S3_BUCKET")
    endpoint = os.environ.get("KONTROL_S3_ENDPOINT")
    if not bucket or not endpoint:
        return None
    return S3CompatibleStorageProvider(
        bucket=bucket, endpoint_url=endpoint,
        region=os.environ.get("KONTROL_S3_REGION"),
        prefix=os.environ.get("KONTROL_S3_PREFIX", "conformidad"))


@pytest.fixture(params=["filesystem", "s3"])
def provider(request, tmp_path):
    if request.param == "filesystem":
        return _filesystem(tmp_path)
    client = _s3()
    if client is None:
        pytest.skip("Sin servicio compatible con S3 real: KONTROL_S3_ENDPOINT "
                    "no está configurado. La conformidad de este adaptador "
                    "queda SIN VERIFICAR en este entorno.")
    return client


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


# ------------------------------------------------------------------ S3 puro
def test_el_adaptador_s3_no_se_acopla_a_un_fabricante():
    """El endpoint es obligatorio y configurable: eso es lo que lo hace
    compatible con MinIO, Ceph o el propio S3 (FR-046-032)."""
    with pytest.raises(StorageError):
        S3CompatibleStorageProvider(bucket="", endpoint_url="https://x")
    with pytest.raises(StorageError):
        S3CompatibleStorageProvider(bucket="b", endpoint_url="")

    provider = S3CompatibleStorageProvider(bucket="b", endpoint_url="https://minio.local")
    assert provider.endpoint_url == "https://minio.local"
    # Ninguna credencial vive en el objeto: llegan por entorno.
    assert not any("key" in a.lower() or "secret" in a.lower()
                   for a in vars(provider))


def test_la_seleccion_de_proveedor_es_configuracion_no_codigo(monkeypatch, tmp_path):
    """Cambiar de proveedor no toca ningún servicio de negocio (FR-046-030)."""
    import app.modules.documents.storage as storage_module

    monkeypatch.setattr(storage_module, "_provider", None)
    monkeypatch.setenv("KONTROL_S3_BUCKET", "kontrol-docs")
    monkeypatch.setenv("KONTROL_S3_ENDPOINT", "https://minio.local")
    assert storage_module.get_storage().name == "S3_COMPATIBLE"

    monkeypatch.setattr(storage_module, "_provider", None)
    monkeypatch.delenv("KONTROL_S3_BUCKET")
    monkeypatch.delenv("KONTROL_S3_ENDPOINT")
    assert storage_module.get_storage().name == "FILESYSTEM"
    monkeypatch.setattr(storage_module, "_provider", None)
