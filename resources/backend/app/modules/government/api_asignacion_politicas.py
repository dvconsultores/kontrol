from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_asignacion_politicas
from app.modules.government.api import _version
from app.modules.government.schemas_asignacion_politicas import (
    PoliticaAsignacionCatalogo,
    PoliticaAsignacionCerrarIn,
    PoliticaAsignacionDetalle,
    PoliticaAsignacionIn,
    PoliticaAsignacionListado,
    PoliticaAsignacionOpciones,
)
from app.modules.identity_access.models import User

router = APIRouter(
    prefix="/gobierno/ocupacion/politicas",
    tags=["gobierno"],
)


@router.get(
    "/catalogo",
    response_model=PoliticaAsignacionCatalogo,
)
def catalogo(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_asignacion_politicas.catalogo()


@router.get(
    "/opciones",
    response_model=PoliticaAsignacionOpciones,
)
def opciones(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_asignacion_politicas.opciones(db, ctx)


@router.get(
    "",
    response_model=PoliticaAsignacionListado,
)
def listar(
    estado: str | None = None,
    figura: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_asignacion_politicas.listar(db, ctx, estado, figura, q)


@router.get(
    "/{politica_id}",
    response_model=PoliticaAsignacionDetalle,
)
def detalle(
    politica_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_asignacion_politicas.detalle(db, ctx, politica_id)


@router.post(
    "",
    response_model=PoliticaAsignacionDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear(
    datos: PoliticaAsignacionIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "configure")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_asignacion_politicas.crear(db, ctx, datos)
    db.commit()
    return resultado


@router.put(
    "/{politica_id}",
    response_model=PoliticaAsignacionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def editar(
    politica_id: str,
    datos: PoliticaAsignacionIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "configure")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_asignacion_politicas.editar(
        db, ctx, politica_id, _version(if_match), datos
    )
    db.commit()
    return resultado


@router.post(
    "/{politica_id}/activar",
    response_model=PoliticaAsignacionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def activar(
    politica_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_asignacion_politicas.activar(
        db, ctx, politica_id, _version(if_match)
    )
    db.commit()
    return resultado


@router.post(
    "/{politica_id}/cerrar",
    response_model=PoliticaAsignacionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def cerrar(
    politica_id: str,
    datos: PoliticaAsignacionCerrarIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "revoke")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_asignacion_politicas.cerrar(
        db, ctx, politica_id, _version(if_match), datos
    )
    db.commit()
    return resultado


@router.post(
    "/{politica_id}/nueva-version",
    response_model=PoliticaAsignacionDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def nueva_version(
    politica_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "configure")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_asignacion_politicas.nueva_version(
        db, ctx, politica_id, _version(if_match)
    )
    db.commit()
    return resultado
