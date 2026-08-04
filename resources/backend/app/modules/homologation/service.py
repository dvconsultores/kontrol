"""Servicio de homologación fiscal y liberación de versión (011).

Homologación: registro (DRAFT), sometimiento (SUBMITTED), evaluación
(APPROVED/REJECTED) con segregación y acto formal. Liberación: versiones
(DRAFT → CANDIDATE → RELEASED/BLOCKED) con gates, homologación documentada
y licencia válida. Eventos append-only para trazabilidad.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.homologation.models import HomologationEvent, HomologationRecord, ReleaseVersion
from app.modules.licensing import service as licensing_service
from app.modules.organization.models import Installation

# Máquinas de estado
HOMOLOGATION_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"SUBMITTED"},
    "SUBMITTED": {"APPROVED", "REJECTED"},
    "APPROVED": set(),
    "REJECTED": set(),
}

RELEASE_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"CANDIDATE"},
    "CANDIDATE": {"RELEASED", "BLOCKED"},
    "RELEASED": set(),
    "BLOCKED": set(),
}

# Gates verificables en la versión (tests, seguridad, respaldo).
REQUIRED_GATES: list[str] = ["tests", "security", "backup"]

# Modalidades fiscales aceptadas (CL-011-08).
MODALITIES: set[str] = {"E_FACTURA", "FACTURA_PAPEL", "FORMA_LIBRE", "MAC", "DIGITAL", "E_COMPRAS"}

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _now() -> datetime:
    return datetime.now(UTC)


def _version_key(version: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return (0,)


def _record_event(
    db: Session,
    *,
    installation_id: str,
    source: str,
    event_type: str,
    detail: dict[str, Any] | None,
    entity_id: str | None,
    homologation_id: str | None,
    created_by: str | None,
) -> None:
    db.add(
        HomologationEvent(
            installation_id=installation_id,
            source=source,
            homologation_id=homologation_id,
            entity_id=entity_id,
            event_type=event_type,
            detail=detail,
            created_by=created_by,
        )
    )


def _assert_transition(current: str, target: str, transitions: dict[str, set[str]], what: str) -> None:
    if target not in transitions.get(current, set()):
        raise ConflictError(
            code="INVALID_STATE_TRANSITION",
            message=f"No se permite pasar {what} de {current} a {target}.",
        )


def _installation(db: Session) -> Installation:
    inst = db.execute(select(Installation).limit(1)).scalars().first()
    if inst is None:
        raise KontrolError(code="INSTALLATION_NOT_FOUND", message="No existe identidad de instalación", status_code=422)
    return inst


def _record_dict(record: HomologationRecord) -> dict[str, Any]:
    # HOMOLOGADO es un estado derivado: solo con APPROVED + acto formal (FR-011-005).
    homologated = record.status == "APPROVED" and bool(record.formal_act_ref)
    return {
        "id": str(record.id),
        "fiscal_version": record.fiscal_version,
        "modality": record.modality,
        "formal_act_ref": record.formal_act_ref,
        "evidence_sha256": record.evidence_sha256,
        "status": record.status,
        "homologated": homologated,
        "evaluated_by": record.evaluated_by,
        "evaluated_at": record.evaluated_at.isoformat() if record.evaluated_at else None,
        "notes": record.notes,
        "created_by": record.created_by,
        "created_at": record.created_at.isoformat(),
    }


def _release_dict(release: ReleaseVersion) -> dict[str, Any]:
    return {
        "id": str(release.id),
        "version": release.version,
        "changelog": release.changelog or {},
        "gates": release.gates or {},
        "homologation_id": release.homologation_id,
        "status": release.status,
        "blocked_reasons": release.blocked_reasons or {},
        "released_by": release.released_by,
        "released_at": release.released_at.isoformat() if release.released_at else None,
        "notes": release.notes,
        "created_by": release.created_by,
        "created_at": release.created_at.isoformat(),
    }


# =========================================================================== #
# Homologación
# =========================================================================== #
def create_record(
    db: Session,
    *,
    fiscal_version: str,
    modality: str,
    formal_act_ref: str | None,
    evidence_sha256: str | None,
    notes: str | None,
    actor: str | None,
) -> dict[str, Any]:
    """Registra un acto de homologación en DRAFT (FR-011-001)."""
    inst = _installation(db)
    if modality not in MODALITIES:
        raise KontrolError(code="INVALID_MODALITY", message=f"Modalidad fiscal no válida: {modality}", status_code=422)
    record = HomologationRecord(
        installation_id=inst.installation_uuid,
        fiscal_version=fiscal_version.strip(),
        modality=modality,
        formal_act_ref=formal_act_ref,
        evidence_sha256=evidence_sha256,
        status="DRAFT",
        notes=notes,
        created_by=actor,
    )
    db.add(record)
    db.flush()
    _record_event(
        db,
        installation_id=inst.installation_uuid,
        source="HOMOLOGATION",
        event_type="HOMOLOGATION_CREATED",
        detail={"fiscal_version": record.fiscal_version, "modality": modality},
        entity_id=str(record.id),
        homologation_id=str(record.id),
        created_by=actor,
    )
    db.commit()
    db.refresh(record)
    return _record_dict(record)


def _owned_record(db: Session, record_id: str) -> HomologationRecord:
    record = db.get(HomologationRecord, record_id)
    if record is None:
        raise NotFoundError(code="HOMOLOGATION_NOT_FOUND", message="Acto de homologación no encontrado")
    return record


def submit_record(db: Session, *, record_id: str, actor: str | None) -> dict[str, Any]:
    """Somete la homologación a evaluación (DRAFT → SUBMITTED) (FR-011-002)."""
    inst = _installation(db)
    record = _owned_record(db, record_id)
    if record.installation_id != inst.installation_uuid:
        raise NotFoundError(code="HOMOLOGATION_NOT_FOUND", message="Acto de homologación no encontrado")
    _assert_transition(record.status, "SUBMITTED", HOMOLOGATION_TRANSITIONS, "la homologación")
    if not record.evidence_sha256:
        raise KontrolError(
            code="HOMOLOGATION_INCOMPLETE",
            message="Para someter se requiere la evidencia (SHA-256) de la versión fiscal.",
            status_code=422,
        )
    record.status = "SUBMITTED"
    _record_event(
        db,
        installation_id=inst.installation_uuid,
        source="HOMOLOGATION",
        event_type="HOMOLOGATION_SUBMITTED",
        detail={"record_id": record_id},
        entity_id=str(record.id),
        homologation_id=str(record.id),
        created_by=actor,
    )
    db.commit()
    db.refresh(record)
    return _record_dict(record)


def evaluate_record(
    db: Session,
    *,
    record_id: str,
    decision: str,
    formal_act_ref: str | None,
    notes: str | None,
    actor: str | None,
) -> dict[str, Any]:
    """Evalúa la homologación (SUBMITTED → APPROVED/REJECTED) (FR-011-003).

    Segregación: quien creó la homologación no puede aprobarla (DOC-01 §5).
    Al aprobar se exige acto formal (FR-011-005).
    """
    inst = _installation(db)
    record = _owned_record(db, record_id)
    if record.installation_id != inst.installation_uuid:
        raise NotFoundError(code="HOMOLOGATION_NOT_FOUND", message="Acto de homologación no encontrado")
    if decision not in {"APPROVED", "REJECTED"}:
        raise KontrolError(code="INVALID_DECISION", message="Decisión debe ser APPROVED o REJECTED", status_code=422)
    _assert_transition(record.status, decision, HOMOLOGATION_TRANSITIONS, "la homologación")

    if record.created_by and actor and record.created_by == actor:
        raise ConflictError(
            code="SEGREGATION_VIOLATION",
            message="Quien creó la homologación no puede evaluarla (segregación de funciones).",
        )

    if decision == "APPROVED":
        formal_act_ref = (formal_act_ref or record.formal_act_ref or "").strip()
        if not formal_act_ref:
            raise KontrolError(
                code="FORMAL_ACT_REQUIRED",
                message="Para aprobar se requiere el acto formal.",
                status_code=422,
            )
        record.formal_act_ref = formal_act_ref

    record.status = decision
    record.evaluated_by = actor
    record.evaluated_at = _now()
    if notes:
        record.notes = (record.notes or "") + ("\n" + notes if record.notes else notes)

    _record_event(
        db,
        installation_id=inst.installation_uuid,
        source="HOMOLOGATION",
        event_type=f"HOMOLOGATION_{decision}",
        detail={"record_id": record_id, "formal_act_ref": record.formal_act_ref},
        entity_id=str(record.id),
        homologation_id=str(record.id),
        created_by=actor,
    )
    db.commit()
    db.refresh(record)
    return _record_dict(record)


def get_records(db: Session) -> list[dict[str, Any]]:
    inst = _installation(db)
    rows = db.execute(
        select(HomologationRecord)
        .where(HomologationRecord.installation_id == inst.installation_uuid)
        .order_by(HomologationRecord.created_at.desc())
    ).scalars().all()
    return [_record_dict(r) for r in rows]


def get_record(db: Session, record_id: str) -> dict[str, Any]:
    record = _owned_record(db, record_id)
    events = db.execute(
        select(HomologationEvent)
        .where(HomologationEvent.homologation_id == str(record.id))
        .order_by(HomologationEvent.created_at.asc())
    ).scalars().all()
    return {
        **_record_dict(record),
        "events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "detail": e.detail,
                "created_by": e.created_by,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
    }


# =========================================================================== #
# Liberación de versión
# =========================================================================== #
def create_release(
    db: Session,
    *,
    version: str,
    changelog: dict[str, Any],
    gates: dict[str, Any],
    notes: str | None,
    actor: str | None,
) -> dict[str, Any]:
    """Crea una versión en DRAFT con changelog y gates (FR-011-010)."""
    inst = _installation(db)
    version = version.strip()
    if not VERSION_RE.match(version):
        raise KontrolError(code="INVALID_VERSION", message="La versión debe tener formato x.y.z.", status_code=422)
    existing = db.execute(
        select(ReleaseVersion).where(
            ReleaseVersion.installation_id == inst.installation_uuid,
            ReleaseVersion.version == version,
        )
    ).scalars().first()
    if existing is not None:
        raise ConflictError(code="VERSION_EXISTS", message=f"La versión {version} ya existe.")
    release = ReleaseVersion(
        installation_id=inst.installation_uuid,
        version=version,
        changelog=changelog or {},
        gates=gates or {},
        status="DRAFT",
        notes=notes,
        created_by=actor,
    )
    db.add(release)
    db.flush()
    _record_event(
        db,
        installation_id=inst.installation_uuid,
        source="RELEASE",
        event_type="RELEASE_CREATED",
        detail={"version": version},
        entity_id=str(release.id),
        homologation_id=None,
        created_by=actor,
    )
    db.commit()
    db.refresh(release)
    return _release_dict(release)


def _owned_release(db: Session, release_id: str) -> ReleaseVersion:
    release = db.get(ReleaseVersion, release_id)
    if release is None:
        raise NotFoundError(code="RELEASE_NOT_FOUND", message="Versión de liberación no encontrada")
    return release


def promote_release(db: Session, *, release_id: str, actor: str | None) -> dict[str, Any]:
    """Promueve la versión a CANDIDATE con los gates registrados (FR-011-011)."""
    inst = _installation(db)
    release = _owned_release(db, release_id)
    if release.installation_id != inst.installation_uuid:
        raise NotFoundError(code="RELEASE_NOT_FOUND", message="Versión de liberación no encontrada")
    _assert_transition(release.status, "CANDIDATE", RELEASE_TRANSITIONS, "la versión")

    gates = release.gates or {}
    missing = [g for g in REQUIRED_GATES if g not in gates]
    if missing:
        raise KontrolError(
            code="GATES_MISSING",
            message=f"Faltan gates por registrar: {', '.join(missing)}.",
            status_code=422,
        )

    release.status = "CANDIDATE"
    _record_event(
        db,
        installation_id=inst.installation_uuid,
        source="RELEASE",
        event_type="RELEASE_PROMOTED",
        detail={"version": release.version},
        entity_id=str(release.id),
        homologation_id=None,
        created_by=actor,
    )
    db.commit()
    db.refresh(release)
    return _release_dict(release)


def release_version(
    db: Session,
    *,
    release_id: str,
    homologation_id: str | None,
    notes: str | None,
    actor: str | None,
) -> dict[str, Any]:
    """Libera la versión a producción con gates (FR-011-012/013).

    Requiere: homologación documentada y aprobada (con acto formal), gates
    verdes y licencia válida (FULL_ACCESS). De lo contrario queda BLOCKED con
    razones. No se permite liberar una versión anterior a la ya liberada.
    """
    inst = _installation(db)
    release = _owned_release(db, release_id)
    if release.installation_id != inst.installation_uuid:
        raise NotFoundError(code="RELEASE_NOT_FOUND", message="Versión de liberación no encontrada")
    _assert_transition(release.status, "RELEASED", RELEASE_TRANSITIONS, "la versión")

    reasons: list[str] = []

    # 1) Homologación documentada y aprobada (FR-011-005/012)
    record = db.get(HomologationRecord, homologation_id) if homologation_id else None
    if record is None or record.status != "APPROVED" or not record.formal_act_ref:
        reasons.append("HOMOLOGATION_NOT_DOCUMENTED")

    # 2) Gates verdes (tests, security, backup)
    gates = release.gates or {}
    for gate in REQUIRED_GATES:
        if not (gates.get(gate) or {}).get("passed"):
            reasons.append(f"GATE_{gate.upper()}_NOT_PASSED")

    # 3) Licencia válida (FULL_ACCESS)
    if licensing_service.current_mode(db) != "FULL_ACCESS":
        reasons.append("LICENSE_NOT_VALID")

    # 4) No re-liberar versiones anteriores a una ya liberada
    released = db.execute(
        select(ReleaseVersion).where(
            ReleaseVersion.installation_id == inst.installation_uuid,
            ReleaseVersion.status == "RELEASED",
        )
    ).scalars().all()
    current_key = _version_key(release.version)
    for prev in released:
        if _version_key(prev.version) > current_key:
            reasons.append("RELEASE_OLDER_THAN_APPLIED")

    if reasons:
        release.status = "BLOCKED"
        release.blocked_reasons = {"reasons": reasons}
        event_type = "RELEASE_BLOCKED"
    else:
        release.status = "RELEASED"
        release.homologation_id = str(record.id) if record else None
        release.released_by = actor
        release.released_at = _now()
        if notes:
            release.notes = (release.notes or "") + ("\n" + notes if release.notes else notes)
        release.blocked_reasons = None
        event_type = "RELEASE_RELEASED"

    _record_event(
        db,
        installation_id=inst.installation_uuid,
        source="RELEASE",
        event_type=event_type,
        detail={"version": release.version, "reasons": reasons},
        entity_id=str(release.id),
        homologation_id=str(record.id) if record else None,
        created_by=actor,
    )
    db.commit()
    db.refresh(release)
    return _release_dict(release)


def list_releases(db: Session) -> list[dict[str, Any]]:
    inst = _installation(db)
    rows = db.execute(
        select(ReleaseVersion)
        .where(ReleaseVersion.installation_id == inst.installation_uuid)
        .order_by(ReleaseVersion.created_at.desc())
    ).scalars().all()
    return [_release_dict(r) for r in rows]


def timeline(db: Session) -> list[dict[str, Any]]:
    """Timeline inmutable de homologación y liberación (FR-011-020)."""
    inst = _installation(db)
    rows = db.execute(
        select(HomologationEvent)
        .where(HomologationEvent.installation_id == inst.installation_uuid)
        .order_by(HomologationEvent.created_at.desc())
    ).scalars().all()
    return [
        {
            "id": str(e.id),
            "source": e.source,
            "event_type": e.event_type,
            "detail": e.detail,
            "entity_id": e.entity_id,
            "created_by": e.created_by,
            "created_at": e.created_at.isoformat(),
        }
        for e in rows
    ]
