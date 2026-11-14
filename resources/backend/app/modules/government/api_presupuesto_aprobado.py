"""API del presupuesto aprobado (BUD-05)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_presupuesto_aprobado
from app.modules.government.api import _version
from app.modules.government.schemas_presupuesto_aprobado import (
    PresupuestoAprobadoVista,
    PresupuestoCreditoIn,
    PresupuestoExistenciasIn,
    PresupuestoIngresoIn,
    PresupuestoMontoIn,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/presupuesto/ejercicios", tags=["gobierno"])


def _version_if_match(if_match: str | None = Header(default=None, alias="If-Match")) -> int | None:
    return _version(if_match)


@router.get("/{year_id}/presupuesto-aprobado", response_model=PresupuestoAprobadoVista)
def vista_presupuesto_aprobado(
    year_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_presupuesto_aprobado.vista(db, ctx, year_id)


@router.post(
    "/{year_id}/presupuesto-aprobado/ingresos",
    response_model=PresupuestoAprobadoVista,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear_ingreso_presupuesto(
    year_id: str,
    datos: PresupuestoIngresoIn,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_aprobado.crear_ingreso(db, ctx, year_id, version, datos.model_dump())
    db.commit()
    return resultado


@router.patch(
    "/{year_id}/presupuesto-aprobado/ingresos/{ingreso_id}",
    response_model=PresupuestoAprobadoVista,
    dependencies=[Depends(require_write_allowed)],
)
def modificar_ingreso_presupuesto(
    year_id: str,
    ingreso_id: str,
    datos: PresupuestoMontoIn,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_aprobado.modificar_ingreso(db, ctx, year_id, version, ingreso_id, datos.model_dump())
    db.commit()
    return resultado


@router.delete(
    "/{year_id}/presupuesto-aprobado/ingresos/{ingreso_id}",
    response_model=PresupuestoAprobadoVista,
    dependencies=[Depends(require_write_allowed)],
)
def eliminar_ingreso_presupuesto(
    year_id: str,
    ingreso_id: str,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_aprobado.eliminar_ingreso(db, ctx, year_id, version, ingreso_id)
    db.commit()
    return resultado


@router.post(
    "/{year_id}/presupuesto-aprobado/creditos",
    response_model=PresupuestoAprobadoVista,
    status_code=201,
    dependencies=[Depends(require_write_allowed)],
)
def crear_credito_presupuesto(
    year_id: str,
    datos: PresupuestoCreditoIn,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_aprobado.crear_credito(db, ctx, year_id, version, datos.model_dump())
    db.commit()
    return resultado


@router.patch(
    "/{year_id}/presupuesto-aprobado/creditos/{credito_id}",
    response_model=PresupuestoAprobadoVista,
    dependencies=[Depends(require_write_allowed)],
)
def modificar_credito_presupuesto(
    year_id: str,
    credito_id: str,
    datos: PresupuestoMontoIn,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_aprobado.modificar_credito(db, ctx, year_id, version, credito_id, datos.model_dump())
    db.commit()
    return resultado


@router.delete(
    "/{year_id}/presupuesto-aprobado/creditos/{credito_id}",
    response_model=PresupuestoAprobadoVista,
    dependencies=[Depends(require_write_allowed)],
)
def eliminar_credito_presupuesto(
    year_id: str,
    credito_id: str,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_aprobado.eliminar_credito(db, ctx, year_id, version, credito_id)
    db.commit()
    return resultado


@router.put(
    "/{year_id}/presupuesto-aprobado/existencias-tesoro",
    response_model=PresupuestoAprobadoVista,
    dependencies=[Depends(require_write_allowed)],
)
def registrar_existencias_presupuesto(
    year_id: str,
    datos: PresupuestoExistenciasIn,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_aprobado.registrar_existencias(db, ctx, year_id, version, datos.model_dump())
    db.commit()
    return resultado


@router.delete(
    "/{year_id}/presupuesto-aprobado/existencias-tesoro",
    response_model=PresupuestoAprobadoVista,
    dependencies=[Depends(require_write_allowed)],
)
def eliminar_existencias_presupuesto(
    year_id: str,
    version: int | None = Depends(_version_if_match),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "manage")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_aprobado.eliminar_existencias(db, ctx, year_id, version)
    db.commit()
    return resultado
