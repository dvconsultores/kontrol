from __future__ import annotations

import io
from datetime import date

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_ocupacion
from app.modules.government.api import _version
from app.modules.government.schemas_ocupacion import (
    AsignacionDetalle,
    AsignacionesListado,
    AsignacionIn,
    AvocarIn,
    CargoOcupacion,
    CatalogoOcupacion,
    DescartarIn,
    EstadoAsignacion,
    EstadoFuncionario,
    FiguraAsignacion,
    FinalizarIn,
    FuncionarioCambios,
    FuncionarioDetalle,
    FuncionarioIn,
    FuncionariosListado,
    OcupacionListado,
    OpcionesOcupacion,
    RevocarIn,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/ocupacion", tags=["gobierno"])


@router.get("/catalogo", response_model=CatalogoOcupacion)
def catalogo(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_ocupacion.catalogo()


@router.get("/opciones", response_model=OpcionesOcupacion)
def opciones(
    ejercicio: int = Query(..., ge=2000, le=2100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_ocupacion.opciones(db, ctx, ejercicio)


@router.get("/funcionarios", response_model=FuncionariosListado)
def listar_funcionarios(
    texto: str | None = Query(None, min_length=1, max_length=100),
    estado: EstadoFuncionario | None = Query(None),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_ocupacion.listar_funcionarios(db, ctx, texto, estado, pagina, por_pagina)


@router.post("/funcionarios", response_model=FuncionarioDetalle, status_code=201, dependencies=[Depends(require_write_allowed)])
def crear_funcionario(
    datos: FuncionarioIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    f = service_ocupacion.crear_funcionario(db, ctx, datos)
    db.commit()
    return service_ocupacion.detalle_funcionario(db, ctx, str(f.id))


@router.get("/funcionarios/{funcionario_id}", response_model=FuncionarioDetalle)
def detalle_funcionario(
    funcionario_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_ocupacion.detalle_funcionario(db, ctx, funcionario_id)


@router.patch("/funcionarios/{funcionario_id}", response_model=FuncionarioDetalle, dependencies=[Depends(require_write_allowed)])
def editar_funcionario(
    funcionario_id: str,
    datos: FuncionarioCambios,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_ocupacion.editar_funcionario(db, ctx, funcionario_id, _version(if_match), datos)
    db.commit()
    return service_ocupacion.detalle_funcionario(db, ctx, funcionario_id)


@router.get("/asignaciones", response_model=AsignacionesListado)
def listar_asignaciones(
    figura: FiguraAsignacion | None = Query(None),
    estado: EstadoAsignacion | None = Query(None),
    funcionario_id: str | None = Query(None, max_length=36),
    cargo_id: str | None = Query(None, max_length=36),
    fecha: date | None = Query(None),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_ocupacion.listar(
        db, ctx, figura, estado, funcionario_id, cargo_id, fecha, pagina, por_pagina
    )


@router.get("/asignaciones.csv")
def exportar_asignaciones_csv(
    figura: FiguraAsignacion | None = Query(None),
    estado: EstadoAsignacion | None = Query(None),
    funcionario_id: str | None = Query(None, max_length=36),
    cargo_id: str | None = Query(None, max_length=36),
    fecha: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    nombre, contenido = service_ocupacion.exportar_csv(
        db, ctx, figura, estado, funcionario_id, cargo_id, fecha
    )
    db.commit()
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post("/asignaciones", response_model=AsignacionDetalle, status_code=201, dependencies=[Depends(require_write_allowed)])
def crear_asignacion(
    datos: AsignacionIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    a = service_ocupacion.crear(db, ctx, datos)
    db.commit()
    return service_ocupacion.detalle(db, ctx, str(a.id))


@router.get("/asignaciones/{asignacion_id}", response_model=AsignacionDetalle)
def detalle_asignacion(
    asignacion_id: str,
    fecha: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_ocupacion.detalle(db, ctx, asignacion_id, fecha)


@router.patch("/asignaciones/{asignacion_id}", response_model=AsignacionDetalle, dependencies=[Depends(require_write_allowed)])
def editar_asignacion(
    asignacion_id: str,
    datos: AsignacionIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_ocupacion.editar(db, ctx, asignacion_id, _version(if_match), datos)
    db.commit()
    return service_ocupacion.detalle(db, ctx, asignacion_id)


@router.post("/asignaciones/{asignacion_id}/activar", response_model=AsignacionDetalle, dependencies=[Depends(require_write_allowed)])
def activar_asignacion(
    asignacion_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_ocupacion.activar(db, ctx, asignacion_id, _version(if_match))
    db.commit()
    return service_ocupacion.detalle(db, ctx, asignacion_id)


@router.post("/asignaciones/{asignacion_id}/descartar", response_model=AsignacionDetalle, dependencies=[Depends(require_write_allowed)])
def descartar_asignacion(
    asignacion_id: str,
    datos: DescartarIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_ocupacion.descartar(db, ctx, asignacion_id, _version(if_match), datos)
    db.commit()
    return service_ocupacion.detalle(db, ctx, asignacion_id)


@router.post("/asignaciones/{asignacion_id}/revocar", response_model=AsignacionDetalle, dependencies=[Depends(require_write_allowed)])
def revocar_asignacion(
    asignacion_id: str,
    datos: RevocarIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "revoke")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_ocupacion.revocar(db, ctx, asignacion_id, _version(if_match), datos)
    db.commit()
    return service_ocupacion.detalle(db, ctx, asignacion_id)


@router.post("/asignaciones/{asignacion_id}/finalizar", response_model=AsignacionDetalle, dependencies=[Depends(require_write_allowed)])
def finalizar_asignacion(
    asignacion_id: str,
    datos: FinalizarIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "revoke")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_ocupacion.finalizar(db, ctx, asignacion_id, _version(if_match), datos)
    db.commit()
    return service_ocupacion.detalle(db, ctx, asignacion_id)


@router.post("/asignaciones/{asignacion_id}/avocar", response_model=AsignacionDetalle, dependencies=[Depends(require_write_allowed)])
def avocar_asignacion(
    asignacion_id: str,
    datos: AvocarIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "revoke")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_ocupacion.avocar(db, ctx, asignacion_id, _version(if_match), datos)
    db.commit()
    return service_ocupacion.detalle(db, ctx, asignacion_id)


@router.get("/cargos", response_model=OcupacionListado)
def listar_cargos(
    ejercicio: int = Query(..., ge=2000, le=2100),
    fecha: date | None = Query(None),
    texto: str | None = Query(None, min_length=1, max_length=100),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_ocupacion.listar_ocupacion(db, ctx, ejercicio, fecha, texto, pagina, por_pagina)


@router.get("/cargos/{cargo_id}", response_model=CargoOcupacion)
def detalle_cargo(
    cargo_id: str,
    fecha: date | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ocupacion", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_ocupacion.cargo_ocupacion(db, ctx, cargo_id, fecha)
