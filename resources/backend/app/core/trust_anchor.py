"""El ancla de confianza de la licencia: la clave pública del propietario (FR-010-148..152).

La confianza fluye en un solo sentido: propietario → clave pública configurada fuera de la
instalación → la instalación verifica → licencia aceptada o rechazada. La clave de la propia
instalación identifica a la instalación (solicitud de activación); **nunca** es ancla: una
instalación que confía en su propia clave se certifica a sí misma.

Sin ancla, o con una que no es una clave pública Ed25519 en PEM, no hay verificación posible:
se falla cerrado, sin sustituto y sin generar nada. En `prod` la ausencia se detecta al arrancar
(`Settings`); en cualquier entorno, al importar.
"""

from __future__ import annotations

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class TrustAnchorError(ValueError):
    """El ancla no está (`missing`) o no sirve (`invalid`). Nunca lleva el material."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"ancla de confianza del propietario {reason}")
        self.reason = reason


def load_trust_anchor(pem: str | None) -> Ed25519PublicKey:
    """La clave pública del propietario, o `TrustAnchorError`. Sin fallback de ningún tipo."""
    if pem is None or not pem.strip():
        raise TrustAnchorError("missing")
    try:
        clave = serialization.load_pem_public_key(pem.encode("utf-8"))
    except (ValueError, TypeError, UnicodeEncodeError):
        raise TrustAnchorError("invalid") from None
    if not isinstance(clave, Ed25519PublicKey):
        raise TrustAnchorError("invalid")
    return clave
