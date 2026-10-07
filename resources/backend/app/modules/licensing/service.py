"""Servicio de licenciamiento local y central (FR-001-002/003/050..056, 010).

- Genera y persiste la identidad de instalación (uuid + par Ed25519).
- Importa y verifica licencias firmadas.
- Calcula y aplica el modo de acceso con fecha confiable.
- Registra eventos locales inmutables.
- Licenciamiento central (010): configuración, sincronización (contrato v1),
  entitlements por módulo, renovación con comprobante, modos y auditoría.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core import license as license_engine
from app.core import trust_anchor
from app.core.config import get_settings
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.licensing.models import (
    LicenseArtifact,
    LicenseCentralConfig,
    LicenseEntitlementSnapshot,
    LicenseEvent,
    LicenseRenewalRequest,
    LicenseState,
    LicenseSyncRun,
)
from app.modules.organization.models import Installation

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _private_key_path() -> str:
    settings = get_settings()
    return os.path.join(settings.installation_volume_path, "installation_private_key.pem")


# --------------------------------------------------------------------------- #
# Identidad de instalación
# --------------------------------------------------------------------------- #
#: Clave del bloqueo consultivo que pone en fila el alta de la instalación
#: («KONTROL» + 01). Constante a propósito: todas las réplicas del backend contra
#: la misma base compiten por el mismo bloqueo.
_BLOQUEO_ALTA_INSTALACION = 0x4B4F4E54524F4C01


def _instalacion_canonica(db: Session) -> Installation | None:
    """La instalación, con orden determinista.

    FR-001-002 dice que hay **una**. Si una base heredada tuviera dos —las que
    dejaba la carrera que este delta corrige—, `limit(1)` sin orden devolvía una u
    otra según el plan de PostgreSQL, y con ella cambiaba contra qué identidad se
    validaba una licencia. Manda la más antigua.
    """
    return db.execute(
        select(Installation).order_by(Installation.created_at, Installation.id).limit(1)
    ).scalars().first()


def _bloquear_alta_de_instalacion(db: Session) -> None:
    """Bloqueo consultivo de transacción: se libera al confirmar.

    Solo existe en PostgreSQL, que es el motor de producción y de toda prueba de
    integración (P21).
    """
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:clave)"), {"clave": _BLOQUEO_ALTA_INSTALACION})


def get_or_create_installation(db: Session) -> Installation:
    """Recupera o crea la identidad persistente de la instalación (FR-001-002/003)."""
    existing = _instalacion_canonica(db)
    if existing:
        return existing

    # Dos peticiones simultáneas contra una instalación recién desplegada pasaban
    # las dos por aquí. Como el UUID es aleatorio, no chocaban en ningún índice:
    # se creaban **dos** instalaciones y la segunda sobrescribía el fichero de
    # clave privada de la primera. El bloqueo las pone en fila, y quien llega
    # segunda relee: si la otra ya la creó, devuelve esa y no escribe nada.
    _bloquear_alta_de_instalacion(db)
    existing = _instalacion_canonica(db)  # relectura bajo el bloqueo
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
    installation = _instalacion_canonica(db)
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
    return license_engine.payload_hash(payload)


def _utc(dt: datetime) -> datetime:
    """Un instante con zona, expresado en UTC; uno sin zona se deja como está."""
    return dt.astimezone(UTC) if dt.tzinfo is not None else dt


_MENSAJES_DE_REEMISION = {
    license_engine.LEGACY_REISSUE_REQUIRES_REVISION: "Ya hay una licencia vigente de este período sin número de emisión; otra licencia distinta del mismo período solo puede sustituirla con una revisión del emisor.",
    license_engine.LEGACY_AFTER_REVISION: "La licencia vigente de este período lleva número de emisión; una licencia sin revisión del mismo período no puede sustituirla.",
    license_engine.REVISION_DOWNGRADE: "La licencia tiene un número de emisión anterior al vigente para este período y no puede sustituirlo.",
    license_engine.REVISION_CONFLICT: "La licencia repite el número de emisión vigente con un contenido distinto; no se aplica.",
}


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

    # 1) El ancla de confianza es la clave pública del propietario, configurada fuera de la
    #    instalación; nunca la clave de la propia instalación (FR-010-148/149). Sin ancla, o con
    #    una que no sirve, se falla cerrado antes de mirar el artefacto: no es un artefacto malo,
    #    es una instalación que no puede verificar nada, y no se anota como evento de licencia.
    public_key_pem = get_settings().license_public_key_pem
    try:
        trust_anchor.load_trust_anchor(public_key_pem)
    except trust_anchor.TrustAnchorError as exc:
        logger.warning("licencia: ancla de confianza del propietario %s; importación rechazada", exc.reason)
        raise KontrolError(
            code=f"LICENSE_TRUST_ANCHOR_{exc.reason.upper()}",
            message="La instalación no tiene configurada una clave pública válida del propietario; no se puede verificar la licencia.",
            status_code=503,
        ) from None
    assert public_key_pem is not None  # lo garantiza el ancla cargada

    # 2) Verificar firma (Ed25519) contra el ancla.
    if not license_engine.verify_license_signature(payload, signature_hex, public_key_pem):
        _record_event(db, installation, "LICENSE_SIGNATURE_INVALID", {"license_id": payload.get("license_id")}, user_id)
        db.commit()
        raise KontrolError(
            code="LICENSE_SIGNATURE_INVALID",
            message="La licencia no es válida o su firma no pudo verificarse.",
            status_code=423,
        )

    # 3) Validar installation_id (una licencia no sirve en otra instalación).
    if payload.get("installation_id") != installation.installation_uuid:
        _record_event(db, installation, "LICENSE_INSTALLATION_MISMATCH", {"license_id": payload.get("license_id")}, user_id)
        db.commit()
        raise KontrolError(
            code="LICENSE_INSTALLATION_MISMATCH",
            message="La licencia no corresponde a esta instalación.",
            status_code=423,
        )

    try:
        license_data = license_engine.parse_license_payload(payload)
    except license_engine.LicenseContractError as exc:
        # Firmado por el propietario pero fuera del contrato (p. ej. `revision` que no es un
        # entero ≥ 1): error del emisor, se rechaza cerrado y sin tocar nada (Spec 004 · Autoridad Central).
        raise KontrolError(code=exc.code, message=str(exc), status_code=423) from None

    # 4) Serializar: la fila de la instalación existe siempre (también antes de la primera
    #    licencia), así que es ella la que se bloquea; después se lee el estado vigente BAJO el
    #    bloqueo, nunca el leído antes. Dos importaciones concurrentes pasan de una en una y la
    #    segunda compara contra lo que la primera dejó (FR-010-210..212; LICENCIA-IMPORT-SIN-BLOQUEO).
    #    En SQLite `with_for_update` no hace nada: la autoridad de concurrencia es PostgreSQL.
    db.execute(select(Installation).where(Installation.id == installation.id).with_for_update()).scalars().one()
    state = db.execute(
        select(LicenseState).where(LicenseState.installation_id == installation.installation_uuid).with_for_update()
    ).scalars().first()

    # 5) Anti-retroceso por período (Fase A, FR-010-200..209): una licencia de período anterior al
    #    vigente no lo sustituye; posterior, sí; el mismo período se acepta como reemisión (§7.1,
    #    riesgo residual LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN). Antes de persistir nada.
    if state is not None:
        orden = license_engine.compare_period(state.period_start, state.period_end, license_data.period_start, license_data.period_end)
        if orden in (license_engine.OLDER_PERIOD, license_engine.INCOMPARABLE_PERIOD):
            _record_event(
                db, installation, "LICENSE_PERIOD_DOWNGRADE_REJECTED",
                {"license_id": license_data.license_id, "current_license_id": state.license_id,
                 "current_period_end": state.period_end.isoformat(), "incoming_period_end": license_data.period_end.isoformat(),
                 "outcome": orden},
                user_id,
            )
            db.commit()
            raise KontrolError(
                code="LICENSE_PERIOD_DOWNGRADE" if orden == license_engine.OLDER_PERIOD else "LICENSE_PERIOD_CONFLICT",
                message=(
                    "La licencia corresponde a un período anterior al vigente y no puede sustituirlo."
                    if orden == license_engine.OLDER_PERIOD
                    else "El período de la licencia no es comparable con el vigente; no se aplica."
                ),
                status_code=423,
            )
        if orden == license_engine.SAME_PERIOD:
            # 5b) Mismo período: ordena la `revision` firmada que asignó el emisor, bajo el MISMO
            #     bloqueo (FR-010-322..348). El vigente es el último artefacto aceptado de la licencia
            #     vigente; cada importación aceptada inserta uno. El cliente no asigna ni corrige
            #     revisiones: solo valida y compara. Legacy es claim ausente, nunca 0 ni `null`.
            vigente = db.execute(
                select(LicenseArtifact)
                .where(LicenseArtifact.license_id == state.license_id)
                .order_by(LicenseArtifact.imported_at.desc(), LicenseArtifact.created_at.desc())
            ).scalars().first()
            try:
                revision_vigente = license_engine.parse_revision(vigente.payload) if vigente is not None else None
            except license_engine.LicenseContractError:
                # El artefacto guardado no cumple el contrato: no se ordena contra él, se rechaza cerrado.
                _record_event(db, installation, "LICENSE_REISSUE_REJECTED",
                              {"license_id": license_data.license_id, "current_license_id": state.license_id,
                               "outcome": "CURRENT_ARTIFACT_INVALID"}, user_id)
                db.commit()
                raise KontrolError(code="LICENSE_CURRENT_ARTIFACT_INVALID",
                                   message="El artefacto de la licencia vigente no cumple el contrato; no se puede ordenar la reemisión.",
                                   status_code=423) from None
            resultado = license_engine.resolve_same_period_reissue(
                current_revision=revision_vigente, current_payload_hash=vigente.payload_hash if vigente is not None else None,
                incoming_revision=license_data.revision, incoming_payload_hash=_payload_hash(payload),
            )
            if resultado in license_engine.REISSUE_REJECTIONS:
                _record_event(
                    db, installation, "LICENSE_REISSUE_REJECTED",
                    {"license_id": license_data.license_id, "current_license_id": state.license_id,
                     "current_revision": revision_vigente, "incoming_revision": license_data.revision, "outcome": resultado},
                    user_id,
                )
                db.commit()
                raise KontrolError(code=f"LICENSE_{resultado}", message=_MENSAJES_DE_REEMISION[resultado], status_code=423)

    # 6) Calcular modo actual.
    last_reliable = state.last_reliable_date if state else None
    mode = license_engine.compute_mode(license_data, _now(), last_reliable_date=last_reliable)

    # 7) Persistir artefacto y estado (versionado, sin sobrescribir historial).
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
    # Los instantes firmados, normalizados a UTC: el instante no cambia, pero SQLite guarda la hora de
    # pared y pierde el desplazamiento, con lo que un período leído de vuelta quedaba 4 h corrido y la
    # reemisión del mismo período se ordenaba como posterior. PostgreSQL (`timestamptz`) ya conservaba
    # el instante; así los dos motores comparan lo mismo (FR-010-323).
    state.period_start = _utc(license_data.period_start)
    state.period_end = _utc(license_data.period_end)
    state.critical_warning_start = _utc(license_data.critical_warning_start)
    state.read_only_start = _utc(license_data.read_only_start)
    state.entitlements = license_data.entitlements
    state.minimum_version = license_data.minimum_version
    state.kid = license_data.kid
    state.verified_at = _now()
    state.last_reliable_date = last_reliable or _now()

    installation.state = "ACTIVE"

    _record_event(db, installation, "LICENSE_IMPORTED", {"license_id": license_data.license_id, "mode": mode, "revision": license_data.revision}, user_id)
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
    installation = _instalacion_canonica(db)
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


# =========================================================================== #
# Licenciamiento central (010)
# =========================================================================== #
# Módulos habilitables por entitlement (002-009). El orden es la matriz vigente.
ENTITLED_MODULES: list[str] = [
    "ventas",
    "compras",
    "inventario",
    "tesoreria",
    "fiscal",
    "regulatorio",
    "reportes",
]

# Máquina de estados de modos para transición manual (FR-010-030).
# READ_ONLY / SECURITY_SUSPENSION son terminales: solo se sale re-importando o
# re-sincronizando una licencia válida (autoridad central).
MODE_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"FULL_ACCESS", "RENEWAL_NOTICE", "READ_ONLY", "SECURITY_SUSPENSION"},
    "FULL_ACCESS": {"RENEWAL_NOTICE", "READ_ONLY", "SECURITY_SUSPENSION"},
    "RENEWAL_NOTICE": {"CRITICAL_RENEWAL_NOTICE", "READ_ONLY", "SECURITY_SUSPENSION"},
    "CRITICAL_RENEWAL_NOTICE": {"READ_ONLY", "SECURITY_SUSPENSION"},
    "READ_ONLY": set(),
    "SECURITY_SUSPENSION": set(),
}

RENEWAL_TRANSITIONS: dict[str, set[str]] = {
    "REPORTED": {"VERIFIED", "REJECTED"},
    "VERIFIED": {"ISSUED", "REJECTED"},
    "ISSUED": set(),
    "REJECTED": set(),
}

MODES = {
    "FULL_ACCESS",
    "RENEWAL_NOTICE",
    "CRITICAL_RENEWAL_NOTICE",
    "READ_ONLY",
    "SECURITY_SUSPENSION",
}


def _dt_from(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def default_sync_client(request_payload: dict[str, Any], server_url: str) -> dict[str, Any]:
    """Cliente HTTP del contrato v1 (POST /v1/license/sync) (FR-010-002).

    Inyectable en `sync_license` para pruebas (fake server); en producción se
    usa este cliente estándar contra el servidor central configurado.
    """
    import json as _json
    import urllib.request as _url

    data = _json.dumps(request_payload).encode("utf-8")
    url = server_url.rstrip("/") + "/v1/license/sync"
    req = _url.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with _url.urlopen(req, timeout=15) as resp:
        return _json.loads(resp.read().decode("utf-8"))


# --------------------------------------------------------------------------- #
# Configuración del servidor central
# --------------------------------------------------------------------------- #
def get_central_config(db: Session) -> dict[str, Any] | None:
    installation = get_installation(db)
    row = db.execute(
        select(LicenseCentralConfig).where(LicenseCentralConfig.installation_id == installation.installation_uuid)
    ).scalars().first()
    if row is None:
        return None
    return {
        "id": str(row.id),
        "server_url": row.server_url,
        "public_key": row.public_key,
        "sync_policy": row.sync_policy or {},
        "grace_days": row.grace_days,
        "enabled": bool(row.enabled),
        "status": row.status,
        "updated_at": row.updated_at.isoformat(),
    }


def upsert_central_config(
    db: Session,
    *,
    server_url: str,
    public_key: str | None,
    sync_policy: dict[str, Any],
    grace_days: int,
    enabled: bool,
    actor: str | None,
) -> dict[str, Any]:
    """Persiste (crea o actualiza) la configuración central (FR-010-001)."""
    installation = get_installation(db)
    row = db.execute(
        select(LicenseCentralConfig).where(LicenseCentralConfig.installation_id == installation.installation_uuid)
    ).scalars().first()
    if row is None:
        row = LicenseCentralConfig(installation_id=installation.installation_uuid)
        db.add(row)
    row.server_url = server_url.strip().rstrip("/")
    row.public_key = public_key
    row.sync_policy = sync_policy or {}
    row.grace_days = max(1, min(int(grace_days), 365))
    row.enabled = bool(enabled)
    _record_event(db, installation, "LICENSE_CENTRAL_CONFIGURED", {"server_url": row.server_url}, actor)
    db.commit()
    db.refresh(row)
    return {
        "id": str(row.id),
        "server_url": row.server_url,
        "public_key": row.public_key,
        "sync_policy": row.sync_policy,
        "grace_days": row.grace_days,
        "enabled": bool(row.enabled),
        "status": row.status,
    }


def _central_config_row(db: Session) -> LicenseCentralConfig:
    installation = get_installation(db)
    row = db.execute(
        select(LicenseCentralConfig).where(LicenseCentralConfig.installation_id == installation.installation_uuid)
    ).scalars().first()
    if row is None or not row.server_url:
        raise KontrolError(
            code="CENTRAL_NOT_CONFIGURED",
            message="El licenciamiento central no está configurado.",
            status_code=422,
        )
    return row


# --------------------------------------------------------------------------- #
# Sincronización con el servidor central (contrato v1)
# --------------------------------------------------------------------------- #
def sync_license(
    db: Session,
    *,
    sync_client: Callable[[dict[str, Any], str], dict[str, Any]] | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    """Sincroniza la licencia con el servidor central (FR-010-002/003/010).

    Idempotente por día: si la misma sincronización ya tuvo éxito, devuelve el
    resultado previo sin repetir el llamado. Registra `license_sync_runs`,
    actualiza `last_reliable_date` (reloj confiable), aplica entitlements y
    genera un snapshot versionado.
    """
    installation = get_installation(db)
    config = _central_config_row(db)

    state = db.execute(
        select(LicenseState).where(LicenseState.installation_id == installation.installation_uuid)
    ).scalars().first()

    license_jws = ""
    if state is not None:
        artifact = db.execute(
            select(LicenseArtifact)
            .where(LicenseArtifact.license_id == state.license_id)
            .order_by(LicenseArtifact.imported_at.desc())
        ).scalars().first()
        if artifact is not None:
            license_jws = json.dumps(artifact.payload, ensure_ascii=False)

    request_payload: dict[str, Any] = {
        "version": "1.0",
        "installation_id": installation.installation_uuid,
        "license_jws": license_jws,
        "modules": list(ENTITLED_MODULES),
        "requested_at": _now().isoformat(),
    }
    # Clave de idempotencia estable: no incluye campos volátiles (requested_at).
    idem_source = {
        "installation_id": installation.installation_uuid,
        "license_jws": license_jws,
        "modules": list(ENTITLED_MODULES),
    }
    idem = hashlib.sha256(
        (json.dumps(idem_source, sort_keys=True, ensure_ascii=False) + _now().strftime("%Y%m%d")).encode("utf-8")
    ).hexdigest()

    # Idempotencia: mismo payload y mismo día ya sincronizado con éxito.
    previous = db.execute(
        select(LicenseSyncRun).where(
            LicenseSyncRun.idempotency_key == idem,
            LicenseSyncRun.status == "SUCCESS",
        )
    ).scalars().first()
    if previous is not None:
        return {"id": str(previous.id), "status": "SUCCESS", "idempotent": True, "response": previous.response}

    client = sync_client or default_sync_client
    try:
        response = client(request_payload, config.server_url)
    except Exception as exc:  # noqa: BLE001 - el cliente externo puede lanzar cualquier cosa
        run = LicenseSyncRun(
            installation_id=installation.installation_uuid,
            status="FAILED",
            request=request_payload,
            error=str(exc),
            idempotency_key=idem,
            ran_at=_now(),
        )
        db.add(run)
        config.status = "DISCONNECTED"
        _record_event(db, installation, "LICENSE_SYNC_FAILED", {"error": str(exc)}, actor)
        db.commit()
        raise KontrolError(
            code="CENTRAL_UNREACHABLE",
            message="No se pudo contactar el servidor central de licencias.",
            status_code=503,
        ) from exc

    run = LicenseSyncRun(
        installation_id=installation.installation_uuid,
        status="SUCCESS",
        request=request_payload,
        response=response,
        idempotency_key=idem,
        ran_at=_now(),
    )
    db.add(run)

    server_status = response.get("status")
    server_time = response.get("server_time")
    entitlements = response.get("entitlements", {})

    if state is not None:
        if server_time:
            state.last_reliable_date = _dt_from(server_time)
        if entitlements:
            state.entitlements = {**(state.entitlements or {}), "modules": list(entitlements.keys())}
        if server_status in MODES:
            state.mode = server_status
        state.verified_at = _now()

    snapshot = LicenseEntitlementSnapshot(
        installation_id=installation.installation_uuid,
        modules=entitlements or {},
        version=str(response.get("version", "v1")),
        taken_at=_now(),
    )
    db.add(snapshot)
    config.status = "CONNECTED"
    _record_event(
        db,
        installation,
        "LICENSE_SYNCED",
        {"status": server_status, "expires_at": response.get("expires_at")},
        actor,
    )
    db.commit()
    return {"id": str(run.id), "status": "SUCCESS", "idempotent": False, "response": response}


def list_sync_runs(db: Session) -> list[dict[str, Any]]:
    installation = get_installation(db)
    rows = db.execute(
        select(LicenseSyncRun)
        .where(LicenseSyncRun.installation_id == installation.installation_uuid)
        .order_by(LicenseSyncRun.ran_at.desc())
    ).scalars().all()
    return [
        {
            "id": str(r.id),
            "status": r.status,
            "request": r.request,
            "response": r.response,
            "error": r.error,
            "ran_at": r.ran_at.isoformat(),
        }
        for r in rows
    ]


# --------------------------------------------------------------------------- #
# Entitlements por módulo
# --------------------------------------------------------------------------- #
def list_entitlement_snapshots(db: Session) -> list[dict[str, Any]]:
    installation = get_installation(db)
    rows = db.execute(
        select(LicenseEntitlementSnapshot)
        .where(LicenseEntitlementSnapshot.installation_id == installation.installation_uuid)
        .order_by(LicenseEntitlementSnapshot.taken_at.desc())
    ).scalars().all()
    return [
        {
            "id": str(s.id),
            "modules": s.modules or {},
            "version": s.version,
            "taken_at": s.taken_at.isoformat(),
        }
        for s in rows
    ]


def current_entitlements(db: Session) -> dict[str, Any]:
    """Matriz vigente de entitlements por módulo (002-009) (FR-010-010/011)."""
    installation = get_installation(db)
    state = db.execute(
        select(LicenseState).where(LicenseState.installation_id == installation.installation_uuid)
    ).scalars().first()

    local_modules: list[str] = []
    if state is not None:
        raw = (state.entitlements or {}).get("modules", [])
        if isinstance(raw, list):
            local_modules = [str(m) for m in raw]
        elif isinstance(raw, dict):
            local_modules = [k for k, v in raw.items() if v]

    snapshot = db.execute(
        select(LicenseEntitlementSnapshot)
        .where(LicenseEntitlementSnapshot.installation_id == installation.installation_uuid)
        .order_by(LicenseEntitlementSnapshot.taken_at.desc())
    ).scalars().first()

    server_modules: dict[str, Any] = snapshot.modules if snapshot else {}

    matrix: dict[str, Any] = {}
    for module in ENTITLED_MODULES:
        if module in server_modules:
            matrix[module] = bool(server_modules[module])
        else:
            matrix[module] = module in local_modules

    return {
        "modules": matrix,
        "version": snapshot.version if snapshot else "local",
        "taken_at": snapshot.taken_at.isoformat() if snapshot else None,
    }


def module_entitled(db: Session, module: str) -> bool:
    """Consulta backend de entitlement de un módulo (denegación por defecto)."""
    matrix = current_entitlements(db)["modules"]
    return bool(matrix.get(module, False))


# --------------------------------------------------------------------------- #
# Tolerancia offline (reloj confiable)
# --------------------------------------------------------------------------- #
def verify_offline(db: Session) -> dict[str, Any]:
    """Verifica la licencia sin conexión dentro de la gracia (FR-010-003)."""
    installation = get_installation(db)
    state = db.execute(
        select(LicenseState).where(LicenseState.installation_id == installation.installation_uuid)
    ).scalars().first()
    config = db.execute(
        select(LicenseCentralConfig).where(LicenseCentralConfig.installation_id == installation.installation_uuid)
    ).scalars().first()
    grace_days = config.grace_days if config is not None else 7

    if state is None or state.last_reliable_date is None:
        return {"offline_valid": False, "reason": "NO_RELIABLE_DATE", "grace_days": grace_days, "grace_days_left": 0}

    now = _now()
    last = state.last_reliable_date
    grace_end = last + timedelta(days=grace_days)
    if now > grace_end:
        return {
            "offline_valid": False,
            "reason": "GRACE_EXPIRED",
            "grace_days": grace_days,
            "grace_days_left": 0,
            "grace_end": grace_end.isoformat(),
            "last_reliable_date": last.isoformat(),
        }
    return {
        "offline_valid": True,
        "reason": "WITHIN_GRACE",
        "grace_days": grace_days,
        "grace_days_left": (grace_end - now).days,
        "grace_end": grace_end.isoformat(),
        "last_reliable_date": last.isoformat(),
    }


# --------------------------------------------------------------------------- #
# Renovación central con comprobante
# --------------------------------------------------------------------------- #
def list_renewal_requests(db: Session) -> list[dict[str, Any]]:
    installation = get_installation(db)
    rows = db.execute(
        select(LicenseRenewalRequest)
        .where(LicenseRenewalRequest.installation_id == installation.installation_uuid)
        .order_by(LicenseRenewalRequest.created_at.desc())
    ).scalars().all()
    return [
        {
            "id": str(r.id),
            "payment_proof_ref": r.payment_proof_ref,
            "status": r.status,
            "notes": r.notes,
            "created_by": r.created_by,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


def transition_renewal(
    db: Session,
    *,
    request_id: str,
    target: str,
    actor: str | None,
) -> dict[str, Any]:
    """Transición del workflow de renovación (FR-010-021).

    REPORTED → VERIFIED → ISSUED / REJECTED. Solo el proveedor emite (ISSUED).
    """
    installation = get_installation(db)
    req = db.get(LicenseRenewalRequest, request_id)
    if req is None or req.installation_id != installation.installation_uuid:
        raise NotFoundError(code="RENEWAL_NOT_FOUND", message="Solicitud de renovación no encontrada")
    if target not in RENEWAL_TRANSITIONS.get(req.status, set()):
        raise ConflictError(
            code="INVALID_STATE_TRANSITION",
            message=f"No se permite pasar la renovación de {req.status} a {target}.",
        )
    req.status = target
    _record_event(db, installation, f"LICENSE_RENEWAL_{target}", {"request_id": request_id}, actor)
    db.commit()
    db.refresh(req)
    return {
        "id": str(req.id),
        "payment_proof_ref": req.payment_proof_ref,
        "status": req.status,
        "notes": req.notes,
    }


# --------------------------------------------------------------------------- #
# Modos de operación y auditoría
# --------------------------------------------------------------------------- #
def transition_mode(db: Session, *, target: str, actor: str | None) -> dict[str, Any]:
    """Transición manual de modo (FR-010-030).

    Valida la máquina de estados; registra el evento de cambio de modo.
    READ_ONLY/SECURITY_SUSPENSION refuerzan el bloqueo de escrituras.
    """
    installation = get_installation(db)
    state = db.execute(
        select(LicenseState).where(LicenseState.installation_id == installation.installation_uuid)
    ).scalars().first()
    if state is None:
        raise NotFoundError(code="LICENSE_NOT_ACTIVATED", message="No existe una licencia activada")
    if target not in MODES:
        raise KontrolError(code="INVALID_MODE", message=f"Modo no válido: {target}", status_code=422)
    if target not in MODE_TRANSITIONS.get(state.mode, set()):
        raise ConflictError(
            code="INVALID_STATE_TRANSITION",
            message=f"No se permite pasar el modo de {state.mode} a {target}.",
        )
    previous = state.mode
    state.mode = target
    _record_event(db, installation, "LICENSE_MODE_CHANGED", {"from": previous, "to": target}, actor)
    db.commit()
    db.refresh(state)
    return {"mode": state.mode, "from": previous, "to": target}


def central_overview(db: Session) -> dict[str, Any]:
    """Vista consolidada para el frontend (FR-010-101)."""
    status = get_status(db)
    config = get_central_config(db)
    entitlements = current_entitlements(db)
    offline = verify_offline(db)
    last_run = list_sync_runs(db)
    return {
        "status": status,
        "central_config": config,
        "entitlements": entitlements,
        "offline": offline,
        "last_sync": last_run[0] if last_run else None,
        "modules": list(ENTITLED_MODULES),
    }
