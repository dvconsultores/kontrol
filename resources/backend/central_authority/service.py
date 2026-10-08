"""Operaciones del propietario: registrar instalaciones y emitir licencias firmadas con `revision`.

La emisión entera es UNA transacción: se bloquea la fila de la instalación (existe siempre, también
antes de la primera licencia de un período), se obtiene o crea el linaje del período, se asigna
`last_revision + 1`, se construye el paquete, se firma, se anota en el libro, se actualiza el linaje
y se audita. Cualquier fallo deshace todo: el número nunca se consideró emitido (sin huecos por fallo;
nunca se reutiliza una `revision` que ya tenga un paquete en el libro: `UNIQUE(lineage_id, revision)`).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete as _sql_delete
from sqlalchemy import select
from sqlalchemy import update as _sql_update
from sqlalchemy.orm import Session

from app.core import license_contract as contract
from app.core import sync_auth_contract as sync_auth
from central_authority.config import Settings, SigningKeyError, active_signing_pem, load_signing_key
from central_authority.models import AuditEvent, Installation, Issuance, PeriodLineage, SyncChallenge

logger = logging.getLogger(__name__)

#: Hora civil del contrato (DOC-07 §5.1): Venezuela no tiene horario de verano.
CARACAS = timezone(timedelta(hours=-4))


class CentralError(Exception):
    """Error funcional de la autoridad, con código estable y mensaje sin material sensible."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class SyncAuthError(CentralError):
    """Rechazo del protocolo de sincronización: código estable, estado HTTP, nada del registro ni de la licencia."""

    def __init__(self, code: str, status_code: int, message: str) -> None:
        super().__init__(code, message)
        self.status_code = status_code


#: Etiqueta de atribución de lo que hace el propio protocolo (no es un operador humano).
OPERADOR_PROTOCOLO = "sync-protocol"


def _now() -> datetime:
    return datetime.now(UTC)


def periodo_anual(anio: int) -> tuple[datetime, datetime]:
    """El período anual del contrato: 1 de abril 00:00:00 → 31 de marzo 23:59:59 del año siguiente."""
    return (datetime(anio, 4, 1, 0, 0, 0, tzinfo=CARACAS), datetime(anio + 1, 3, 31, 23, 59, 59, tzinfo=CARACAS))


def hitos_del_periodo(period_start: datetime, period_end: datetime) -> tuple[datetime, datetime]:
    """Aviso crítico y solo lectura: 21 de abril y 1 de mayo tras un período anual del contrato; para
    un período que no sea el anual, veinte y treinta días después del fin."""
    anual = periodo_anual(period_start.astimezone(CARACAS).year)
    if (contract._as_utc(period_start), contract._as_utc(period_end)) == (contract._as_utc(anual[0]), contract._as_utc(anual[1])):
        fin = period_end.astimezone(CARACAS)
        return (datetime(fin.year, 4, 21, 0, 0, 0, tzinfo=CARACAS), datetime(fin.year, 5, 1, 0, 0, 0, tzinfo=CARACAS))
    return (period_end + timedelta(days=20), period_end + timedelta(days=30))


def _audit(db: Session, *, operation: str, operator: str, outcome: str, installation_uuid: str | None = None,
           period: tuple[datetime, datetime] | None = None, revision: int | None = None, issuance_id: str | None = None,
           detail: dict[str, Any] | None = None) -> None:
    db.add(AuditEvent(
        operation=operation, operator=operator, outcome=outcome, installation_uuid=installation_uuid,
        period_start=period[0] if period else None, period_end=period[1] if period else None,
        revision=revision, issuance_id=issuance_id, detail=detail,
    ))


