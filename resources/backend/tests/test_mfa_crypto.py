"""MFA · cifrado del secreto con anillo de claves (Spec 002/003 · OQ-GAB-2)."""

from __future__ import annotations

import base64
import os

import pytest
from mfa_apoyo import clave_de_prueba

from app.core.config import get_settings
from app.modules.identity_access.mfa_crypto import (
    MfaDecryptError,
    MfaUnavailable,
    decrypt_secret,
    encrypt_secret,
    parse_key_ring,
)


@pytest.fixture
def entorno_mfa_keys(monkeypatch):
    """Limpia la caché de Settings antes y después."""
    get_settings.cache_clear()
    try:
        yield
    finally:
        get_settings.cache_clear()


def _clave_b64():
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


@pytest.fixture
def anillo_una_clave(monkeypatch, entorno_mfa_keys):
    valor = clave_de_prueba()
    monkeypatch.setenv("KONTROL_MFA_KEYS", valor)
    get_settings.cache_clear()
    return valor


def test_mfa_k01_ida_y_vuelta(anillo_una_clave):
    """MFA-K01: decrypt(encrypt(raw)) == raw; kid devuelto es el de la primera clave."""
    raw = os.urandom(40)
    kid_esperado, _ = parse_key_ring(anillo_una_clave)[0]

    kid, blob = encrypt_secret(raw, aad="usuario-1")
    assert kid == kid_esperado
    assert decrypt_secret(kid, blob, aad="usuario-1") == raw


def test_mfa_k02_texto_cifrado_no_es_texto_plano(anillo_una_clave):
    """MFA-K02: raw no está en blob; dos cifrados difieren; longitud exacta."""
    raw = os.urandom(40)

    _, blob_1 = encrypt_secret(raw, aad="usuario-1")
    _, blob_2 = encrypt_secret(raw, aad="usuario-1")

    assert raw not in blob_1
    assert raw not in blob_2
    assert blob_1 != blob_2
    assert len(blob_1) == 12 + len(raw) + 16


def test_mfa_k03_manipulacion(anillo_una_clave):
    """MFA-K03: alterar un byte del blob produce MfaDecryptError."""
    raw = os.urandom(40)
    kid, blob = encrypt_secret(raw, aad="usuario-1")

    blob_alterado = bytearray(blob)
    blob_alterado[-1] ^= 0x01

    with pytest.raises(MfaDecryptError):
        decrypt_secret(kid, bytes(blob_alterado), aad="usuario-1")


def test_mfa_k04_aad_distinto(anillo_una_clave):
    """MFA-K04: un AAD distinto produce MfaDecryptError."""
    raw = os.urandom(40)
    kid, blob = encrypt_secret(raw, aad="usuario-1")

    with pytest.raises(MfaDecryptError):
        decrypt_secret(kid, blob, aad="usuario-2")


def test_mfa_k05_clave_equivocada(monkeypatch, entorno_mfa_keys):
    """MFA-K05: mismo kid con otra clave produce MfaDecryptError."""
    raw = os.urandom(40)
    kid_primera = "k1"
    clave_primera = _clave_b64()
    monkeypatch.setenv("KONTROL_MFA_KEYS", f"{kid_primera}:{clave_primera}")
    get_settings.cache_clear()

    _, blob = encrypt_secret(raw, aad="usuario-1")

    clave_segunda = _clave_b64()
    monkeypatch.setenv("KONTROL_MFA_KEYS", f"{kid_primera}:{clave_segunda}")
    get_settings.cache_clear()

    with pytest.raises(MfaDecryptError):
        decrypt_secret(kid_primera, blob, aad="usuario-1")


def test_mfa_k06_kid_desconocido(anillo_una_clave):
    """MFA-K06: kid desconocido produce MfaUnavailable."""
    raw = os.urandom(40)
    _, blob = encrypt_secret(raw, aad="usuario-1")

    with pytest.raises(MfaUnavailable):
        decrypt_secret("kid-desconocido", blob, aad="usuario-1")


def test_mfa_k07_rotacion(monkeypatch, entorno_mfa_keys):
    """MFA-K07: con rotación, el blob viejo descifra y el nuevo usa la primera clave."""
    raw = os.urandom(40)
    clave_a = _clave_b64()
    clave_b = _clave_b64()

    monkeypatch.setenv("KONTROL_MFA_KEYS", f"k1:{clave_a}")
    get_settings.cache_clear()

    kid_viejo, blob_viejo = encrypt_secret(raw, aad="usuario-1")

    monkeypatch.setenv("KONTROL_MFA_KEYS", f"k2:{clave_b},k1:{clave_a}")
    get_settings.cache_clear()

    assert decrypt_secret(kid_viejo, blob_viejo, aad="usuario-1") == raw

    kid_nuevo, _ = encrypt_secret(raw, aad="usuario-1")
    assert kid_nuevo == "k2"


def test_mfa_k08_sin_configuracion(monkeypatch, entorno_mfa_keys):
    """MFA-K08: sin anillo, cifrar y descifrar producen MfaUnavailable."""
    monkeypatch.delenv("KONTROL_MFA_KEYS", raising=False)
    get_settings.cache_clear()

    with pytest.raises(MfaUnavailable):
        encrypt_secret(os.urandom(32), aad="usuario-1")

    with pytest.raises(MfaUnavailable):
        decrypt_secret("k1", os.urandom(32), aad="usuario-1")


def test_mfa_k09_parse_key_ring():
    """MFA-K09: parse_key_ring valida anillos correctos y rechaza los inválidos sin filtrar claves."""
    clave_1 = _clave_b64()
    clave_2 = _clave_b64()

    valido_uno = f"k1:{clave_1}"
    valido_dos = f"k1:{clave_1}, k2:{clave_2.rstrip('=')}"
    valido_tres = f" k1:{clave_1} , k2:{clave_2} "

    assert parse_key_ring(valido_uno) == [("k1", base64.urlsafe_b64decode(clave_1))]
    anillo_dos = parse_key_ring(valido_dos)
    assert len(anillo_dos) == 2
    assert anillo_dos[0][0] == "k1"
    assert anillo_dos[1][0] == "k2"
    assert anillo_dos[1][1] == base64.urlsafe_b64decode(clave_2)
    assert len(parse_key_ring(valido_tres)) == 2

    invalidos = [
        "",
        "sin-dos-puntos",
        f"k1:{clave_1},k1:{clave_2}",
        f"kid-invalido-!:{clave_1}",
        f"k1:no-es-base64{clave_1}",
        "k1:@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@",
        f"k1:{base64.urlsafe_b64encode(os.urandom(16)).decode()}",
        f"k1:{base64.urlsafe_b64encode(os.urandom(31)).decode()}",
        f"k1:{base64.urlsafe_b64encode(os.urandom(33)).decode()}",
    ]

    for invalido in invalidos:
        with pytest.raises(ValueError) as error:
            parse_key_ring(invalido)
        mensaje = str(error.value)
        codificado = invalido.split(":", 1)[1] if ":" in invalido else ""
        if ":" in invalido:
            assert codificado not in mensaje
        assert clave_1 not in mensaje
        assert clave_2 not in mensaje
