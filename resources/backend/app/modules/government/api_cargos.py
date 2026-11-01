"""API de los cargos con competencias y límites de firma/aprobación (GOV-0-03, ORG-03).

Los cargos viven en la estructura del ejercicio (`/gobierno/estructuras/{ejercicio}/cargos`); la empresa la fija el contexto y todo exige el módulo `gobierno`.
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
from app.modules.government import service_cargos
from app.modules.government.api import _version
from app.modules.government.schemas_cargos import (
    CargoCambio,
    CargoIn,
    CargoOut,
    CompetenciaCambio,
    CompetenciaIn,
    DesactivacionCargoIn,
    ListaCargos,
    RetiroCompetenciaIn,
    VersionesCargo,
)
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/estructuras", tags=["government"])

_ESCRITURA = [Depends(require_write_allowed)]


def _puede_publicar(db: Session, user: User) -> bool:
    """Indica si el usuario puede cambiar la autoridad de un cargo vigente (`gobierno_cargos:publish`)."""
    return identity_service.user_has_permission(
        user,
        identity_service.get_user_permissions(db, user),
        "gobierno_cargos",
        "publish",
    )


@router.get("/{ejercicio}/cargos", response_model=ListaCargos)
def list_cargos(
    ejercicio: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cargos", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_cargos.listar_cargos(db, ctx, ejercicio)


@router.post("/{ejercicio}/cargos", response_model=CargoOut, status_code=201, dependencies=_ESCRITURA)
def create_cargo(
    ejercicio: int,
    body: CargoIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cargos", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_cargos.crear_cargo(db, ctx, ejercicio, body)
    db.commit()
    return datos


@router.get("/{ejercicio}/cargos/exportar")
def export_cargos(
    ejercicio: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cargos", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    nombre, contenido = service_cargos.exportar_cargos_csv(db, ctx, ejercicio)
    db.commit()
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/{ejercicio}/cargos/{cargo_id}", response_model=CargoOut)
def get_cargo(
    ejercicio: int,
    cargo_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cargos", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_cargos.obtener_cargo(db, ctx, ejercicio, cargo_id)


@router.patch("/{ejercicio}/cargos/{cargo_id}", response_model=CargoOut, dependencies=_ESCRITURA)
def update_cargo(
    ejercicio: int,
    cargo_id: str,
    body: CargoCambio,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cargos", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_cargos.modificar_cargo(db, ctx, ejercicio, cargo_id, body, _version(if_match))
    db.commit()
    return datos


@router.delete("/{ejercicio}/cargos/{cargo_id}", status_code=204, dependencies=_ESCRITURA)
def delete_cargo(
    ejercicio: int,
    cargo_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cargos", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    service_cargos.eliminar_cargo(db, ctx, ejercicio, cargo_id, _version(if_match))
    db.commit()
    return Response(status_code=204)


@router.post("/{ejercicio}/cargos/{cargo_id}/activar", response_model=CargoOut, dependencies=_ESCRITURA)
def activate_cargo(
    ejercicio: int,
    cargo_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cargos", "publish")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_cargos.activar_cargo(db, ctx, ejercicio, cargo_id, _version(if_match))
    db.commit()
    return datos


@router.post("/{ejercicio}/cargos/{cargo_id}/desactivar", response_model=CargoOut, dependencies=_ESCRITURA)
def deactivate_cargo(
    ejercicio: int,
    cargo_id: str,
    body: DesactivacionCargoIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cargos", "publish")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_cargos.desactivar_cargo(db, ctx, ejercicio, cargo_id, body, _version(if_match))
    db.commit()
    return datos


@router.post("/{ejercicio}/cargos/{cargo_id}/competencias", response_model=CargoOut, status_code=201, dependencies=_ESCRITURA)
def create_competencia(
    ejercicio: int,
    cargo_id: str,
    body: CompetenciaIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_cargos", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_cargos.agregar_competencia(
        db, ctx, ejercicio, cargo_id, body, _version(if_match), _puede_publicar(db, user)
    )
    db.commit()
    return datos


@router.patch("/{ejercicio}/cargos/{cargo_id}/competencias/{competencia_id}", response_model=CargoOut, dependencies=_ESCRITURA)
def update_competencia(
    ejercicio: int,
    cargo_id: str,
    competencia_id: str,
    body: CompetenciaCambio,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_cargos", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_cargos.cambiar_competencia(
        db, ctx, ejercicio, cargo_id, competencia_id, body, _version(if_match), _puede_publicar(db, user)
    )
    db.commit()
    return datos


@router.post("/{ejercicio}/cargos/{cargo_id}/competencias/{competencia_id}/retirar", response_model=CargoOut, dependencies=_ESCRITURA)
def revoke_competencia(
    ejercicio: int,
    cargo_id: str,
    competencia_id: str,
    body: RetiroCompetenciaIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_cargos", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service_cargos.retirar_competencia(
        db, ctx, ejercicio, cargo_id, competencia_id, body, _version(if_match), _puede_publicar(db, user)
    )
    db.commit()
    return datos


@router.get("/{ejercicio}/cargos/{cargo_id}/versiones", response_model=VersionesCargo)
def get_cargo_versiones(
    ejercicio: int,
    cargo_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_cargos", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service_cargos.versiones_cargo(db, ctx, ejercicio, cargo_id)
