"""API del compromiso presupuestario (BUD-08)."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_presupuesto_compromiso
from app.modules.government.schemas_presupuesto_compromiso import (
    AnulacionCompromisoIn,
    CompromisoIn,
    CompromisoOut,
    CompromisosVista,
    OpcionesCompromisoVista,
    VerificacionLimiteOut,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/presupuesto/ejercicios", tags=["gobierno"])


@router.get(
    "/{year_id}/compromisos/opciones",
    response_model=OpcionesCompromisoVista,
)
def vista_opciones_compromiso(
    year_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_presupuesto_compromiso.opciones(db, ctx, year_id)


@router.get(
    "/{year_id}/compromisos",
    response_model=CompromisosVista,
)
def listar_compromisos(
    year_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_presupuesto_compromiso.listar(db, ctx, year_id)


@router.get(
    "/{year_id}/compromisos/verificacion-limite",
    response_model=VerificacionLimiteOut,
)
def verificacion_limite(
    year_id: str,
    autoridad_cargo_id: str = Query(max_length=36),
    total: Decimal = Query(gt=0, max_digits=18, decimal_places=2),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_presupuesto_compromiso.verificacion_limite(
        db, ctx, year_id, autoridad_cargo_id, total
    )


@router.get(
    "/{year_id}/compromisos/{compromiso_id}",
    response_model=CompromisoOut,
)
def ver_compromiso(
    year_id: str,
    compromiso_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_presupuesto_compromiso.detalle(db, ctx, year_id, compromiso_id)


@router.post(
    "/{year_id}/compromisos",
    response_model=CompromisoOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_allowed)],
)
def registrar_compromiso(
    year_id: str,
    cuerpo: CompromisoIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_presupuesto", "commit")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_compromiso.emitir(db, ctx, user, year_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post(
    "/{year_id}/compromisos/{compromiso_id}/anular",
    response_model=CompromisoOut,
    dependencies=[Depends(require_write_allowed)],
)
def anular_compromiso(
    year_id: str,
    compromiso_id: str,
    cuerpo: AnulacionCompromisoIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_presupuesto", "commit")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_compromiso.anular(
        db, ctx, user, year_id, compromiso_id, cuerpo.model_dump()
    )
    db.commit()
    return resultado


@router.get(
    "/{year_id}/compromisos/{compromiso_id}/documento",
)
def descargar_compromiso(
    year_id: str,
    compromiso_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    _modulo: None = Depends(require_module("gobierno")),
):
    file_name, stream, file_size = service_presupuesto_compromiso.abrir_documento(
        db, ctx, year_id, compromiso_id
    )
    db.commit()
    disposition = f'attachment; filename="{file_name}"'
    return StreamingResponse(
        stream,
        media_type="application/pdf",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": disposition,
            "Content-Length": str(file_size),
        },
    )