# --------------------------------------------------------------------------- registro
def register_installation(db: Session, *, installation_uuid: str, public_key_pem: str, customer_id: str,
                          contract_id: str, company_tax_id: str | None, operator: str) -> Installation:
    """Alta idempotente: la misma identidad con los mismos datos devuelve el registro; con datos
    distintos no se sobrescribe nada (`INSTALLATION_CONFLICT`)."""
    if not installation_uuid.strip() or not operator.strip():
        raise CentralError("INVALID_ARGUMENT", "La identidad de la instalación y el operador son obligatorios.")
    try:
        contract.load_public_key(public_key_pem)
        huella = sync_auth.public_key_fingerprint(public_key_pem)
    except ValueError:
        raise CentralError("INVALID_PUBLIC_KEY", "La clave pública de la instalación no es una clave Ed25519 en PEM.") from None
    existente = db.execute(select(Installation).where(Installation.installation_uuid == installation_uuid)).scalars().first()
    if existente is not None:
        iguales = (existente.public_key_pem.strip(), existente.customer_id, existente.contract_id, existente.company_tax_id) == (
            public_key_pem.strip(), customer_id, contract_id, company_tax_id)
        _audit(db, operation="REGISTER_INSTALLATION", operator=operator, installation_uuid=installation_uuid,
               outcome="IDEMPOTENT" if iguales else "INSTALLATION_CONFLICT")
        db.commit()
        if not iguales:
            raise CentralError("INSTALLATION_CONFLICT", "La instalación ya está registrada con otros datos; no se sobrescribe.")
        return existente
    # Una clave de identidad pertenece a UNA instalación: la misma clave para otra identidad se rechaza (FR-010-367/372).
    otra = db.execute(select(Installation).where(Installation.public_key_fingerprint == huella)).scalars().first()
    if otra is not None:
        _audit(db, operation="REGISTER_INSTALLATION", operator=operator, installation_uuid=installation_uuid,
               outcome="INSTALLATION_KEY_ALREADY_BOUND")
        db.commit()
        raise CentralError("INSTALLATION_KEY_ALREADY_BOUND", "Esa clave pública ya está vinculada a otra instalación; no se vincula.")
    fila = Installation(installation_uuid=installation_uuid, public_key_pem=public_key_pem, public_key_fingerprint=huella,
                        customer_id=customer_id, contract_id=contract_id, company_tax_id=company_tax_id, registered_by=operator)
    db.add(fila)
    db.flush()
    _audit(db, operation="REGISTER_INSTALLATION", operator=operator, installation_uuid=installation_uuid, outcome="OK")
    db.commit()
    return fila


def get_installation(db: Session, installation_uuid: str) -> Installation:
    fila = db.execute(select(Installation).where(Installation.installation_uuid == installation_uuid)).scalars().first()
    if fila is None:
        # Sin listar otras instalaciones ni identificadores internos.
        raise CentralError("INSTALLATION_NOT_FOUND", "La instalación no está registrada en la autoridad.")
    return fila


# --------------------------------------------------------------------------- emisión
def _nuevo_license_id() -> str:
    return "LIC-" + uuid.uuid4().hex[:12].upper()


