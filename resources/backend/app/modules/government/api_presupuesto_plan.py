"""API del plan operativo y fuentes de financiamiento (BUD-03, BUD-04)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_presupuesto_fuentes, service_presupuesto_plan
from app.modules.government.api import _version
from app.modules.government.schemas_presupuesto_plan import (
    PresupuestoFuenteCambioIn,
    PresupuestoFuenteIn,
    PresupuestoFuentesVista,
    PresupuestoMetaCambioIn,
    PresupuestoMetaIn,
    PresupuestoObjetivoCambioIn,
    PresupuestoObjetivoIn,
    PresupuestoPlanIn,
    PresupuestoPlanVista,
    PresupuestoRestriccionIn,
    PresupuestoVinculoIn,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/presupuesto/ejercicios", tags=["gobierno"])


def _version_if_match(if_match: str | None = Header(default=None, alias="If-Match")) -> int | None:
    return _version(if_match)


@router.get("/{year_id}/plan", response_model=PresupuestoPlanVista)
def vista_plan(
    year_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_presupuesto_plan.vista_plan(db, ctx, year_id)


@router.put(
    "/{year_id}/plan",
    response_model=PresupuestoPlanVista,
    dependencies=[Depends(require_write_allowed)],
)
def registrar_plan(
    year_id: str,
    datos: PresupuestoPlanIn,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_plan.registrar_plan(db, ctx, year_id, version, datos.model_dump())
    db.commit()
    return resultado


@router.post(
    "/{year_id}/plan/objetivos",
    response_model=PresupuestoPlanVista,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear_objetivo(
    year_id: str,
    datos: PresupuestoObjetivoIn,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_plan.crear_objetivo(db, ctx, year_id, version, datos.model_dump())
    db.commit()
    return resultado


@router.patch(
    "/{year_id}/plan/objetivos/{objetivo_id}",
    response_model=PresupuestoPlanVista,
    dependencies=[Depends(require_write_allowed)],
)
def modificar_objetivo(
    year_id: str,
    objetivo_id: str,
    datos: PresupuestoObjetivoCambioIn,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_plan.modificar_objetivo(db, ctx, year_id, version, objetivo_id, datos.descripcion)
    db.commit()
    return resultado


@router.delete(
    "/{year_id}/plan/objetivos/{objetivo_id}",
    response_model=PresupuestoPlanVista,
    dependencies=[Depends(require_write_allowed)],
)
def eliminar_objetivo(
    year_id: str,
    objetivo_id: str,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_plan.eliminar_objetivo(db, ctx, year_id, version, objetivo_id)
    db.commit()
    return resultado


@router.put(
    "/{year_id}/categorias/{categoria_id}/vinculo",
    response_model=PresupuestoPlanVista,
    dependencies=[Depends(require_write_allowed)],
)
def vincular_categoria(
    year_id: str,
    categoria_id: str,
    datos: PresupuestoVinculoIn,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_plan.vincular_categoria(db, ctx, year_id, version, categoria_id, datos.model_dump())
    db.commit()
    return resultado


@router.post(
    "/{year_id}/plan/metas",
    response_model=PresupuestoPlanVista,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear_meta(
    year_id: str,
    datos: PresupuestoMetaIn,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_plan.crear_meta(db, ctx, year_id, version, datos.model_dump())
    db.commit()
    return resultado


@router.patch(
    "/{year_id}/plan/metas/{meta_id}",
    response_model=PresupuestoPlanVista,
    dependencies=[Depends(require_write_allowed)],
)
def modificar_meta(
    year_id: str,
    meta_id: str,
    datos: PresupuestoMetaCambioIn,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_plan.modificar_meta(db, ctx, year_id, version, meta_id, datos.model_dump())
    db.commit()
    return resultado


@router.delete(
    "/{year_id}/plan/metas/{meta_id}",
    response_model=PresupuestoPlanVista,
    dependencies=[Depends(require_write_allowed)],
)
def eliminar_meta(
    year_id: str,
    meta_id: str,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_plan.eliminar_meta(db, ctx, year_id, version, meta_id)
    db.commit()
    return resultado


@router.get("/{year_id}/fuentes", response_model=PresupuestoFuentesVista)
def vista_fuentes(
    year_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_presupuesto_fuentes.vista_fuentes(db, ctx, year_id)


@router.post(
    "/{year_id}/fuentes",
    response_model=PresupuestoFuentesVista,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear_fuente(
    year_id: str,
    datos: PresupuestoFuenteIn,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_fuentes.crear_fuente(db, ctx, year_id, version, datos.model_dump())
    db.commit()
    return resultado


@router.patch(
    "/{year_id}/fuentes/{fuente_id}",
    response_model=PresupuestoFuentesVista,
    dependencies=[Depends(require_write_allowed)],
)
def modificar_fuente(
    year_id: str,
    fuente_id: str,
    datos: PresupuestoFuenteCambioIn,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_fuentes.modificar_fuente(db, ctx, year_id, version, fuente_id, datos.model_dump())
    db.commit()
    return resultado


@router.delete(
    "/{year_id}/fuentes/{fuente_id}",
    response_model=PresupuestoFuentesVista,
    dependencies=[Depends(require_write_allowed)],
)
def eliminar_fuente(
    year_id: str,
    fuente_id: str,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_fuentes.eliminar_fuente(db, ctx, year_id, version, fuente_id)
    db.commit()
    return resultado


@router.post(
    "/{year_id}/fuentes/{fuente_id}/restricciones",
    response_model=PresupuestoFuentesVista,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def agregar_restriccion(
    year_id: str,
    fuente_id: str,
    datos: PresupuestoRestriccionIn,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_fuentes.agregar_restriccion(
        db, ctx, year_id, version, fuente_id, datos.model_dump()
    )
    db.commit()
    return resultado


@router.delete(
    "/{year_id}/fuentes/{fuente_id}/restricciones/{restriccion_id}",
    response_model=PresupuestoFuentesVista,
    dependencies=[Depends(require_write_allowed)],
)
def eliminar_restriccion(
    year_id: str,
    fuente_id: str,
    restriccion_id: str,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_fuentes.eliminar_restriccion(
        db, ctx, year_id, version, fuente_id, restriccion_id
    )
    db.commit()
    return resultado
