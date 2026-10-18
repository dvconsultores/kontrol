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
    api_prefix: str = "/api/v1"

    @property
    def app_version(self) -> str:
        """La versión del producto (FR-001-084; ADR-D0-006 R-D0-06-4: «versión del producto» en la
        solicitud de activación). Autoridad única: `app.__version__`, que viaja dentro del artefacto
        desplegado (`Dockerfile.backend` copia `app/`, no `pyproject.toml`); `pyproject.toml` la refleja y
        una prueba lo vigila. No es un ajuste: ninguna variable de entorno ni fichero puede declarar
        una versión distinta de la del código que corre (PANEL-VERSION-VACIA)."""
        from app import __version__

        return __version__

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

    # Licencia · conjunto de confianza del propietario (FR-010-148..151, 437..444). Dos formas, que se suman:
    # el par de una sola clave (`KONTROL_LICENSE_PUBLIC_KEY_PEM` identificada por `KONTROL_LICENSE_PUBLIC_KEY_KID`)
    # y `KONTROL_LICENSE_TRUST_KEYS`, un JSON `kid → PEM pública` para rotar con solapamiento (A + B).
    # Siempre desde fuera de la instalación; una licencia nunca añade ni sustituye anclas. Obligatorio en
    # `prod` (falla al inicio si no hay un conjunto válido); sin él nunca se verifica una licencia.
    license_public_key_kid: str = "kontrol-lic-2026-01"
    license_public_key_pem: str | None = None
    license_trust_keys: str | None = None
    license_timezone: str = "America/Caracas"
    installation_volume_path: str = "/data/license-state"

    # Almacenamiento
    storage_path: str = "/data/storage"
    backup_path: str = "/data/backups"
    max_upload_bytes: int = 25 * 1024 * 1024

    # Analizador antimalware documental (Spec 046; OBS-09, opción B de la dueña). La elección es EXPLÍCITA:
    # `clamscan` lanza el binario local por proceso (QA y desarrollo); `clamd` transmite el contenido por INSTREAM
    # al demonio del servicio `clamd` de la composición. Ninguna de las dos cae en la otra ni en «sin análisis»
    # cuando falla: el resultado es `SCAN_FAILED` y la subida se rechaza (falso seguro).
    document_scanner: str = Field(default="clamscan", pattern="^(clamscan|clamd)$")
    clamd_host: str = Field(default="clamd", min_length=1)
    clamd_port: int = Field(default=3310, ge=1, le=65535)

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
        from app.core.trust_anchor import TrustAnchorError, load_trust_set

        try:
            load_trust_set(trust_keys=self.license_trust_keys, legacy_pem=self.license_public_key_pem, legacy_kid=self.license_public_key_kid)
        except TrustAnchorError as exc:
            raise ValueError(
                f"KONTROL_LICENSE_PUBLIC_KEY_PEM (con KONTROL_LICENSE_PUBLIC_KEY_KID) o KONTROL_LICENSE_TRUST_KEYS es obligatoria "
                f"en prod y debe contener claves públicas Ed25519 del propietario en PEM, una por kid (ancla {exc.reason})"
            ) from None
        return self


@lru_cache
def get_settings() -> Settings:
    # Los campos de Settings se pueblan desde env (pydantic-settings).
    return Settings()  # type: ignore[call-arg]
