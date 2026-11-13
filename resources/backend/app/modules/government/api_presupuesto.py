"""API del módulo de presupuesto gubernamental (BUD-01, BUD-02)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Header, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_presupuesto
from app.modules.government.api import _version
from app.modules.government.schemas_presupuesto import (
    PresupuestoCategoriaCambioIn,
    PresupuestoCategoriaIn,
    PresupuestoCierreIn,
    PresupuestoClasificadorIn,
    PresupuestoEjercicioDetalle,
    PresupuestoEjercicioIn,
    PresupuestoEjercicioListado,
    PresupuestoFundamentoIn,
    PresupuestoNivelesIn,
    PresupuestoPartidaIn,
    PresupuestoPartidasListado,
    PresupuestoPrecompromisoIn,
    PresupuestoTipoPartida,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/presupuesto/ejercicios", tags=["gobierno"])


@router.get("", response_model=PresupuestoEjercicioListado)
def listar(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_presupuesto.listar(db, ctx)


@router.post(
    "",
    response_model=PresupuestoEjercicioDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear(
    datos: PresupuestoEjercicioIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    ejercicio = service_presupuesto.crear(db, ctx, datos.anio)
    db.commit()
    return ejercicio


@router.get("/{year_id}", response_model=PresupuestoEjercicioDetalle)
def detalle(
    year_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_presupuesto.detalle(db, ctx, year_id)


@router.put(
    "/{year_id}/niveles",
    response_model=PresupuestoEjercicioDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def configurar_niveles(
    year_id: str,
    datos: PresupuestoNivelesIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    ejercicio = service_presupuesto.configurar_niveles(
        db, ctx, year_id, _version(if_match), [n.nombre for n in datos.niveles]
    )
    db.commit()
    return ejercicio


@router.post(
    "/{year_id}/categorias",
    response_model=PresupuestoEjercicioDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear_categoria(
    year_id: str,
    datos: PresupuestoCategoriaIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    ejercicio = service_presupuesto.crear_categoria(db, ctx, year_id, _version(if_match), datos.model_dump())
    db.commit()
    return ejercicio


@router.patch(
    "/{year_id}/categorias/{categoria_id}",
    response_model=PresupuestoEjercicioDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def modificar_categoria(
    year_id: str,
    categoria_id: str,
    datos: PresupuestoCategoriaCambioIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    ejercicio = service_presupuesto.modificar_categoria(
        db, ctx, year_id, _version(if_match), categoria_id, datos.denominacion
    )
    db.commit()
    return ejercicio


@router.delete(
    "/{year_id}/categorias/{categoria_id}",
    response_model=PresupuestoEjercicioDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def eliminar_categoria(
    year_id: str,
    categoria_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    ejercicio = service_presupuesto.eliminar_categoria(db, ctx, year_id, _version(if_match), categoria_id)
    db.commit()
    return ejercicio


@router.put(
    "/{year_id}/clasificador",
    response_model=PresupuestoEjercicioDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def registrar_clasificador(
    year_id: str,
    datos: PresupuestoClasificadorIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    ejercicio = service_presupuesto.registrar_clasificador(db, ctx, year_id, _version(if_match), datos.model_dump())
    db.commit()
    return ejercicio


@router.get("/{year_id}/clasificador/partidas", response_model=PresupuestoPartidasListado)
def listar_partidas(
    year_id: str,
    tipo: PresupuestoTipoPartida | None = Query(None),
    q: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_presupuesto.listar_partidas(db, ctx, year_id, tipo, q)


@router.post(
    "/{year_id}/clasificador/partidas",
    response_model=PresupuestoEjercicioDetalle,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear_partida(
    year_id: str,
    datos: PresupuestoPartidaIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    ejercicio = service_presupuesto.crear_partida(db, ctx, year_id, _version(if_match), datos.model_dump())
    db.commit()
    return ejercicio


@router.delete(
    "/{year_id}/clasificador/partidas/{partida_id}",
    response_model=PresupuestoEjercicioDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def eliminar_partida(
    year_id: str,
    partida_id: str,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    ejercicio = service_presupuesto.eliminar_partida(db, ctx, year_id, _version(if_match), partida_id)
    db.commit()
    return ejercicio


@router.post(
    "/{year_id}/clasificador/importar",
    response_model=PresupuestoEjercicioDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def importar_partidas(
    year_id: str,
    archivo: UploadFile = File(...),
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    ejercicio = service_presupuesto.importar_partidas(
        db, ctx, year_id, _version(if_match), archivo.file.read()
    )
    db.commit()
    return ejercicio


@router.post(
    "/{year_id}/aprobar",
    response_model=PresupuestoEjercicioDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def aprobar(
    year_id: str,
    datos: PresupuestoFundamentoIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "approve")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    ejercicio = service_presupuesto.aprobar(db, ctx, year_id, _version(if_match), datos.model_dump())
    db.commit()
    return ejercicio


@router.post(
    "/{year_id}/reconducir",
    response_model=PresupuestoEjercicioDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def reconducir(
    year_id: str,
    datos: PresupuestoFundamentoIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "approve")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    ejercicio = service_presupuesto.reconducir(db, ctx, year_id, _version(if_match), datos.model_dump())
    db.commit()
    return ejercicio


@router.post(
    "/{year_id}/cerrar",
    response_model=PresupuestoEjercicioDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def cerrar(
    year_id: str,
    datos: PresupuestoCierreIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "close")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    ejercicio = service_presupuesto.cerrar(db, ctx, year_id, _version(if_match), datos.model_dump())
    db.commit()
    return ejercicio


@router.post(
    "/{year_id}/precompromiso",
    response_model=PresupuestoEjercicioDetalle,
    dependencies=[Depends(require_write_allowed)],
)
def cambiar_precompromiso(
    year_id: str,
    datos: PresupuestoPrecompromisoIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "approve")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    ejercicio = service_presupuesto.cambiar_precompromiso(
        db, ctx, year_id, _version(if_match), datos.model_dump()
    )
    db.commit()
    return ejercicio
