"""Generación del QR del alta MFA.

El QR es solo una comodidad, no la fuente de verdad: la clave manual sigue
disponible. El frontend lo pinta con un `<img src>` sin inyectar marcado.
"""

from __future__ import annotations

import segno


def svg_data_uri(otpauth_uri: str) -> str:
    """Convierte la URI otpauth interna en una imagen SVG embebida.

    Solo se aceptan URIs `otpauth://totp/` generadas por el sistema.
    """
    if not otpauth_uri.startswith("otpauth://totp/"):
        raise ValueError("El QR solo codifica URIs otpauth://totp/ internas")
    return segno.make(otpauth_uri, error="m", micro=False).svg_data_uri(scale=4, border=4)
