"""Cifrado del secreto TOTP con un anillo de claves AES-256-GCM.

Si la clave está ausente o el identificador es desconocido no hay MFA posible y
nunca se vuelve a autenticación solo con contraseña (fallo cerrado). Una
manipulación del texto cifrado o una clave errónea producen `MfaDecryptError`.
"""

from __future__ import annotations

import base64
import binascii
import os
import re

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_KID = re.compile(r"[A-Za-z0-9_-]{1,32}")


class MfaUnavailable(Exception):
    """Clave ausente o kid desconocido: no hay MFA posible y el sistema falla cerrado."""


class MfaDecryptError(Exception):
    """El texto cifrado fue manipulado o la clave es errónea."""


def parse_key_ring(value: str) -> list[tuple[str, bytes]]:
    """Parsea un anillo `kid:clave_base64url[,kid:clave]` y valida cada entrada.

    Los mensajes de error identifican la posición y el problema, sin incluir
    nunca la clave ni la entrada completa.
    """
    anillo: list[tuple[str, bytes]] = []
    visto: set[str] = set()

    entradas = value.split(",")
    if not any(entrada.strip() for entrada in entradas):
        raise ValueError("El anillo MFA no puede estar vacío")

    for posicion, entrada in enumerate(entradas, start=1):
        texto = entrada.strip()
        if not texto:
            raise ValueError(f"Entrada {posicion} vacía")

        if ":" not in texto:
            raise ValueError(f"Entrada {posicion} sin separador kid:clave")

        kid, clave = texto.split(":", 1)
        if _KID.fullmatch(kid) is None:
            raise ValueError(f"Entrada {posicion} con identificador de clave no válido")

        if kid in visto:
            raise ValueError(f"Entrada {posicion} con identificador de clave duplicado")
        visto.add(kid)

        try:
            relleno = "=" * (-len(clave) % 4)
            decodificada = base64.urlsafe_b64decode(clave + relleno)
        except (binascii.Error, ValueError):
            raise ValueError(f"Entrada {posicion} con clave no decodificable") from None

        if len(decodificada) != 32:
            raise ValueError(f"Entrada {posicion} con clave de longitud distinta de 32 bytes")

        anillo.append((kid, decodificada))

    return anillo


def _ring() -> list[tuple[str, bytes]]:
    """Lee el anillo configurado; sin anillo → `MfaUnavailable`. Un anillo malformado nunca llega aquí:
    `Settings` lo rechaza al arrancar (`_mfa_keys_validas`)."""
    from app.core.config import get_settings

    valor = get_settings().mfa_keys
    if valor is None:
        raise MfaUnavailable("KONTROL_MFA_KEYS no configurada")
    return parse_key_ring(valor)


def encrypt_secret(raw: bytes, *, aad: str) -> tuple[str, bytes]:
    """Cifra el secreto con la primera clave del anillo.

    Genera un nonce aleatorio de 96 bits para cada cifrado
    (NIST SP 800-38D). El AAD liga el secreto a una cuenta o recurso.
    """
    anillo = _ring()
    kid, clave = anillo[0]
    nonce = os.urandom(12)
    blob = nonce + AESGCM(clave).encrypt(nonce, raw, aad.encode())
    return kid, blob


def decrypt_secret(kid: str, blob: bytes, *, aad: str) -> bytes:
    """Descifra un secreto con la clave identificada por `kid`.

    Si el kid no existe, el MFA no está disponible. Cualquier manipulación o
    clave incorrecta se traduce en `MfaDecryptError`.
    """
    anillo = _ring()
    claves = dict(anillo)
    clave = claves.get(kid)
    if clave is None:
        raise MfaUnavailable("Identificador de clave MFA no disponible")

    if len(blob) < 28:
        raise MfaDecryptError("Texto cifrado incompleto")

    nonce = blob[:12]
    cifrado = blob[12:]
    try:
        return AESGCM(clave).decrypt(nonce, cifrado, aad.encode())
    except InvalidTag:
        raise MfaDecryptError("Texto cifrado inválido o AAD incorrecto") from None


def active_key_id() -> str:
    """Devuelve el identificador de la primera clave del anillo."""
    anillo = _ring()
    return anillo[0][0]
