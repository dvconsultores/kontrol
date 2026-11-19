from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_actas_politicas, service_actas_regla
from app.modules.government.api import _version
from app.modules.government.schemas_actas_politicas import (
    PoliticaActaCatalogo,
    PoliticaActaCerrarIn,
    PoliticaActaDetalle,
    PoliticaActaIn,
    PoliticaActaListado,
    PoliticaActaOpciones,
)
from app.modules.identity_access.models import User
from app.shared.clock import hoy_de_negocio

router = APIRouter(
    prefix="/gobierno/actas-entrega/politicas",
    tags=["gobierno"],
)


@router.get("/catalogo", response_model=PoliticaActaCatalogo)
def catalogo(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_actas", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_actas_politicas.catalogo()


@router.get("/opciones", response_model=PoliticaActaOpciones)
def opciones(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_actas", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_actas_politicas.opciones(db, ctx)


@router.get("/numeracion/vista-previa")
def numeracion_vista_previa(
    patron: str,
    anio: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_actas", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    anio_resuelto = anio if anio is not None else hoy_de_negocio().year
    return service_actas_regla.vista_previa(patron, anio_resuelto)


@router.get("", response_model=PoliticaActaListado)
def listar(
    estado: str | None = None,
    q: str | None = None,
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, ge=1),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_actas", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_actas_politicas.listar(db, ctx, estado, q, pagina, por_pagina)


@router.get("/{politica_id}", response_model=PoliticaActaDetalle)
def detalle(
    politica_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_actas", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_actas_politicas.detalle(db, ctx, politica_id)


@router.post(
    "",
    response_model=PoliticaActaDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear(
    datos: PoliticaActaIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_actas", "configure")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_actas_politicas.crear(db, ctx, datos)
    db.commit()
    return resultado


@router.put(
    "/{politica_id}",
    response_model=PoliticaActaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def editar(
    politica_id: str,
    datos: PoliticaActaIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_actas", "configure")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_actas_politicas.editar(
        db, ctx, politica_id, _version(if_match), datos
    )
    db.commit()
    return resultado


@router.post(
    "/{politica_id}/nueva-version",
    response_model=PoliticaActaDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def nueva_version(
    politica_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_actas", "configure")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_actas_politicas.nueva_version(
        db, ctx, politica_id, _version(if_match)
    )
    db.commit()
    return resultado


@router.post(
    "/{politica_id}/activar",
    response_model=PoliticaActaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def activar(
    politica_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_actas", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_actas_politicas.activar(
        db, ctx, politica_id, _version(if_match)
    )
    db.commit()
    return resultado


@router.post(
    "/{politica_id}/cerrar",
    response_model=PoliticaActaDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def cerrar(
    politica_id: str,
    datos: PoliticaActaCerrarIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_actas", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_actas_politicas.cerrar(
        db, ctx, politica_id, _version(if_match), datos
    )
    db.commit()
    return resultado
