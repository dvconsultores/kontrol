"""S3N · S3 no soportado: configuración con fallo cerrado y almacenamiento solo de sistema de archivos (Spec 046 · OD-S3-01)."""

import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

import app.modules.documents.storage as storage_module
from app.core.config import Settings, get_settings


@pytest.fixture
def entorno_limpio(monkeypatch):
    """Deja el entorno sin variables KONTROL_S3_* y reinicia cachés y proveedor."""
    nombres = (
        "KONTROL_S3_BUCKET",
        "KONTROL_S3_ENDPOINT",
        "KONTROL_S3_REGION",
        "KONTROL_S3_PREFIX",
        "kontrol_s3_bucket",
        "kontrol_s3_endpoint",
        "kontrol_s3_region",
        "kontrol_s3_prefix",
    )
    for nombre in nombres:
        monkeypatch.delenv(nombre, raising=False)

    get_settings.cache_clear()
    monkeypatch.setattr(storage_module, "_provider", None)
    try:
        yield
    finally:
        get_settings.cache_clear()
        monkeypatch.setattr(storage_module, "_provider", None)


@pytest.mark.parametrize(
    "nombre_variable",
    [
        "KONTROL_S3_BUCKET",
        "KONTROL_S3_ENDPOINT",
        "KONTROL_S3_REGION",
        "KONTROL_S3_PREFIX",
        "kontrol_s3_bucket",
    ],
)
def test_s3n_01_variable_s3_individual_impide_arranque(monkeypatch, entorno_limpio, nombre_variable):
    """S3N-01: una sola variable KONTROL_S3_* provoca ValidationError sin filtrar su valor."""
    monkeypatch.setenv(nombre_variable, "valor-sintetico-s3")
    get_settings.cache_clear()

    with pytest.raises(ValidationError) as error:
        Settings()

    mensaje = str(error.value)
    assert nombre_variable in mensaje
    assert "OD-S3-01" in mensaje
    assert "valor-sintetico-s3" not in mensaje


def test_s3n_02_configuracion_completa_s3_falla_cerrada(monkeypatch, entorno_limpio):
    """S3N-02: la antigua configuración completa de S3 también falla cerrada sin filtrar valores."""
    monkeypatch.setenv("KONTROL_S3_BUCKET", "bucket-sintetico")
    monkeypatch.setenv("KONTROL_S3_ENDPOINT", "https://minio.invalid")
    get_settings.cache_clear()

    with pytest.raises(ValidationError) as error:
        Settings()

    mensaje = str(error.value)
    assert "KONTROL_S3_BUCKET" in mensaje
    assert "KONTROL_S3_ENDPOINT" in mensaje
    assert "bucket-sintetico" not in mensaje
    assert "https://minio.invalid" not in mensaje


def test_s3n_03_variable_s3_en_fichero_env_tambien_falla(monkeypatch, tmp_path, entorno_limpio):
    """S3N-03: la variable en .env también impide arrancar y su valor no aparece en el error."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("KONTROL_S3_BUCKET=bucket-en-fichero\n", encoding="utf-8")
    get_settings.cache_clear()

    with pytest.raises(ValidationError) as error:
        Settings()

    mensaje = str(error.value)
    assert "KONTROL_S3_BUCKET" in mensaje
    assert "bucket-en-fichero" not in mensaje


def test_s3n_04_sin_variables_s3_almacenamiento_es_sistema_de_archivos(monkeypatch, tmp_path, entorno_limpio):
    """S3N-04: sin variables KONTROL_S3_* la configuración valida y el almacenamiento es FILESYSTEM."""
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    storage_module._provider = None

    Settings()
    assert storage_module.get_storage().name == "FILESYSTEM"


def test_s3n_05_get_storage_no_tiene_caida_silenciosa(monkeypatch, entorno_limpio):
    """S3N-05: con una variable S3 presente, get_storage() falla cerrado en lugar de usar filesystem."""
    monkeypatch.setenv("KONTROL_S3_BUCKET", "bucket-sintetico")
    get_settings.cache_clear()
    storage_module._provider = None

    with pytest.raises(ValidationError):
        storage_module.get_storage()


def test_s3n_06_adaptador_s3_jubilado_sin_boto3_ni_os_environ_en_get_storage():
    """S3N-06: la clase S3 ya no existe y el módulo no menciona boto3 ni KONTROL_S3."""
    assert not hasattr(storage_module, "S3CompatibleStorageProvider")

    fuente_modulo = Path(storage_module.__file__).read_text(encoding="utf-8")
    assert "boto3" not in fuente_modulo
    assert "KONTROL_S3" not in fuente_modulo

    fuente_get_storage = inspect.getsource(storage_module.get_storage)
    assert "os.environ" not in fuente_get_storage
