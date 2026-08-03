"""Configuración central de KONTROL.

Todas las variables usan el prefijo KONTROL_*. Las variables sensibles se
validan al inicio y el servicio falla de forma segura si falta alguna
(FR-001-005). Ningún secreto se versiona; solo `.env.example` con nombres.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KONTROL_",
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
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

    # Licencia
    license_public_key_kid: str = "kontrol-lic-2026-01"
    license_public_key_pem: str | None = None  # clave pública Ed25519 embebida o inyectada
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


@lru_cache
def get_settings() -> Settings:
    # Los campos de Settings se pueblan desde env (pydantic-settings).
    return Settings()  # type: ignore[call-arg]
