"""Contrato puro de la licencia firmada (DOC-07 §10; Spec 004 · Autoridad Central Fase 1).

Lo que comparten el cliente y la Autoridad Central: los campos del paquete, la canonicalización
que produce los bytes firmados, la firma y la verificación Ed25519, y el orden entre períodos. No
importa configuración, base de datos ni errores del cliente: este módulo debe poder importarse
desde un servicio aislado sin arrastrar nada de la instalación.

Regla de compatibilidad (probada en `evidence/licencia-revision/canonicalizacion.txt`): los bytes
firmados salen del diccionario tal como viene; un paquete legacy no trae `revision` y no se
reconstruye jamás con `"revision": null`; un paquete revisionado la trae dentro del material firmado.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

# Modos de acceso (DOC-07 §5.2)
FULL_ACCESS = "FULL_ACCESS"
RENEWAL_NOTICE = "RENEWAL_NOTICE"
CRITICAL_RENEWAL_NOTICE = "CRITICAL_RENEWAL_NOTICE"
READ_ONLY = "READ_ONLY"
SECURITY_SUSPENSION = "SECURITY_SUSPENSION"

# Orden entre períodos (DOC-07 §5.1; «no retroceder el período» §10.4/§15.1/§18.2)
SAME_PERIOD = "SAME_PERIOD"
NEWER_PERIOD = "NEWER_PERIOD"
OLDER_PERIOD = "OLDER_PERIOD"
INCOMPARABLE_PERIOD = "INCOMPARABLE_PERIOD"

ISSUER_NAME = "KONTROL Licensing Authority"


class LicenseContractError(ValueError):
    """El paquete no cumple el contrato (p. ej. una `revision` que no es un entero ≥ 1)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class LicenseData:
    """Datos de una licencia firmada."""

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
    #: Orden de emisión dentro de instalación + período, asignado por la autoridad. `None` = legacy.
    revision: int | None = None


def parse_revision(payload: dict[str, Any]) -> int | None:
    """La `revision` del paquete: ausente → legacy (`None`); presente → entero ≥ 1, nada más.

    Un booleano es un `int` en Python y no es una revisión; una cadena, un decimal, cero o un
    negativo tampoco. El contrato no admite `null` explícito: la ausencia es la única forma legacy.
    """
    if "revision" not in payload:
        return None
    valor = payload["revision"]
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < 1:
        raise LicenseContractError("LICENSE_INVALID_REVISION", "La revisión de la licencia debe ser un entero mayor o igual que 1.")
    return valor


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
        revision=parse_revision(payload),
    )


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    """Los bytes que se firman y se verifican: el diccionario, con claves ordenadas, en UTF-8."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")


def payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def load_public_key(pem: str) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(pem.encode("utf-8"))
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("La clave pública no es Ed25519")
    return key


def load_private_key(pem: str) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(pem.encode("utf-8"), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("La clave privada no es Ed25519")
    return key


def sign_license_payload(payload: dict[str, Any], private_key: Ed25519PrivateKey) -> str:
    """Firma Ed25519 de los bytes canónicos del paquete, en hexadecimal. Solo la autoridad la usa."""
    return private_key.sign(canonical_bytes(payload)).hex()


def verify_license_signature(payload: dict[str, Any], signature_hex: str, public_key_pem: str) -> bool:
    """Verifica la firma del paquete de licencia (Ed25519).

    Una licencia alterada o mal firmada NO produce READ_ONLY; produce
    SECURITY_SUSPENSION (DOC-07 §10.1).
    """
    try:
        public_key = load_public_key(public_key_pem)
        public_key.verify(bytes.fromhex(signature_hex), canonical_bytes(payload))
        return True
    except (InvalidSignature, ValueError, KeyError):
        return False


def _as_utc(dt: datetime) -> datetime:
    """Normaliza datetimes a UTC (SQLite devuelve naive en DateTime(timezone))."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def compare_period(current_start: datetime, current_end: datetime, incoming_start: datetime, incoming_end: datetime) -> str:
    """Ordena dos licencias por su período firmado, y solo por él.

    Igual inicio e igual fin → `SAME_PERIOD`. Inicio y fin ambos posteriores → `NEWER_PERIOD`.
    Inicio y fin ambos anteriores → `OLDER_PERIOD`. Si inicio y fin no se mueven en el mismo
    sentido (períodos que se cruzan o comparten un extremo), el paquete no describe un período
    del contrato y no se ordena: `INCOMPARABLE_PERIOD`, que el llamador trata cerrado. Nada más
    participa: ni `kid`, ni `license_id`, ni derechos, ni la fecha de importación, ni el reloj.
    """
    cs, ce, is_, ie = _as_utc(current_start), _as_utc(current_end), _as_utc(incoming_start), _as_utc(incoming_end)
    if is_ == cs and ie == ce:
        return SAME_PERIOD
    if is_ > cs and ie > ce:
        return NEWER_PERIOD
    if is_ < cs and ie < ce:
        return OLDER_PERIOD
    return INCOMPARABLE_PERIOD
