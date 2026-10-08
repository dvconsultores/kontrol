"""Reverificación del artefacto de licencia vigente: al arrancar y antes de cada autorización de
escritura (Spec 004 · `LICENCIA-ESTADO-SIN-REVERIFICAR`; DOC-07 §10.1, §14.5, §15.1, §16.2).

Qué se reverifica: el último artefacto aceptado de la licencia que el estado señala, contra el conjunto
de confianza ACTUAL (`kid` firmado → clave exacta → firma del propietario), su integridad (hash), su
vínculo con el estado y la identidad de la instalación. Qué no: no se reimporta, no se ordena, no se
toca el artefacto ni el historial, no se reconstruye el estado derivado. Un fallo deja al vigente sin
autoridad de escritura (`SECURITY_SUSPENSION`, modo existente y terminal: se sale reimportando o
sincronizando una licencia válida); sesión, lectura, importación y sync siguen disponibles. Puro,
barato (una firma Ed25519) e idempotente: se ejecuta en cada proceso y en cada petición de escritura,
y por eso no necesita caché ni estado compartido. Lo único que escribe es un evento de auditoría por
fallo distinto (sin material: ni artefacto, ni firma, ni claves).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import license_reverification as nucleo
from app.core import trust_anchor
from app.core.config import get_settings
from app.modules.licensing.models import LicenseArtifact, LicenseEvent, LicenseState
from app.modules.organization.models import Installation

logger = logging.getLogger(__name__)

EVENTO_FALLO = "LICENSE_STATE_REVERIFICATION_FAILED"
#: Resultado del arranque de ESTE proceso (solo informativo; la autoridad la da `reverificar_vigente` en cada petición).
ultimo_arranque: nucleo.Reverification | None = None


def artefacto_vigente(db: Session, state: LicenseState) -> LicenseArtifact | None:
    """El último artefacto aceptado de la licencia vigente (la misma regla que la reemisión por `revision`)."""
    return db.execute(
        select(LicenseArtifact)
        .where(LicenseArtifact.license_id == state.license_id)
        .order_by(LicenseArtifact.imported_at.desc(), LicenseArtifact.created_at.desc())
    ).scalars().first()


def reverificar_vigente(db: Session, installation: Installation, state: LicenseState | None) -> nucleo.Reverification:
    """Clasifica el vigente con la política de confianza de HOY y, si falla, lo deja anotado una vez."""
    if state is None:
        return nucleo.Reverification(nucleo.NO_CURRENT_LICENSE, "no_state")
    artefacto = artefacto_vigente(db, state)
    if artefacto is None:
        resultado = nucleo.Reverification(nucleo.ARTIFACT_STATE_MISMATCH, "artifact_missing", state.license_id, state.kid)
    else:
        ajustes = get_settings()
        try:
            confianza = trust_anchor.load_trust_set(
                trust_keys=ajustes.license_trust_keys, legacy_pem=ajustes.license_public_key_pem, legacy_kid=ajustes.license_public_key_kid)
        except trust_anchor.TrustAnchorError as exc:
            resultado = nucleo.Reverification(nucleo.TRUST_SET_INVALID, exc.reason, state.license_id, artefacto.kid)
        else:
            resultado = nucleo.evaluate_current_artifact(
                payload=artefacto.payload, signature_hex=artefacto.signature_hex, stored_hash=artefacto.payload_hash,
                installation_uuid=installation.installation_uuid, state_license_id=state.license_id, trust_set=confianza)
    if resultado.status in nucleo.FAILURES:
        _anotar_fallo(db, installation, resultado)
    return resultado


def _anotar_fallo(db: Session, installation: Installation, resultado: nucleo.Reverification) -> None:
    """Un evento por fallo distinto: reinicios repetidos con el mismo estado inválido no lo repiten."""
    detalle: dict[str, Any] = {"license_id": resultado.license_id, "kid": resultado.kid, "status": resultado.status, "reason": resultado.reason}
    ultimo = db.execute(
        select(LicenseEvent)
        .where(LicenseEvent.installation_id == installation.installation_uuid, LicenseEvent.event_type == EVENTO_FALLO)
        .order_by(LicenseEvent.created_at.desc(), LicenseEvent.id.desc())
    ).scalars().first()
    if ultimo is not None and ultimo.detail == detalle:
        return
    db.add(LicenseEvent(installation_id=installation.installation_uuid, event_type=EVENTO_FALLO, detail=detalle, user_id=None, source="SYSTEM"))
    db.commit()
    logger.warning("licencia: el artefacto vigente no supera la reverificación (%s: %s); escrituras suspendidas hasta importar o sincronizar una licencia válida",
                   resultado.status, resultado.reason)


def reverificar_al_arrancar(session_factory: Callable[[], Session]) -> nucleo.Reverification | None:
    """Una vez por proceso, antes de servir (DOC-07 §10.1, §14.5). Si la base no responde, no tumba el
    proceso: el gate por petición vuelve a decidir con la base disponible, y hasta entonces nada
    se autoriza desde un estado no verificado."""
    global ultimo_arranque
    from app.modules.licensing.service import _instalacion_canonica

    try:
        db = session_factory()
    except Exception as exc:  # noqa: BLE001 - sin base no hay reverificación posible; se anota y se reintenta por petición
        logger.warning("licencia: la reverificación de arranque no pudo abrir la base (%s)", type(exc).__name__)
        ultimo_arranque = None
        return None
    try:
        installation = _instalacion_canonica(db)
        if installation is None:
            ultimo_arranque = nucleo.Reverification(nucleo.NO_CURRENT_LICENSE, "no_installation")
            return ultimo_arranque
        state = db.execute(select(LicenseState).where(LicenseState.installation_id == installation.installation_uuid)).scalars().first()
        ultimo_arranque = reverificar_vigente(db, installation, state)
        logger.info("licencia: reverificación de arranque %s (%s)", ultimo_arranque.status, ultimo_arranque.reason)
        return ultimo_arranque
    except Exception as exc:  # noqa: BLE001 - ídem: la base puede no estar migrada aún en el primer arranque
        logger.warning("licencia: la reverificación de arranque no pudo ejecutarse (%s)", type(exc).__name__)
        ultimo_arranque = None
        return None
    finally:
        db.close()
