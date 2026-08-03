"""Motor local de licencias (ADR-005, DOC-07).

La instalación está en el servidor del cliente, pero la autoridad de
licenciamiento pertenece al propietario de KONTROL. La aplicación local
solo verifica licencias firmadas (Ed25519) y aplica el modo autorizado.
La clave privada jamás reside aquí (FR-001-055).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.core.config import get_settings
from app.core.errors import LicenseBlockedError

# Modos de acceso (DOC-07 §5.2)
FULL_ACCESS = "FULL_ACCESS"
RENEWAL_NOTICE = "RENEWAL_NOTICE"
CRITICAL_RENEWAL_NOTICE = "CRITICAL_RENEWAL_NOTICE"
READ_ONLY = "READ_ONLY"
SECURITY_SUSPENSION = "SECURITY_SUSPENSION"


@dataclass
class LicenseData:
    """Datos de una licencia firmada vigente."""

    license_id: str
    installation_id: str
    customer_id: str
    contract_id: str
    company_tax_id: str | None
    period_start: datetime
    period_end: datetime
    critical_warning_start: datetime
    read_only_start: datetime
    entitlements: dict[str, Any] = field(default_factory=dict)
    minimum_version: str | None = None
    kid: str | None = None


def parse_license_payload(payload: dict[str, Any]) -> LicenseData:
    def _dt(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    return LicenseData(
        license_id=str(payload["license_id"]),
        installation_id=str(payload["installation_id"]),
        customer_id=str(payload.get("customer_id", "")),
        contract_id=str(payload.get("contract_id", "")),
        company_tax_id=payload.get("company_tax_id"),
        period_start=_dt(payload["period_start"]),
        period_end=_dt(payload["period_end"]),
        critical_warning_start=_dt(payload.get("critical_warning_start", payload["period_end"])),
        read_only_start=_dt(payload.get("read_only_start", payload["period_end"])),
        entitlements=payload.get("entitlements", {}),
        minimum_version=payload.get("minimum_version"),
        kid=payload.get("kid"),
    )


def load_public_key(pem: str) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(pem.encode("utf-8"))
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("La clave pública no es Ed25519")
    return key


def verify_license_signature(payload: dict[str, Any], signature_hex: str, public_key_pem: str) -> bool:
    """Verifica la firma del paquete de licencia (Ed25519).

    Una licencia alterada o mal firmada NO produce READ_ONLY; produce
    SECURITY_SUSPENSION (DOC-07 §10.1).
    """
    try:
        public_key = load_public_key(public_key_pem)
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        public_key.verify(bytes.fromhex(signature_hex), canonical)
        return True
    except (InvalidSignature, ValueError, KeyError):
        return False


def compute_mode(license_data: LicenseData, now: datetime, *, last_reliable_date: datetime | None = None) -> str:
    """Calcula el modo de acceso con fecha confiable (FR-001-052/056).

    Reglas (DOC-07 §5):
    - Antes de period_start con activación previa no existe; aquí se asume vigente.
    - En periodo pagado → FULL_ACCESS.
    - period_end <= now < critical_warning_start → RENEWAL_NOTICE.
    - critical_warning_start <= now < read_only_start → CRITICAL_RENEWAL_NOTICE.
    - now >= read_only_start → READ_ONLY.
    """
    # Protección contra retroceso: si el reloj retrocede respecto de la
    # última fecha confiable, usar la mayor (mantener la fecha mayor).
    if last_reliable_date is not None and now < last_reliable_date:
        now = last_reliable_date

    if now < license_data.period_start:
        return FULL_ACCESS
    if now > license_data.period_end:
        if now >= license_data.read_only_start:
            return READ_ONLY
        if now >= license_data.critical_warning_start:
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
