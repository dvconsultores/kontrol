"""Helper compartido para las pruebas MFA.

Proporciona un anillo de claves sintético generado en ejecución, un oráculo TOTP
independiente del producto y un reloj mutable para simular pasos de tiempo.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import struct
from datetime import UTC, datetime, timedelta

import pytest

_ULTIMO_INSTANTE: datetime | None = None


def clave_de_prueba() -> str:
    """Devuelve un anillo sintético con una clave de 32 bytes generada en ejecución."""
    kid = f"t{secrets.token_hex(4)}"
    clave = base64.urlsafe_b64encode(os.urandom(32)).decode()
    return f"{kid}:{clave}"


def codigo_totp(clave_manual: str, instante: datetime) -> str:
    """Calcula un código TOTP RFC 6238 usando un oráculo independiente del producto.

    Acepta claves con espacios, minúsculas y sin relleno.
    """
    clave_normalizada = clave_manual.replace(" ", "").upper()
    relleno = "=" * (-len(clave_normalizada) % 8)
    clave = base64.b32decode(clave_normalizada + relleno)
    paso = int(instante.timestamp()) // 30
    mac = hmac.new(clave, struct.pack(">Q", paso), hashlib.sha1)
    hmac_resultado = mac.digest()
    desplazamiento = hmac_resultado[-1] & 0x0F
    binario = (hmac_resultado[desplazamiento] & 0x7F) << 24
    binario |= (hmac_resultado[desplazamiento + 1] & 0xFF) << 16
    binario |= (hmac_resultado[desplazamiento + 2] & 0xFF) << 8
    binario |= hmac_resultado[desplazamiento + 3] & 0xFF
    return f"{binario % 10**6:06d}"


class RelojMfa:
    """Reloj mutable para simular el paso del tiempo en pruebas MFA."""

    def __init__(self, inicio: datetime) -> None:
        self._instante = inicio

    def ahora(self) -> datetime:
        return self._instante

    def avanzar(self, segundos: float) -> None:
        self._instante += timedelta(seconds=segundos)

    def siguiente_paso(self) -> None:
        """Avanza hasta el inicio exacto del siguiente paso de 30 s."""
        paso = int(self._instante.timestamp()) // 30
        self._instante = datetime.fromtimestamp((paso + 1) * 30, UTC)


@pytest.fixture
def reloj_mfa(monkeypatch):
    """Fixture que inyecta un RelojMfa en app.core.clock.now.

    El reloj nunca retrocede entre pruebas del mismo proceso para que la
    antirrepetición TOTP de un usuario compartido no vea pasos repetidos.
    """
    global _ULTIMO_INSTANTE
    inicio = datetime.now(UTC)
    if _ULTIMO_INSTANTE is not None and _ULTIMO_INSTANTE > inicio:
        inicio = _ULTIMO_INSTANTE
    reloj = RelojMfa(inicio)
    monkeypatch.setattr("app.core.clock.now", reloj.ahora)
    yield reloj
    _ULTIMO_INSTANTE = reloj.ahora()
