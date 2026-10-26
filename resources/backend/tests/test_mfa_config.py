"""MFA · validación de configuración KONTROL_MFA_KEYS (Spec 002/003 · OQ-GAB-2)."""

from __future__ import annotations

import base64
import os

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from mfa_apoyo import clave_de_prueba
from pydantic import ValidationError

from app.core.config import Settings, get_settings


@pytest.fixture
def entorno_config(monkeypatch, tmp_path):
    """Aísla el directorio de trabajo y limpia la caché de Settings."""
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    try:
        yield
    finally:
        get_settings.cache_clear()


def _ancla_valida() -> str:
    clave = ed25519.Ed25519PrivateKey.generate()
    publica = clave.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return publica.decode()


def _fija_secreto(monkeypatch) -> None:
    monkeypatch.setenv("KONTROL_SECRET_KEY", "sintetico-" + os.urandom(24).hex())


def test_mfa_cfg01_local_sin_variable(monkeypatch, entorno_config):
    """MFA-CFG01: en local sin KONTROL_MFA_KEYS, mfa_keys es None."""
    monkeypatch.delenv("KONTROL_MFA_KEYS", raising=False)
    _fija_secreto(monkeypatch)
    get_settings.cache_clear()

    assert Settings().mfa_keys is None


def test_mfa_cfg02_local_con_anillo(monkeypatch, entorno_config):
    """MFA-CFG02: en local con anillo válido, mfa_keys conserva el valor."""
    anillo = clave_de_prueba()
    monkeypatch.setenv("KONTROL_MFA_KEYS", anillo)
    _fija_secreto(monkeypatch)
    get_settings.cache_clear()

    assert Settings().mfa_keys == anillo


def test_mfa_cfg03_malformado(monkeypatch, entorno_config):
    """MFA-CFG03: un anillo malformado produce ValidationError sin filtrar el valor."""
    _fija_secreto(monkeypatch)
    monkeypatch.setenv("KONTROL_MFA_KEYS", "kid-sin-dos-puntos")
    get_settings.cache_clear()

    with pytest.raises(ValidationError) as error:
        Settings()

    assert "KONTROL_MFA_KEYS" in str(error.value)
    assert "kid-sin-dos-puntos" not in str(error.value)

    clave_corta = base64.urlsafe_b64encode(os.urandom(16)).decode()
    monkeypatch.setenv("KONTROL_MFA_KEYS", f"k:{clave_corta}")
    get_settings.cache_clear()

    with pytest.raises(ValidationError) as error:
        Settings()

    assert "KONTROL_MFA_KEYS" in str(error.value)
    assert clave_corta not in str(error.value)


def test_mfa_cfg04_prod_sin_variable(monkeypatch, entorno_config):
    """MFA-CFG04: en prod sin KONTROL_MFA_KEYS produce ValidationError."""
    monkeypatch.setenv("KONTROL_ENVIRONMENT", "prod")
    monkeypatch.delenv("KONTROL_MFA_KEYS", raising=False)
    monkeypatch.setenv("KONTROL_LICENSE_PUBLIC_KEY_PEM", _ancla_valida())
    _fija_secreto(monkeypatch)
    get_settings.cache_clear()

    with pytest.raises(ValidationError) as error:
        Settings()

    assert "KONTROL_MFA_KEYS" in str(error.value)


def test_mfa_cfg05_prod_con_anillo(monkeypatch, entorno_config):
    """MFA-CFG05: en prod con ancla y anillo válidos, Settings se crea correctamente."""
    anillo = clave_de_prueba()
    monkeypatch.setenv("KONTROL_ENVIRONMENT", "prod")
    monkeypatch.setenv("KONTROL_MFA_KEYS", anillo)
    monkeypatch.setenv("KONTROL_LICENSE_PUBLIC_KEY_PEM", _ancla_valida())
    _fija_secreto(monkeypatch)
    get_settings.cache_clear()

    ajustes = Settings()
    assert ajustes.mfa_keys == anillo


def test_mfa_cfg06_sin_ajustes_de_desactivacion():
    """MFA-CFG06: no existen campos para desactivar o puentear MFA."""
    campos = Settings.model_fields
    assert not any("disable" in nombre and "mfa" in nombre for nombre in campos)
    assert not any("skip" in nombre and "mfa" in nombre for nombre in campos)
    assert "fixed_otp" not in campos
    assert "accept_any" not in campos
    assert "test_mfa" not in campos
