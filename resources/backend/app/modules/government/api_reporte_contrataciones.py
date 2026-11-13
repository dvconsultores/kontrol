"""API del Reporte de contrataciones de Gobierno (REP03-R1)."""

from __future__ import annotations

import io
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission
from app.modules.government import service_reporte_contrataciones
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/contrataciones/reporte", tags=["gobierno-reporte-contrataciones"])


@router.get("")
def obtener_reporte(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_expedientes", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_reporte_contrataciones.reporte(
        db,
        ctx,
        desde=desde,
        hasta=hasta,
    )


@router.get(".csv")
def exportar_reporte(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_expedientes", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    nombre, contenido = service_reporte_contrataciones.exportar_csv(
        db,
        ctx,
        desde=desde,
        hasta=hasta,
    )
    db.commit()
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
