"""Configuración central de KONTROL.

Todas las variables usan el prefijo KONTROL_*. Las variables sensibles se
validan al inicio y el servicio falla de forma segura si falta alguna
(FR-001-005). Ningún secreto se versiona; solo `.env.example` con nombres.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KONTROL_",
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
        # Un error de validación no reproduce los valores: la configuración lleva secretos y el
        # ancla de la licencia, y el mensaje acaba en el registro de arranque (FR-010-151/156).
        hide_input_in_errors=True,
    )

    # Identidad del entorno
    environment: str = Field(default="local", pattern="^(local|dev|qa|uat|staging|prod)$")
    app_name: str = "KONTROL"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"

    # Base de datos (usuario restringido, no superusuario)
    db_url: str = Field(default="postgresql+psycopg2://kontrol:kontrol@db:5432/kontrol")

    # Seguridad
    secret_key: str  # obligatoria: falla al inicio si falta
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    cookie_secure: bool = True
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    csrf_enabled: bool = True
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    password_min_length: int = 10
    login_rate_limit_per_minute: int = 5
    lockout_after_failures: int = 5
    lockout_minutes: int = 15

    #: Zona del **calendario de negocio** (Spec 001 · POLICY-CLOCK-LOCAL). Decide qué
    #: día es «hoy» para vigencias, vencimientos y selección de reglas. No confundir
    #: con los instantes técnicos, que son UTC por `ADR-D0-001` y no se convierten.
    business_timezone: str = "America/Caracas"

    # Licencia
    license_public_key_kid: str = "kontrol-lic-2026-01"
    # Ancla de confianza de la licencia: la clave pública Ed25519 del propietario, inyectada
    # desde fuera de la instalación. Obligatoria en `prod` (falla al inicio si falta o no sirve);
    # sin ella nunca se verifica una licencia, en ningún entorno (FR-010-148..151).
    license_public_key_pem: str | None = None
    license_timezone: str = "America/Caracas"
    installation_volume_path: str = "/data/license-state"

    # Almacenamiento
    storage_path: str = "/data/storage"
    backup_path: str = "/data/backups"
    max_upload_bytes: int = 25 * 1024 * 1024

    # Observabilidad
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_json: bool = True

    @field_validator("secret_key")
    @classmethod
    def _secret_key_not_default(cls, v: str) -> str:
        if not v or len(v) < 32:
            raise ValueError("KONTROL_SECRET_KEY debe tener al menos 32 caracteres")
        return v

    @model_validator(mode="after")
    def _trust_anchor_required_in_prod(self) -> Settings:
        """En `prod`, el ancla del propietario es obligatoria y debe servir: mismo contrato que
        `secret_key`, fallar al inicio. No se genera, no se sustituye, no se avisa a medias."""
        if self.environment != "prod":
            return self
        from app.core.trust_anchor import TrustAnchorError, load_trust_anchor

        try:
            load_trust_anchor(self.license_public_key_pem)
        except TrustAnchorError as exc:
            raise ValueError(
                f"KONTROL_LICENSE_PUBLIC_KEY_PEM es obligatoria en prod y debe ser la clave pública "
                f"Ed25519 del propietario en PEM (ancla {exc.reason})"
            ) from None
        return self


@lru_cache
def get_settings() -> Settings:
    # Los campos de Settings se pueblan desde env (pydantic-settings).
    return Settings()  # type: ignore[call-arg]
