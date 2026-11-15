"""API de tasas oficiales BCV de Gobierno (TRE-09)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_tasas
from app.modules.government.schemas_tasas import (
    AnulacionTasaOficialIn,
    CorreccionTasaOficialIn,
    TasaOficialDetalle,
    TasaOficialIn,
    TasaOficialOut,
    TasasOficialesVista,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/tesoreria/tasas", tags=["gobierno"])


@router.get("", response_model=TasasOficialesVista)
def listar_tasas(
    moneda: str | None = None,
    estado: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_tasas", "view")),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_tasas.listar(db, ctx, moneda, estado, desde, hasta)


@router.get("/{tasa_id}", response_model=TasaOficialDetalle)
def ver_tasa(
    tasa_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_tasas", "view")),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_tasas.detalle(db, ctx, tasa_id)


@router.post(
    "",
    response_model=TasaOficialOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_allowed)],
)
def registrar_tasa(
    cuerpo: TasaOficialIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_tasas", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_tasas.crear(db, ctx, user, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post(
    "/{tasa_id}/correccion",
    response_model=TasaOficialOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_allowed)],
)
def corregir_tasa(
    tasa_id: str,
    cuerpo: CorreccionTasaOficialIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_tasas", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_tasas.corregir(db, ctx, user, tasa_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post(
    "/{tasa_id}/aprobar",
    response_model=TasaOficialOut,
    dependencies=[Depends(require_write_allowed)],
)
def aprobar_tasa(
    tasa_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_tasas", "approve")),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_tasas.aprobar(db, ctx, user, tasa_id)
    db.commit()
    return resultado


@router.post(
    "/{tasa_id}/anular",
    response_model=TasaOficialOut,
    dependencies=[Depends(require_write_allowed)],
)
def anular_tasa(
    tasa_id: str,
    cuerpo: AnulacionTasaOficialIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_tasas", "approve")),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_tasas.anular(db, ctx, user, tasa_id, cuerpo.model_dump())
    db.commit()
    return resultado
