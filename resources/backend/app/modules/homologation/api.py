"""API de homologación y liberación (011).

Endpoints `/homologation/*` con errores uniformes, transiciones explícitas,
segregación de funciones y gates de liberación en backend.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission, require_tenant_permission, require_write_allowed
from app.modules.homologation import service as homologation_service
from app.modules.identity_access.models import User

router = APIRouter(prefix="/homologation", tags=["homologacion"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class HomologationCreate(BaseModel):
    fiscal_version: str = Field(min_length=1, max_length=32)
    modality: str = Field(default="E_FACTURA", max_length=32)
    formal_act_ref: str | None = Field(default=None, max_length=255)
    evidence_sha256: str | None = Field(default=None, max_length=64)
    notes: str | None = None


class EvaluateBody(BaseModel):
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")
    formal_act_ref: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class ReleaseCreate(BaseModel):
    version: str = Field(min_length=1, max_length=32)
    changelog: dict[str, Any] = Field(default_factory=dict)
    gates: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class ReleaseBody(BaseModel):
    homologation_id: str | None = None
    notes: str | None = None


# --------------------------------------------------------------------------- #
# Homologación
# --------------------------------------------------------------------------- #
@router.get("/records")
def list_records(db: Session = Depends(get_db), user: User = Depends(require_permission("homologacion", "view"))):
    items = homologation_service.get_records(db)
    return {"items": items, "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/records", dependencies=[Depends(require_write_allowed)])
def create_record(
    body: HomologationCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_tenant_permission("homologacion", "create")),
):
    return homologation_service.create_record(
        db,
        fiscal_version=body.fiscal_version,
        modality=body.modality,
        formal_act_ref=body.formal_act_ref,
        evidence_sha256=body.evidence_sha256,
        notes=body.notes,
        actor=str(actor.id),
    )


@router.get("/records/{record_id}")
def get_record(record_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("homologacion", "view"))):
    return homologation_service.get_record(db, record_id)


@router.post("/records/{record_id}/submit", dependencies=[Depends(require_write_allowed)])
def submit_record(
    record_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_tenant_permission("homologacion", "edit")),
):
    return homologation_service.submit_record(db, record_id=record_id, actor=str(actor.id))


@router.post("/records/{record_id}/evaluate", dependencies=[Depends(require_write_allowed)])
def evaluate_record(
    record_id: str,
    body: EvaluateBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_tenant_permission("homologacion", "approve")),
):
    return homologation_service.evaluate_record(
        db,
        record_id=record_id,
        decision=body.decision,
        formal_act_ref=body.formal_act_ref,
        notes=body.notes,
        actor=str(actor.id),
    )


# --------------------------------------------------------------------------- #
# Liberación de versión
# --------------------------------------------------------------------------- #
@router.get("/releases")
def list_releases(db: Session = Depends(get_db), user: User = Depends(require_permission("homologacion", "view"))):
    items = homologation_service.list_releases(db)
    return {"items": items, "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/releases", dependencies=[Depends(require_write_allowed)])
def create_release(
    body: ReleaseCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_tenant_permission("homologacion", "create")),
):
    return homologation_service.create_release(
        db,
        version=body.version,
        changelog=body.changelog,
        gates=body.gates,
        notes=body.notes,
        actor=str(actor.id),
    )


@router.post("/releases/{release_id}/promote", dependencies=[Depends(require_write_allowed)])
def promote_release(
    release_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_tenant_permission("homologacion", "edit")),
):
    return homologation_service.promote_release(db, release_id=release_id, actor=str(actor.id))


@router.post("/releases/{release_id}/release", dependencies=[Depends(require_write_allowed)])
def release_version(
    release_id: str,
    body: ReleaseBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_tenant_permission("homologacion", "approve")),
):
    return homologation_service.release_version(
        db,
        release_id=release_id,
        homologation_id=body.homologation_id,
        notes=body.notes,
        actor=str(actor.id),
    )


# --------------------------------------------------------------------------- #
# Timeline
# --------------------------------------------------------------------------- #
@router.get("/timeline")
def timeline(db: Session = Depends(get_db), user: User = Depends(require_permission("homologacion", "view"))):
    return {"items": homologation_service.timeline(db), "total": len(homologation_service.timeline(db))}