def issue_license(db: Session, *, settings: Settings, installation_uuid: str, period_start: datetime, period_end: datetime,
                  entitlements: dict[str, Any], minimum_version: str, operator: str) -> dict[str, Any]:
    """Emite (o reemite) la licencia de una instalación para un período: la siguiente `revision` del linaje.

    Devuelve el paquete firmado `{"payload", "signature_hex", "license_id", "revision"}`.
    """
    if not operator.strip():
        raise CentralError("INVALID_ARGUMENT", "El operador es obligatorio.")
    if contract._as_utc(period_end) <= contract._as_utc(period_start):
        raise CentralError("INVALID_PERIOD", "El período debe terminar después de empezar.")
    if not isinstance(entitlements, dict):
        raise CentralError("INVALID_ENTITLEMENTS", "Los derechos deben ser un objeto.")
    try:
        clave = load_signing_key(active_signing_pem(settings))  # la privada del `kid` activo, y solo esa (FR-010-450/451)
    except SigningKeyError as exc:
        logger.warning("autoridad: clave de firma del propietario %s; emisión rechazada", exc.reason)
        _audit(db, operation="ISSUE_LICENSE", operator=operator, installation_uuid=installation_uuid,
               period=(period_start, period_end), outcome=f"SIGNING_KEY_{exc.reason.upper()}")
        db.commit()
        raise CentralError(f"SIGNING_KEY_{exc.reason.upper()}", "La autoridad no tiene una clave de firma válida; no se emite.") from None

    try:
        # 1) Bloquear la instalación: serializa las emisiones de esta instalación, incluida la primera del período.
        inst = db.execute(
            select(Installation).where(Installation.installation_uuid == installation_uuid).with_for_update()
        ).scalars().first()
        if inst is None:
            raise CentralError("INSTALLATION_NOT_FOUND", "La instalación no está registrada en la autoridad.")
        # 2) El linaje del período, bajo el bloqueo.
        linaje = db.execute(
            select(PeriodLineage).where(
                PeriodLineage.installation_id == inst.id,
                PeriodLineage.period_start == period_start,
                PeriodLineage.period_end == period_end,
            ).with_for_update()
        ).scalars().first()
        if linaje is None:
            linaje = PeriodLineage(installation_id=inst.id, period_start=period_start, period_end=period_end, last_revision=0)
            db.add(linaje)
            db.flush()
        revision = linaje.last_revision + 1
        # 3) El paquete (DOC-07 §10.2 + `revision`), con los hitos del contrato.
        critico, solo_lectura = hitos_del_periodo(period_start, period_end)
        payload: dict[str, Any] = {
            "issuer": contract.ISSUER_NAME,
            "license_id": _nuevo_license_id(),
            "installation_id": inst.installation_uuid,
            "customer_id": inst.customer_id,
            "contract_id": inst.contract_id,
            "company_tax_id": inst.company_tax_id,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "critical_warning_start": critico.isoformat(),
            "read_only_start": solo_lectura.isoformat(),
            "entitlements": entitlements,
            "minimum_version": minimum_version,
            "kid": settings.signing_kid,
            "revision": revision,
        }
        contract.parse_license_payload(payload)  # el paquete cumple el contrato antes de firmarse
        firma = contract.sign_license_payload(payload, clave)
        # 4) Libro, linaje y auditoría; todo o nada.
        emision = Issuance(
            installation_id=inst.id, lineage_id=linaje.id, license_id=payload["license_id"], revision=revision,
            period_start=period_start, period_end=period_end, kid=settings.signing_kid, payload=payload,
            payload_hash=contract.payload_hash(payload), signature_hex=firma, issued_by=operator,
        )
        db.add(emision)
        linaje.last_revision = revision
        db.flush()
        _audit(db, operation="ISSUE_LICENSE", operator=operator, installation_uuid=inst.installation_uuid,
               period=(period_start, period_end), revision=revision, issuance_id=emision.id, outcome="OK",
               detail={"license_id": payload["license_id"], "kid": settings.signing_kid})
        db.commit()
    except Exception:
        db.rollback()
        raise
    logger.info("autoridad: emitida %s revision %s para la instalación %s", payload["license_id"], revision, inst.installation_uuid)
    return {"payload": payload, "signature_hex": firma, "license_id": payload["license_id"], "revision": revision}


# --------------------------------------------------------------------------- consulta
def _fila(e: Issuance) -> dict[str, Any]:
    return {
        "issuance_id": e.id, "license_id": e.license_id, "installation_id": e.payload.get("installation_id"),
        "revision": e.revision, "period_start": e.period_start.isoformat(), "period_end": e.period_end.isoformat(),
        "kid": e.kid, "payload": e.payload, "payload_hash": e.payload_hash, "signature_hex": e.signature_hex,
        "issued_at": e.issued_at.isoformat(), "issued_by": e.issued_by,
    }


def get_issuance(db: Session, license_id: str) -> dict[str, Any]:
    e = db.execute(select(Issuance).where(Issuance.license_id == license_id)).scalars().first()
    if e is None:
        raise CentralError("ISSUANCE_NOT_FOUND", "No existe esa emisión.")
    return _fila(e)


def list_issuances(db: Session, installation_uuid: str) -> list[dict[str, Any]]:
    inst = get_installation(db, installation_uuid)
    filas = db.execute(
        select(Issuance).where(Issuance.installation_id == inst.id).order_by(Issuance.period_start, Issuance.revision)
    ).scalars().all()
    return [_fila(e) for e in filas]


