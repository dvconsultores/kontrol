"""Configuración de la Autoridad Central (prefijo `KONTROL_CENTRAL_`, independiente del cliente).

Las claves privadas de firma del propietario llegan por configuración externa y nunca se generan aquí:
en `prod` la configuración no carga sin un conjunto válido con el `kid` activo (mismo contrato que el
ancla del cliente). Para rotar con solapamiento, el conjunto admite varias claves (`SIGNING_KEYS`,
JSON `kid → PEM privada`) además del par de una sola clave (`SIGNING_PRIVATE_KEY_PEM` + `SIGNING_KID`);
**un solo `kid` activo** (`SIGNING_KID`) firma las emisiones nuevas. Los errores de validación no
reproducen los valores: aquí viajan secretos. Nada se guarda en la base.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from functools import lru_cache
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.license_contract import load_private_key

SERVICE_NAME = "kontrol-central-authority"


class SigningKeyError(ValueError):
    """La clave de firma no está (`missing`), no sirve (`invalid`), el conjunto se contradice (`duplicate_kid`,
    `duplicate_key`) o el `kid` activo no tiene clave (`active_kid_missing`). Nunca lleva el material."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"clave de firma del propietario {reason}")
        self.reason = reason


def load_signing_key(pem: str | None) -> Ed25519PrivateKey:
    if pem is None or not pem.strip():
        raise SigningKeyError("missing")
    try:
        return load_private_key(pem)
    except (ValueError, TypeError, UnicodeEncodeError):
        raise SigningKeyError("invalid") from None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KONTROL_CENTRAL_",
        env_file=".env.central",
        extra="ignore",
        case_sensitive=False,
        hide_input_in_errors=True,
    )

    environment: str = Field(default="local", pattern="^(local|dev|qa|uat|staging|prod)$")
    db_url: str  # obligatoria: la base PROPIA de la autoridad, nunca la de un cliente
    # Clave privada Ed25519 del propietario, en PEM, inyectada desde fuera. Obligatoria en `prod`.
    signing_private_key_pem: str | None = None
    # El `kid` ACTIVO: identifica la clave que firma las emisiones nuevas y viaja dentro del paquete firmado.
    signing_kid: str = "kontrol-lic-2026-01"
    # Conjunto de firma para rotar con solapamiento: JSON `kid → PEM privada`. Se suma al par anterior.
    signing_keys: str | None = None
    #: Vida de un desafío de autenticación del sync (FR-010-376): corta y configurable; técnica, no de negocio.
    sync_challenge_ttl_seconds: int = Field(default=120, ge=5, le=900)
    log_json: bool = False

    @model_validator(mode="after")
    def _signing_key_required_in_prod(self) -> Settings:
        if self.environment != "prod":
            return self
        try:
            load_signing_key_set(self)
        except SigningKeyError as exc:
            raise ValueError(
                f"KONTROL_CENTRAL_SIGNING_PRIVATE_KEY_PEM (con KONTROL_CENTRAL_SIGNING_KID) o KONTROL_CENTRAL_SIGNING_KEYS es obligatoria "
                f"en prod: claves privadas Ed25519 del propietario en PEM, una por kid, con el kid activo presente (clave {exc.reason})"
            ) from None
        return self


def load_signing_key_set(settings: Settings) -> dict[str, str]:
    """El conjunto de firma `kid → PEM privada` (FR-010-448..451): el par de una clave más el JSON, validados.

    Vacío → `missing`; PEM que no es Ed25519 privada → `invalid`; un `kid` con dos claves distintas →
    `duplicate_kid`; la misma clave bajo dos `kid` → `duplicate_key`; el `kid` activo sin clave →
    `active_kid_missing`. Sin «primera clave por defecto»: el activo es explícito o no hay firma.
    """
    entradas: list[tuple[Any, Any]] = []
    if settings.signing_keys is not None and settings.signing_keys.strip():
        try:
            mapa = json.loads(settings.signing_keys)
        except ValueError:
            raise SigningKeyError("invalid") from None
        if not isinstance(mapa, Mapping):
            raise SigningKeyError("invalid")
        entradas.extend(mapa.items())
    if settings.signing_private_key_pem is not None and settings.signing_private_key_pem.strip():
        entradas.append((settings.signing_kid, settings.signing_private_key_pem))
    if not entradas:
        raise SigningKeyError("missing")
    conjunto: dict[str, str] = {}
    por_material: dict[bytes, str] = {}
    for kid, pem in entradas:
        if not isinstance(kid, str) or not kid.strip() or any(c.isspace() for c in kid.strip()) or not isinstance(pem, str):
            raise SigningKeyError("invalid")
        kid = kid.strip()
        clave = load_signing_key(pem)
        der = clave.public_key().public_bytes(encoding=serialization.Encoding.DER, format=serialization.PublicFormat.SubjectPublicKeyInfo)
        if kid in conjunto:
            if por_material.get(der) != kid:
                raise SigningKeyError("duplicate_kid")
            continue
        if der in por_material:
            raise SigningKeyError("duplicate_key")
        conjunto[kid] = pem.strip() + "\n"
        por_material[der] = kid
    if settings.signing_kid.strip() not in conjunto:
        raise SigningKeyError("active_kid_missing")
    return conjunto


def active_signing_pem(settings: Settings) -> str:
    """La clave privada del `kid` activo, o `SigningKeyError`. Es la única que firma emisiones nuevas."""
    return load_signing_key_set(settings)[settings.signing_kid.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
