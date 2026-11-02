"""API de las notificaciones administrativas y registros (DOC-04, PDD-DOC04-04).

Las notificaciones viven en el ejercicio (`/gobierno/notificaciones`); la empresa la fija el contexto y todo exige el módulo `gobierno`.
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
from app.modules.government import service_notificaciones
from app.modules.government.api import _version
from app.modules.government.schemas_notificaciones import (
    AnulacionIn,
    IntentoIn,
    ListaNotificaciones,
    NotificacionAdministrativaOut,
    NotificacionCambio,
    NotificacionIn,
    VersionesNotificacion,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/notificaciones", tags=["gobierno"])

_ESCRITURA = [Depends(require_write_allowed)]


@router.get("", response_model=ListaNotificaciones)
def list_notificaciones(
    anio: int = Query(ge=2000, le=2100),
    estado: Literal["PENDIENTE", "NOTIFICADA", "ANULADA"] | None = None,
    acto_id: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_notificaciones", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_notificaciones.listar_notificaciones(db, ctx, anio, estado, acto_id)


@router.get("/exportar")
def export_notificaciones(
    anio: int = Query(ge=2000, le=2100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_notificaciones", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    nombre, contenido = service_notificaciones.exportar_notificaciones_csv(db, ctx, anio)
    db.commit()
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post("", response_model=NotificacionAdministrativaOut, status_code=201, dependencies=_ESCRITURA)
def create_notificacion(
    body: NotificacionIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_notificaciones", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_notificaciones.crear_notificacion(db, ctx, body, str(user.id))
    db.commit()
    return datos


@router.get("/{notificacion_id}", response_model=NotificacionAdministrativaOut)
def get_notificacion(
    notificacion_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_notificaciones", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_notificaciones.obtener_notificacion(db, ctx, notificacion_id)


@router.patch("/{notificacion_id}", response_model=NotificacionAdministrativaOut, dependencies=_ESCRITURA)
def update_notificacion(
    notificacion_id: str,
    body: NotificacionCambio,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_notificaciones", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_notificaciones.modificar_notificacion(
        db, ctx, notificacion_id, body, _version(if_match), str(user.id)
    )
    db.commit()
    return datos


@router.post("/{notificacion_id}/anular", response_model=NotificacionAdministrativaOut, dependencies=_ESCRITURA)
def anular_notificacion(
    notificacion_id: str,
    body: AnulacionIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_notificaciones", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_notificaciones.anular_notificacion(
        db, ctx, notificacion_id, body, _version(if_match), user
    )
    db.commit()
    return datos


@router.post("/{notificacion_id}/intentos", response_model=NotificacionAdministrativaOut, dependencies=_ESCRITURA)
def registrar_intento(
    notificacion_id: str,
    body: IntentoIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_notificaciones", "record")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_notificaciones.registrar_intento(
        db, ctx, notificacion_id, body, _version(if_match), user
    )
    db.commit()
    return datos


@router.get("/{notificacion_id}/versiones", response_model=VersionesNotificacion)
def get_notificacion_versiones(
    notificacion_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_notificaciones", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_notificaciones.versiones_notificacion(db, ctx, notificacion_id)