# --------------------------------------------------------------------------- sync autenticado (desafío-respuesta)
def create_sync_challenge(db: Session, *, settings: Settings, installation_uuid: Any) -> dict[str, Any]:
    """Un desafío nuevo: nonce aleatorio de 256 bits, caducidad corta del servidor, un solo uso.

    Responde igual para una instalación desconocida (la fila queda sin instalación y nunca autentica):
    el endpoint no enumera el registro. Devuelve solo lo necesario para construir la prueba.
    """
    if not isinstance(installation_uuid, str) or not installation_uuid.strip() or len(installation_uuid) > 64:
        raise SyncAuthError("SYNC_INSTALLATION_INVALID", 400, "La identidad de la instalación no es válida.")
    ahora = _now()
    # Limpieza perezosa y acotada: lo que venció hace más de una hora ya no puede volver a valer.
    db.execute(_sql_delete(SyncChallenge).where(SyncChallenge.expires_at < ahora - timedelta(hours=1)))
    inst = db.execute(select(Installation).where(Installation.installation_uuid == installation_uuid)).scalars().first()
    nonce = sync_auth.new_nonce()
    fila = SyncChallenge(installation_id=inst.id if inst is not None else None, nonce_sha256=sync_auth.nonce_digest(nonce),
                         protocol_version=sync_auth.PROTOCOL_VERSION, created_at=ahora,
                         expires_at=ahora + timedelta(seconds=settings.sync_challenge_ttl_seconds))
    db.add(fila)
    db.flush()
    _audit(db, operation="SYNC_CHALLENGE", operator=OPERADOR_PROTOCOLO, installation_uuid=inst.installation_uuid if inst else None,
           outcome="OK" if inst is not None else "UNKNOWN_INSTALLATION", detail={"challenge_id": fila.id})
    db.commit()
    return {"protocol_version": sync_auth.PROTOCOL_VERSION, "challenge_id": fila.id, "nonce": nonce,
            "expires_at": fila.expires_at.isoformat()}


def _rechazo_sync(db: Session, *, code: str, status_code: int, message: str, installation_uuid: str | None,
                  challenge_id: str | None) -> SyncAuthError:
    db.rollback()
    _audit(db, operation="SYNC", operator=OPERADOR_PROTOCOLO, installation_uuid=installation_uuid, outcome=code,
           detail={"challenge_id": challenge_id} if challenge_id else None)
    db.commit()
    return SyncAuthError(code, status_code, message)


def authenticate_sync(db: Session, *, headers: Mapping[str, str], method: str, path: str, query: str, body: bytes) -> Installation:
    """Verifica la prueba de la instalación y consume el desafío atómicamente (FR-010-379..399).

    Orden: versión → cabeceras → destino → desafío (bajo `FOR UPDATE`) con su instalación, nonce y
    versión → consumido → caducado → firma con la clave del REGISTRO (una firma inválida no consume)
    → consumo atómico (exactamente una fila). Instalación desconocida y firma inválida comparten
    código: el sync no dice qué identidades existen.
    """
    cabeceras = {k.lower(): v for k, v in headers.items()}

    def cabecera(nombre: str) -> str:
        valor = cabeceras.get(nombre.lower(), "")
        if not valor.strip():
            raise _rechazo_sync(db, code="SYNC_AUTH_INVALID", status_code=401, message="Faltan las credenciales del protocolo de sincronización.",
                                installation_uuid=None, challenge_id=None)
        return valor.strip()

    try:
        version = sync_auth.parse_protocol_version(cabecera(sync_auth.HEADER_PROTOCOL))
    except sync_auth.SyncAuthContractError as exc:
        raise _rechazo_sync(db, code=exc.code, status_code=400, message=str(exc), installation_uuid=None, challenge_id=None) from None
    installation_uuid = cabecera(sync_auth.HEADER_INSTALLATION)
    challenge_id = cabecera(sync_auth.HEADER_CHALLENGE)
    nonce = cabecera(sync_auth.HEADER_NONCE)
    firma = cabecera(sync_auth.HEADER_SIGNATURE)
    if query or method.upper() != sync_auth.SYNC_METHOD or path != sync_auth.SYNC_TARGET:
        raise _rechazo_sync(db, code="SYNC_TARGET_MISMATCH", status_code=401, message="El destino de la petición no es el del protocolo.",
                            installation_uuid=installation_uuid, challenge_id=challenge_id)
    try:
        sobre = sync_auth.build_envelope(installation_id=installation_uuid, challenge_id=challenge_id, nonce=nonce, method=method,
                                         target=path, body_sha256=sync_auth.body_sha256(body), protocol_version=version)
    except sync_auth.SyncAuthContractError:
        raise _rechazo_sync(db, code="SYNC_AUTH_INVALID", status_code=401, message="Las credenciales del protocolo no son válidas.",
                            installation_uuid=installation_uuid, challenge_id=challenge_id) from None

    inst = db.execute(select(Installation).where(Installation.installation_uuid == installation_uuid)).scalars().first()
    desafio = db.execute(select(SyncChallenge).where(SyncChallenge.id == challenge_id).with_for_update()).scalars().first()
    if inst is None:
        raise _rechazo_sync(db, code="SYNC_AUTH_INVALID", status_code=401, message="Las credenciales del protocolo no son válidas.",
                            installation_uuid=None, challenge_id=challenge_id)
    if (desafio is None or desafio.installation_id != inst.id or desafio.nonce_sha256 != sync_auth.nonce_digest(nonce)
            or desafio.protocol_version != version):
        raise _rechazo_sync(db, code="SYNC_CHALLENGE_INVALID", status_code=401, message="El desafío no es válido para esta instalación.",
                            installation_uuid=inst.installation_uuid, challenge_id=challenge_id)
    if desafio.consumed_at is not None:
        raise _rechazo_sync(db, code="SYNC_CHALLENGE_USED", status_code=401, message="El desafío ya fue utilizado.",
                            installation_uuid=inst.installation_uuid, challenge_id=challenge_id)
    ahora = _now()
    if contract._as_utc(desafio.expires_at) <= ahora:
        raise _rechazo_sync(db, code="SYNC_CHALLENGE_EXPIRED", status_code=401, message="El desafío ha caducado.",
                            installation_uuid=inst.installation_uuid, challenge_id=challenge_id)
    if not sync_auth.verify_envelope(sobre, firma, inst.public_key_pem):
        raise _rechazo_sync(db, code="SYNC_AUTH_INVALID", status_code=401, message="Las credenciales del protocolo no son válidas.",
                            installation_uuid=inst.installation_uuid, challenge_id=challenge_id)
    consumido = db.execute(
        _sql_update(SyncChallenge)
        .where(SyncChallenge.id == challenge_id, SyncChallenge.consumed_at.is_(None), SyncChallenge.expires_at > ahora)
        .values(consumed_at=ahora)
        .execution_options(synchronize_session=False)  # el consumo lo decide la base, no una evaluación en memoria
    )
    if consumido.rowcount != 1:
        raise _rechazo_sync(db, code="SYNC_CHALLENGE_USED", status_code=401, message="El desafío ya fue utilizado.",
                            installation_uuid=inst.installation_uuid, challenge_id=challenge_id)
    db.commit()  # el consumo queda escrito pase lo que pase después: un desafío consumido no resucita
    return inst


