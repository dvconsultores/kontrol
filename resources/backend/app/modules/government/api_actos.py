"""API de los actos administrativos con autoridad, motivación y eficacia (DOC-02, GOV-DOC-003).

Los actos viven en el ejercicio (`/gobierno/actos`); la empresa la fija el contexto y todo exige el módulo `gobierno`.
"""

from __future__ import annotations

import io
from datetime import date

from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import (
    require_module,
    require_permission,
    require_write_allowed,
)
from app.modules.government import service_actos
from app.modules.government.api import _version
from app.modules.government.schemas_actos import (
    ActoCambio,
    ActoIn,
    ActoOut,
    CorreccionIn,
    EficaciaIn,
    EmisionIn,
    ListaActos,
    ListaAutoridades,
    ReferenciaIn,
    VersionesActo,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/actos", tags=["government"])

_ESCRITURA = [Depends(require_write_allowed)]


@router.get("", response_model=ListaActos)
def list_actos(
    anio: int = Query(ge=1900, le=2100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_actos", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_actos.listar_actos(db, ctx, anio)


@router.post("", response_model=ActoOut, status_code=201, dependencies=_ESCRITURA)
def create_acto(
    body: ActoIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_actos", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_actos.crear_acto(db, ctx, body, str(user.id))
    db.commit()
    return datos


@router.get("/exportar")
def export_actos(
    anio: int = Query(ge=1900, le=2100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_actos", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    nombre, contenido = service_actos.exportar_actos_csv(db, ctx, anio)
    db.commit()
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/autoridades", response_model=ListaAutoridades)
def autoridades(
    fecha: date,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_actos", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_actos.autoridades(db, ctx, fecha)


@router.get("/{acto_id}", response_model=ActoOut)
def get_acto(
    acto_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_actos", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_actos.obtener_acto(db, ctx, acto_id)


@router.patch("/{acto_id}", response_model=ActoOut, dependencies=_ESCRITURA)
def update_acto(
    acto_id: str,
    body: ActoCambio,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_actos", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_actos.modificar_acto(db, ctx, acto_id, body, _version(if_match), str(user.id))
    db.commit()
    return datos


@router.delete("/{acto_id}", status_code=204, dependencies=_ESCRITURA)
def delete_acto(
    acto_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_actos", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_actos.eliminar_acto(db, ctx, acto_id, _version(if_match), str(user.id))
    db.commit()
    return Response(status_code=204)


@router.post("/{acto_id}/emitir", response_model=ActoOut, dependencies=_ESCRITURA)
def emit_acto(
    acto_id: str,
    body: EmisionIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_actos", "issue")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_actos.emitir_acto(db, ctx, acto_id, body, _version(if_match), user)
    db.commit()
    return datos


@router.post("/{acto_id}/eficacia", response_model=ActoOut, dependencies=_ESCRITURA)
def register_eficacia(
    acto_id: str,
    body: EficaciaIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_actos", "issue")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_actos.registrar_eficacia(db, ctx, acto_id, body, _version(if_match), user)
    db.commit()
    return datos


@router.post("/{acto_id}/corregir", response_model=ActoOut, dependencies=_ESCRITURA)
def correct_acto(
    acto_id: str,
    body: CorreccionIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_actos", "issue")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_actos.corregir_acto(db, ctx, acto_id, body, _version(if_match), user)
    db.commit()
    return datos


@router.post("/{acto_id}/revocar", response_model=ActoOut, dependencies=_ESCRITURA)
def revoke_acto(
    acto_id: str,
    body: ReferenciaIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_actos", "annul")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_actos.revocar_acto(db, ctx, acto_id, body, _version(if_match), user)
    db.commit()
    return datos


@router.post("/{acto_id}/anular", response_model=ActoOut, dependencies=_ESCRITURA)
def nullify_acto(
    acto_id: str,
    body: ReferenciaIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_actos", "annul")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_actos.anular_acto(db, ctx, acto_id, body, _version(if_match), user)
    db.commit()
    return datos


@router.get("/{acto_id}/versiones", response_model=VersionesActo)
def get_acto_versiones(
    acto_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_actos", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_actos.versiones_acto(db, ctx, acto_id)
