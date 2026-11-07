"""API de políticas de cierre de Gobierno (CTL-10, GOV-CTL-012)."""

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
from app.modules.government import service_cierres
from app.modules.government.api import _version
from app.modules.government.schemas_cierres import (
    BloqueosListado,
    CatalogoCierres,
    ControlIn,
    MotivoRetiroIn,
    PoliticaCambios,
    PoliticaDetalle,
    PoliticaIn,
    PoliticasListado,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/cierres", tags=["gobierno"])


@router.get("/catalogo", response_model=CatalogoCierres)
def catalogo(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cierre", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_cierres.catalogo()


@router.get("/politicas", response_model=PoliticasListado)
def listar(
    accion_cierre: str | None = Query(None),
    estado: str | None = Query(None),
    pagina: int = Query(1, ge=1),
    tamano: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cierre", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_cierres.listar(db, ctx, accion_cierre, estado, pagina, tamano)


@router.post(
    "/politicas",
    response_model=PoliticaDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear(
    datos: PoliticaIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cierre", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    politica = service_cierres.crear(db, ctx, datos)
    db.commit()
    return service_cierres.detalle(db, ctx, str(politica.id))


@router.get("/politicas/{politica_id}", response_model=PoliticaDetalle)
def detalle(
    politica_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cierre", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_cierres.detalle(db, ctx, politica_id)


@router.patch(
    "/politicas/{politica_id}",
    response_model=PoliticaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def editar(
    politica_id: str,
    cambios: PoliticaCambios,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cierre", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    politica = service_cierres.editar(db, ctx, politica_id, _version(if_match), cambios)
    db.commit()
    return service_cierres.detalle(db, ctx, str(politica.id))


@router.post(
    "/politicas/{politica_id}/controles",
    response_model=PoliticaDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def anadir_control(
    politica_id: str,
    datos: ControlIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cierre", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    politica = service_cierres.anadir_control(db, ctx, politica_id, _version(if_match), datos)
    db.commit()
    return service_cierres.detalle(db, ctx, str(politica.id))


@router.delete(
    "/politicas/{politica_id}/controles/{control_id}",
    response_model=PoliticaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def quitar_control(
    politica_id: str,
    control_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cierre", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    politica = service_cierres.quitar_control(db, ctx, politica_id, control_id, _version(if_match))
    db.commit()
    return service_cierres.detalle(db, ctx, str(politica.id))


@router.post(
    "/politicas/{politica_id}/activar",
    response_model=PoliticaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def activar(
    politica_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cierre", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    politica = service_cierres.activar(db, ctx, politica_id, _version(if_match))
    db.commit()
    return service_cierres.detalle(db, ctx, str(politica.id))


@router.post(
    "/politicas/{politica_id}/retirar",
    response_model=PoliticaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def retirar(
    politica_id: str,
    datos: MotivoRetiroIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cierre", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    politica = service_cierres.retirar(db, ctx, politica_id, _version(if_match), datos)
    db.commit()
    return service_cierres.detalle(db, ctx, str(politica.id))


@router.get("/bloqueos", response_model=BloqueosListado)
def bloqueos(
    accion_cierre: str | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    pagina: int = Query(1, ge=1),
    tamano: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cierre", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_cierres.listar_bloqueos(
        db, ctx, accion_cierre, desde, hasta, pagina, tamano
    )

