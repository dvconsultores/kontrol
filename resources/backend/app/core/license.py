"""Motor local de licencias (ADR-005, DOC-07).

La instalación está en el servidor del cliente, pero la autoridad de
licenciamiento pertenece al propietario de KONTROL. La aplicación local
solo verifica licencias firmadas (Ed25519) y aplica el modo autorizado.
La clave privada jamás reside aquí (FR-001-055).

El contrato del paquete —campos, canonicalización, firma, verificación y orden entre períodos—
vive en `app.core.license_contract`, puro y compartido con la Autoridad Central; aquí se reexporta
y se añade lo que solo el cliente necesita: el cálculo del modo y el bloqueo de escrituras.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.errors import LicenseBlockedError
from app.core.license_contract import (  # noqa: F401 — reexportados: el resto del cliente importa de aquí
    CRITICAL_RENEWAL_NOTICE,
    FULL_ACCESS,
    INCOMPARABLE_PERIOD,
    NEWER_PERIOD,
    OLDER_PERIOD,
    READ_ONLY,
    RENEWAL_NOTICE,
    SAME_PERIOD,
    SECURITY_SUSPENSION,
    LicenseContractError,
    LicenseData,
    _as_utc,
    canonical_bytes,
    compare_period,
    load_public_key,
    parse_license_payload,
    parse_revision,
    payload_hash,
    verify_license_signature,
)


def compute_mode(license_data: LicenseData, now: datetime, *, last_reliable_date: datetime | None = None) -> str:
    """Calcula el modo de acceso con fecha confiable (FR-001-052/056).

    Reglas (DOC-07 §5):
    - Antes de period_start con activación previa no existe; aquí se asume vigente.
    - En periodo pagado → FULL_ACCESS.
    - period_end <= now < critical_warning_start → RENEWAL_NOTICE.
    - critical_warning_start <= now < read_only_start → CRITICAL_RENEWAL_NOTICE.
    - now >= read_only_start → READ_ONLY.
    """
    now = _as_utc(now)
    period_start = _as_utc(license_data.period_start)
    period_end = _as_utc(license_data.period_end)
    critical_warning_start = _as_utc(license_data.critical_warning_start)
    read_only_start = _as_utc(license_data.read_only_start)

    # Protección contra retroceso: si el reloj retrocede respecto de la
    # última fecha confiable, usar la mayor (mantener la fecha mayor).
    if last_reliable_date is not None:
        last_reliable_date = _as_utc(last_reliable_date)
        if now < last_reliable_date:
            now = last_reliable_date

    if now < period_start:
        return FULL_ACCESS
    if now > period_end:
        if now >= read_only_start:
            return READ_ONLY
        if now >= critical_warning_start:
            return CRITICAL_RENEWAL_NOTICE
        return RENEWAL_NOTICE
    return FULL_ACCESS



def mode_blocks_write(mode: str) -> bool:
    return mode in {READ_ONLY, SECURITY_SUSPENSION}


def _now() -> datetime:
    return datetime.now(UTC)


def ensure_write_allowed(mode: str) -> None:
    """Bloquea escrituras en READ_ONLY / SECURITY_SUSPENSION (FR-001-053)."""
    if mode == READ_ONLY:
        raise LicenseBlockedError(
            code="LICENSE_READ_ONLY",
            message="La licencia anual de KONTROL no ha sido renovada. La instalación se encuentra en modo solo consulta.",
        )
    if mode == SECURITY_SUSPENSION:
        raise LicenseBlockedError(
            code="LICENSE_SECURITY_SUSPENSION",
            message="La licencia no es válida. Contacte al soporte de KONTROL.",
        )


def public_key_from_settings() -> str | None:
    return get_settings().license_public_key_pem
