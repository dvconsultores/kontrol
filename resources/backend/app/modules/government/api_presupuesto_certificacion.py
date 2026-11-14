"""API de disponibilidad y certificación (BUD-06)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_presupuesto_certificacion
from app.modules.government.schemas_presupuesto_certificacion import (
    AnulacionIn,
    CertificacionesVista,
    CertificacionIn,
    CertificacionOut,
    DisponibilidadVista,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/presupuesto/ejercicios", tags=["gobierno"])


@router.get("/{year_id}/disponibilidad", response_model=DisponibilidadVista)
def vista_disponibilidad(
    year_id: str,
    categoria_id: str | None = Query(default=None),
    unidad_id: str | None = Query(default=None),
    partida_id: str | None = Query(default=None),
    fuente_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    filtros = {
        "categoria_id": categoria_id,
        "unidad_id": unidad_id,
        "partida_id": partida_id,
        "fuente_id": fuente_id,
    }
    return service_presupuesto_certificacion.disponibilidad(db, ctx, year_id, filtros)


@router.get("/{year_id}/certificaciones", response_model=CertificacionesVista)
def listar_certificaciones(
    year_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_presupuesto_certificacion.listar(db, ctx, year_id)


@router.get("/{year_id}/certificaciones/{certificacion_id}", response_model=CertificacionOut)
def ver_certificacion(
    year_id: str,
    certificacion_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_presupuesto_certificacion.detalle(db, ctx, year_id, certificacion_id)


@router.post(
    "/{year_id}/certificaciones",
    response_model=CertificacionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_allowed)],
)
def emitir_certificacion(
    year_id: str,
    cuerpo: CertificacionIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_presupuesto", "certify")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_certificacion.emitir(db, ctx, user, year_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.post(
    "/{year_id}/certificaciones/{certificacion_id}/anular",
    response_model=CertificacionOut,
    dependencies=[Depends(require_write_allowed)],
)
def anular_certificacion(
    year_id: str,
    certificacion_id: str,
    cuerpo: AnulacionIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_presupuesto", "certify")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    resultado = service_presupuesto_certificacion.anular(db, ctx, user, year_id, certificacion_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.get("/{year_id}/certificaciones/{certificacion_id}/documento")
def descargar_certificacion(
    year_id: str,
    certificacion_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_presupuesto", "view")),
    _modulo: None = Depends(require_module("gobierno")),
):
    file_name, stream, file_size = service_presupuesto_certificacion.abrir_documento(
        db, ctx, year_id, certificacion_id
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
