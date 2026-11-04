"""API de segregación de funciones de Gobierno (CTL-01, GOV-CTL-001).

La guarda preventiva no tiene API: vive dentro de los servicios de DOC-02 y CTL-06.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import (
    require_module,
    require_permission,
    require_write_allowed,
)
from app.modules.government import service_sod
from app.modules.government.api import _version
from app.modules.government.schemas_sod import (
    CatalogoSod,
    CierreSodIn,
    ConflictosSodListado,
    EstadoReglaSod,
    ProcesoSod,
    ReglaSodCambios,
    ReglaSodDetalle,
    ReglaSodIn,
    ReglasSodListado,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/sod", tags=["gobierno"])


@router.get("/acciones", response_model=CatalogoSod)
def catalogo(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_sod", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_sod.catalogo()


@router.get("/reglas", response_model=ReglasSodListado)
def listar(
    estado: EstadoReglaSod | None = Query(None),
    proceso: ProcesoSod | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_sod", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_sod.listar(db, ctx, estado, proceso)


@router.post(
    "/reglas",
    response_model=ReglaSodDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear(
    datos: ReglaSodIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_sod", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    regla = service_sod.crear(db, ctx, datos)
    db.commit()
    return service_sod.detalle(db, ctx, str(regla.id))


@router.get("/reglas/{regla_id}", response_model=ReglaSodDetalle)
def detalle(
    regla_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_sod", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_sod.detalle(db, ctx, regla_id)


@router.patch(
    "/reglas/{regla_id}",
    response_model=ReglaSodDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def editar(
    regla_id: str,
    cambios: ReglaSodCambios,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_sod", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    regla = service_sod.editar(db, ctx, regla_id, _version(if_match), cambios)
    db.commit()
    return service_sod.detalle(db, ctx, str(regla.id))


@router.post(
    "/reglas/{regla_id}/activar",
    response_model=ReglaSodDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def activar(
    regla_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_sod", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    regla = service_sod.activar(db, ctx, regla_id, _version(if_match))
    db.commit()
    return service_sod.detalle(db, ctx, str(regla.id))


@router.post(
    "/reglas/{regla_id}/cerrar",
    response_model=ReglaSodDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def cerrar(
    regla_id: str,
    datos: CierreSodIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_sod", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    regla = service_sod.cerrar(db, ctx, regla_id, _version(if_match), datos)
    db.commit()
    return service_sod.detalle(db, ctx, str(regla.id))


@router.get("/conflictos", response_model=ConflictosSodListado)
def conflictos(
    regla_id: str | None = Query(None, max_length=36),
    proceso: ProcesoSod | None = Query(None),
    accion: str | None = Query(None, max_length=32),
    usuario: str | None = Query(None, min_length=1, max_length=64),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_sod", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_sod.conflictos(
        db,
        ctx,
        regla_id,
        proceso,
        accion,
        usuario,
        desde,
        hasta,
        pagina,
        por_pagina,
    )