def select_current_issuance(db: Session, installation: Installation) -> Issuance | None:
    """El artefacto vigente del libro: período primero, `revision` después; nunca por fecha de emisión."""
    return db.execute(
        select(Issuance).where(Issuance.installation_id == installation.id)
        .order_by(Issuance.period_end.desc(), Issuance.period_start.desc(), Issuance.revision.desc())
    ).scalars().first()


def sync_response(db: Session, *, installation: Installation, body: Any, challenge_id: str) -> dict[str, Any]:
    """Tras autenticar: la identidad del cuerpo debe ser la del sobre; se devuelve el artefacto exacto del libro."""
    if not isinstance(body, dict) or body.get("installation_id") != installation.installation_uuid:
        raise _rechazo_sync(db, code="SYNC_INSTALLATION_MISMATCH", status_code=403,
                            message="La instalación del cuerpo no es la instalación autenticada.",
                            installation_uuid=installation.installation_uuid, challenge_id=challenge_id)
    emision = select_current_issuance(db, installation)
    ahora = _now()
    if emision is None:
        _audit(db, operation="SYNC", operator=OPERADOR_PROTOCOLO, installation_uuid=installation.installation_uuid, outcome="NO_LICENSE",
               detail={"challenge_id": challenge_id})
        db.commit()
        return {"version": "1", "status": "NO_LICENSE", "server_time": ahora.isoformat(), "license": None}
    _audit(db, operation="SYNC", operator=OPERADOR_PROTOCOLO, installation_uuid=installation.installation_uuid, outcome="OK",
           revision=emision.revision, issuance_id=emision.id, detail={"challenge_id": challenge_id, "license_id": emision.license_id})
    db.commit()
    return {"version": "1", "status": "LICENSE", "server_time": ahora.isoformat(),
            "license": {"payload": emision.payload, "signature_hex": emision.signature_hex},
            "license_id": emision.license_id, "revision": emision.revision}
