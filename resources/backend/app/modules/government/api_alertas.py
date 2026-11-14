from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission
from app.modules.government.schemas_alertas import AlertaOut, AlertasOut, RevisionAlertaIn
from app.modules.government.service_alertas import listar_alertas, revisar_alerta
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/control", tags=["gobierno"])


@router.get("/alertas", response_model=AlertasOut)
def get_alertas(
    tipo: str | None = Query(None),
    estado: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_alertas", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return listar_alertas(db, ctx, tipo=tipo, estado=estado, usuario_id=str(user.id))


@router.post("/alertas/revisiones", response_model=AlertaOut, status_code=201)
def post_revision(
    body: RevisionAlertaIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("gobierno_alertas", "review")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return revisar_alerta(
        db,
        ctx,
        usuario_id=str(user.id),
        clave=body.clave,
        resultado=body.resultado,
        observacion=body.observacion,
    )
