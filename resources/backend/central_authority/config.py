"""Configuración de la Autoridad Central (prefijo `KONTROL_CENTRAL_`, independiente del cliente).

La clave privada de firma del propietario llega por configuración externa y nunca se genera aquí:
en `prod` la configuración no carga sin ella (mismo contrato que el ancla del cliente). Los errores
de validación no reproducen los valores: aquí viajan secretos.
"""

from __future__ import annotations

from functools import lru_cache

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.license_contract import load_private_key

SERVICE_NAME = "kontrol-central-authority"


class SigningKeyError(ValueError):
    """La clave de firma no está (`missing`) o no sirve (`invalid`). Nunca lleva el material."""

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
    # Identificador de la clave de firma (semántica actual del `kid`): una sola clave activa en Fase 1.
    signing_kid: str = "kontrol-lic-2026-01"
    #: Vida de un desafío de autenticación del sync (FR-010-376): corta y configurable; técnica, no de negocio.
    sync_challenge_ttl_seconds: int = Field(default=120, ge=5, le=900)
    log_json: bool = False

    @model_validator(mode="after")
    def _signing_key_required_in_prod(self) -> Settings:
        if self.environment != "prod":
            return self
        try:
            load_signing_key(self.signing_private_key_pem)
        except SigningKeyError as exc:
            raise ValueError(
                f"KONTROL_CENTRAL_SIGNING_PRIVATE_KEY_PEM es obligatoria en prod y debe ser la clave privada "
                f"Ed25519 del propietario en PEM (clave {exc.reason})"
            ) from None
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
