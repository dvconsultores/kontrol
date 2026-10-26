"""API de licenciamiento local (FR-001-050..056, DOC-07 §12.2).

Frontera de lectura (FR-010-102..111): `GET /license/status` es público y mínimo —solo lo
que la experiencia de acceso necesita—; toda lectura detallada de licencia o instalación
exige sesión y `license:view`. El backend es la autoridad: el frontend solo lo respeta.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user,
    require_permission,
    require_recent_reauth,
    require_write_allowed,
)
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


class LicensePublicStatus(BaseModel):
    """Contrato mínimo pre-sesión (FR-010-102..105): lista explícita, nada más.

    `mode` es la única fuente de verdad del acceso; `license_url` es el enlace del aviso.
    Se construye campo a campo desde el estado del servicio —no se serializa y excluye—,
    así un campo nuevo en `get_status` nunca sale por aquí. `extra="forbid"` lo refuerza.
    """

    model_config = ConfigDict(extra="forbid")

    mode: str = Field(description="FULL_ACCESS, RENEWAL_NOTICE, CRITICAL_RENEWAL_NOTICE, READ_ONLY, SECURITY_SUSPENSION o PENDING")
    license_url: str = Field(description="Ruta de la pantalla «Mi licencia»")


@router.get("/installation-request")
def installation_request(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("license", "view")),
):
    """Descarga la solicitud de activación (DOC-07 §6.2): identidad y clave pública de la
    instalación, así que la lee quien puede ver la licencia (FR-010-108)."""
    installation = licensing_service.get_or_create_installation(db)
    return licensing_service.installation_request_payload(installation)


# Importar una licencia muta el estado de la instalación: la carga el administrador local
# (US-003) con la autoridad de activar que ya existe, `license:create` —la misma de
# `POST /licensing/sync`—; la firma del propietario es la otra compuerta, no esta (FR-010-125..127).
# Sin `require_write_allowed`: renovar en READ_ONLY debe poder entrar (FR-010-131/132).
@router.post("/activate", dependencies=[Depends(require_recent_reauth)])
def activate(
    payload: LicenseImportRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("license", "create")),
):
    """Importa la licencia inicial firmada (FR-001-054)."""
    state = licensing_service.import_license(
        db,
        payload=payload.payload,
        signature_hex=payload.signature_hex,
        source="MANUAL",
        user_id=str(actor.id),
    )
    return {"ok": True, "license_id": state.license_id, "mode": state.mode}


@router.post("/import", dependencies=[Depends(require_recent_reauth)])
def import_offline(
    payload: LicenseImportRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("license", "create")),
):
    """Importa archivo firmado en modo offline."""
    state = licensing_service.import_license(
        db,
        payload=payload.payload,
        signature_hex=payload.signature_hex,
        source="OFFLINE",
        user_id=str(actor.id),
    )
    return {"ok": True, "license_id": state.license_id, "mode": state.mode}


@router.get("/status", response_model=LicensePublicStatus)
def status(db: Session = Depends(get_db)) -> LicensePublicStatus:
    """Estado público mínimo, sin sesión (FR-010-102..106): solo `mode` y `license_url`.

    Cerrado ante error: sin licencia el servicio dice `PENDING`; si el estado no trae `mode`,
    esto falla en vez de responder un modo inventado.
    """
    estado = licensing_service.get_status(db)
    return LicensePublicStatus(mode=estado["mode"], license_url=estado["license_url"])


@router.get("/detail")
def detail(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("license", "view")),
):
    """Estado completo: identidad, licencia, modo, fechas y derechos (FR-001-052/054, FR-010-107)."""
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
def history(db: Session = Depends(get_db), _: User = Depends(require_permission("license", "view"))):
    """Historial local inmutable (FR-010-108)."""
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
def get_central_config(db: Session = Depends(get_db), _: User = Depends(require_permission("license", "view"))):
    """Configuración del servidor central (FR-010-001)."""
    return licensing_service.get_central_config(db)


@central_router.put(
    "/central-config",
    dependencies=[Depends(require_write_allowed), Depends(require_recent_reauth)],
)
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


@central_router.post("/sync", dependencies=[Depends(require_recent_reauth)])
def sync_license(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("license", "create")),
):
    """Sincroniza/activa la licencia con el servidor central autenticando a la instalación (FR-010-002).

    Sin `require_write_allowed`: en `READ_ONLY` la renovación legítima debe seguir siendo posible
    (FR-010-412); la compuerta es la sesión con `license:create`."""
    return licensing_service.sync_license(db, actor=str(actor.id))


@central_router.get("/sync-runs")
def list_sync_runs(db: Session = Depends(get_db), _: User = Depends(require_permission("license", "view"))):
    """Historial de sincronizaciones (FR-010-004)."""
    return {"items": licensing_service.list_sync_runs(db), "total": len(licensing_service.list_sync_runs(db))}


@central_router.get("/entitlements")
def entitlements(db: Session = Depends(get_db), _: User = Depends(require_permission("license", "view"))):
    """Matriz vigente de entitlements por módulo (FR-010-010)."""
    return licensing_service.current_entitlements(db)


@central_router.get("/entitlement-snapshots")
def entitlement_snapshots(db: Session = Depends(get_db), _: User = Depends(require_permission("license", "view"))):
    """Snapshots de la matriz (FR-010-012)."""
    return {"items": licensing_service.list_entitlement_snapshots(db), "total": len(licensing_service.list_entitlement_snapshots(db))}


@central_router.get("/offline-status")
def offline_status(db: Session = Depends(get_db), _: User = Depends(require_permission("license", "view"))):
    """Tolerancia offline con reloj confiable (FR-010-003)."""
    return licensing_service.verify_offline(db)


@central_router.get("/renewal-requests")
def list_renewal_requests(db: Session = Depends(get_db), _: User = Depends(require_permission("license", "view"))):
    """Solicitudes de renovación (FR-010-020)."""
    return {"items": licensing_service.list_renewal_requests(db), "total": len(licensing_service.list_renewal_requests(db))}


@central_router.post(
    "/renewal-requests",
    dependencies=[Depends(require_write_allowed), Depends(require_recent_reauth)],
)
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


@central_router.post(
    "/renewal-requests/{request_id}/transition",
    dependencies=[Depends(require_write_allowed), Depends(require_recent_reauth)],
)
def transition_renewal(
    request_id: str,
    body: RenewalTransitionBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("license", "approve")),
):
    """Workflow de renovación: REPORTED→VERIFIED→ISSUED/REJECTED (FR-010-021)."""
    return licensing_service.transition_renewal(db, request_id=request_id, target=body.target, actor=str(actor.id))


@central_router.post(
    "/mode-transition",
    dependencies=[Depends(require_write_allowed), Depends(require_recent_reauth)],
)
def transition_mode(
    body: ModeTransitionBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("license", "approve")),
):
    """Transición manual de modo (FR-010-030)."""
    return licensing_service.transition_mode(db, target=body.target, actor=str(actor.id))


@central_router.get("/overview")
def overview(db: Session = Depends(get_db), _: User = Depends(require_permission("license", "view"))):
    """Vista consolidada para el frontend (FR-010-101)."""
    return licensing_service.central_overview(db)
