from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_comision_politicas
from app.modules.government.api import _version
from app.modules.government.schemas_comision_politicas import (
    PoliticaCerrarIn,
    PoliticaComisionCatalogo,
    PoliticaComisionDetalle,
    PoliticaComisionIn,
    PoliticaComisionOpciones,
    PoliticasComisionListado,
)
from app.modules.identity_access.models import User

router = APIRouter(
    prefix="/gobierno/contrataciones/politicas-comision",
    tags=["gobierno"],
)


@router.get(
    "/catalogo",
    response_model=PoliticaComisionCatalogo,
)
def catalogo(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_comision_politicas.catalogo()


@router.get(
    "/opciones",
    response_model=PoliticaComisionOpciones,
)
def opciones(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_comision_politicas.opciones(db, ctx)


@router.get(
    "",
    response_model=PoliticasComisionListado,
)
def listar(
    estado: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_comision_politicas.listar(db, ctx, estado, q)


@router.get(
    "/{politica_id}",
    response_model=PoliticaComisionDetalle,
)
def detalle(
    politica_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_comision_politicas.detalle(db, ctx, politica_id)


@router.post(
    "",
    response_model=PoliticaComisionDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear(
    datos: PoliticaComisionIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "configure")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_comision_politicas.crear(db, ctx, datos)
    db.commit()
    return resultado


@router.put(
    "/{politica_id}",
    response_model=PoliticaComisionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def editar(
    politica_id: str,
    datos: PoliticaComisionIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "configure")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_comision_politicas.editar(
        db, ctx, politica_id, _version(if_match), datos
    )
    db.commit()
    return resultado


@router.post(
    "/{politica_id}/activar",
    response_model=PoliticaComisionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def activar(
    politica_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_comision_politicas.activar(
        db, ctx, politica_id, _version(if_match)
    )
    db.commit()
    return resultado


@router.post(
    "/{politica_id}/cerrar",
    response_model=PoliticaComisionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def cerrar(
    politica_id: str,
    datos: PoliticaCerrarIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "close")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_comision_politicas.cerrar(
        db, ctx, politica_id, _version(if_match), datos
    )
    db.commit()
    return resultado


@router.post(
    "/{politica_id}/nueva-version",
    response_model=PoliticaComisionDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def nueva_version(
    politica_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_comisiones", "configure")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_comision_politicas.nueva_version(
        db, ctx, politica_id, _version(if_match)
    )
    db.commit()
    return resultado
