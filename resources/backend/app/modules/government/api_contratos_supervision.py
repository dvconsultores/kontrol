"""API de la supervisión del contrato (CNT-04, GOV-CNT-004)."""
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_contratos_supervision
from app.modules.government.schemas_contratos_supervision import DesignacionCreate
from app.modules.identity_access.models import User
from app.shared.clock import hoy_de_negocio

router = APIRouter(prefix="/gobierno/contratos/{contrato_id}/supervision", tags=["gobierno"])


@router.get("")
def get_supervision(
    contrato_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_contratos_supervision.supervision(db, ctx, contrato_id)


@router.get("/opciones")
def get_opciones(
    contrato_id: str,
    fecha: date | None = Query(default=None),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "assign_supervisor")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    fecha_efectiva = fecha or hoy_de_negocio()
    return service_contratos_supervision.opciones(db, ctx, contrato_id, fecha_efectiva)


@router.get("/en")
def get_supervisor_en(
    contrato_id: str,
    fecha: date = Query(...),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return {
        "fecha": fecha.isoformat(),
        "supervisor": service_contratos_supervision.supervisor_en(db, ctx, contrato_id, fecha),
    }


@router.post("/designaciones", status_code=status.HTTP_201_CREATED)
def post_designacion(
    contrato_id: str,
    cuerpo: DesignacionCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "assign_supervisor")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_supervision.designar(db, ctx, contrato_id, cuerpo.model_dump())
    db.commit()
    return resultado
