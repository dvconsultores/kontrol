"""API del ente de Gobierno (GOV-0-01).

La empresa del contexto es el contenedor del ente (OD-GOV0-03); todo `/ente*`
exige el módulo `gobierno` de la licencia (AD-GOV0-02).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import (
    get_current_user,
    require_module,
    require_permission,
    require_write_allowed,
)
from app.modules.government import service
from app.modules.government.schemas import EnteCambio, EnteIn, EnteOut, ModuloOut, VersionesOut
from app.modules.identity_access.models import User
from app.modules.licensing import service as licensing_service

router = APIRouter(prefix="/gobierno", tags=["government"])

#: Orden de las guardas: permiso → empresa (404 ajena, 403 solo en otra) → módulo de licencia;
#: el módulo es el último parámetro de cada ruta /ente* (FastAPI resuelve en orden).
_ESCRITURA = [Depends(require_write_allowed)]


def _version(if_match: str | None) -> int | None:
    limpio = (if_match or "").strip().strip('"')
    return int(limpio) if limpio.isdigit() else None


@router.get("/modulo", response_model=ModuloOut)
def get_modulo(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"habilitado": licensing_service.module_entitled(db, "gobierno")}


@router.get("/ente", response_model=EnteOut)
def get_ente(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ente", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service.obtener(db, ctx)


@router.post("/ente", response_model=EnteOut, status_code=201, dependencies=_ESCRITURA)
def create_ente(
    body: EnteIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ente", "create")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service.crear(db, ctx, body)
    db.commit()
    return datos


@router.patch("/ente", response_model=EnteOut, dependencies=_ESCRITURA)
def update_ente(
    body: EnteCambio,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ente", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service.modificar(db, ctx, body, _version(if_match))
    db.commit()
    return datos


@router.post("/ente/activar", response_model=EnteOut, dependencies=_ESCRITURA)
def activate_ente(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ente", "activate")),
    ctx: CompanyContext = Depends(get_company_context),
    if_match: str | None = Header(default=None, alias="If-Match"),
    _modulo: None = Depends(require_module("gobierno")),
):
    datos = service.activar(db, ctx, _version(if_match))
    db.commit()
    return datos


@router.get("/ente/versiones", response_model=VersionesOut)
def get_ente_versiones(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_ente", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return service.versiones(db, ctx)
