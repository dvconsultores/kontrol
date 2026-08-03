"""Servicio de licenciamiento local (FR-001-002/003/050/051/052/053/054/055).

- Genera y persiste la identidad de instalación (uuid + par Ed25519).
- Importa y verifica licencias firmadas.
- Calcula y aplica el modo de acceso con fecha confiable.
- Registra eventos locales inmutables.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import license as license_engine
from app.core.config import get_settings
from app.core.errors import KontrolError, NotFoundError
from app.modules.licensing.models import (
    LicenseArtifact,
    LicenseEvent,
    LicenseRenewalRequest,
    LicenseState,
)
from app.modules.organization.models import Installation


def _now() -> datetime:
    return datetime.now(UTC)


def _private_key_path() -> str:
    settings = get_settings()
    return os.path.join(settings.installation_volume_path, "installation_private_key.pem")


# --------------------------------------------------------------------------- #
# Identidad de instalación
# --------------------------------------------------------------------------- #
def get_or_create_installation(db: Session) -> Installation:
    """Recupera o crea la identidad persistente de la instalación (FR-001-002/003)."""
    existing = db.execute(select(Installation).limit(1)).scalars().first()
    if existing:
        return existing

    # Generar identidad nueva
    installation_uuid = f"KTL-VE-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}"
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Persistir la clave privada local en el volumen protegido (nunca se envía).
    # Se crea con permisos 0600 de forma atómica.
    os.makedirs(get_settings().installation_volume_path, exist_ok=True)
    key_path = _private_key_path()
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(private_pem.decode("utf-8"))

    installation = Installation(
        installation_uuid=installation_uuid,
        public_key=public_pem.decode("utf-8"),
        state="PENDING",
        key_reference=key_path,
    )
    db.add(installation)
    db.commit()
    db.refresh(installation)
    return installation


def get_installation(db: Session) -> Installation:
    installation = db.execute(select(Installation).limit(1)).scalars().first()
    if not installation:
        raise NotFoundError(code="INSTALLATION_NOT_FOUND", message="No existe identidad de instalación")
    return installation


def installation_request_payload(installation: Installation) -> dict[str, Any]:
    """Solicitud de activación (cliente, instalación, clave pública, versión)."""
    settings = get_settings()
    return {
        "installation_id": installation.installation_uuid,
        "public_key": installation.public_key,
        "version": settings.app_version,
        "nonce": uuid.uuid4().hex,
        "requested_at": _now().isoformat(),
    }


# --------------------------------------------------------------------------- #
# Importación y verificación de licencia
# --------------------------------------------------------------------------- #
def _payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def import_license(
    db: Session,
    *,
    payload: dict[str, Any],
    signature_hex: str,
    source: str = "MANUAL",
    user_id: str | None = None,
) -> LicenseState:
    """Importa y verifica una licencia firmada (FR-001-050/051/054).

    Flujo: verificar firma con clave pública → validar installation_id →
    calcular modo → persistir estado, artefacto y evento.
    """
    installation = get_installation(db)

    # 1) Verificar firma (Ed25519) con la clave pública distribuida.
    public_key_pem = get_settings().license_public_key_pem or installation.public_key
    if not public_key_pem or not license_engine.verify_license_signature(payload, signature_hex, public_key_pem):
        _record_event(db, installation, "LICENSE_SIGNATURE_INVALID", {"license_id": payload.get("license_id")}, user_id)
        db.commit()
        raise KontrolError(
            code="LICENSE_SIGNATURE_INVALID",
            message="La licencia no es válida o su firma no pudo verificarse.",
            status_code=423,
        )

    # 2) Validar installation_id (una licencia no sirve en otra instalación).
    if payload.get("installation_id") != installation.installation_uuid:
        _record_event(db, installation, "LICENSE_INSTALLATION_MISMATCH", {"license_id": payload.get("license_id")}, user_id)
        db.commit()
        raise KontrolError(
            code="LICENSE_INSTALLATION_MISMATCH",
            message="La licencia no corresponde a esta instalación.",
            status_code=423,
        )

    license_data = license_engine.parse_license_payload(payload)

    # 3) Calcular modo actual.
    state = db.execute(select(LicenseState).where(LicenseState.installation_id == installation.installation_uuid)).scalars().first()
    last_reliable = state.last_reliable_date if state else None
    mode = license_engine.compute_mode(license_data, _now(), last_reliable_date=last_reliable)

    # 4) Persistir artefacto y estado (versionado, sin sobrescribir historial).
    artifact = LicenseArtifact(
        license_id=license_data.license_id,
        payload=payload,
        signature_hex=signature_hex,
        payload_hash=_payload_hash(payload),
        kid=payload.get("kid"),
        imported_at=_now(),
    )
    db.add(artifact)

    if state is None:
        state = LicenseState(installation_id=installation.installation_uuid)
        db.add(state)
    state.license_id = license_data.license_id
    state.mode = mode
    state.period_start = license_data.period_start
    state.period_end = license_data.period_end
    state.critical_warning_start = license_data.critical_warning_start
    state.read_only_start = license_data.read_only_start
    state.entitlements = license_data.entitlements
    state.minimum_version = license_data.minimum_version
    state.kid = license_data.kid
    state.verified_at = _now()
    state.last_reliable_date = last_reliable or _now()

    installation.state = "ACTIVE"

    _record_event(db, installation, "LICENSE_IMPORTED", {"license_id": license_data.license_id, "mode": mode}, user_id)
    db.commit()
    db.refresh(state)
    return state


def _record_event(
    db: Session,
    installation: Installation,
    event_type: str,
    detail: dict[str, Any] | None,
    user_id: str | None,
) -> None:
    db.add(
        LicenseEvent(
            installation_id=installation.installation_uuid,
            event_type=event_type,
            detail=detail,
            user_id=user_id,
        )
    )


# --------------------------------------------------------------------------- #
# Estado y modo actual
# --------------------------------------------------------------------------- #
def get_status(db: Session) -> dict[str, Any]:
    installation = get_installation(db)
    state = db.execute(select(LicenseState).where(LicenseState.installation_id == installation.installation_uuid)).scalars().first()

    if state is None:
        return {
            "installation_id": installation.installation_uuid,
            "activated": False,
            "mode": "PENDING",
            "period_start": None,
            "period_end": None,
            "read_only_start": None,
            "entitlements": {},
            "minimum_version": None,
            "license_url": "/mi-licencia",
        }

    mode = license_engine.compute_mode(
        license_engine.LicenseData(
            license_id=state.license_id,
            installation_id=installation.installation_uuid,
            customer_id="",
            contract_id="",
            company_tax_id=None,
            period_start=state.period_start,
            period_end=state.period_end,
            critical_warning_start=state.critical_warning_start or state.period_end,
            read_only_start=state.read_only_start or state.period_end,
            entitlements=state.entitlements,
            minimum_version=state.minimum_version,
            kid=state.kid,
        ),
        _now(),
        last_reliable_date=state.last_reliable_date,
    )
    # Persistir el modo recalculado si cambió
    if mode != state.mode:
        state.mode = mode
        db.commit()

    return {
        "installation_id": installation.installation_uuid,
        "activated": True,
        "license_id": state.license_id,
        "mode": mode,
        "period_start": state.period_start.isoformat(),
        "period_end": state.period_end.isoformat(),
        "critical_warning_start": state.critical_warning_start.isoformat() if state.critical_warning_start else None,
        "read_only_start": state.read_only_start.isoformat() if state.read_only_start else None,
        "entitlements": state.entitlements,
        "minimum_version": state.minimum_version,
        "kid": state.kid,
        "license_url": "/mi-licencia",
    }


def current_mode(db: Session) -> str:
    """Modo actual para el middleware de licencia (FR-001-053)."""
    installation = db.execute(select(Installation).limit(1)).scalars().first()
    if not installation:
        return license_engine.SECURITY_SUSPENSION
    state = db.execute(select(LicenseState).where(LicenseState.installation_id == installation.installation_uuid)).scalars().first()
    if state is None:
        return "PENDING"
    return get_status(db)["mode"]


def create_renewal_request(
    db: Session,
    *,
    payment_proof_ref: str | None,
    notes: str | None,
    user_id: str | None,
) -> LicenseRenewalRequest:
    installation = get_installation(db)
    request = LicenseRenewalRequest(
        installation_id=installation.installation_uuid,
        payment_proof_ref=payment_proof_ref,
        status="REPORTED",
        notes=notes,
        created_by=user_id,
    )
    db.add(request)
    _record_event(db, installation, "LICENSE_RENEWAL_REQUESTED", {"request_id": str(request.id)}, user_id)
    db.commit()
    db.refresh(request)
    return request


def get_history(db: Session) -> list[dict[str, Any]]:
    installation = get_installation(db)
    events = db.execute(select(LicenseEvent).where(LicenseEvent.installation_id == installation.installation_uuid).order_by(LicenseEvent.created_at.desc())).scalars().all()
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "detail": e.detail,
            "source": e.source,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]
