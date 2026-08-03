"""API de licenciamiento local (FR-001-050..056, DOC-07 §12.2)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.identity_access.models import User
from app.modules.licensing import service as licensing_service

router = APIRouter(prefix="/license", tags=["license"])


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
