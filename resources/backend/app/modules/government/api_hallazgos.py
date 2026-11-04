"""API de hallazgos y acciones correctivas de Gobierno (CTL-06, GOV-CTL-06).

Expone el ciclo de vida de los hallazgos: registro, recomendaciones, acciones correctivas, plan de remediación, ejecución,
avances, presentación, verificación y devolución, además del listado, catálogo de cargos responsables y exportación CSV.
"""

from __future__ import annotations

import io
from typing import Literal

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import (
    require_module,
    require_permission,
    require_write_allowed,
)
from app.modules.government import service_hallazgos
from app.modules.government.api import _version
from app.modules.government.schemas_hallazgos import (
    AccionIn,
    AvanceIn,
    CargosResponsables,
    DevolucionIn,
    HallazgoDetalle,
    HallazgoIn,
    HallazgosFiltros,
    HallazgosListado,
    RecomendacionIn,
    VerificacionIn,
)
from app.modules.identity_access.models import User

EstadoHallazgo = Literal[
    "ABIERTO",
    "PLAN_DE_ACCION",
    "EN_REMEDIACION",
    "EVIDENCIA_PRESENTADA",
    "CERRADO",
]
RiesgoHallazgo = Literal["ALTO", "MEDIO", "BAJO"]
OrigenHallazgo = Literal["MUESTRA", "INDEPENDIENTE"]

router = APIRouter(prefix="/gobierno/hallazgos", tags=["gobierno"])


@router.get("", response_model=HallazgosListado)
def listar(
    estado: EstadoHallazgo | None = Query(None),
    riesgo: RiesgoHallazgo | None = Query(None),
    origen: OrigenHallazgo | None = Query(None),
    vencidas: bool = False,
    texto: str | None = Query(None, min_length=1, max_length=100),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_hallazgos", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_hallazgos.listar(
        db,
        ctx,
        HallazgosFiltros(estado=estado, riesgo=riesgo, origen=origen, vencidas=vencidas, texto=texto),
        pagina=pagina,
        por_pagina=por_pagina,
    )


@router.get("/cargos-responsables", response_model=CargosResponsables)
def cargos_responsables(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_hallazgos", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_hallazgos.cargos_responsables(db, ctx)


@router.get("/exportar")
def exportar(
    estado: EstadoHallazgo | None = Query(None),
    riesgo: RiesgoHallazgo | None = Query(None),
    origen: OrigenHallazgo | None = Query(None),
    vencidas: bool = False,
    texto: str | None = Query(None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_hallazgos", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    nombre, contenido = service_hallazgos.exportar_csv(
        db,
        ctx,
        HallazgosFiltros(estado=estado, riesgo=riesgo, origen=origen, vencidas=vencidas, texto=texto),
    )
    db.commit()
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post(
    "",
    response_model=HallazgoDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def registrar(
    datos: HallazgoIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_hallazgos", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_hallazgos.registrar(db, ctx, datos)
    db.commit()
    return resultado


@router.get("/{hallazgo_id}", response_model=HallazgoDetalle)
def detalle(
    hallazgo_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_hallazgos", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_hallazgos.detalle(db, ctx, hallazgo_id)


@router.post(
    "/{hallazgo_id}/recomendaciones",
    response_model=HallazgoDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def agregar_recomendacion(
    hallazgo_id: str,
    datos: RecomendacionIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_hallazgos", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_hallazgos.agregar_recomendacion(db, ctx, hallazgo_id, datos, _version(if_match))
    db.commit()
    return resultado


@router.post(
    "/{hallazgo_id}/acciones",
    response_model=HallazgoDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def agregar_accion(
    hallazgo_id: str,
    datos: AccionIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_hallazgos", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_hallazgos.agregar_accion(db, ctx, hallazgo_id, datos, _version(if_match))
    db.commit()
    return resultado


@router.post(
    "/{hallazgo_id}/plan",
    response_model=HallazgoDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def registrar_plan(
    hallazgo_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_hallazgos", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_hallazgos.registrar_plan(db, ctx, hallazgo_id, _version(if_match))
    db.commit()
    return resultado


@router.post(
    "/{hallazgo_id}/ejecucion",
    response_model=HallazgoDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def iniciar_ejecucion(
    hallazgo_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_hallazgos", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_hallazgos.iniciar_ejecucion(db, ctx, hallazgo_id, _version(if_match))
    db.commit()
    return resultado


@router.post(
    "/{hallazgo_id}/acciones/{accion_id}/avances",
    response_model=HallazgoDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def registrar_avance(
    hallazgo_id: str,
    accion_id: str,
    datos: AvanceIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_hallazgos", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_hallazgos.registrar_avance(db, ctx, hallazgo_id, accion_id, datos, _version(if_match))
    db.commit()
    return resultado


@router.post(
    "/{hallazgo_id}/presentar",
    response_model=HallazgoDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def presentar(
    hallazgo_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_hallazgos", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_hallazgos.presentar(db, ctx, hallazgo_id, _version(if_match))
    db.commit()
    return resultado


@router.post(
    "/{hallazgo_id}/verificar",
    response_model=HallazgoDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def verificar(
    hallazgo_id: str,
    datos: VerificacionIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_hallazgos", "verify")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_hallazgos.verificar(db, ctx, hallazgo_id, datos, _version(if_match), user)
    db.commit()
    return resultado


@router.post(
    "/{hallazgo_id}/devolver",
    response_model=HallazgoDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def devolver(
    hallazgo_id: str,
    datos: DevolucionIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_hallazgos", "verify")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_hallazgos.devolver(db, ctx, hallazgo_id, datos, _version(if_match))
    db.commit()
    return resultado
