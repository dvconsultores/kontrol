from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission
from app.modules.government.schemas_bitacora import (
    BitacoraEventoDetalle,
    BitacoraEventos,
    BitacoraFiltros,
)
from app.modules.government.service_bitacora import detalle, filtros, listar
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/bitacora", tags=["gobierno"])


@router.get("/filtros", response_model=BitacoraFiltros)
def get_filtros(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_auditoria", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return filtros(db, ctx)


@router.get("", response_model=BitacoraEventos)
def get_eventos(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_auditoria", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
    desde: date | None = None,
    hasta: date | None = None,
    accion: str | None = Query(None, max_length=64),
    usuario: str | None = Query(None, min_length=1, max_length=150),
    funcionario_id: UUID | None = None,
    unidad_id: UUID | None = None,
    request_id: str | None = Query(None, min_length=1, max_length=64),
    resultado: Literal["EXITO", "RECHAZO", "DENEGACION"] | None = None,
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=10, le=200),
):
    return listar(
        db,
        ctx,
        desde=desde,
        hasta=hasta,
        accion=accion,
        usuario=usuario,
        funcionario_id=str(funcionario_id) if funcionario_id is not None else None,
        unidad_id=str(unidad_id) if unidad_id is not None else None,
        request_id=request_id,
        resultado=resultado,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@router.get("/{evento_id}", response_model=BitacoraEventoDetalle)
def get_evento(
    evento_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_auditoria", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return detalle(db, ctx, evento_id)
