"""API del Reporte de control interno de Gobierno (REP10-R1)."""

from __future__ import annotations

import io
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission
from app.modules.government import service_reporte_control
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/control-interno", tags=["gobierno-control-interno"])


def _ver_hallazgos(db: Session, user: User) -> bool:
    permisos = identity_service.get_user_permissions(db, user)
    return identity_service.user_has_permission(user, permisos, "gobierno_hallazgos", "view")


@router.get("/reporte")
def obtener_reporte(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_auditoria", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_reporte_control.reporte(
        db,
        ctx,
        desde=desde,
        hasta=hasta,
        ver_hallazgos=_ver_hallazgos(db, user),
    )


@router.get("/reporte.csv")
def exportar_reporte(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_auditoria", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    nombre, contenido = service_reporte_control.exportar_csv(
        db,
        ctx,
        desde=desde,
        hasta=hasta,
        ver_hallazgos=_ver_hallazgos(db, user),
    )
    db.commit()
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
