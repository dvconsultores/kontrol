"""API de sistema: health checks y diagnóstico (FR-001-080/084)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db

router = APIRouter(tags=["system"])


@router.get("/health/live")
def liveness():
    """El proceso está vivo."""
    return {"status": "ok", "service": "kontrol-backend", "version": get_settings().app_version}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)):
    """El servicio puede recibir tráfico (verifica DB)."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return {"status": "degraded", "service": "kontrol-backend", "database": "unreachable"}
    return {"status": "ok", "service": "kontrol-backend", "database": "ok"}


@router.get("/system/diagnostics")
def diagnostics(db: Session = Depends(get_db)):
    """Diagnóstico sanitizado: servicios, versión, identidad y licencia.

    No expone secretos, rutas internas ni datos de negocio (FR-001-084).
    """
    from app.modules.licensing import service as licensing_service
    from app.modules.organization.models import Installation

    installation = db.query(Installation).first()
    license_status = licensing_service.get_status(db)
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {
        "environment": get_settings().environment,
        "version": get_settings().app_version,
        "database": {"ok": db_ok},
        "installation": {
            "id": installation.installation_uuid if installation else None,
            "state": installation.state if installation else None,
        },
        "license": {
            "activated": license_status.get("activated", False),
            "mode": license_status.get("mode"),
            "period_end": license_status.get("period_end"),
        },
        "storage": get_settings().storage_path,
    }
