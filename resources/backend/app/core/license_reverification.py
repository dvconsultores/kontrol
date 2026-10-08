"""Reverificación PURA del artefacto de licencia vigente contra la política de confianza actual
(Spec 004 · `LICENCIA-ESTADO-SIN-REVERIFICAR`; DOC-07 §10.1, §14.5, §15.1, §16.2).

No reimporta, no ordena, no muta: toma el artefacto firmado tal como está persistido y responde si
HOY, con el conjunto de confianza de HOY, sigue siendo la licencia de esta instalación. La fuente es el
artefacto (carga + firma + hash); el estado derivado solo aporta el vínculo (`license_id`). Las fechas y
los derechos del estado no se comparan aquí: el modo se recalcula en lectura y el contrato no define
reconstruir el estado desde el artefacto. Sin SQLAlchemy, sin settings, sin red.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.core import trust_anchor
from app.core.license_contract import LicenseContractError, parse_license_payload, payload_hash, verify_license_signature

NO_CURRENT_LICENSE = "NO_CURRENT_LICENSE"
MALFORMED_ARTIFACT = "MALFORMED_ARTIFACT"
KID_MISSING = "KID_MISSING"
KID_UNKNOWN = "KID_UNKNOWN"
SIGNATURE_INVALID = "SIGNATURE_INVALID"
INSTALLATION_MISMATCH = "INSTALLATION_MISMATCH"
ARTIFACT_STATE_MISMATCH = "ARTIFACT_STATE_MISMATCH"
TRUST_SET_INVALID = "TRUST_SET_INVALID"
VALID = "VALID"
#: Lo que no es `VALID` ni `NO_CURRENT_LICENSE` deja al vigente sin autoridad de escritura (SECURITY_SUSPENSION).
FAILURES = frozenset({MALFORMED_ARTIFACT, KID_MISSING, KID_UNKNOWN, SIGNATURE_INVALID, INSTALLATION_MISMATCH, ARTIFACT_STATE_MISMATCH, TRUST_SET_INVALID})


@dataclass(frozen=True)
class Reverification:
    status: str
    reason: str
    license_id: str | None = None
    kid: str | None = None

    @property
    def grants_authority(self) -> bool:
        return self.status == VALID


def evaluate_current_artifact(*, payload: Any, signature_hex: Any, stored_hash: Any, installation_uuid: str,
                              state_license_id: str, trust_set: Mapping[str, str]) -> Reverification:
    """Clasifica el artefacto vigente. Orden: integridad y vínculo → `kid` firmado → clave EXACTA del
    conjunto actual → firma → contrato → identidad. Nunca prueba otras claves."""
    if not isinstance(payload, Mapping) or not isinstance(signature_hex, str):
        return Reverification(MALFORMED_ARTIFACT, "artifact_unreadable", state_license_id)
    carga = dict(payload)
    license_id = carga.get("license_id") if isinstance(carga.get("license_id"), str) else None
    kid = carga.get("kid") if isinstance(carga.get("kid"), str) else None
    try:
        huella = payload_hash(carga)
    except (TypeError, ValueError):
        return Reverification(MALFORMED_ARTIFACT, "payload_not_canonicalizable", license_id, kid)
    if stored_hash != huella:
        return Reverification(ARTIFACT_STATE_MISMATCH, "payload_hash", license_id, kid)
    if license_id != state_license_id:
        return Reverification(ARTIFACT_STATE_MISMATCH, "license_id", license_id, kid)
    try:
        clave = trust_anchor.resolve_trusted_owner_key(carga.get("kid"), trust_set)
    except trust_anchor.TrustAnchorError as exc:
        return Reverification(KID_MISSING if exc.reason == "kid_missing" else KID_UNKNOWN, exc.reason, license_id, kid)
    if not verify_license_signature(carga, signature_hex, clave):
        return Reverification(SIGNATURE_INVALID, "owner_signature", license_id, kid)
    try:
        datos = parse_license_payload(carga)
    except (LicenseContractError, KeyError, ValueError, TypeError) as exc:
        return Reverification(MALFORMED_ARTIFACT, getattr(exc, "code", type(exc).__name__), license_id, kid)
    if datos.installation_id != installation_uuid:
        return Reverification(INSTALLATION_MISMATCH, "installation_id", license_id, kid)
    return Reverification(VALID, "ok", license_id, kid)
