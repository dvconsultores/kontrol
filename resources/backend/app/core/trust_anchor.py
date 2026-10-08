"""El ancla de confianza de la licencia: las claves públicas del propietario, elegidas por `kid` (FR-010-148..152, 437..466).

La confianza fluye en un solo sentido: propietario → clave pública configurada fuera de la
instalación → la instalación verifica → licencia aceptada o rechazada. La clave de la propia
instalación identifica a la instalación (solicitud de activación); **nunca** es ancla: una
instalación que confía en su propia clave se certifica a sí misma.

Sin ancla, o con una que no es una clave pública Ed25519 en PEM, no hay verificación posible:
se falla cerrado, sin sustituto y sin generar nada. En `prod` la ausencia se detecta al arrancar
(`Settings`); en cualquier entorno, al importar.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class TrustAnchorError(ValueError):
    """El ancla no está (`missing`), no sirve (`invalid`), la configuración se contradice (`duplicate_kid`,
    `duplicate_key`) o el paquete no señala una clave del conjunto (`kid_missing`, `unknown_kid`). Nunca lleva el material."""

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


def _pem_normalizado(pem: Any) -> tuple[str, bytes]:
    """La clave pública Ed25519 en PEM (normalizada) y sus bytes DER, o `invalid`."""
    if not isinstance(pem, str):
        raise TrustAnchorError("invalid")
    clave = load_trust_anchor(pem)
    return pem.strip() + "\n", clave.public_bytes(encoding=serialization.Encoding.DER, format=serialization.PublicFormat.SubjectPublicKeyInfo)


def load_trust_set(*, trust_keys: str | Mapping[str, Any] | None, legacy_pem: str | None, legacy_kid: str | None) -> dict[str, str]:
    """El conjunto de confianza `kid → PEM pública`, provisto desde fuera de la instalación (FR-010-437..444).

    `trust_keys` es el JSON (o el mapa) `kid → PEM` de `KONTROL_LICENSE_TRUST_KEYS`; el par legacy
    (`KONTROL_LICENSE_PUBLIC_KEY_PEM` + `KONTROL_LICENSE_PUBLIC_KEY_KID`) es una entrada más, la de los
    despliegues de una sola clave. Vacío → `missing`. Un `kid` con dos claves distintas → `duplicate_kid`;
    la misma clave bajo dos `kid` → `duplicate_key` (el contrato no define alias). Un `kid` es una etiqueta
    sin espacios. Nada de aquí viene de una licencia: un paquete no añade ni sustituye anclas.
    """
    entradas: list[tuple[Any, Any]] = []
    if trust_keys is not None and not (isinstance(trust_keys, str) and not trust_keys.strip()):
        mapa = trust_keys
        if isinstance(mapa, str):
            try:
                mapa = json.loads(mapa)
            except ValueError:
                raise TrustAnchorError("invalid") from None
        if not isinstance(mapa, Mapping):
            raise TrustAnchorError("invalid")
        entradas.extend(mapa.items())
    if legacy_pem is not None and legacy_pem.strip():
        if not isinstance(legacy_kid, str) or not legacy_kid.strip():
            raise TrustAnchorError("kid_missing")
        entradas.append((legacy_kid, legacy_pem))
    if not entradas:
        raise TrustAnchorError("missing")
    conjunto: dict[str, str] = {}
    por_material: dict[bytes, str] = {}
    for kid, pem in entradas:
        if not isinstance(kid, str) or not kid.strip() or any(c.isspace() for c in kid.strip()):
            raise TrustAnchorError("invalid")
        kid = kid.strip()
        pem_norm, der = _pem_normalizado(pem)
        if kid in conjunto:
            if conjunto[kid] != pem_norm:
                raise TrustAnchorError("duplicate_kid")
            continue  # la misma entrada repetida (p. ej. el par legacy también en el JSON)
        if der in por_material:
            raise TrustAnchorError("duplicate_key")
        conjunto[kid] = pem_norm
        por_material[der] = kid
    return conjunto


def resolve_trusted_owner_key(kid: Any, trust_set: Mapping[str, str]) -> str:
    """EXACTAMENTE la clave pública del `kid` firmado, o `kid_missing` / `unknown_kid`. Nunca «todas hasta que una verifique»."""
    if not isinstance(kid, str) or not kid.strip():
        raise TrustAnchorError("kid_missing")
    try:
        return trust_set[kid]
    except KeyError:
        raise TrustAnchorError("unknown_kid") from None
