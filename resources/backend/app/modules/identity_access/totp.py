"""TOTP RFC 6238 para el segundo factor de autenticación.

Este módulo solo usa la biblioteca estándar. No depende de relojes inyectables:
el reloj de las decisiones MFA está centralizado en `app.core.clock`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import struct
from datetime import datetime
from urllib.parse import quote, urlencode

PERIOD = 30
DIGITS = 6
ALGORITHM = "SHA1"
SKEW_STEPS = 1

_SECRET_BYTES = 20


def generate_secret() -> bytes:
    """Genera un secreto TOTP de 20 bytes con aleatoriedad segura."""
    return secrets.token_bytes(_SECRET_BYTES)


def encode_secret(raw: bytes) -> str:
    """Codifica el secreto en Base32 mayúscula sin relleno."""
    return base64.b32encode(raw).decode().rstrip("=")


def format_manual_key(b32: str) -> str:
    """Formatea la clave manual en grupos de 4 caracteres separados por espacio."""
    grupos = [b32[i : i + 4] for i in range(0, len(b32), 4)]
    return " ".join(grupos)


def time_step(at: datetime) -> int:
    """Calcula el paso TOTP para un instante dado."""
    return int(at.timestamp()) // PERIOD


def code_at(raw: bytes, step: int) -> str:
    """Calcula el código TOTP de 6 dígitos para un paso y secreto dados."""
    mensaje = struct.pack(">Q", step)
    mac = hmac.new(raw, mensaje, hashlib.sha1)
    hmac_resultado = mac.digest()
    desplazamiento = hmac_resultado[-1] & 0x0F
    binario = (hmac_resultado[desplazamiento] & 0x7F) << 24
    binario |= (hmac_resultado[desplazamiento + 1] & 0xFF) << 16
    binario |= (hmac_resultado[desplazamiento + 2] & 0xFF) << 8
    binario |= hmac_resultado[desplazamiento + 3] & 0xFF
    return str(binario % 10**DIGITS).zfill(DIGITS)


def match_step(raw: bytes, code: str, at: datetime) -> int | None:
    """Compara un código introducido con los pasos s-1, s y s+1.

    Acepta espacios alrededor o dentro del código; solo se consideran válidos
    exactamente 6 dígitos ASCII. La comparación se realiza en tiempo constante.
    """
    normalizado = code.replace(" ", "")
    if re.fullmatch(r"[0-9]{6}", normalizado, flags=re.ASCII) is None:
        return None

    paso_actual = time_step(at)
    candidatos = [paso_actual + d for d in range(-SKEW_STEPS, SKEW_STEPS + 1)]

    encontrado: int | None = None
    for paso in candidatos:
        esperado = code_at(raw, paso)
        if encontrado is None and hmac.compare_digest(esperado, normalizado):
            encontrado = paso
    return encontrado


def provisioning_uri(raw: bytes, *, account: str, issuer: str = "KONTROL") -> str:
    """Construye la URI otpauth para registrar la cuenta en una app autenticadora."""
    parametros = {
        "secret": encode_secret(raw),
        "issuer": issuer,
        "algorithm": ALGORITHM,
        "digits": DIGITS,
        "period": PERIOD,
    }
    return f"otpauth://totp/{quote(issuer)}:{quote(account)}?{urlencode(parametros)}"
