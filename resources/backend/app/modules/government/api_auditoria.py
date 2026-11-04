"""API de consulta y muestreo read-only del auditor de Gobierno (CTL-04, GOV-CTL-005).

Proyección de la bitácora inmutable limitada a Gobierno y a la empresa activa; la única escritura es la muestra (papel de trabajo).
"""

from __future__ import annotations

import io
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import (
    require_module,
    require_permission,
    require_write_allowed,
)
from app.modules.government import service_auditoria
from app.modules.government.schemas_auditoria import (
    AuditoriaEventoDetalle,
    AuditoriaEventos,
    AuditoriaFiltros,
    AuditoriaFiltrosPoblacion,
    AuditoriaMuestraDetalle,
    AuditoriaMuestras,
    MuestraIn,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/auditoria", tags=["gobierno"])


@router.get("/filtros", response_model=AuditoriaFiltros)
def filtros(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_auditoria", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_auditoria.filtros(db, ctx)


@router.get("/eventos", response_model=AuditoriaEventos)
def listar_eventos(
    desde: date | None = None,
    hasta: date | None = None,
    proceso: str | None = Query(None, max_length=10),
    accion: str | None = Query(None, max_length=64),
    usuario: str | None = Query(None, min_length=1, max_length=150),
    texto: str | None = Query(None, min_length=1, max_length=100),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_auditoria", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_auditoria.listar_eventos(
        db,
        ctx,
        AuditoriaFiltrosPoblacion(
            desde=desde,
            hasta=hasta,
            proceso=proceso,
            accion=accion,
            usuario=usuario,
            texto=texto,
        ),
        pagina=pagina,
        por_pagina=por_pagina,
    )


@router.get("/eventos/{evento_id}", response_model=AuditoriaEventoDetalle)
def detalle_evento(
    evento_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_auditoria", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_auditoria.detalle_evento(db, ctx, evento_id)


@router.get("/muestras", response_model=AuditoriaMuestras)
def listar_muestras(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_auditoria", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_auditoria.listar_muestras(db, ctx)


@router.post(
    "/muestras",
    response_model=AuditoriaMuestraDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def registrar_muestra(
    datos: MuestraIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_auditoria", "sample")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_auditoria.registrar_muestra(db, ctx, datos)
    db.commit()
    return resultado


@router.get("/muestras/{muestra_id}", response_model=AuditoriaMuestraDetalle)
def obtener_muestra(
    muestra_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_auditoria", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_auditoria.obtener_muestra(db, ctx, muestra_id)


@router.get("/muestras/{muestra_id}/exportar")
def exportar_muestra(
    muestra_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_auditoria", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    nombre, contenido = service_auditoria.exportar_muestra_csv(db, ctx, muestra_id)
    db.commit()
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
