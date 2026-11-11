from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission
from app.modules.government.schemas_separacion import SeparacionOut
from app.modules.government.service_separacion import separacion
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/control", tags=["gobierno"])


@router.get("/separacion", response_model=SeparacionOut)
def get_separacion(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("gobierno_auditoria", "view")),
    ctx: CompanyContext = Depends(get_company_context),
    _modulo: None = Depends(require_module("gobierno")),
):
    return separacion(db, ctx)
