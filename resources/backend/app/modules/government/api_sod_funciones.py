"""API de funciones incompatibles del procedimiento de contratación (PROC-11, GOV-PROC-017)."""

from __future__ import annotations

import io
from datetime import date

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_sod_funciones
from app.modules.government.api import _version
from app.modules.government.schemas_sod_funciones import (
    ActivacionFuncionIn,
    CatalogoFunciones,
    CierreFuncionIn,
    ConflictoFuncion,
    ConflictosFuncionListado,
    EstadoReglaFuncion,
    FuncionProcedimiento,
    ReglaFuncionDetalle,
    ReglaFuncionIn,
    ReglasFuncionListado,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/sod/funciones", tags=["gobierno"])


@router.get("", response_model=CatalogoFunciones)
def catalogo(
    _user: User = Depends(require_permission("gobierno_sod", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_sod_funciones.catalogo()


@router.get("/reglas", response_model=ReglasFuncionListado)
def listar(
    estado: EstadoReglaFuncion | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_sod", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_sod_funciones.listar(db, ctx, estado)


@router.post(
    "/reglas",
    response_model=ReglaFuncionDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear(
    datos: ReglaFuncionIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_sod", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    regla = service_sod_funciones.crear(db, ctx, datos.model_dump())
    db.commit()
    return regla


@router.get("/reglas/{regla_id}", response_model=ReglaFuncionDetalle)
def detalle(
    regla_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_sod", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_sod_funciones.detalle(db, ctx, regla_id)


@router.post(
    "/reglas/{regla_id}/activar",
    response_model=ReglaFuncionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def activar(
    regla_id: str,
    datos: ActivacionFuncionIn | None = None,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_sod", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    regla = service_sod_funciones.activar(
        db, ctx, regla_id, _version(if_match), (datos or ActivacionFuncionIn()).model_dump()
    )
    db.commit()
    return regla


@router.post(
    "/reglas/{regla_id}/cerrar",
    response_model=ReglaFuncionDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def cerrar(
    regla_id: str,
    datos: CierreFuncionIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_sod", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    regla = service_sod_funciones.cerrar(db, ctx, regla_id, _version(if_match), datos.model_dump())
    db.commit()
    return regla


@router.get("/conflictos", response_model=ConflictosFuncionListado)
def conflictos(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    rol: FuncionProcedimiento | None = Query(None),
    expediente_id: str | None = Query(None, max_length=36),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_sod", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    desde, hasta = _periodo(desde, hasta)
    items = service_sod_funciones.conflictos_por_periodo(db, ctx, desde, hasta, rol, expediente_id)
    return ConflictosFuncionListado(items=items, total=len(items), desde=desde, hasta=hasta)


@router.get("/conflictos.csv")
def exportar_conflictos(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    rol: FuncionProcedimiento | None = Query(None),
    expediente_id: str | None = Query(None, max_length=36),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_sod", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    desde, hasta = _periodo(desde, hasta)
    nombre, contenido = service_sod_funciones.exportar_csv(db, ctx, desde, hasta, rol, expediente_id)
    db.commit()
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/expedientes/{expediente_id}", response_model=list[ConflictoFuncion])
def conflictos_de_expediente(
    expediente_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_expedientes", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_sod_funciones.conflictos_del_expediente(db, ctx, expediente_id)


def _periodo(desde: date | None, hasta: date | None) -> tuple[date, date]:
    from app.shared.clock import hoy_de_negocio

    hoy = hoy_de_negocio()
    return desde or date(hoy.year, 1, 1), hasta or hoy
