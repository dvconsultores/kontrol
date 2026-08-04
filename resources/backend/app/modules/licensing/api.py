"""API de licenciamiento local (FR-001-050..056, DOC-07 §12.2)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, require_write_allowed
from app.modules.identity_access.models import User
from app.modules.licensing import service as licensing_service

router = APIRouter(prefix="/license", tags=["license"])
central_router = APIRouter(prefix="/licensing", tags=["licenciamiento"])


class LicenseImportRequest(BaseModel):
    payload: dict[str, Any] = Field(description="Contenido firmado de la licencia")
    signature_hex: str = Field(min_length=1, description="Firma Ed25519 en hexadecimal")


class RenewalRequestCreate(BaseModel):
    payment_proof_ref: str | None = None
    notes: str | None = None


@router.get("/installation-request")
def installation_request(db: Session = Depends(get_db)):
    """Descarga la solicitud de activación (DOC-07 §6.2)."""
    installation = licensing_service.get_or_create_installation(db)
    return licensing_service.installation_request_payload(installation)


@router.post("/activate")
def activate(payload: LicenseImportRequest, db: Session = Depends(get_db)):
    """Importa la licencia inicial firmada (FR-001-054)."""
    state = licensing_service.import_license(
        db,
        payload=payload.payload,
        signature_hex=payload.signature_hex,
        source="MANUAL",
    )
    return {"ok": True, "license_id": state.license_id, "mode": state.mode}


@router.post("/import")
def import_offline(payload: LicenseImportRequest, db: Session = Depends(get_db)):
    """Importa archivo firmado en modo offline."""
    state = licensing_service.import_license(
        db,
        payload=payload.payload,
        signature_hex=payload.signature_hex,
        source="OFFLINE",
    )
    return {"ok": True, "license_id": state.license_id, "mode": state.mode}


@router.get("/status")
def status(db: Session = Depends(get_db)):
    """Estado, modo, fechas y derechos (FR-001-052/054)."""
    return licensing_service.get_status(db)


@router.post("/renewal-request")
def renewal_request(
    body: RenewalRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Registra comprobante/solicitud de renovación (no confirma)."""
    request = licensing_service.create_renewal_request(db, payment_proof_ref=body.payment_proof_ref, notes=body.notes, user_id=str(user.id))
    return {"ok": True, "id": str(request.id), "status": request.status}


@router.get("/history")
def history(db: Session = Depends(get_db)):
    """Historial local inmutable."""
    return licensing_service.get_history(db)


# =========================================================================== #
# Licenciamiento central (010)
# =========================================================================== #
class CentralConfigUpdate(BaseModel):
    server_url: str = Field(min_length=1, max_length=255)
    public_key: str | None = None
    sync_policy: dict[str, Any] = Field(default_factory=dict)
    grace_days: int = Field(default=7, ge=1, le=365)
    enabled: bool = True


class RenewalCreate(BaseModel):
    payment_proof_ref: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class RenewalTransitionBody(BaseModel):
    target: str = Field(pattern="^(VERIFIED|ISSUED|REJECTED)$")


class ModeTransitionBody(BaseModel):
    target: str


@central_router.get("/central-config")
def get_central_config(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Configuración del servidor central (FR-010-001)."""
    return licensing_service.get_central_config(db)


@central_router.put("/central-config", dependencies=[Depends(require_write_allowed)])
def upsert_central_config(
    body: CentralConfigUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("license", "edit")),
):
    """Persiste la configuración central (FR-010-001)."""
    return licensing_service.upsert_central_config(
        db,
        server_url=body.server_url,
        public_key=body.public_key,
        sync_policy=body.sync_policy,
        grace_days=body.grace_days,
        enabled=body.enabled,
        actor=str(actor.id),
    )


@central_router.post("/sync", dependencies=[Depends(require_write_allowed)])
def sync_license(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("license", "create")),
):
    """Sincroniza/activa la licencia con el servidor central (FR-010-002)."""
    return licensing_service.sync_license(db, actor=str(actor.id))


@central_router.get("/sync-runs")
def list_sync_runs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Historial de sincronizaciones (FR-010-004)."""
    return {"items": licensing_service.list_sync_runs(db), "total": len(licensing_service.list_sync_runs(db))}


@central_router.get("/entitlements")
def entitlements(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Matriz vigente de entitlements por módulo (FR-010-010)."""
    return licensing_service.current_entitlements(db)


@central_router.get("/entitlement-snapshots")
def entitlement_snapshots(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Snapshots de la matriz (FR-010-012)."""
    return {"items": licensing_service.list_entitlement_snapshots(db), "total": len(licensing_service.list_entitlement_snapshots(db))}


@central_router.get("/offline-status")
def offline_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Tolerancia offline con reloj confiable (FR-010-003)."""
    return licensing_service.verify_offline(db)


@central_router.get("/renewal-requests")
def list_renewal_requests(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Solicitudes de renovación (FR-010-020)."""
    return {"items": licensing_service.list_renewal_requests(db), "total": len(licensing_service.list_renewal_requests(db))}


@central_router.post("/renewal-requests", dependencies=[Depends(require_write_allowed)])
def create_renewal_request(
    body: RenewalCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("license", "create")),
):
    """Registra solicitud de renovación con comprobante (FR-010-020)."""
    req = licensing_service.create_renewal_request(
        db, payment_proof_ref=body.payment_proof_ref, notes=body.notes, user_id=str(actor.id)
    )
    return {"ok": True, "id": str(req.id), "status": req.status}


@central_router.post("/renewal-requests/{request_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_renewal(
    request_id: str,
    body: RenewalTransitionBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("license", "approve")),
):
    """Workflow de renovación: REPORTED→VERIFIED→ISSUED/REJECTED (FR-010-021)."""
    return licensing_service.transition_renewal(db, request_id=request_id, target=body.target, actor=str(actor.id))


@central_router.post("/mode-transition", dependencies=[Depends(require_write_allowed)])
def transition_mode(
    body: ModeTransitionBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("license", "approve")),
):
    """Transición manual de modo (FR-010-030)."""
    return licensing_service.transition_mode(db, target=body.target, actor=str(actor.id))


@central_router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Vista consolidada para el frontend (FR-010-101)."""
    return licensing_service.central_overview(db)
