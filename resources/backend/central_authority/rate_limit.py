"""Límite de tasa de la emisión de desafíos (Spec 004 · `CENTRAL-SYNC-SIN-LIMITE-DE-TASA`): la decisión PURA.

Defensa en profundidad contra el abuso del endpoint pre-autenticación: no sustituye a la identidad
Ed25519, al desafío de un solo uso ni a la firma del sobre. Dimensión: **global** por autoridad (la
única identidad fiable antes de autenticar; la IP de origen pertenece a la pasarela, y el
`installation_id` lo controla el llamador). Algoritmo: ventana deslizante exacta sobre las filas que
la autoridad ya persiste (`cla_sync_challenges.created_at`): sin tabla nueva, sin memoria por proceso,
sin reloj compartido; el estado es el mismo PostgreSQL que da autoridad al desafío, así que vale para
varios trabajadores y no tiene un modo de fallo propio (si la base no responde, tampoco se emite).
Sin `sleep`, sin azar: rechazo inmediato con `Retry-After` determinista.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

CAPACITY_EXCEEDED = "capacity_exceeded"
DISABLED = "disabled"
OK = "ok"


@dataclass(frozen=True)
class RateLimitPolicy:
    enabled: bool
    capacity: int  # desafíos admitidos dentro de cualquier ventana de `window_seconds`
    window_seconds: int

    def __post_init__(self) -> None:
        if self.capacity < 1 or self.window_seconds < 1:
            raise ValueError("capacity y window_seconds deben ser >= 1")


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    reason: str
    retry_after_seconds: int | None = None


def window_start(policy: RateLimitPolicy, now: datetime) -> datetime:
    """El inicio de la ventana deslizante que termina en `now` (ambos en UTC)."""
    return now - timedelta(seconds=policy.window_seconds)


def decide(*, policy: RateLimitPolicy, now: datetime, issued_in_window: int, oldest_in_window: datetime | None) -> RateLimitDecision:
    """`issued_in_window`: desafíos ya emitidos con `created_at >= window_start`; `oldest_in_window`: el más
    antiguo de ellos (UTC) o `None`. Admite mientras haya hueco; si no, el reintento es cuando el más
    antiguo salga de la ventana (al menos 1 s, nunca más que la ventana)."""
    if not policy.enabled:
        return RateLimitDecision(True, DISABLED)
    if issued_in_window < 0:
        raise ValueError("issued_in_window no puede ser negativo")
    if issued_in_window < policy.capacity:
        return RateLimitDecision(True, OK)
    if oldest_in_window is None:
        # Sin instante del más antiguo no hay cálculo posible: cerrado ante error, con la ventana entera.
        return RateLimitDecision(False, CAPACITY_EXCEEDED, policy.window_seconds)
    libre_en = (oldest_in_window + timedelta(seconds=policy.window_seconds) - now).total_seconds()
    return RateLimitDecision(False, CAPACITY_EXCEEDED, max(1, min(policy.window_seconds, math.ceil(libre_en))))
