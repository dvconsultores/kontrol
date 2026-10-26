"""Reloj único para las decisiones de seguridad MFA y de sesión.

Las pruebas pueden reemplazarlo con monkeypatch. Ninguna variable de entorno ni
configuración cambia su comportamiento: siempre devuelve el instante actual en UTC.
"""

from __future__ import annotations

from datetime import UTC, datetime


def now() -> datetime:
    """Devuelve el instante actual con zona horaria UTC."""
    return datetime.now(UTC)
