"""API de la estructura organizativa por ejercicio (GOV-0-02, ORG-02).

La empresa del contexto es el contenedor de la estructura; todo `/gobierno/estructuras*`
exige el módulo `gobierno` de la licencia.
"""

from __future__ import annotations

import io

from fastapi import APIRouter, Depends, Header, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import (
    require_module,
    require_permission,
    require_write_allowed,
)
from app.modules.government import service_estructura
from app.modules.government.api import _version
from app.modules.government.schemas_estructura import (
    DesactivacionIn,
    EstructuraIn,
    EstructuraOut,
    ListaEstructuras,
    UnidadCambio,
    UnidadIn,
    UnidadOut,
    VersionesUnidad,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/estructuras", tags=["government"])

_ESCRITURA = [Depends(require_write_allowed)]


@router.get("", response_model=ListaEstructuras)
def list_estructuras(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_estructura", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_estructura.listar(db, ctx)


@router.post("", response_model=EstructuraOut, status_code=201, dependencies=_ESCRITURA)
def create_estructura(
    body: EstructuraIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_estructura", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_estructura.abrir(db, ctx, body)
    db.commit()
    return datos


@router.get("/{ejercicio}", response_model=EstructuraOut)
def get_estructura(
    ejercicio: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_estructura", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_estructura.obtener(db, ctx, ejercicio)


@router.post("/{ejercicio}/publicar", response_model=EstructuraOut, dependencies=_ESCRITURA)
def publish_estructura(
    ejercicio: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_estructura", "publish")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_estructura.publicar(db, ctx, ejercicio, _version(if_match))
    db.commit()
    return datos


@router.post("/{ejercicio}/cerrar", response_model=EstructuraOut, dependencies=_ESCRITURA)
def close_estructura(
    ejercicio: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_estructura", "close")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_estructura.cerrar(db, ctx, ejercicio, _version(if_match))
    db.commit()
    return datos


@router.get("/{ejercicio}/exportar")
def export_estructura(
    ejercicio: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_estructura", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    nombre, contenido = service_estructura.exportar_csv(db, ctx, ejercicio)
    db.commit()
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post("/{ejercicio}/unidades", response_model=UnidadOut, status_code=201, dependencies=_ESCRITURA)
def create_unidad(
    ejercicio: int,
    body: UnidadIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_estructura", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_estructura.crear_unidad(db, ctx, ejercicio, body)
    db.commit()
    return datos


@router.patch("/{ejercicio}/unidades/{unidad_id}", response_model=UnidadOut, dependencies=_ESCRITURA)
def update_unidad(
    ejercicio: int,
    unidad_id: str,
    body: UnidadCambio,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_estructura", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_estructura.modificar_unidad(db, ctx, ejercicio, unidad_id, body, _version(if_match))
    db.commit()
    return datos


@router.post("/{ejercicio}/unidades/{unidad_id}/desactivar", response_model=UnidadOut, dependencies=_ESCRITURA)
def deactivate_unidad(
    ejercicio: int,
    unidad_id: str,
    body: DesactivacionIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_estructura", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_estructura.desactivar_unidad(db, ctx, ejercicio, unidad_id, body, _version(if_match))
    db.commit()
    return datos


@router.delete("/{ejercicio}/unidades/{unidad_id}", status_code=204, dependencies=_ESCRITURA)
def delete_unidad(
    ejercicio: int,
    unidad_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_estructura", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_estructura.eliminar_unidad(db, ctx, ejercicio, unidad_id, _version(if_match))
    db.commit()
    return Response(status_code=204)


@router.get("/{ejercicio}/unidades/{unidad_id}/versiones", response_model=VersionesUnidad)
def get_unidad_versiones(
    ejercicio: int,
    unidad_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_estructura", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_estructura.versiones_unidad(db, ctx, ejercicio, unidad_id)
