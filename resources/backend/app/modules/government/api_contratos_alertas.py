from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_contratos_alertas
from app.modules.government.schemas_contratos_alertas import PoliticasUpdate
from app.modules.identity_access.models import User

router = APIRouter(tags=["gobierno"])


@router.get("/gobierno/contratos/{contrato_id}/alertas")
def get_alertas(
    contrato_id: str,
    estado: Literal["ACTIVE", "RESOLVED", "ALL"] = "ACTIVE",
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_contratos_alertas.alertas_del_contrato(db, ctx, user, contrato_id, estado)


@router.get("/gobierno/contratos-alertas/politicas")
def get_politicas(
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_contratos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_contratos_alertas.politicas(db, ctx)


@router.put("/gobierno/contratos-alertas/politicas")
def put_politicas(
    cuerpo: PoliticasUpdate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("notificaciones", "configure")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    r = service_contratos_alertas.guardar_politicas(db, ctx, user, [i.model_dump() for i in cuerpo.items])
    db.commit()
    return r
