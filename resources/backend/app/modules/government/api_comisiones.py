from __future__ import annotations

import io
from datetime import date

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_comisiones
from app.modules.government.api import _version
from app.modules.government.schemas_comisiones import (
    ComisionCatalogo,
    ComisionDescartarIn,
    ComisionDetalle,
    ComisionesListado,
    ComisionFinIn,
    ComisionIn,
    ComisionOpciones,
    InhibicionIn,
    InhibicionResolverIn,
    MiembroFinIn,
    MiembroIn,
    SncIn,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/contrataciones/comisiones", tags=["gobierno"])


@router.get(
    "/catalogo",
    response_model=ComisionCatalogo,
)
def catalogo(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_comisiones.catalogo()


@router.get(
    "/opciones",
    response_model=ComisionOpciones,
)
def opciones(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_comisiones.opciones(db, ctx)


@router.get(
    "",
    response_model=ComisionesListado,
)
def listar(
    q: str | None = Query(default=None, max_length=100),
    status: str | None = Query(default=None),
    tipo: str | None = Query(default=None),
    situacion: str | None = Query(default=None, max_length=16),
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=25, ge=10, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_comisiones.listar(
        db,
        ctx,
        q=q,
        status=status,
        tipo=tipo,
        situacion=situacion,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@router.get(
    "/comisiones.csv",
)
def exportar_csv(
    q: str | None = Query(default=None, max_length=100),
    status: str | None = Query(default=None),
    tipo: str | None = Query(default=None),
    situacion: str | None = Query(default=None, max_length=16),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    nombre, contenido = service_comisiones.exportar_csv(
        db, ctx, q=q, status=status, tipo=tipo, situacion=situacion
    )
    db.commit()
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post(
    "",
    response_model=ComisionDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear(
    datos: ComisionIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    creada = service_comisiones.crear(db, ctx, datos)
    db.commit()
    return service_comisiones.detalle(db, ctx, creada["id"], None)


@router.get(
    "/{comision_id}",
    response_model=ComisionDetalle,
)
def detalle(
    comision_id: str,
    fecha: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_comisiones.detalle(db, ctx, comision_id, fecha)


@router.patch(
    "/{comision_id}",
    response_model=ComisionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def editar(
    comision_id: str,
    datos: ComisionIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_comisiones.editar(db, ctx, comision_id, _version(if_match), datos)
    db.commit()
    return service_comisiones.detalle(db, ctx, comision_id, None)


@router.post(
    "/{comision_id}/descartar",
    response_model=ComisionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def descartar(
    comision_id: str,
    datos: ComisionDescartarIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_comisiones.descartar(db, ctx, comision_id, _version(if_match), datos)
    db.commit()
    return service_comisiones.detalle(db, ctx, comision_id, None)


@router.post(
    "/{comision_id}/activar",
    response_model=ComisionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def activar(
    comision_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_comisiones.activar(db, ctx, comision_id, _version(if_match))
    db.commit()
    return service_comisiones.detalle(db, ctx, comision_id, None)


@router.post(
    "/{comision_id}/cerrar",
    response_model=ComisionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def cerrar(
    comision_id: str,
    datos: ComisionFinIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "close")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_comisiones.cerrar(db, ctx, comision_id, _version(if_match), datos)
    db.commit()
    return service_comisiones.detalle(db, ctx, comision_id, None)


@router.post(
    "/{comision_id}/notificacion-snc",
    response_model=ComisionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def notificar_snc(
    comision_id: str,
    datos: SncIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_comisiones.notificar_snc(db, ctx, comision_id, _version(if_match), datos)
    db.commit()
    return service_comisiones.detalle(db, ctx, comision_id, None)


@router.post(
    "/{comision_id}/miembros",
    response_model=ComisionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def anadir_miembro(
    comision_id: str,
    datos: MiembroIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_comisiones.anadir_miembro(db, ctx, comision_id, _version(if_match), datos)
    db.commit()
    return service_comisiones.detalle(db, ctx, comision_id, None)


@router.delete(
    "/{comision_id}/miembros/{miembro_id}",
    response_model=ComisionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def retirar_miembro(
    comision_id: str,
    miembro_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_comisiones.retirar_miembro(db, ctx, comision_id, _version(if_match), miembro_id)
    db.commit()
    return service_comisiones.detalle(db, ctx, comision_id, None)


@router.post(
    "/{comision_id}/miembros/{miembro_id}/terminar",
    response_model=ComisionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def terminar_miembro(
    comision_id: str,
    miembro_id: str,
    datos: MiembroFinIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "close")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_comisiones.terminar_miembro(
        db, ctx, comision_id, _version(if_match), miembro_id, datos
    )
    db.commit()
    return service_comisiones.detalle(db, ctx, comision_id, None)


@router.post(
    "/{comision_id}/inhibiciones",
    response_model=ComisionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def declarar_inhibicion(
    comision_id: str,
    datos: InhibicionIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_comisiones.declarar_inhibicion(db, ctx, comision_id, datos)
    db.commit()
    return service_comisiones.detalle(db, ctx, comision_id, None)


@router.post(
    "/{comision_id}/inhibiciones/{inhibicion_id}/resolver",
    response_model=ComisionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def resolver_inhibicion(
    comision_id: str,
    inhibicion_id: str,
    datos: InhibicionResolverIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_comisiones.resolver_inhibicion(
        db, ctx, comision_id, inhibicion_id, _version(if_match), datos
    )
    db.commit()
    return service_comisiones.detalle(db, ctx, comision_id, None)
